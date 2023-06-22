#!/usr/bin/env python


import logging
import unittest
from unittest import skip, TestCase
import pathlib
from io import StringIO

import requests
from responses import _recorder, RequestsMock

import savetowayback as save

logging.disable(logging.CRITICAL)

path = pathlib.Path(__file__).parent.resolve()
responses_file = path / "test_files/responses.yaml"


@_recorder.record(file_path=responses_file)
def test_recorder():
    # TODO: AO3
    rsp = requests.get("https://nhentai.net/g/149789/1")
    rsp = requests.get("https://nhentai.net/g/149789/3")
    rsp = requests.get("https://nhentai.net/g/149789/23")
    rsp = requests.get("https://nhentai.net/g/449729/1")
    rsp = requests.get("https://imhentai.xxx/view/791259/1/")
    rsp = requests.get("https://imhentai.xxx/view/791259/2/")
    rsp = requests.get("https://imhentai.xxx/view/791259/3/")
    rsp = requests.get("https://forums.spacebattles.com/threads/subduction-worm.305227/")
    rsp = requests.get("https://forums.spacebattles.com/threads/subduction-worm.305227/page-10")
    rsp = requests.get("https://forums.spacebattles.com/threads/subduction-worm.305227/page-33")
    rsp = requests.get("https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/")
    rsp = requests.get("https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/page-2")
    rsp = requests.get("https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/page-5")
    rsp = requests.get("https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/")
    rsp = requests.get("https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/page-2")
    rsp = requests.get("https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/page-41")
    rsp = requests.get("https://www.fanfiction.net/s/13905005/1/Two-Minutes-Silence")
    rsp = requests.get("https://www.fanfiction.net/s/13905005/22/Two-Minutes-Silence")
    rsp = requests.get("https://archiveofourown.org/works/30308658/chapters/74705736")
    rsp = requests.get("https://archiveofourown.org/works/30308658/chapters/75128508?view_adult=true")
    rsp = requests.get("https://archiveofourown.org/works/30308658/chapters/81088840?view_adult=true")



class SaveFormat(TestCase):
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

class IsUpdatable(TestCase):
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

class IsSaved(TestCase):
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

class CompFormat(TestCase):
	def test_sb_no_page(self):
		url = "https://forums.spacebattles.com/threads/madokami-quest.252226/page-13"
		url_formatted = "https://forums.spacebattles.com/threads/madokami-quest.252226"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_sb_no_page_newline(self):
		url = "https://forums.spacebattles.com/threads/madokami-quest.252226/page-13\n"
		url_formatted = "https://forums.spacebattles.com/threads/madokami-quest.252226"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_sb_page(self):
		url = "https://forums.spacebattles.com/threads/madokami-quest.252226/"
		url_formatted = "https://forums.spacebattles.com/threads/madokami-quest.252226"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_sv_no_page(self):
		url = "https://forums.sufficientvelocity.com/threads/splintered-worm-qa-quest.24509/"
		url_formatted = "https://forums.sufficientvelocity.com/threads/splintered-worm-qa-quest.24509"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_sv_no_page_space(self):
		url = " https://forums.sufficientvelocity.com/threads/splintered-worm-qa-quest.24509/ "
		url_formatted = "https://forums.sufficientvelocity.com/threads/splintered-worm-qa-quest.24509"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_sv_page(self):
		url = "https://forums.sufficientvelocity.com/threads/splintered-worm-qa-quest.24509/page-4/"
		url_formatted = "https://forums.sufficientvelocity.com/threads/splintered-worm-qa-quest.24509"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_nh_no_page(self):
		url = "https://nhentai.net/g/362088"
		url_formatted = "https://nhentai.net/g/362088"
		self.assertEqual(url_formatted, save.comp_format(url))

	def test_nh_page(self):
		url = "https://nhentai.net/g/362088/3/"
		url_formatted = "https://nhentai.net/g/362088"
		self.assertEqual(url_formatted, save.comp_format(url))


class GetNH(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()


	def test_get_first_page(self):
		start_url = "https://nhentai.net/g/149789"
		next_url = "https://nhentai.net/g/149789/1"
		self.assertEqual(next_url, save.get_nh(start_url))

	
	def test_get_middle_page(self):
		start_url = "https://nhentai.net/g/149789/2"
		next_url = "https://nhentai.net/g/149789/3"
		self.assertEqual(next_url, save.get_nh(start_url))

	@skip("Error: doesn't detect 404 - not found")
	def test_detect_end(self):
		start_url = "https://nhentai.net/g/149789/22"
		next_url = None
		self.assertEqual(next_url, save.get_nh(start_url))

# TODO: add tests for around page 10-11, there appears to be something wrong around there
class GetIMH(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()


	def test_get_first_page(self):
		start_url = "https://imhentai.xxx/gallery/791259/"
		next_url = "https://imhentai.xxx/view/791259/1/"
		self.assertEqual(next_url, save.get_imh(start_url))

	
	def test_get_middle_page(self):
		start_url = "https://imhentai.xxx/view/791259/1/"
		next_url = "https://imhentai.xxx/view/791259/2/"
		self.assertEqual(next_url, save.get_imh(start_url))

	@skip("Error: doesn't detect 404 - not found")
	def test_detect_end(self):
		start_url = "https://imhentai.xxx/view/791259/2/"
		next_url = None
		self.assertEqual(next_url, save.get_imh(start_url))

class GetSB(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()

	def test_get_first_page(self):
		start_url = "https://forums.spacebattles.com/threads/subduction-worm.305227/"
		next_url = "https://forums.spacebattles.com/threads/subduction-worm.305227/page-2"
		self.assertEqual(next_url, save.get_sb(start_url))

	def test_get_middle_page(self):
		start_url = "https://forums.spacebattles.com/threads/subduction-worm.305227/page-10"
		next_url = "https://forums.spacebattles.com/threads/subduction-worm.305227/page-11"
		self.assertEqual(next_url, save.get_sb(start_url))

	def test_get_detect_last_page(self):
		start_url = "https://forums.spacebattles.com/threads/subduction-worm.305227/page-33"
		next_url = None
		self.assertEqual(next_url, save.get_sb(start_url))

class GetSV(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()

	def test_get_first_page(self):
		start_url = "https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/"
		next_url = "https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/page-2"
		self.assertEqual(next_url, save.get_sv(start_url))

	def test_get_middle_page(self):
		start_url = "https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/page-2"
		next_url = "https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/page-3"
		self.assertEqual(next_url, save.get_sv(start_url))

	def test_get_detect_last_page(self):
		start_url = "https://forums.sufficientvelocity.com/threads/fleisch-und-stein-worm-si-after-a-fashion.55253/page-5"
		next_url = None
		self.assertEqual(next_url, save.get_sv(start_url))

class GetQQ(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()

	def test_get_first_page(self):
		start_url = "https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/"
		next_url = "https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/page-2"
		self.assertEqual(next_url, save.get_qq(start_url))

	def test_get_middle_page(self):
		start_url = "https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/page-2"
		next_url = "https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/page-3"
		self.assertEqual(next_url, save.get_qq(start_url))

	def test_get_detect_last_page(self):
		start_url = "https://forum.questionablequesting.com/threads/the-skittering-chaos-worm-hazbin-hotel.12674/page-41"
		next_url = None
		self.assertEqual(next_url, save.get_qq(start_url))

class GetFF(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()

	@skip("ff broken")
	def test_get_first_page(self):
		start_url = "https://www.fanfiction.net/s/13905005/1/Two-Minutes-Silence"
		next_url = "https://www.fanfiction.net/s/13905005/2/Two-Minutes-Silence"
		self.assertEqual(next_url, save.get_ffn(start_url))

	@skip("ff broken")
	def test_get_detect_last_page(self):
		start_url = "https://www.fanfiction.net/s/13905005/22/Two-Minutes-Silence"
		next_url = None
		self.assertEqual(next_url, save.get_ffn(start_url))

class GetAO3(TestCase):
	def setUp(self):
		self.r_mock = RequestsMock(assert_all_requests_are_fired=False)
		self.r_mock._add_from_file(responses_file)
		self.r_mock.start()

	def tearDown(self):
		self.r_mock.stop()
		self.r_mock.reset()

	def test_get_first_page(self):
		start_url = "https://archiveofourown.org/works/30308658/chapters/74705736"
		next_url = "https://archiveofourown.org/works/30308658/chapters/74705736?view_adult=true"
		self.assertEqual(next_url, save.get_ao3(start_url))

	def test_get_middle_page(self):
		start_url = "https://archiveofourown.org/works/30308658/chapters/75128508?view_adult=true"
		next_url = "https://archiveofourown.org/works/30308658/chapters/77777837"
		self.assertEqual(next_url, save.get_ao3(start_url))

	def test_get_full_work(self):
		start_url = "https://archiveofourown.org/works/30308658/chapters/81088840?view_adult=true"
		next_url = "https://archiveofourown.org/works/30308658?view_full_work=true"
		self.assertEqual(next_url, save.get_ao3(start_url))


class ReadSaved(TestCase):
	def test_read(self):
		file = StringIO(
			"https://nhentai.net/g/376173/\n"
			"https://imhentai.xxx/gallery/774551/\n"
			"https://forums.spacebattles.com/threads/walkabouts-worm-au.278895/page-44\n"
		)
		lines_ref = list(line.strip() for line in file.readlines())
		file.seek(0)

		lines = save.read_saved(file)

		self.assertEqual(lines, lines_ref)
		
		file.write("https://forums.spacebattles.com/threads/vicarious-worm-au.317269/page-3")
		self.assertEqual(lines, lines_ref)

		file.seek(0)
		lines_ref2 = list(line.strip() for line in file.readlines())
		self.assertNotEqual(lines, lines_ref2)




if __name__ == "__main__":
	#test_recorder()
	unittest.main()
	
