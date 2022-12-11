#!/mnt/c/Users/RedKnite/AppData/Local/Programs/Python/Python38/python.exe
# save_to_wayback.py
# last used 1/9/21

import sys
import time
from urllib.parse import urljoin
from urllib3.exceptions import ProtocolError
import bs4
import requests
import savepagenow as save

def ffn_btn(tag):
	try:
		assert ["btn"] == tag["class"]
		assert tag.text == "Next >"
		return True
	except (KeyError, AssertionError) as e:
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
	except (KeyError, AssertionError) as e:
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
	except (KeyError, AssertionError) as e:
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
		assert tag.text == "404 – Not Found"
		assert tag.name == "h1"
		return True
	except AssertionError as e:
		return False


def get_nh(url):
	page = requests.get(url)
	soup = bs4.BeautifulSoup(page.text, "html.parser")
	if soup.find_all(check_nh):
		return None

	id_len = len(url[22:].split("/")[0])

	if url[22 + id_len + 1:].count("/") > 0:
		parts = url.split("/")
		parts[-2] = str(int(parts[-2]) + 1)
		new_url = "/".join(parts)
		return new_url
	else:
		return url + "1/"



def add_link(url):
	last_url = None
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
				print(f"Saved: {url}")
				time.sleep(30)
				delay = 50
				break
			except Exception as e:
				errors += 1
				print(f"Error{errors}: {url}, {type(e)}: {e}")
				delay += 650
				time.sleep(delay)

		last_url = url
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
		else:
			url = None
	
	return last_url


def read_saved():
	with open("saved.txt", "r") as save_file:
		lines = list(save_file.readlines())
	return lines

def write_saved(lines, filename="saved.txt"):
	with open(filename, "w") as save_file:
		save_file.write("\n".join(lines))


def is_updatatable(url):
	"Or all possible failure conditions then invert the result"

	not_up = False
	not_up = not_up or url.startswith("https://nhentai.net/g/")

	return not not_up

def update_old(lines):
	for index, preurl in enumerate(list(lines)):
		url = preurl.strip()
		if is_updatatable(url):
			last = add_link(url)
			if last:
				lines[index] = last


def main():
	
	lines = read_saved()
	lines = [line.strip() for line in lines]
	
	try:
		if "-u" in sys.argv:
			update_old(lines)
		
		if "-f" in sys.argv:
			with open("new_urls.txt", "r") as file:
				for url in file.readlines():
					last = add_link(url.strip())
					if last:
						lines.append(last)
		else:
			for url in sys.argv[1:]:
				last = add_link(url)
				if last:
					lines.append(last)

		lines = list(set(lines))
	except:
		write_saved(lines, filename="save_dump.txt")
	else:
		write_saved(lines)



if __name__ == "__main__":
	#time.sleep(1)

	main()


