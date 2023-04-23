#!/usr/bin/env python


import unittest
import logging

import savetowayback as save

logging.disable(logging.CRITICAL)



class SaveFormat(unittest.TestCase):
	def test_sb_no_page_no_slash(self):
		url = "https://forums.spacebattles.com/threads/medical-cut-twice-worm-au.309599"
		self.assertEqual(url, save.save_format(url))

	def test_sb_no_page_slash(self):
		url = "https://forums.spacebattles.com/threads/medical-cut-twice-worm-au.309599/"
		url_formatted = "https://forums.spacebattles.com/threads/medical-cut-twice-worm-au.309599"
		self.assertEqual(url_formatted, save.save_format(url))

	def test_sb_page_no_slash(self):
		url = "https://forums.spacebattles.com/threads/medical-cut-twice-worm-au.309599/page-10"
		self.assertEqual(url, save.save_format(url))

	def test_sb_page_slash(self):
		url = "https://forums.spacebattles.com/threads/medical-cut-twice-worm-au.309599/page-10/"
		url_formatted = "https://forums.spacebattles.com/threads/medical-cut-twice-worm-au.309599/page-10"
		self.assertEqual(url_formatted, save.save_format(url))

	def test_sv_no_page_no_slash(self):
		url = "https://forums.sufficientvelocity.com/threads/administrative-mishap-supergirl-worm.70756"
		self.assertEqual(url, save.save_format(url))

	def test_sv_page_slash(self):
		url = "https://forums.sufficientvelocity.com/threads/administrative-mishap-supergirl-worm.70756/page-40/"
		url_formatted = "https://forums.sufficientvelocity.com/threads/administrative-mishap-supergirl-worm.70756/page-40"
		self.assertEqual(url_formatted, save.save_format(url))

if __name__ == "__main__":
	unittest.main()
