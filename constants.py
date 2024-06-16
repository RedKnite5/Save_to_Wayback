from types import TracebackType

__all__ = [
    "FF_URL",
    "SB_URL",
    "SV_URL",
    "QQ_URL",
    "NH_URL",
    "IMH_URL",
    "AO3_URL",
    "RR_URL",
    "ExceptionInfo",
]

FF_URL  = "https://www.fanfiction.net/"
SB_URL  = "https://forums.spacebattles.com/"
SV_URL  = "https://forums.sufficientvelocity.com/"
QQ_URL  = "https://forum.questionablequesting.com/"
NH_URL  = "https://nhentai.net/g/"
IMH_URL = "https://imhentai.xxx/"
AO3_URL = "https://archiveofourown.org/"
RR_URL  = "https://www.royalroad.com/"

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
