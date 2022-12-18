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
import bs4
import requests
import savepagenow as save


new_urls = "new_urls.txt"
INCREMENT = 60
SAVE = False

# ao3


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


log_file = "urls_saved.log"
logger = setup_logger("first_logger", log_file, logging.DEBUG)


def prep_ao3_url(url):
	if not url.startswith("https://archiveofourown.org/"):
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


def ao3_btn(tag):
	try:
		assert "a" == tag.name
		assert tag.text == "Next Chapter →"
		return True
	except AssertionError:
		return False
	

def get_ao3(url):
	page = requests.get(url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(ao3_btn)
	
	if btns:
		next_url = urljoin("https://archiveofourown.org/", btns[0].attrs["href"])
		return prep_ao3_url(next_url)
	return None
	

def ffn_btn(tag):
	try:
		assert ["btn"] == tag["class"]
		assert tag.text == "Next >"
		return True
	except (KeyError, AssertionError):
		return False

def get_ffn(url):
	page = requests.get(url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(ffn_btn)
	try:
		assert btns[0]["onclick"] == btns[1]["onclick"]
	except IndexError:
		return None
	assert btns[0]["onclick"].startswith("self.location='")

	return urljoin("https://www.fanfiction.net/", btns[0]["onclick"][15:][:-1])


def sb_btn(tag):
	try:
		assert ["pageNav-jump", "pageNav-jump--next"] == tag["class"]
		assert tag.text == "Next"
		assert tag.name == "a"
		return True
	except (KeyError, AssertionError):
		return False

def get_sb(url):
	page = requests.get(url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(sb_btn)

	try:
		assert btns[0].attrs["href"] == btns[1].attrs["href"]
	except IndexError:
		return None

	return urljoin("https://forums.spacebattles.com/", btns[0].attrs["href"])

def get_sv(url):
	page = requests.get(url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(sb_btn)

	try:
		assert btns[0].attrs["href"] == btns[1].attrs["href"]
	except IndexError:
		return None

	return urljoin("https://forums.sufficientvelocity.com/", btns[0].attrs["href"])


def qq_btn(tag):
	try:
		assert tag.name == "a"
		assert ["text"] == tag["class"]
		assert tag.text == "Next >"
		return True
	except (KeyError, AssertionError):
		return False

def get_qq(url):
	page = requests.get(url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	btns = soup.find_all(qq_btn)

	try:
		assert btns[0].attrs["href"] == btns[1].attrs["href"]
	except IndexError:
		return None

	return urljoin("https://forum.questionablequesting.com/", btns[0].attrs["href"])


def check_nh(tag):
	try:
		assert "404 – Not Found" in tag.text
		return True
	except AssertionError:
		return False

def get_nh(url):
	id_len = len(url[22:].split("/")[0])

	new_url = None
	if url[22 + id_len + 1:].count("/") > 0:
		parts = url.split("/")
		parts[-2] = str(int(parts[-2]) + 1)
		new_url = "/".join(parts)
	else:
		new_url = url + "1/"
	
	page = requests.get(new_url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	if soup.find_all(check_nh):
		return None
	return new_url


def make_imh_checker(pages):
	def check_imh(tag):
		try:
			assert tag.name == "span"
			assert tag["class"] == ["current"]
			assert int(tag.text) > pages
			
			return True
		except (AssertionError, KeyError):
			return False
	return check_imh

def total_pages_imh(tag):
	try:
		assert tag.name == "span"
		
		logger.debug(f"{tag['class'] = }")
		assert tag["class"] == ["total_pages"]
		return True
	except (AssertionError, KeyError):
		return False

def get_imh(url):
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
	
	page = requests.get(new_url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	
	total_page_tag = soup.find(total_pages_imh)
	if total_page_tag is None:
		append_update_extras(new_url)
		logger.error(f"new redirecting url: {new_url}")
		return None
	pages = int(total_page_tag.text)
	
	logger.debug(f"imh total page count is {pages}")
	
	if soup.find_all(make_imh_checker(pages)):
		return None
	return new_url


def add_link(url_original):
	last_url = None
	
	url = url_original.strip()
	if url.startswith("https://archiveofourown.org/"):
		url = prep_ao3_url(url)

	while url:
		delay = 0
		errors = 0
		while True:
			try:
				save.capture(
					url,
					user_agent="mr.awesome10000@gmail.com using savepagenow",
					accept_cache=True
				)

				time.sleep(30)
				print(f"Saved: {url}")
				
				logging.info(f"Saved: {url}")
				delay = 60
				break
			except save.BlockedByRobots as e:
				logging.critical(f"Error{errors} Skipping blocked by robots: {url}, {e}")

				delay = 60
				time.sleep(120)

				break
			except Exception as e:
				errors += 1
				logger.error(f"Error{errors}: {url}, {e}")
				delay += INCREMENT
				time.sleep(delay)

		if is_updatatable(url):
			last_url = url
		else:
			last_url = url_original.strip()

		if url.startswith("https://www.fanfiction.net/"):
			url = get_ffn(url)
		elif url.startswith("https://forums.spacebattles.com/"):
			url = get_sb(url)
		elif url.startswith("https://forums.sufficientvelocity.com/"):
			url = get_sv(url)
		elif url.startswith("https://forum.questionablequesting.com/"):
			url = get_qq(url)
		elif url.startswith("https://nhentai.net/g/"):
			url = get_nh(url)
		elif url.startswith("https://imhentai.xxx/"):
			url = get_imh(url)
		elif url.startswith("https://archiveofourown.org/"):
			url = get_ao3(url)
		else:
			url = None

	return last_url

def save_url_list(urls, lines):
	url_queue = deque(urls)
	for url in urls:
		if is_saved(url):
			continue
		last = add_link(url)
		if last:
			lines.append(last)
		url_queue.popleft()
	
	return lines, url_queue


def read_saved():
	if not hasattr(read_saved, "lines"):
		with open("saved.txt", "r") as save_file:
			lines = list(line.strip() for line in save_file.readlines())
		read_saved.lines = lines
	return read_saved.lines

def write_saved(lines, filename):
	with open(filename, "w") as save_file:
		save_file.write("\n".join(lines))

def append_update_extras(url):
	with open("update_extras.txt", "a") as file:
		file.write(url + "\n")

def accumulator_factory_startswith(url):
	def accumulator(boolean, start):
		return boolean or url.startswith(start)
	return accumulator

def is_updatatable(url):
	"Or all possible failure conditions then invert the result"
	
	not_updatable = [
		"https://nhentai.net/g/",
		"https://imhentai.xxx/"
	]
	
	return not reduce(accumulator_factory_startswith(url), not_updatable)

def is_saved(url):
	lines = read_saved()
	if url in lines:
		return True
	
	cutoff_page = [line.rsplit("/", 1)[0] for line in lines]
	if url in cutoff_page:
		return True
	if url.rsplit("/", 1)[0] in cutoff_page:
		return True
	
	return False
	

def update_old(lines):
	for index, preurl in enumerate(list(lines)):
		url = preurl.strip()
		if is_updatatable(url):
			last = add_link(url)
			if last:
				lines[index] = last



def save_url_list(urls, lines, url_queue):
	url_queue.extend(url.strip() for url in urls)
	for url in urls:
		if is_saved(url):
			continue
		last = add_link(url)
		if last:
			lines.append(last)
			logger.debug(f"appending {last} to lines")
		url_queue.popleft()



help = """Usage: python3 savetowayback.py [-uf] [URLS]...
	Save webpages to the wayback machine.
	
	URLS should be a space separated list of webpages to save to the wayback machine

	Options:
	  -u        save new content on any old webpages
	  -f        look in "new_urls.txt" for a list of urls to save
"""

def main():
	lines = read_saved()
	
	if "--help" in sys.argv:
		print(help)
		return

	
	try:
		given = sys.argv[1:]
		todo_file = new_urls
		save_file = "saved.txt"
		
		
		if "-u" in sys.argv:
			update_old(lines)
			given.remove("-u")
		
		url_queue = deque()
		if "-f" in sys.argv:
			given.remove("-f")
			with open(new_urls, "r") as file:
				urls = file.readlines()
			save_url_list(urls, lines, url_queue)
		
		save_url_list(given, lines, url_queue)

		lines = list(set(lines))
	except BaseException as e:
		if isinstance(e, KeyboardInterrupt):
			log_message = "KeyboardInterrupt"
		else:
			todo_file = "urls_unfinished.txt"
			save_file = "save_dump.txt"
			log_message = "Uncaught Fatal Exception"
		
		logger.critical(log_message)
		
		raise
	finally:
		if SAVE:
			write_saved(lines, save_file)
			write_saved(url_queue, todo_file)
		
		logger.info("Stopping")



if __name__ == "__main__":
	#time.sleep(1)
	
	logging.info("Starting")

	main()

