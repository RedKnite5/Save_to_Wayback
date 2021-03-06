# save_to_wayback.py
# used 1/9/21
# last used 12/20/21

import sys
import time
import logging
from urllib.parse import urljoin
from urllib3.exceptions import ProtocolError
import bs4
import requests
import savepagenow as save

logging.basicConfig(filename='urls_saved.log', level=logging.INFO)

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
		assert "404 ??? Not Found" in tag.text
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
		
		logging.debug(f"{tag['class'] = }")
		assert tag["class"] == ["total_pages"]
		return True
	except (AssertionError, KeyError):
		return False

def get_imh(url):
	logging.debug(f"Getting next imh style url from {url}")
	
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
	pages = int(total_page_tag.text)
	
	logging.debug(f"imh total page count is {pages}")
	
	if soup.find_all(make_imh_checker(pages)):
		return None
	return new_url


def add_link(url):
	while url:
		delay = 50
		errors = 0
		while True:
			try:
				save.capture(
					url,
					user_agent="mr.awesome10000@gmail.com using savepagenow",
					accept_cache=True
				)
				logging.info(f"Saved: {url}")
				time.sleep(70)
				delay = 50
				break
			except save.BlockedByRobots as e:
				logging.critical(f"Error{errors} Skipping blocked by robots: {url}, {e}")
				delay = 50
				time.sleep(120)
				break
			except Exception as e:
				errors += 1
				logging.error(f"Error{errors}: {url}, {e}")
				delay += 650
				time.sleep(delay)

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
		else:
			url = None


if __name__ == "__main__":
	logging.info("Starting")
	
	try:
		for url in sys.argv[1:]:
			add_link(url)

		with open("url_list.txt", "r") as file:
			for url in file.readlines():
				add_link(url.strip())
	except:
		raise
	finally:
		logging.info("Stopping")



