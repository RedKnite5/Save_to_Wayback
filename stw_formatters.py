import logging
from types import TracebackType

type ExceptionInfo = (
	tuple[
		type[BaseException],
		BaseException,
		TracebackType | None
	]
	| tuple[None, None, None]
)

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

	def __init__(self, *, url: str | None, datefmt: str | None = None):
		super().__init__(fmt="%(asctime)s %(exc_name)s%(message)s", datefmt=datefmt)
		self.url = url

	def format(self, record: logging.LogRecord) -> str:
		url = getattr(record, "url", None)
		url = str(url)

		exc_name = ""
		if record.exc_info:
			exc_name = self.formatException(record.exc_info)

		url = dict_replace(url, self.abvreviations)
		record.exc_name = exc_name

		old_msg = record.msg
		record.msg = str(record.msg).format(url=url)

		record.message = record.getMessage()
		if self.usesTime():
			record.asctime = self.formatTime(record, self.datefmt)
		message = self.formatMessage(record)

		record.msg = old_msg

		return message

	def formatException(self, ei: ExceptionInfo) -> str:
		exc_name = getattr(ei[0], "__name__", "Name Missing Exception")
		return exc_name + " "


class FileFormatter(logging.Formatter):
	def __init__(self, *, url: str | None, datefmt: str | None = None):
		super().__init__(fmt="%(asctime)s %(message)s", datefmt=datefmt)
		self.url = url

	def format(self, record: logging.LogRecord) -> str:
		url = getattr(record, "url", None)
		url = str(url)

		old_msg = record.msg
		record.msg = str(record.msg).format(url=url)

		record.message = record.getMessage()
		if self.usesTime():
			record.asctime = self.formatTime(record, self.datefmt)
		message = self.formatMessage(record)

		if record.exc_info:
			message += self.formatException(record.exc_info)

		record.msg = old_msg

		return message

	def formatException(self, ei: ExceptionInfo) -> str:
		exc_name = getattr(ei[0], "__name__", "Name Missing Exception")
		exc_args = ei[1]
		return f"\n{exc_name}: {exc_args}"
