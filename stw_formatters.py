from collections.abc import Mapping
import logging
from types import TracebackType


type ExceptionInfo = (
	bool
	| tuple[
		type[BaseException],
		BaseException,
		TracebackType | None
	]
	| tuple[None, None, None]
	| BaseException
	| None
)

def dict_replace(string: str, dictionary: Mapping[str, str]) -> str:
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
		"https://imhentai.xxx/": "IMH/",
		"https://archiveofourown.org/works/": "AO3/",
		"https://www.royalroad.com/fiction/": "RR/",
	}

	def __init__(self, *, datefmt: str | None = None):
		super().__init__(fmt="%(asctime)s %(exc_name)s%(message)s", datefmt=datefmt)

	def format(self, record: logging.LogRecord) -> str:
		url = getattr(record, "url", None)
		url = str(url)
		url = dict_replace(url, self.abvreviations)

		record.message = record.getMessage()
		record.message = record.message.format(url=url)

		exc_name = ""
		if record.exc_info:
			exc_name = self.formatException(record.exc_info)
		record.exc_name = exc_name

		if self.usesTime():
			record.asctime = self.formatTime(record, self.datefmt)
		message = self.formatMessage(record)

		return message

	def formatException(self, ei: ExceptionInfo) -> str:
		if isinstance(ei, tuple):
			if ei[0] is not None:
				exc_name = ei[0].__name__
			else:
				exc_name = "None"
		else:
			if isinstance(ei, BaseException):
				exc_name = type(ei).__name__
			else:
				exc_name = "None"
		return exc_name + " "


class FileFormatter(logging.Formatter):
	def __init__(self, *, datefmt: str | None = None):
		super().__init__(fmt="%(asctime)s %(message)s", datefmt=datefmt)

	def format(self, record: logging.LogRecord) -> str:
		url = getattr(record, "url", None)
		url = str(url)

		record.message = record.getMessage()
		record.message = record.message.format(url=url)

		if self.usesTime():
			record.asctime = self.formatTime(record, self.datefmt)
		message = self.formatMessage(record)

		if record.exc_info:
			message += self.formatException(record.exc_info)

		return message

	def formatException(self, ei: ExceptionInfo) -> str:
		if isinstance(ei, tuple):
			if ei[0] is not None:
				exc_name = ei[0].__name__
				exc_args = str(ei[1])
			else:
				exc_name = "None"
				exc_args = "Empty"
		else:
			if isinstance(ei, BaseException):
				exc_name = type(ei).__name__
				exc_args = str(ei)
			else:
				exc_name = "None"
				exc_args = "Empty"

		return f"\n{exc_name}: {exc_args}"
