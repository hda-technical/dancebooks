#!/usr/bin/env python3

import unittest

#WARN: importing class, not object
import config

CONFIG_PATH_PRODUCTION = "../configs/dancebooks.production.conf"
CONFIG_PATH_TESTING = "../configs/dancebooks.testing.conf"
		
class ConfigTest(unittest.TestCase):
	def test_production(self):
		self.production = config.Config(CONFIG_PATH_PRODUCTION)

	def test_testing(self):
		self.testing = config.Config(CONFIG_PATH_TESTING)
		
	def test_common_fields(self):
		self.testing = config.Config(CONFIG_PATH_TESTING)
		self.production = config.Config(CONFIG_PATH_PRODUCTION)
		
		test_redirections = self.testing.www.id_redirections.keys()
		prod_redirections = self.production.www.id_redirections.keys()
		self.assertEqual(
			self.testing.www.id_redirections,
			self.production.www.id_redirections,
			"Id redirections mismatch: Left: {0}, Right: {1}".format(
				repr(test_redirections - prod_redirections), 
				repr(prod_redirections - test_redirections)
			)
		)
		test_keywords = self.testing.parser.keywords
		prod_keywords = self.production.parser.keywords
		self.assertEqual(
			test_keywords,
			prod_keywords,
			"Keywords mismatch: Left: {0}, Right: {1}".format(
				repr(test_keywords - prod_keywords), 
				repr(prod_keywords - test_keywords)
			)
		)
		self.assertEqual(
			self.testing.www.index_params,
			self.production.www.index_params
		)
		self.assertEqual(
			self.testing.www.search_params,
			self.production.www.search_params
		)
		
		


if __name__ == '__main__':
	unittest.main()
