# save_to_wayback.py
# used 1/9/21
# used 12/20/21
# used DEC/13/22
# used APR/26/23

import logging
import sys
import time
from collections import deque
from typing import Callable, Sequence, Protocol
from urllib.parse import urljoin
from urllib3.exceptions import ProtocolError


import bs4
import requests
import savepagenow as save


NEW_URLS = "new_urls.txt"
SAVED_URLS = "saved.txt"
DEFAULT_DELAY = 30
TOOMANYREQUESTS_DELAY = 60 * 5 + 30
BLOCKED_BY_ROBOTS_DELAY = 120
SAVE = True

# TODO: Royal Road
# TODO: on repeated errors check if page has already been saved
# TODO: continue after laptop gets closed while running. may already work???

FF_URL  = "https://www.fanfiction.net/"
SB_URL  = "https://forums.spacebattles.com/"
SV_URL  = "https://forums.sufficientvelocity.com/"
QQ_URL  = "https://forum.questionablequesting.com/"
NH_URL  = "https://nhentai.net/g/"
IMH_URL = "https://imhentai.xxx/"
AO3_URL = "https://archiveofourown.org/"


# ffn now has NOARCHIVE and doesnt work
# nhentai has robots.txt tell wayback to not save

# fix redirects
# https://imhentai.xxx/view/723747/1/
# https://imhentai.xxx/view/930947/1/

# https://imhentai.xxx/gallery/764389/
# https://imhentai.xxx/gallery/905223/


class File(Protocol):
	def readlines(self) -> list[str]:
		...


def setup_logger(name: str, log_file: str, level: int=logging.INFO) -> logging.Logger:
	"""To setup as many loggers as you want"""

	handler = logging.FileHandler(log_file)

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.addHandler(handler)

	return logger


LOG_FILE = "urls_saved.log"
logger = setup_logger("first_logger", LOG_FILE)


class WebsiteLink:
	def __init__(self, url: str):
		self.url: str = url

	def get_next(self) -> str | None:
		return None

	def is_updatatable(self) -> bool:
		#not_updatable = [
		#	NH_URL,
		#	IMH_URL
		#]

		#for start in not_updatable:
		#	if url.startswith(start):
		#		return False
		return True
	
	def comp_format(self) -> str:
		return self.url.strip().strip("/")

	def __repr__(self):
		return f"Link({self.url})"
	

class AO3Link(WebsiteLink):
	def __init__(self, url: str):
		super().__init__(url)
		#self.prep_ao3_url()

	@staticmethod
	def ao3_btn(tag: bs4.element.Tag) -> bool:
		try:
			assert "a" == tag.name
			assert tag.text == "Next Chapter →"
			return True
		except AssertionError:
			return False

	def get_next(self) -> str:
		if self.url.endswith("view_full_work=true"):
			self.url = ""
			return self.url

		# if current version is normal, next is adult version
		# otherwise next is next chapter or empty string
		if not self.url.strip("/").endswith("?view_adult=true"):
			self.url = self.url.strip("/") + "?view_adult=true"
			return self.url

		page = requests.get(self.url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		btns = soup.find_all(self.ao3_btn)

		if btns:
			next_url = urljoin(AO3_URL, btns[0].attrs["href"])
			self.url = next_url.strip("#workskin")
			return self.url

		if "/chapters/" in self.url:
			base = self.url.split("/chapters/")[0]
			add_link(base + "?view_full_work=true")
			add_link(base + "?view_adult=true&view_full_work=true")
		
		self.url = ""
		return self.url
	
	def prep_ao3_url(self) -> None:
		if not self.url.startswith(AO3_URL):
			raise ValueError(f"Not AO3 url: {self.url}")

		if self.url.endswith("#workskin"):
			self.url = self.url[:-9]
		if not self.url.endswith("?view_adult=true"):
			self.url = self.url + "?view_adult=true"
		# if view adult is not added then the actual content of the chapter
		# is not saved. Saving both may be better, but only saving the
		# adult version seems to work. This is less helpful in non-adult
		# stories.
	
	def comp_format(self) -> str:
		return self.url.strip().strip("?view_adult=true").split("chapters")[0]

class FFLink(WebsiteLink):
	@staticmethod
	def ffn_btn(tag: bs4.element.Tag) -> bool:
		try:
			assert ["btn"] == tag["class"]
			assert tag.text == "Next >"
			return True
		except (KeyError, AssertionError):
			return False

	def is_updatatable(self) -> bool:
		return False  # not updatable because blocked

	def get_next(self) -> str:
		page = requests.get(self.url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		btns = soup.find_all(self.ffn_btn)
		try:
			assert btns[0]["onclick"] == btns[1]["onclick"]
		except IndexError:
			self.url = ""
			return self.url
		assert btns[0]["onclick"].startswith("self.location='")

		self.url = urljoin(FF_URL, btns[0]["onclick"][15:][:-1])
		return self.url

	def comp_format(self) -> str:
		# TODO: ff
		return super().comp_format()

class SBLink(WebsiteLink):
	@staticmethod
	def sb_btn(tag: bs4.element.Tag) -> bool:
		try:
			assert ["pageNav-jump", "pageNav-jump--next"] == tag["class"]
			assert tag.text == "Next"
			assert tag.name == "a"
			return True
		except (KeyError, AssertionError):
			return False

	def get_next(self) -> str:
		page = requests.get(self.url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		btns = soup.find_all(self.sb_btn)
		try:
			assert btns[0].attrs["href"] == btns[1].attrs["href"]
		except IndexError:
			self.url = ""
			return self.url

		self.url =  urljoin(SB_URL, btns[0].attrs["href"])
		return self.url
	
	def comp_format(self) -> str:
		return self.url.strip().split("/page-")[0].strip("/")

class SVLink(WebsiteLink):
	def get_next(self) -> str:
		page = requests.get(self.url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		btns = soup.find_all(SBLink.sb_btn)

		try:
			assert btns[0].attrs["href"] == btns[1].attrs["href"]
		except IndexError:
			self.url = ""
			return self.url

		self.url = urljoin(SV_URL, btns[0].attrs["href"])
		return self.url

	def comp_format(self) -> str:
		return self.url.strip().split("/page-")[0].strip("/")

class QQLink(WebsiteLink):
	@staticmethod
	def qq_btn(tag: bs4.element.Tag) -> bool:
		try:
			assert tag.name == "a"
			assert ["text"] == tag["class"]
			assert tag.text == "Next >"
			return True
		except (KeyError, AssertionError):
			return False

	def get_next(self) -> str:
		page = requests.get(self.url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		btns = soup.find_all(self.qq_btn)

		try:
			assert btns[0].attrs["href"] == btns[1].attrs["href"]
		except IndexError:
			self.url = ""
			return self.url

		self.url = urljoin(QQ_URL, btns[0].attrs["href"])
		return self.url

	def comp_format(self) -> str:
		return self.url.strip().split("/page-")[0].strip("/")

class NHLink(WebsiteLink):
	@staticmethod
	def check_nh(tag: bs4.element.Tag) -> bool:
		try:
			assert "404 – Not Found" in tag.text
			return True
		except AssertionError:
			return False
	
	def is_updatatable(self) -> bool:
		return False

	def get_next(self) -> str:
		url = self.url.strip("/") + "/"
		id_len = len(url[22:].split("/")[0])

		new_url = ""
		if url[22 + id_len + 1:].count("/") > 0:
			parts = url.split("/")
			parts[-2] = str(int(parts[-2]) + 1)
			new_url = "/".join(parts)
		else:
			new_url = url + "1"
		
		new_url = new_url.strip("/")

		page = requests.get(new_url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		if soup.find_all(self.check_nh):
			self.url = ""
			return self.url
		self.url = new_url
		return self.url
	
	def comp_format(self) -> str:
		return NH_URL + self.url.strip()[len(NH_URL):].split("/")[0]

class IMHLink(WebsiteLink):
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

	def is_updatatable(self) -> bool:
		return False

	@staticmethod
	def total_pages_imh(tag: bs4.element.Tag) -> bool:
		try:
			assert tag.name == "span"

			logger.debug(f"{tag['class'] = }")
			assert tag["class"] == ["total_pages"]
			return True
		except (AssertionError, KeyError):
			return False

	def get_next(self) -> str:
		logger.debug(f"Getting next imh style url from {self.url}")

		new_url = None
		url = self.url

		if not url.endswith("/"):
			url += "/"

		if "gallery" in url:
			new_url = url.replace("gallery", "view") + "1/"
		else:
			parts = url.split("/")
			parts[-2] = str(int(parts[-2]) + 1)
			new_url = "/".join(parts)

		page = requests.get(new_url, timeout=120)
		soup = bs4.BeautifulSoup(page.text, "html.parser")

		total_page_tag = soup.find(self.total_pages_imh)
		if total_page_tag is None:
			# should not write to saved file in this case
			# currently does
			append_update_extras(new_url)
			logger.error(f"new redirecting url: {new_url}")
			self.url = ""
			return self.url
		pages = int(total_page_tag.text)

		logger.debug(f"imh total page count is {pages}")

		if soup.find_all(self.make_imh_checker(pages)):
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

def make_link(url: str) -> WebsiteLink:
	if url.startswith(FF_URL):
		return FFLink(url)
	elif url.startswith(SB_URL):
		return SBLink(url)
	elif url.startswith(SV_URL):
		return SVLink(url)
	elif url.startswith(QQ_URL):
		return QQLink(url)
	elif url.startswith(NH_URL):
		return NHLink(url)
	elif url.startswith(IMH_URL):
		return IMHLink(url)
	elif url.startswith(AO3_URL):
		return AO3Link(url)
	else:
		return WebsiteLink(url)

def pick_url_to_save(link: WebsiteLink, url_original: str) -> str:
	if link.is_updatatable():
		return link.url
	else:
		return url_original.strip()

def attempt_get_next(link: WebsiteLink) -> WebsiteLink:
	for i in range(10):  # try 10 times
		try:
			link.get_next()
			return link
		except requests.exceptions.ConnectionError as exc:
			logger.error(f"Error {i+1} getting: {link.url}, {exc}")
			time.sleep(1)
	return WebsiteLink("")

def add_link(url_original: str) -> str | None:
	last_url = None

	url = url_original.strip()
	link = make_link(url)

	while link.url:
		errors = 0
		while True:
			try:
				print("Start Saving")
				logger.info("Start Saving")
				save.capture(
					link.url,
					user_agent="mr.awesome10000@gmail.com using savepagenow",
					accept_cache=True
				)

				print("Saved: ", link)
				time.sleep(DEFAULT_DELAY)

				logging.info(f"Saved: {link}")
				break
			except save.BlockedByRobots as exc:
				logging.critical(f"Error{errors} Skipping blocked by robots: {link}, {exc}")
				# should not save in this case

				time.sleep(BLOCKED_BY_ROBOTS_DELAY)

				break
			except Exception as exc:
				errors += 1
				logger.error(f"Error{errors}: {link}, {exc}")
				time.sleep(TOOMANYREQUESTS_DELAY)

		#if link.is_updatatable():
		#	last_url = url
		#else:
		#	last_url = url_original.strip()
		last_url = pick_url_to_save(link, url_original)

		link = attempt_get_next(link)

	return last_url

def read_saved(file: File | None = None) -> list[str]:
	if not hasattr(read_saved, "lines"):
		if file is None:
			with open(SAVED_URLS, "r") as save_file:
				lines = list(line.strip() for line in save_file.readlines())
		else:
			lines = list(line.strip() for line in file.readlines())
		read_saved.lines = lines
	return read_saved.lines

def write_saved(lines: Sequence[str], filename: str) -> None:
	with open(filename, "w") as save_file:
		save_file.write("\n".join(lines))

def append_update_extras(url: str, filename: str="update_extras.txt") -> None:
	with open(filename, "a") as file:
		file.write(url + "\n")

def is_saved(url: str, lines: Sequence[str] | None = None) -> bool:
	if lines is None:
		lines = read_saved()
	formatted = comp_format(url)
	if url in lines or formatted in lines:
		return True

	# TODO: caching
	cutoff_page = [comp_format(line) for line in lines]

	if formatted in cutoff_page:
		return True
	return False


def update_old(lines: list[str]) -> None:
	for index, preurl in enumerate(list(lines)):
		url = preurl.strip()
		if not make_link(url).is_updatatable():
			continue
		last = add_link(url)
		if not last:
			continue
		lines[index] = last
		if SAVE:
			write_saved(lines, SAVED_URLS)
			logger.info("Saving")


def save_url_list(urls: list[str], lines: list[str], save_to_new: bool) -> None:
	url_queue: deque[str] = deque()
	url_queue.extend(url.strip() for url in urls)
	for url in urls:
		if is_saved(url):
			url_queue.popleft()
			continue
		last = save_format(add_link(url))
		if last:
			lines.append(last)
			logger.debug(f"appending {last} to lines")
		url_queue.popleft()
		if SAVE:
			write_saved(lines, SAVED_URLS)
			if save_to_new:
				write_saved(url_queue, NEW_URLS)
			logger.info("Saving")


def comp_format(url: str) -> str:
	return make_link(url).comp_format()


def save_format(url: str | None) -> str | None:
	"""Format the url to be saved in the save file"""
	if not url:
		return url

	url = url.strip("/")
	if url.startswith(IMH_URL):
		if "view" in url:
			url = url.replace("view", "gallery")
			url = url.rsplit("/", 1)[0]
		return url
	return url.strip("?view_adult=true")


HELP = """Usage: python3 savetowayback.py [-uf] [URLS]...
	Save webpages to the wayback machine.

	URLS should be a space separated list of webpages to save to the wayback machine

	Options:
	  -u        save new content on any old webpages
	  -f        look in "new_urls.txt" for a list of urls to save
"""

def main() -> None:
	lines = read_saved()

	if "--help" in sys.argv:
		print(HELP)
		return

	try:
		given = sys.argv[1:]
		todo_file = NEW_URLS
		save_file = SAVED_URLS

		if "-u" in sys.argv:
			update_old(lines)
			given.remove("-u")

		if "-f" in sys.argv:
			given.remove("-f")
			with open(NEW_URLS, "r") as file:
				urls = file.readlines()
			save_url_list(urls, lines, save_to_new=True)

		save_url_list(given, lines, save_to_new=False)

		lines = list(set(lines))
	except BaseException as exc:
		if isinstance(exc, KeyboardInterrupt):
			log_message = "KeyboardInterrupt"
		else:
			todo_file = "urls_unfinished.txt"
			save_file = "save_dump.txt"
			log_message = "Uncaught Fatal Exception"

		logger.critical(log_message)

		raise
	finally:
		logger.info("Stopping")



if __name__ == "__main__":
	logging.info("Starting")
	main()

