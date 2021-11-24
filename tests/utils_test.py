#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks import utils


def test_making_genitive():

	# single words must be handled
	assert utils.make_genitive("стол") == "стола"
	# word capitalization must be preserved
	assert utils.make_genitive("Cтол") == "Cтола"

	# surname
	assert utils.make_genitive("Навальный") == "Навального"
	assert utils.make_genitive("Пушкин") == "Пушкина"

	# name + surname
	assert utils.make_genitive("Александр Пушкин") == "Александра Пушкина"
	assert utils.make_genitive("Александра Пушкина") == "Александры Пушкиной"
	assert utils.make_genitive("Алексей Навальный") == "Алексея Навального"

	# name + second name + surname
	assert utils.make_genitive("Александр Сергеевич Пушкин") == "Александра Сергеевича Пушкина"
	# same for feminine
	assert utils.make_genitive("Александра Сергеевна Пушкина") == "Александры Сергеевны Пушкиной"
	# some corner cases non handled properly by pymorphy2
	assert utils.make_genitive("Николай Иосифович Эльяш") == "Николая Иосифовича Эльяша"
	assert utils.make_genitive("Мария Михайловна Деркач") == "Марии Михайловны Деркач"

	# name + second name + hyphenized surname
	assert utils.make_genitive("Владимир Дмитриевич Бонч-Бруевич") == "Владимира Дмитриевича Бонч-Бруевича"
	assert utils.make_genitive("Евгения Владимировна Еремина-Соленикова") == "Евгении Владимировны Ереминой-Солениковой"
