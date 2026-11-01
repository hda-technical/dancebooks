#!/usr/bin/env python3

import pytest

from dancebooks import utils


def test_making_genitive():
	# latin text - should be preserved without exceptions
	assert utils.make_genitive("University of Aberdeen") == "University of Aberdeen"

	# only lastname
	assert utils.make_genitive("Навальный") == "Навального"
	assert utils.make_genitive("Навальная") == "Навальной"
	assert utils.make_genitive("Пушкин") == "Пушкина"

	# firstname + lastname
	assert utils.make_genitive("Александр Пушкин") == "Александра Пушкина"
	assert utils.make_genitive("Александра Пушкина") == "Александры Пушкиной"
	assert utils.make_genitive("Алексей Навальный") == "Алексея Навального"

	# firstname + middlename + lastname
	assert utils.make_genitive("Александр Сергеевич Пушкин") == "Александра Сергеевича Пушкина"
	# same for feminine
	assert utils.make_genitive("Александра Сергеевна Пушкина") == "Александры Сергеевны Пушкиной"
	# some corner cases
	assert utils.make_genitive("Николай Иосифович Эльяш") == "Николая Иосифовича Эльяша"
	assert utils.make_genitive("Мария Михайловна Деркач") == "Марии Михайловны Деркач"

	# firstname + middle name + hyphened lastname
	assert utils.make_genitive("Владимир Дмитриевич Бонч-Бруевич") == "Владимира Дмитриевича Бонч-Бруевича"
	assert utils.make_genitive("Евгения Владимировна Еремина-Соленикова") == "Евгении Владимировны Ереминой-Солениковой"
