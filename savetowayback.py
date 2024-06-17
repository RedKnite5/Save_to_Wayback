# save_to_wayback.py
# used 1/9/21
# used 12/20/21
# used DEC/13/22
# used APR/26/23
# used DEC/19/23
# used MAY/5/24 -u 954
# used JUN/16/24 -u 1135

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from functools import partial
import json
import logging
import logging.config
from os import getenv
from os import path
import signal
import sys
import time
from types import FrameType, TracebackType
from typing import Any, NoReturn, overload, override, TypeVar
from urllib.parse import urljoin

import bs4
from dotenv import load_dotenv
import requests
import requests.exceptions as req_excepts
import savepagenow as save
from savepagenow import exceptions as SPN_exceptions

from constants import *

# TODO: on repeated errors check if page has already been saved
# TODO: ff comp_format

# ffn now has NOARCHIVE and doesnt work
# NH has robots.txt tell wayback to not save

# added /home/veronica/miniconda3/envs/savetowayback/lib/python3.12/site-packages/savepagenow/py.typed
# should remove when savepagenow gets its own

DATA_FOLDER	= "data"
NEW_URLS = path.join(DATA_FOLDER, "new_urls.txt")
SAVED_URLS = path.join(DATA_FOLDER, "saved.txt")
UPDATE_EXTRAS = path.join(DATA_FOLDER, "update_extras.txt")
DEFAULT_DELAY = 45
BLOCKED_BY_ROBOTS_DELAY = 120
SAVE = True

load_dotenv()
EMAIL = getenv("SAVEPAGENOW_EMAIL")

type TagIdentifier = Callable[[bs4.element.Tag], bool]
type _ArgsType = tuple[object, ...] | Mapping[str, object]

class ConnectionTimeoutError(RuntimeError):
	pass

class Timeout:
	def __init__(self, seconds: int = 1, error_message: str = "Timeout"):
		self.seconds = seconds
		self.error_message = error_message

	def handle_timeout(self, signum: int, frame: FrameType | None) -> NoReturn:
		raise ConnectionTimeoutError(self.error_message)

	def __enter__(self) -> None:
		signal.signal(signal.SIGALRM, self.handle_timeout)
		signal.alarm(self.seconds)

	def __exit__(self,
			type_: type[BaseException] | None,
			value: BaseException | None,
			traceback: TracebackType | None) -> None:
		signal.alarm(0)

open_utf8 = partial(open, encoding="utf-8")

class FlexibleLogger(logging.Logger):
	@override
	def _log(self,
			level: int,
			msg: object,
			args: _ArgsType,
			exc_info: ExceptionInfo = None,
			extra: Mapping[str, object] | None = None,
			stack_info: bool = False,
			stacklevel: int = 1,
			**kwargs: object) -> None:
		if extra is not None:
			extra = dict(extra)
			extra.update(kwargs)
		else:
			extra = kwargs

		super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


def setup_logging() -> logging.Logger:
	with open_utf8("logging_config.json") as file:
		config = json.load(file)
	logging.config.dictConfig(config)

	logging.setLoggerClass(FlexibleLogger)

	return logging.getLogger("savetowayback")

logger = setup_logging()

def cut_end(string: str, ending: str) -> str:
	if string.endswith(ending):
		return string[:-len(ending)]
	return string

def ensure_endswith(string: str, suffix: str) -> str:
	if not string.endswith(suffix):
		return string + suffix
	return string

T = TypeVar("T")  # change to 3.12 generic syntax when pylance supports it
D = TypeVar("D")
@overload         # dont use overloads when mypy supports defaults with generics
def getitem(l: Sequence[T], /, index: int) -> T | None: ...
@overload
def getitem(l: Sequence[T], /, index: int, default: D) -> T | D: ...

def getitem(l, /, index, default = None):
	return l[index] if -len(l) <= index < len(l) else default

def isdigit(s: Any, /) -> bool:
	try:
		int(s)
		return True
	except (ValueError, TypeError):
		return False

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

	def add(self, item: str, /) -> None:
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

	def add_last_to_saved(self, last: str) -> None:
		if not last:
			return
		self.add(last)
		logger.debug("appending {url} to lines", url=last)
		self.save()

	def try_update(self, url: str, index: int, first: bool) -> None:
		saver = LinkAdder(first=first)
		try:
			saver.add_link(url)
		finally:
			if saver.last_url:
				logger.info(f"Updated {index + 1}: {{url}}", url=saver.last_url)
				self.lines[index] = saver.last_url
				self.save()

	def update_old(self, start: int = 0) -> None:
		for index, preurl in enumerate(self.lines[start:], start):
			url = preurl.strip()
			if not make_link(url).is_updatatable:
				continue
			self.try_update(url, index, index == start)

class LinkAdder:
	def __init__(self, url: str = "", first: bool = False):
		self.last_url: str = ""
		if first:
			self.sleep_time = 0
		else:
			self.sleep_time = DEFAULT_DELAY

		if url:
			self.add_link(url)

	def add_link(self, url: str) -> str:
		logger.debug("add link {url}", url=url)
		self.last_url = ""

		link = make_link(url.strip())

		while link.url:
			self.save_url(link, url)
			link = link.attempt_get_next()

		return self.last_url

	def save_url(self, link: WebsiteLink, original_url: str) -> None:
		expected_errors = (
			ConnectionTimeoutError,
			SPN_exceptions.UnknownError,
			req_excepts.SSLError,   # maybe move this to a more specific location?
		)
		errors = 0
		while True:
			try:
				time.sleep(self.sleep_time)
				capture_with_logging(link)
				self.last_url = pick_url_to_save(link, original_url)
				self.sleep_time = DEFAULT_DELAY
				return
			except save.BlockedByRobots as exc:
				logger.error(
					f"Error {errors} Skipping blocked by robots: {{url}}",
					exc_info=exc,
					url=link
				)
				# should not save in this case
				self.sleep_time = BLOCKED_BY_ROBOTS_DELAY
				return
			except SPN_exceptions.TooManyRequests as exc:
				errors += 1
				logger.warning(
					f"Error {errors}: {{url}}",
					exc_info=exc,
					url=link
				)

				if isinstance(link, IMHLink) and errors >= 2:
					new_url = link.new_url_with_redirect(link.url)
					link.url = new_url

				self.sleep_time = too_many_reqs_delay(errors)
			except expected_errors as exc:
				errors += 1
				logger.warning(
					f"Error {errors}: {{url}}",
					exc_info=exc,
					url=link
				)
				self.sleep_time = too_many_reqs_delay(errors)
			except Exception as exc:
				errors += 1
				logger.warning(
					f"Error Unknown {errors}: {{url}}",
					exc_info=exc,
					url=link
				)
				self.sleep_time = too_many_reqs_delay(errors)

def get_elements(url: str, func: TagIdentifier) -> list[bs4.element.Tag]:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	return soup.find_all(func)

class WebsiteLink:
	"""Base class for links to all websites"""
	URL_PRFIX: str = ""

	is_updatatable: bool = False

	def __init__(self, url: str):
		self.url: str = url

	def get_next(self) -> str | None:
		return None

	def comp_format(self) -> str:
		return self.url.strip(" /")

	def __str__(self) -> str:
		return self.url

	def __repr__(self) -> str:
		return f"Link(\"{self.url}\")"

	def attempt_get_next(self) -> WebsiteLink:
		catch_exceptions = (
			req_excepts.ConnectionError,
			req_excepts.ReadTimeout
		)
		for i in range(10):  # try 10 times
			try:
				self.get_next()
				return self
			except catch_exceptions as exc:
				logger.warning(
					f"Error {i+1} getting next: {{url}}",
					exc_info=exc,
					url=self.url
				)
				time.sleep(1)
		logger.error(
			"Error could not get next from: {url}. Skipping",
			url=self.url
		)
		return WebsiteLink("")

class XenForoLink(WebsiteLink):
	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if tag.get("class") != ["pageNav-jump", "pageNav-jump--next"]:
			return False
		if tag.text != "Next" or tag.name != "a":
			return False
		return True

	@override
	def get_next(self) -> str:
		btns = get_elements(self.url, self.check_btn)
		if (len(btns) < 2
			or btns[0].attrs.get("href") != btns[1].attrs.get("href")):

			self.url = ""
			return self.url

		self.url = urljoin(self.URL_PRFIX, btns[0].attrs["href"])
		return self.url

	@override
	def comp_format(self) -> str:
		return self.url.strip().split("/page-")[0].strip("/")

	is_updatatable = True

class SBLink(XenForoLink):
	URL_PRFIX = SB_URL

class SVLink(XenForoLink):
	URL_PRFIX = SV_URL

class QQLink(XenForoLink):
	URL_PRFIX = QQ_URL
	# TODO: check this is still correct given the recent QQ update
	@override
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

	@override
	def get_next(self) -> str:
		btns = get_elements(self.url, self.check_btn)
		if len(btns) < 2 or btns[0].get("onclick") != btns[1].get("onclick"):
			self.url = ""
			return self.url
		# assert btns[0]["onclick"].startswith("self.location='")

		url_end = btns[0]["onclick"][15:][:-1]  # TODO: name magic number 15
		if isinstance(url_end, str):
			self.url = urljoin(self.URL_PRFIX, url_end)
			return self.url

		self.url = ""  # should never get here
		return self.url

class NHLink(WebsiteLink):
	URL_PRFIX = NH_URL
	BASE_LENGTH = len(URL_PRFIX)
	@staticmethod
	def check_nh(tag: bs4.element.Tag) -> bool:
		if "404 – Not Found" in tag.text:
			return True
		return False

	def make_new_url(self, url: str) -> str:
		url = url.strip("/") + "/"
		url_ending = url[self.BASE_LENGTH:]
		id_len = len(url_ending.split("/")[0])

		new_url = ""
		if url[self.BASE_LENGTH + id_len + 1:].count("/") > 0:
			new_url = self.increment_page(url)
		else:
			new_url = url + "1"

		return new_url.strip("/")

	def increment_page(self, url: str) -> str:
		parts = url.split("/")
		page = int(parts[-2])
		parts[-2] = str(page + 1)
		return "/".join(parts)

	@override
	def get_next(self) -> str:
		new_url = self.make_new_url(self.url)

		if get_elements(self.url, self.check_nh):
			self.url = ""
			return self.url
		self.url = new_url
		return self.url

	@override
	def comp_format(self) -> str:
		url = self.url.strip()
		url_path = url[len(self.URL_PRFIX):]
		url_parts = url_path.split("/")
		return self.URL_PRFIX + url_parts[0]

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

	def gallery_to_view(self, url):
		return self.make_new_url(ensure_endswith(url, "/"))

	def make_new_url(self, url: str) -> str:
		if "gallery" in url:
			return url.replace("gallery", "view") + "1/"

		parts = url.split("/")
		parts[-2] = str(int(parts[-2]) + 1)
		return "/".join(parts)

	def new_url_with_redirect(self, url: str) -> str:
		old_url = url
		redirect = check_redirect(old_url)
		if redirect != "":
			old_url = self.URL_PRFIX[:-1] + redirect

		return self.gallery_to_view(old_url)

	def get_total_pages(self, url: str) -> tuple[int, bool]:
		page = requests.get(url, timeout=120)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		total_page_tag = soup.find(self.total_pages_imh)
		if total_page_tag is None:
			return 0, True

		pages = int(total_page_tag.text)
		is_last_page = bool(soup.find_all(self.make_imh_checker(pages)))
		return pages, is_last_page

	@override
	def get_next(self) -> str:
		logger.debug(
			"Getting next imh style url from {url}",
			url=self.url
		)

		new_url = self.new_url_with_redirect(self.url)

		pages, is_last_page = self.get_total_pages(new_url)

		if not pages:
			# should not write to saved file in this case
			append_update_extras(new_url)
			logger.error("new redirecting url: {url}", url=new_url)
			self.url = ""
			return self.url

		logger.debug(f"imh total page count is {pages}")

		if is_last_page:
			self.url = ""
			return self.url

		self.url = new_url
		return self.url

	@override
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
		LinkAdder(base + "?view_full_work=true")
		LinkAdder(base + "?view_adult=true&view_full_work=true")

	@override
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

	@override
	def comp_format(self) -> str:
		url = self.url.strip()
		url_base = cut_end(url, "?view_adult=true")
		return url_base.split("chapters")[0]

	is_updatatable = True

class RRLink(WebsiteLink):
	URL_PRFIX = RR_URL
	@staticmethod
	def check_btn(tag: bs4.element.Tag) -> bool:
		if tag.name == "a" and tag.text == "Next Chapter":
			return True
		return False

	@override
	def get_next(self) -> str:
		btns = get_elements(self.url, self.check_btn)
		if btns:
			self.url = urljoin(RR_URL, btns[0].attrs["href"])
			return self.url

		self.url = ""  # should never get here
		return self.url

	is_updatatable = True

def make_link(url: str) -> WebsiteLink:
	# could try to do something with __init_subclass__ here
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
	# TODO: in the case of redirection the original case should instead return
	# the base form of the link url
	if link.is_updatatable:
		return link.url
	#if link.can_redirect() and comp_format(link.url) != comp_format(url_original):
	#	logger.debug(f"record both {link.url} and {url_original}")
	#	return link.url, url_original
	return url_original.strip()

def check_redirect(url: str) -> str:
	try:
		r = requests.head(url, timeout=60)
	except req_excepts.Timeout:
		logger.warning(
			"redirection check on {url} timed out",
			url=url
		)
		return ""

	location = r.headers.get("location")
	if location is not None and location != url:
		logger.info(
			f"redirected from {{url}} to {location}",
			url=url
		)
		return location
	return ""

def capture_with_logging(link: WebsiteLink) -> None:
	logger.debug("Start Saving")
	with Timeout(seconds=300):
		save.capture(
			link.url,
			#user_agent=f"{EMAIL} using savepagenow Python",
			accept_cache=True,
			authenticate=True
		)
	logger.info("Saved: {url}", url=link)

def too_many_reqs_delay(errors: int) -> int:
	return int(min(60 * 2 * 2**errors, 4*60*60))

def write_saved(lines: Sequence[str], filename: str) -> None:
	with open_utf8(filename, "w") as save_file:
		save_file.write("\n".join(lines))

def append_update_extras(url: str, filename: str = UPDATE_EXTRAS) -> None:
	if not SAVE:
		return
	with open_utf8(filename, "a") as file:
		file.write(url + "\n")

def save_url_list(urls: Sequence[str], saved: Saved, save_to_new: bool) -> None:
	url_queue = deque(url.strip() for url in urls)
	saver = LinkAdder(first=True)
	for url in urls:
		url_queue.popleft()
		if saved.is_saved(url):
			logger.info("is saved, skipping: {url}", url=url)
			continue
		last = save_format(saver.add_link(url))
		saved.add_last_to_saved(last)
		if SAVE and save_to_new:
			write_saved(url_queue, NEW_URLS)

def comp_format(url: str) -> str:
	return make_link(url).comp_format()

def save_format(url: str) -> str:
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

HELP = f"""Usage: python3 savetowayback.py [-u [START]] [-f] [URLS]...
	Save webpages to the wayback machine.

	URLS should be a space separated list of webpages to save to the wayback machine

	Options:
	  -u START  save new content on any old webpages starting at line START, default 0
	  -f        look in "{NEW_URLS}" for a list of urls to save
"""

def parse_args_and_save(saved: Saved) -> None:
	given = sys.argv[1:]

	if "-u" in sys.argv:
		u_index = sys.argv.index("-u")
		if (start_str := getitem(sys.argv, u_index+1)) and isdigit(start_str):
			given.pop(u_index)
			start = int(start_str) - 1
		else:
			start = 0

		saved.update_old(start)
		given.remove("-u")

	if "-f" in sys.argv:
		given.remove("-f")
		with open_utf8(NEW_URLS, "r") as file:
			urls = file.readlines()
		save_url_list(urls, saved, save_to_new=True)

	save_url_list(given, saved, save_to_new=False)

def main() -> None:
	saved = Saved(SAVED_URLS)

	if "--help" in sys.argv:
		print(HELP)
		return

	try:
		parse_args_and_save(saved)
	except KeyboardInterrupt:
		logger.critical("Keyboard Interrupt")
		sys.exit()
	except Exception as exc:
		logger.critical(exc)
		logger.critical("Uncaught Fatal Exception")
		raise
	finally:
		logger.debug("Stopping")

if __name__ == "__main__":
	logger.info("Starting")
	main()
