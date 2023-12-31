import time
import bs4
import requests

URL_LIST = "urls_to_be_named.txt"
URL_MAP = "urls_and_names.txt"

lines = None
with open(URL_LIST, "r") as file:
	lines = file.readlines()

for url in lines:
	title = ""
	try:
		page = requests.get(url, timeout=60)
		soup = bs4.BeautifulSoup(page.text, "html.parser")
		title = soup.find('title')
	except Exception as e:
		print(url, e)
	try:
		if "New\n          Session" in title.string:
			print("New Session: ", url)
	except Exception:
		print(title.string.split(" - ")[0])
	time.sleep(3)
	#with open(URL_MAP, "a+") as file:
	#	file.write(url + " ::: " + title.string)
