#!/usr/bin/env python3
#coding: utf-8

import collections
import logging
import os
import unittest

from babel.messages import pofile

from dancebooks import utils

LOCALIZATION_BASEDIR = "www/translations"
MESSAGES_REL_PATH = "LC_MESSAGES/messages.po"

class LocalizationTest(unittest.TestCase):
	def setUp(self):
		"""
		Reads the localization via babel
		"""
		self.catalogs = dict()
		for locale in os.listdir(LOCALIZATION_BASEDIR):
			po_file_path = os.path.join(LOCALIZATION_BASEDIR, locale, MESSAGES_REL_PATH)
			with open(po_file_path, "r") as po_file:
				self.catalogs[locale] = pofile.read_po(po_file)


	def	test_messages_match(self):
		"""
		Tests if all the localizations have the same order
		translation keys
		"""
		has_mismatches = False

		messages = collections.defaultdict(list)
		for locale, catalog in self.catalogs.items():
			for message in catalog:
				messages[locale].append(message.id)

		first_locale = utils.first(messages.keys())
		first_message_list = messages.pop(first_locale)
		for locale, message_list in messages.items():
			self.assertEqual(
				len(first_message_list),
				len(message_list)
			)
			self.assertEqual(
				set(first_message_list),
				set(message_list)
			)
			for index, message in enumerate(message_list):
				if message != first_message_list[index]:
					logging.debug("Mismatch at position {index}. {first_locale} has {first_message}, {locale} has {message}".format(
						index=index,
						first_locale=first_locale,
						first_message=first_message_list[index],
						locale=locale,
						message=message
					))
					has_mismatches = True
		self.assertFalse(has_mismatches)





if __name__ == "__main__":
	unittest.main()
