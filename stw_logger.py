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

	def __init__(self, *, url: str | None, shorten: bool, datefmt: str | None = None):
		super().__init__(fmt="%(asctime)s %(message)s", datefmt=datefmt)
		self.url = url
		self.shorten = shorten

	def format(self, record: logging.LogRecord) -> str:
		url = getattr(record, "url", None)
		url = str(url)

		exc_name = exc_text = ""
		if record.exc_info:
			exc_name = getattr(record.exc_info[0], "__name__", "Name Missing")
			exc_args = record.exc_info[1]
			exc_text = f"{exc_name}: {exc_args}"

		if self.shorten:
			url = dict_replace(url, self.abvreviations)
			exc_text = exc_name

		record.msg = str(record.msg).format(url=url)

		record.message = record.getMessage()
		if self.usesTime():
			record.asctime = self.formatTime(record, self.datefmt)
		message = self.formatMessage(record)

		if exc_text:
			if message[-1:] != "\n":
				message = message + "\n"
			message = message + exc_text

		return message
