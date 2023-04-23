# save_to_wayback.py
# used 1/9/21
# used 12/20/21
# used DEC/13/22

import sys
import time
from functools import reduce
from collections import deque
import logging
from urllib.parse import urljoin
from urllib3.exceptions import ProtocolError
from typing import Callable, Sequence

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

FF_URL  = "https://www.fanfiction.net/"
SB_URL  = "https://forums.spacebattles.com/"
SV_URL  = "https://forums.sufficientvelocity.com/"
QQ_URL  = "https://forum.questionablequesting.com/"
NH_URL  = "https://nhentai.net/g/"
IMH_URL = "https://imhentai.xxx/"
AO3_URL = "https://archiveofourown.org/"


# ffn now has NOARCHIVE and doesnt work

# fix redirects
# https://imhentai.xxx/view/723747/1/
# https://imhentai.xxx/view/930947/1/

# https://imhentai.xxx/gallery/764389/
# https://imhentai.xxx/gallery/905223/

def setup_logger(name, log_file, level=logging.INFO):
	"""To setup as many loggers as you want"""

	handler = logging.FileHandler(log_file)

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.addHandler(handler)

	return logger


LOG_FILE = "urls_saved.log"
logger = setup_logger("first_logger", LOG_FILE)


def prep_ao3_url(url: str) -> str:
	if not url.startswith(AO3_URL):
		raise ValueError(f"Not AO3 url: {url}")

	if url.endswith("#workskin"):
		url = url[:-9]
	if not url.endswith("?view_adult=true"):
		url = url + "?view_adult=true"
	# if view adult is not added then the actual content of the chapter
	# is not saved. Saving both may be better, but only saving the
	# adult version seems to work. This is less helpful in non-adult
	# stories.
	
	return url


def ao3_btn(tag: bs4.element.Tag) -> bool:
	try:
		assert "a" == tag.name
		assert tag.text == "Next Chapter →"
		return True
	except AssertionError:
		return False

def get_ao3(url: str) -> str | None:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(ao3_btn)

	if btns:
		next_url = urljoin(AO3_URL, btns[0].attrs["href"])
		return prep_ao3_url(next_url)
	return None
	

def ffn_btn(tag: bs4.element.Tag) -> bool:
	try:
		assert ["btn"] == tag["class"]
		assert tag.text == "Next >"
		return True
	except (KeyError, AssertionError):
		return False

def get_ffn(url: str) -> str | None:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(ffn_btn)
	try:
		assert btns[0]["onclick"] == btns[1]["onclick"]
	except IndexError:
		return None
	assert btns[0]["onclick"].startswith("self.location='")

	return urljoin(FF_URL, btns[0]["onclick"][15:][:-1])


def sb_btn(tag: bs4.element.Tag) -> bool:
	try:
		assert ["pageNav-jump", "pageNav-jump--next"] == tag["class"]
		assert tag.text == "Next"
		assert tag.name == "a"
		return True
	except (KeyError, AssertionError):
		return False

def get_sb(url: str) -> str | None:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(sb_btn)

	try:
		assert btns[0].attrs["href"] == btns[1].attrs["href"]
	except IndexError:
		return None

	return urljoin(SB_URL, btns[0].attrs["href"])

def get_sv(url: str) -> str | None:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(sb_btn)

	try:
		assert btns[0].attrs["href"] == btns[1].attrs["href"]
	except IndexError:
		return None

	return urljoin(SV_URL, btns[0].attrs["href"])


def qq_btn(tag: bs4.element.Tag) -> bool:
	try:
		assert tag.name == "a"
		assert ["text"] == tag["class"]
		assert tag.text == "Next >"
		return True
	except (KeyError, AssertionError):
		return False

def get_qq(url: str) -> str | None:
	page = requests.get(url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(qq_btn)

	try:
		assert btns[0].attrs["href"] == btns[1].attrs["href"]
	except IndexError:
		return None

	return urljoin(QQ_URL, btns[0].attrs["href"])


def check_nh(tag: bs4.element.Tag) -> bool:
	try:
		assert "404 – Not Found" in tag.text
		return True
	except AssertionError:
		return False

def get_nh(url: str) -> str | None:
	id_len = len(url[22:].split("/")[0])

	new_url = None
	if url[22 + id_len + 1:].count("/") > 0:
		parts = url.split("/")
		parts[-2] = str(int(parts[-2]) + 1)
		new_url = "/".join(parts)
	else:
		new_url = url + "1/"

	page = requests.get(new_url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	if soup.find_all(check_nh):
		return None
	return new_url


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

def total_pages_imh(tag: bs4.element.Tag) -> bool:
	try:
		assert tag.name == "span"

		logger.debug(f"{tag['class'] = }")
		assert tag["class"] == ["total_pages"]
		return True
	except (AssertionError, KeyError):
		return False

def get_imh(url: str) -> str | None:
	logger.debug(f"Getting next imh style url from {url}")

	new_url = None

	if not url.endswith("/"):
		url += "/"

	if "gallery" in url:
		new_url = url.replace("gallery", "view") + "1/"
	else:
		parts = url.split("/")
		parts[-2] = str(int(parts[-2]) + 1)
		new_url = "/".join(parts)

	page = requests.get(new_url, timeout=60)
	soup = bs4.BeautifulSoup(page.text, "html.parser")

	total_page_tag = soup.find(total_pages_imh)
	if total_page_tag is None:
		# should not write to saved file in this case
		# currently does
		append_update_extras(new_url)
		logger.error(f"new redirecting url: {new_url}")
		return None
	pages = int(total_page_tag.text)

	logger.debug(f"imh total page count is {pages}")

	if soup.find_all(make_imh_checker(pages)):
		return None
	return new_url


def add_link(url_original: str) -> str | None:
	last_url = None

	url = url_original.strip()
	if url.startswith(AO3_URL):
		url = prep_ao3_url(url)

	while url:

		errors = 0
		while True:
			try:
				save.capture(
					url,
					user_agent="mr.awesome10000@gmail.com using savepagenow",
					accept_cache=True
				)

				print(f"Saved: {url}")
				time.sleep(DEFAULT_DELAY)

				logging.info(f"Saved: {url}")
				break
			except save.BlockedByRobots as exc:
				logging.critical(f"Error{errors} Skipping blocked by robots: {url}, {exc}")
				# should not save in this case

				time.sleep(BLOCKED_BY_ROBOTS_DELAY)

				break
			except Exception as exc:
				errors += 1
				logger.error(f"Error{errors}: {url}, {exc}")
				time.sleep(TOOMANYREQUESTS_DELAY)

		if is_updatatable(url):
			last_url = url
		else:
			last_url = url_original.strip()

		if url.startswith(FF_URL):
			url = get_ffn(url)
		elif url.startswith(SB_URL):
			url = get_sb(url)
		elif url.startswith(SV_URL):
			url = get_sv(url)
		elif url.startswith(QQ_URL):
			url = get_qq(url)
		elif url.startswith(NH_URL):
			url = get_nh(url)
		elif url.startswith(IMH_URL):
			url = get_imh(url)
		elif url.startswith(AO3_URL):
			url = get_ao3(url)
		else:
			url = None

	return last_url


def read_saved() -> list[str]:
	if not hasattr(read_saved, "lines"):
		with open(SAVED_URLS, "r") as save_file:
			lines = list(line.strip() for line in save_file.readlines())
		read_saved.lines = lines
	return read_saved.lines

def write_saved(lines: Sequence[str], filename: str) -> None:
	with open(filename, "w") as save_file:
		save_file.write("\n".join(lines))

def append_update_extras(url: str) -> None:
	with open("update_extras.txt", "a") as file:
		file.write(url + "\n")

def accumulator_factory_startswith(url: str) -> Callable[[bool, str], bool]:
	def accumulator(boolean: bool, start: str) -> bool:
		return boolean or url.startswith(start)
	return accumulator

def is_updatatable(url: str) -> bool:
	"Or all possible failure conditions then invert the result"

	not_updatable = [
		NH_URL,
		IMH_URL
	]

	return not reduce(accumulator_factory_startswith(url), not_updatable)

def is_saved(url: str) -> bool:
	lines = read_saved()
	formatted = save_format(url)
	if url in lines or formatted in lines:
		return True
	
	# TODO: caching
	cutoff_page = []
	for line in lines:
		if line.startswith(SB_URL) or line.startswith(SV_URL) or line.startswith(QQ_URL):
			cutoff_page.append(line.split("/page-")[0])
		elif line.startswith(NH_URL):
			cutoff_page.append(NH_URL + "g/" + line[len(NH_URL + "g/"):].split("/")[0])
		elif line.startswith(IMH_URL):
			new_line = line.strip("/")
			if "view" in url:
				new_line = new_line.replace("view", "gallery")
				new_line = new_line.rsplit("/")[0]
			cutoff_page.append(new_line)
		else:  # TODO: ao3  
			cutoff_page.append(line.strip("/"))
	
	if formatted in cutoff_page:
		return True

	#cutoff_page = [line.rsplit("/", 1)[0] for line in lines]
	#if url in cutoff_page:
	#	return True
	#if url.rsplit("/", 1)[0] in cutoff_page:
	#	return True

	return False


def update_old(lines: list[str]) -> None:
	for index, preurl in enumerate(list(lines)):
		url = preurl.strip()
		if is_updatatable(url):
			last = add_link(url)
			if last:
				lines[index] = last


def save_url_list(urls: list[str], lines: list[str], url_queue: deque) -> None:
	url_queue.extend(url.strip() for url in urls)
	for url in urls:
		if is_saved(url):
			continue
		last = save_format(add_link(url))
		if last:
			lines.append(last)
			logger.debug(f"appending {last} to lines")
		url_queue.popleft()
		if SAVE:
			write_saved(lines, SAVED_URLS)
			write_saved(url_queue, NEW_URLS)
			logger.info("Saving")


def save_format(url: str | None) -> str | None:
	"""Format the url to be saved in the save file"""
	if not url:
		return url

	url = url.strip("/")
	if url.startswith(IMH_URL):
		if "view" in url:
			url = url.replace("view", "gallery")
			url = url.rsplit("/")[0]
		return url
	return url
	

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

		url_queue = deque()
		if "-f" in sys.argv:
			given.remove("-f")
			with open(NEW_URLS, "r") as file:
				urls = file.readlines()
			save_url_list(urls, lines, url_queue)

		save_url_list(given, lines, url_queue)

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
	#time.sleep(1)
	
	logging.info("Starting")

	main()

