#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks import utils


def make_tree(root):
	"""
	Creates a folder tree, returns {relative path: size} of the files made
	"""
	files = {
		"root.pdf": b"a",
		"subfolder/nested.pdf": b"bb",
		"subfolder/deeper/deepest.pdf": b"ccc",
		"excluded/hidden.pdf": b"dddd",
	}
	for path, content in files.items():
		abspath = os.path.join(root, path)
		os.makedirs(os.path.dirname(abspath), exist_ok=True)
		with open(abspath, "wb") as fp:
			fp.write(content)
	return {path: len(content) for path, content in files.items()}


def test_listing(tmp_path):
	"""
	Every file of the tree should be listed, and only the files
	"""
	root = tmp_path
	files = make_tree(root)
	scanned = utils.ScannedDir(root)

	assert set(scanned.files()) == {
		os.path.join(root, path)
		for path in files
	}
	# folders aren't files
	assert os.path.join(root, "subfolder") not in scanned


def test_contains_and_getsize(tmp_path):
	root = tmp_path
	files = make_tree(root)
	scanned = utils.ScannedDir(root)

	for path, size in files.items():
		abspath = os.path.join(root, path)
		assert abspath in scanned
		assert scanned.getsize(abspath) == size

	missing = os.path.join(root, "subfolder", "missing.pdf")
	assert missing not in scanned
	assert scanned.getsize(missing) is None

	# a file of a folder that was never scanned is not there either
	assert os.path.join(root, "..", "elsewhere.pdf") not in scanned


def test_lookup_is_case_sensitive(tmp_path):
	"""
	WARN: os.path.isfile() is case-insensitive on a drvfs mount, this isn't
	"""
	root = tmp_path
	make_tree(root)
	scanned = utils.ScannedDir(root)

	assert os.path.join(root, "root.pdf") in scanned
	assert os.path.join(root, "ROOT.PDF") not in scanned
	assert scanned.getsize(os.path.join(root, "Root.Pdf")) is None


def test_excludes(tmp_path):
	"""
	Excluded folders should not be descended into
	"""
	root = tmp_path
	make_tree(root)
	scanned = utils.ScannedDir(root, excludes={"excluded"})

	assert os.path.join(root, "root.pdf") in scanned
	assert os.path.join(root, "subfolder", "deeper", "deepest.pdf") in scanned
	assert os.path.join(root, "excluded", "hidden.pdf") not in scanned


def test_missing_root(tmp_path):
	"""
	An unreadable root yields an empty listing instead of raising
	"""
	scanned = utils.ScannedDir(tmp_path / "no-such-folder")
	assert scanned.files() == []
