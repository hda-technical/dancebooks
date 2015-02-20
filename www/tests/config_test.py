#!/usr/bin/env python3

import unittest

#WARN: importinh class, not object
from config import Config

class ConfigTest(unittest.TestCase):
	def test_production(self):
		CONFIG_PATH = "../configs/dancebooks.production.conf"
		self.production_config = Config(CONFIG_PATH)

	def test_testing(self):
		CONFIG_PATH = "../configs/dancebooks.testing.conf"
		self.testing_config = Config(CONFIG_PATH)


if __name__ == '__main__':
	unittest.main()
