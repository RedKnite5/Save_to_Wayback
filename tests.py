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

	def test_imh_gallery_no_slash(self):
		url = "https://imhentai.xxx/gallery/773818"
		self.assertEqual(url, save.save_format(url))

	def test_imh_gallery_slash(self):
		url = "https://imhentai.xxx/gallery/773818/"
		url_formatted = "https://imhentai.xxx/gallery/773818"
		self.assertEqual(url_formatted, save.save_format(url))

	def test_imh_view_no_slash(self):
		url = "https://imhentai.xxx/view/523105/45"
		url_formatted = "https://imhentai.xxx/gallery/523105"
		self.assertEqual(url_formatted, save.save_format(url))

	def test_imh_view_slash(self):
		url = "https://imhentai.xxx/view/523105/45/"
		url_formatted = "https://imhentai.xxx/gallery/523105"
		self.assertEqual(url_formatted, save.save_format(url))
	
	@unittest.skip("later")
	def test_qq(self):
		pass

	@unittest.skip("later")
	def test_nh(self):
		pass

	@unittest.skip("later")
	def test_ao3(self):
		pass


class IsUpdatable(unittest.TestCase):
	def test_is_updatable_sb(self):
		url = "https://forums.spacebattles.com/threads/tombstones-worm.293073/page-14"
		self.assertTrue(save.is_updatatable(url))

	def test_is_updatable_qq(self):
		url = "https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/"
		self.assertTrue(save.is_updatatable(url))

	def test_is_not_updatable_imh(self):
		url = "https://imhentai.xxx/gallery/525793"
		self.assertFalse(save.is_updatatable(url))

	def test_is_not_updatable_nh(self):
		url = "https://nhentai.net/g/267342/"
		self.assertFalse(save.is_updatatable(url))


class IsSaved(unittest.TestCase):
	def setUp(self) -> None:
		self.lines = [
			"https://nhentai.net/g/378138/",
			"https://nhentai.net/g/378139",
			"https://imhentai.xxx/gallery/790067/",
			"https://imhentai.xxx/view/525793/1416/",
			"https://imhentai.xxx/view/597392/11",
			"https://forums.spacebattles.com/threads/dr-who-worm-master.294607/page-6",
			"https://forums.spacebattles.com/threads/earworm-worm-reverse-si.402781/",
		]
	

	def test_finds_nh_id(self):
		self.assertTrue(save.is_saved("https://nhentai.net/g/378139", self.lines))

	def test_finds_nh(self):
		self.assertTrue(save.is_saved("https://nhentai.net/g/378139/", self.lines))

	def test_finds_nh_with_slash(self):
		self.assertTrue(save.is_saved("https://nhentai.net/g/378138", self.lines))

	def test_finds_nh_with_slash_both(self):
		self.assertTrue(save.is_saved("https://nhentai.net/g/378138/", self.lines))

	def test_find_imh_gal(self):
		self.assertTrue(save.is_saved("https://imhentai.xxx/gallery/790067/", self.lines))

	def test_find_imh_view_as_gal(self):
		self.assertTrue(save.is_saved("https://imhentai.xxx/view/790067/10", self.lines))

	def test_find_imh_view(self):
		self.assertTrue(save.is_saved("https://imhentai.xxx/view/525793/1416/", self.lines))

	def test_find_imh_gal_as_view(self):
		self.assertTrue(save.is_saved("https://imhentai.xxx/gallery/525793/", self.lines))

	def test_find_imh_gal_as_view_no_slash(self):
		self.assertTrue(save.is_saved("https://imhentai.xxx/gallery/597392/", self.lines))

	def test_find_sb(self):
		self.assertTrue(save.is_saved("https://forums.spacebattles.com/threads/earworm-worm-reverse-si.402781/", self.lines))

	def test_find_sb_with_page(self):
		self.assertTrue(save.is_saved("https://forums.spacebattles.com/threads/earworm-worm-reverse-si.402781/page-3", self.lines))

	def test_find_sb_page(self):
		self.assertTrue(save.is_saved("https://forums.spacebattles.com/threads/dr-who-worm-master.294607/page-6", self.lines))

	def test_find_sb_page_without_page(self):
		self.assertTrue(save.is_saved("https://forums.spacebattles.com/threads/dr-who-worm-master.294607", self.lines))

	def test_doesnt_find_missing_thread(self):
		self.assertFalse(save.is_saved("https://forums.spacebattles.com/threads/fire.2989", self.lines))

	def test_doesnt_find_missing_nh(self):
		self.assertFalse(save.is_saved("https://nhentai.net/g/178132", self.lines))

	def test_doesnt_find_missing_imh(self):
		self.assertFalse(save.is_saved("https://imhentai.xxx/view/497/5", self.lines))
		
	def test_doesnt_find_missing_imh_gal(self):
		self.assertFalse(save.is_saved("https://imhentai.xxx/gallery/497/", self.lines))

class CompFormat(unittest.TestCase):
	def test_sb_no_page(self):
		url = "https://forums.spacebattles.com/threads/madokami-quest.252226/page-13"
		url_formatted = "https://forums.spacebattles.com/threads/madokami-quest.252226"
		self.assertEqual(url_formatted, save.comp_format(url))










if __name__ == "__main__":
	unittest.main()
