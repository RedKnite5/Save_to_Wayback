import logging


def dict_replace(string, dictionary):
	for find, replace in dictionary.items():
		string = string.replace(find, replace)
	return string

class STDOutFormatter(logging.Formatter):
	abvreviations = {
		"https://www.fanfiction.net/": "FF/",
		"https://forums.spacebattles.com/threads/": "SB/",
		"https://forums.sufficientvelocity.com/threads/": "SV/",
		"https://forum.questionablequesting.com/threads/": "QQ/",
		"https://nhentai.net/g/": "NH/",
		"https://imhentai.xxx/gallery/": "IMH/",
		"https://archiveofourown.org/works/": "AO3/",
		"https://www.royalroad.com/fiction/": "RR/",
	}

	def __init__(self, *, url: str | None, shorten):
		super().__init__(fmt="%(asctime)s %(message)s")
		self.url = url
		self.shorten = shorten

	def format(self, record: logging.LogRecord) -> str:
		# print(f"{record.__dict__ = }")
		url = getattr(record, "url", None)

		if hasattr(url, "url"):
			url = str(url.url)
		else:
			url = str(url)

		if self.shorten:
			url = dict_replace(url, self.abvreviations)

		return super().format(record) % {"url": url}
