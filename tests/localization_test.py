#!/usr/bin/env python3

import os
import sys

from babel.messages import pofile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCALIZATION_BASEDIR = "www/translations"


def read_po_files():
	po_files = dict()
	for locale in os.listdir(LOCALIZATION_BASEDIR):
		po_file_path = f"{LOCALIZATION_BASEDIR}/{locale}/LC_MESSAGES/messages.po"
		with open(po_file_path, "r") as po_file:
			po_files[locale] = pofile.read_po(po_file)
	return po_files


def	test_messages_match():
	po_files = read_po_files()
	base_locale = next(iter(po_files.keys()))
	base_messages = po_files[base_locale]
	for locale, messages in po_files.items():
		for base_msg, msg in zip(base_messages, messages):
			assert msg.id == base_msg.id, f"While testing locale {locale} against {base_locale}: got {msg.id}, while expecting {base_msg.id}"
