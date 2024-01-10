# save_to_wayback.py
# used 1/9/21
# used 12/20/21
# used DEC/13/22
# used APR/26/23
# used DEC/19/23

from __future__ import annotations

import logging
import sys
import time
from collections import deque
from collections.abc import Callable, Sequence
from urllib.parse import urljoin
from functools import partial
import signal

import bs4
import requests
import savepagenow as save


NEW_URLS = "new_urls.txt"
SAVED_URLS = "saved.txt"
DEFAULT_DELAY = 30
BLOCKED_BY_ROBOTS_DELAY = 120
SAVE = True

# TODO: on repeated errors check if page has already been saved
# TODO: continue after laptop gets closed while running. may already work???
# TODO: ff comp_format

FF_URL  = "https://www.fanfiction.net/"
SB_URL  = "https://forums.spacebattles.com/"
SV_URL  = "https://forums.sufficientvelocity.com/"
QQ_URL  = "https://forum.questionablequesting.com/"
NH_URL  = "https://nhentai.net/g/"
IMH_URL = "https://imhentai.xxx/"
AO3_URL = "https://archiveofourown.org/"
RR_URL  = "https://www.royalroad.com/"


# ffn now has NOARCHIVE and doesnt work
# nhentai has robots.txt tell wayback to not save

# fix redirects
# https://imhentai.xxx/view/723747/1/
# https://imhentai.xxx/view/930947/1/

# https://imhentai.xxx/gallery/764389/
# https://imhentai.xxx/gallery/905223/

TagIdentifier = Callable[[bs4.element.Tag], bool]

class TimeoutError(RuntimeError):
	pass

class Timeout:
	def __init__(self, seconds=1, error_message='Timeout'):
		self.seconds = seconds
		self.error_message = error_message
	def handle_timeout(self, signum, frame):
		raise TimeoutError(self.error_message)
	def __enter__(self):
		signal.signal(signal.SIGALRM, self.handle_timeout)
		signal.alarm(self.seconds)
	def __exit__(self, type, value, traceback):
		signal.alarm(0)

open_utf8 = partial(open, encoding="utf-8")

def setup_loggers() -> logging.Logger:
	"""To setup as many loggers as you want"""

	log_file = "urls_saved.log"

	FORMAT = "%(asctime)s %(message)s"
	formatter = logging.Formatter(FORMAT)

	stderr_handler = logging.StreamHandler()
	file_handler = logging.FileHandler(log_file)

	stderr_handler.setFormatter(formatter)
	file_handler.setFormatter(formatter)

	stderr_log = logging.getLogger("stderr_logger")
	file_log = logging.getLogger("stderr_logger.file_logger")
	stderr_log.setLevel(logging.INFO)
	stderr_handler.setLevel(logging.INFO)
	file_log.setLevel(logging.DEBUG)
	file_handler.setLevel(logging.DEBUG)
	stderr_log.addHandler(stderr_handler)
	file_log.addHandler(file_handler)

	return file_log


logger = setup_loggers()

def cut_end(string: str, ending: str) -> str:
	if string.endswith(ending):
		return string[:-len(ending)]
	return string

def ensure_endswith(string: str, suffix: str) -> str:
	if not string.endswith(suffix):
		return string + suffix
	return string

class Saved:
	def __init__(self, file: str):
		self.filename = file
		self.lines: list[str] = self.read_saved()

	def read_saved(self) -> list[str]:
		with open_utf8(self.filename, "r") as save_file:
			return list(line.strip() for line in save_file.readlines())

	def is_saved(self, url: str) -> bool:
		formatted = comp_format(url)
		if url in self.lines or formatted in self.lines:
			return True

		# TODO: caching
		cutoff_page = [comp_format(line) for line in self.lines]

		if formatted in cutoff_page:
			return True
		return False

	def add(self, item: str) -> None:
		self.lines.append(item)

	def clear_dupes(self) -> None:
		seen: set[str] = set()
		seen_add = seen.add
		self.lines = [x for x in self.lines if not (x in seen or seen_add(x))]

	def save(self) -> None:
		if not SAVE:
			return
		self.clear_dupes()
		write_saved(self.lines, self.filename)
		logger.info("Recording")

	def add_last_to_saved(self, last: str | None) -> None:
		if not last:
			return
		self.add(last)
		logger.debug(f"appending {last} to lines")
		self.save()

	def update_old(self) -> None:
		for index, preurl in enumerate(self.lines):
			url = preurl.strip()
			if not make_link(url).is_updatatable():
				continue
			last = add_link(url)
			if not last:
				continue
			self.lines[index] = last
			self.save()

def get_elements(url: str, func: TagIdentifier) -> list[bs4.element.Tag]:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	return soup.find_all(func)

class WebsiteLink:
	"""Base class for links to all websites"""
	URL_PRFIX: str = ""

	def __init__(self, url: str):
		self.url: str = url

	def get_next(self) -> str | None:
		return None

	def is_updatatable(self) -> bool:
		return False

	def comp_format(self) -> str:
		return self.url.strip(" /")

	def __str__(self) -> str:
		return self.url

	def __repr__(self) -> str:
		return f"Link(\"{self.url}\")"

	def attempt_get_next(self) -> WebsiteLink:
		for i in range(10):  # try 10 times
			try:
				self.get_next()
				return self
			except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as exc:
				logger.warning(f"Error {i+1} getting next: {self.url}, {exc}")
				time.sleep(1)
		logger.error(f"Error could not get next from: {self.url}. Skipping")
		return WebsiteLink("")

class XenForoLink(WebsiteLink):
	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if tag.get("class") != ["pageNav-jump", "pageNav-jump--next"]:
			return False
		if tag.text != "Next" or tag.name != "a":
			return False
		return True

	def get_next(self) -> str:
		btns = get_elements(self.url, self.check_btn)
		if (len(btns) < 2
			or btns[0].attrs.get("href") != btns[1].attrs.get("href")):

			self.url = ""
			return self.url

		self.url = urljoin(self.URL_PRFIX, btns[0].attrs["href"])
		return self.url

	def comp_format(self) -> str:
		return self.url.strip().split("/page-")[0].strip("/")

	def is_updatatable(self) -> bool:
		return True

class SBLink(XenForoLink):
	URL_PRFIX = SB_URL

class SVLink(XenForoLink):
	URL_PRFIX = SV_URL

class QQLink(XenForoLink):
	URL_PRFIX = QQ_URL
	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if (tag.name == "a"
			and tag.get("class") == ["text"]
			and tag.text == "Next >"):
			return True
		return False

class FFLink(WebsiteLink):
	URL_PRFIX = FF_URL
	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if tag.get("class") == ["btn"] and tag.text == "Next >":
			return True
		return False

	def get_next(self) -> str:
		btns = get_elements(self.url, self.check_btn)
		if len(btns) < 2 or btns[0].get("onclick") != btns[1].get("onclick"):
			self.url = ""
			return self.url
		# assert btns[0]["onclick"].startswith("self.location='")

		url_end = btns[0]["onclick"][15:][:-1]
		if isinstance(url_end, str):
			self.url = urljoin(self.URL_PRFIX, url_end)
			return self.url

		self.url = ""  # should never get here
		return self.url

class NHLink(WebsiteLink):
	URL_PRFIX = NH_URL
	@staticmethod
	def check_nh(tag: bs4.element.Tag) -> bool:
		if "404 – Not Found" in tag.text:
			return True
		return False

	def make_new_url(self, url: str) -> str:
		url = url.strip("/") + "/"
		id_len = len(url[22:].split("/")[0])

		new_url = ""
		if url[22 + id_len + 1:].count("/") > 0:
			parts = url.split("/")
			parts[-2] = str(int(parts[-2]) + 1)
			new_url = "/".join(parts)
		else:
			new_url = url + "1"

		return new_url.strip("/")

	def get_next(self) -> str:
		new_url = self.make_new_url(self.url)

		if get_elements(self.url, self.check_nh):
			self.url = ""
			return self.url
		self.url = new_url
		return self.url

	def comp_format(self) -> str:
		return self.URL_PRFIX + self.url.strip()[len(self.URL_PRFIX):].split("/")[0]

class IMHLink(WebsiteLink):
	URL_PRFIX = IMH_URL
	@staticmethod
	def make_imh_checker(pages: int) -> Callable[[bs4.element.Tag], bool]:
		def check_imh(tag: bs4.element.Tag) -> bool:
			try:
				assert tag.name == "span"
				assert tag["class"] == ["current"]
				assert int(tag.text) > pages

				return True
			except (AssertionError, KeyError):
				return False
		return check_imh

	@staticmethod
	def total_pages_imh(tag: bs4.element.Tag) -> bool:
		try:
			assert tag.name == "span"

			logger.debug(f"{tag['class'] = }")
			assert tag["class"] == ["total_pages"]
			return True
		except (AssertionError, KeyError):
			return False

	def make_new_url(self, url: str) -> str:
		if "gallery" in url:
			return url.replace("gallery", "view") + "1/"

		parts = url.split("/")
		parts[-2] = str(int(parts[-2]) + 1)
		return "/".join(parts)

	def get_total_pages(self, url: str) -> tuple[int, bool]:
		page = requests.get(url, timeout=120)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		total_page_tag = soup.find(self.total_pages_imh)
		if total_page_tag is None:
			return 0, True

		pages = int(total_page_tag.text)
		is_last_page = bool(soup.find_all(self.make_imh_checker(pages)))
		return pages, is_last_page

	def get_next(self) -> str:
		logger.debug(f"Getting next imh style url from {self.url}")

		new_url = self.make_new_url(ensure_endswith(self.url, "/"))
		pages, is_last_page = self.get_total_pages(new_url)

		if not pages:
			# should not write to saved file in this case
			# currently does
			append_update_extras(new_url)
			logger.error(f"new redirecting url: {new_url}")
			self.url = ""
			return self.url

		logger.debug(f"imh total page count is {pages}")

		if is_last_page:
			self.url = ""
			return self.url

		self.url = new_url
		return self.url

	def comp_format(self) -> str:
		url = self.url.strip().strip("/")
		if "view" in url:
			url = url.replace("view", "gallery")
			url = url.rsplit("/", 1)[0]
		return url

class AO3Link(WebsiteLink):
	URL_PRFIX = AO3_URL

	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if tag.name == "a" and tag.text == "Next Chapter →":
			return True
		return False

	def save_full_work(self) -> None:
		if "/chapters/" not in self.url:
			return
		base = self.url.split("/chapters/")[0]
		add_link(base + "?view_full_work=true")
		add_link(base + "?view_adult=true&view_full_work=true")

	def get_next(self) -> str:
		if self.url.endswith("view_full_work=true"):
			self.url = ""
			return self.url

		# if view adult is not added then the actual content of the chapter
		# is not saved. Saving both may be better, but only saving the
		# adult version seems to work. This is less helpful in non-adult
		# stories.

		# if current version is normal, next is adult version
		# otherwise next is next chapter or empty string
		if not self.url.strip("/").endswith("?view_adult=true"):
			self.url = self.url.strip("/") + "?view_adult=true"
			return self.url

		btns = get_elements(self.url, self.check_btn)
		# may fail if work is restricted
		if btns:
			next_url = urljoin(AO3_URL, btns[0].attrs["href"])
			self.url = cut_end(next_url, "#workskin")
			return self.url

		self.save_full_work()

		self.url = ""
		return self.url

	def comp_format(self) -> str:
		return cut_end(self.url.strip(), "?view_adult=true").split("chapters")[0]

	def is_updatatable(self) -> bool:
		return True

class RRLink(WebsiteLink):
	URL_PRFIX = RR_URL
	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if tag.name == "a" and tag.text == "Next Chapter":
			return True
		return False

	def get_next(self) -> str:
		btns = get_elements(self.url, self.check_btn)
		if btns:
			self.url = urljoin(RR_URL, btns[0].attrs["href"])
			return self.url

		self.url = ""  # should never get here
		return self.url

	def is_updatatable(self) -> bool:
		return True

def make_link(url: str) -> WebsiteLink:
	link_classes = (
		FFLink,
		SBLink,
		SVLink,
		QQLink,
		NHLink,
		IMHLink,
		AO3Link,
		RRLink,
	)
	for link_class in link_classes:
		if url.startswith(link_class.URL_PRFIX):
			return link_class(url)
	return WebsiteLink(url)

def pick_url_to_save(link: WebsiteLink, url_original: str) -> str:
	if link.is_updatatable():
		return link.url
	return url_original.strip()

def capture_with_logging(link: WebsiteLink) -> None:
	logger.debug("Start Saving")
	with Timeout(seconds=300):
		save.capture(
			link.url,
			user_agent="mr.Awesome10000@gmail.com using savepagenow python",
			accept_cache=True
		)
	logger.info(f"Saved: {link}")

def too_many_reqs_delay(errors: int) -> int:
	return min(60 * 2 * 2**errors, 4*60*60)

def save_url(link: WebsiteLink) -> None:
	errors = 0
	while True:
		try:
			capture_with_logging(link)
			time.sleep(DEFAULT_DELAY)
			return
		except save.BlockedByRobots as exc:
			logger.error(f"Error {errors} Skipping blocked by robots: {link}, {exc}")
			# should not save in this case
			time.sleep(BLOCKED_BY_ROBOTS_DELAY)
			return
		except save.exceptions.TooManyRequests as exc:
			errors += 1
			logger.warning(f"Error {errors}: {link}, TooManyRequests: {exc}")
			time.sleep(too_many_reqs_delay(errors))
		except TimeoutError as exc:
			errors += 1
			logger.warning(f"Error {errors}: {link}, Timeout: {exc}")
			time.sleep(too_many_reqs_delay(errors))
		except Exception as exc:
			errors += 1
			logger.warning(f"Error {errors}: {link}, {type(exc)}: {exc}")
			time.sleep(too_many_reqs_delay(errors))

def add_link(url: str) -> str | None:
	logger.debug(f"add_link {url}")
	last_url = None

	link = make_link(url.strip())

	while link.url:
		save_url(link)
		last_url = pick_url_to_save(link, url)
		link = link.attempt_get_next()

	return last_url

def write_saved(lines: Sequence[str], filename: str) -> None:
	with open_utf8(filename, "w") as save_file:
		save_file.write("\n".join(lines))

def append_update_extras(url: str, filename: str="update_extras.txt") -> None:
	if not SAVE:
		return
	with open_utf8(filename, "a") as file:
		file.write(url + "\n")

def save_url_list(urls: Sequence[str], saved: Saved, save_to_new: bool) -> None:
	url_queue = deque(url.strip() for url in urls)
	for url in urls:
		url_queue.popleft()
		if saved.is_saved(url):
			logger.info(f"is saved, skipping: {url}")
			continue
		last = save_format(add_link(url))
		saved.add_last_to_saved(last)
		if SAVE and save_to_new:
			write_saved(url_queue, NEW_URLS)

def comp_format(url: str) -> str:
	return make_link(url).comp_format()

def save_format(url: str | None) -> str | None:
	"""Format the url to be saved in the save file"""

	# TODO: move to classes

	if not url:
		return url

	url = url.strip("/")
	if url.startswith(IMH_URL):
		if "view" in url:
			url = url.replace("view", "gallery")
			url = url.rsplit("/", 1)[0]
		return url
	return cut_end(url, "?view_adult=true")

HELP = """Usage: python3 savetowayback.py [-uf] [URLS]...
	Save webpages to the wayback machine.

	URLS should be a space separated list of webpages to save to the wayback machine

	Options:
	  -u        save new content on any old webpages
	  -f        look in "new_urls.txt" for a list of urls to save
"""

def parse_args_and_save(saved: Saved) -> None:
	given = sys.argv[1:]

	if "-u" in sys.argv:
		saved.update_old()
		given.remove("-u")

	if "-f" in sys.argv:
		given.remove("-f")
		with open_utf8(NEW_URLS, "r") as file:
			urls = file.readlines()
		save_url_list(urls, saved, save_to_new=True)

	save_url_list(given, saved, save_to_new=False)

def pick_exit_log_message(exc: BaseException) -> str:
	if isinstance(exc, KeyboardInterrupt):
		return "KeyboardInterrupt"
	logger.critical(exc)
	return "Uncaught Fatal Exception"

def main() -> None:
	saved = Saved(SAVED_URLS)

	if "--help" in sys.argv:
		print(HELP)
		return

	try:
		parse_args_and_save(saved)
	except BaseException as exc:
		log_message = pick_exit_log_message(exc)
		logger.critical(log_message)
		raise
	finally:
		logger.info("Stopping")


if __name__ == "__main__":
	logger.info("Starting")
	main()
