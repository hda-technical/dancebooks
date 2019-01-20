#!/usr/bin/env python3
#coding: utf-8

import unittest

from dancebooks import utils

class UtilsTest(unittest.TestCase):
	def test_making_genitive(self):
		#test for handling single word with capitalization inheritance
		self.assertEqual(utils.make_genitive("стол"), "стола")
		self.assertEqual(utils.make_genitive("Cтол"), "Cтола")
		
		#name + surname
		self.assertEqual(utils.make_genitive("Навальный"), "Навального")
		self.assertEqual(utils.make_genitive("Александр Пушкин"), "Александра Пушкина")
		self.assertEqual(utils.make_genitive("Алексей Навальный"), "Алексея Навального")
		self.assertEqual(utils.make_genitive("Александра Пушкина"), "Александры Пушкиной")
		
		#name + second name + surname
		self.assertEqual(utils.make_genitive("Александр Сергеевич Пушкин"), "Александра Сергеевича Пушкина")
		self.assertEqual(utils.make_genitive("Александра Сергеевна Пушкина"), "Александры Сергеевны Пушкиной")
		#FIXME: "Эльяш" surname is not known by pymorphy2
		#self.assertEqual(utils.make_genitive("Николай Иосифович Эльяш"), "Николая Иосифовича Эльяша")
		self.assertEqual(utils.make_genitive("Мария Михайловна Деркач"), "Марии Михайловны Деркач")
		
		#name + second name + hyphenized surname
		#FIXME: example is not working since internally we do split Бонч-Бруевич surname and receive "Бонча-Бруевича" in result
		#self.assertEqual(utils.make_genitive("Владимир Дмитриевич Бонч-Бруевич"), "Владимира Дмитриевича Бонч-Бруевича")
		self.assertEqual(utils.make_genitive("Евгения Владимировна Еремина-Соленикова"), "Евгении Владимировны Ереминой-Солениковой")
		
		
	
	
if __name__ == "__main__":
	unittest.main()