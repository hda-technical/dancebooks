#!/usr/bin/env python3
import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks.utils import make_genitive_via_petrovich



@pytest.mark.parametrize("make_genitive", [make_genitive_via_petrovich])
def test_making_genitive(make_genitive):
	# latin text - should be preserved without exceptions
	assert make_genitive("University of Aberdeen") == "University of Aberdeen"

	# only lastname
	assert make_genitive("Навальный") == "Навального"
	assert make_genitive("Навальная") == "Навальной"
	assert make_genitive("Пушкин") == "Пушкина"

	# firstname + lastname
	assert make_genitive("Александр Пушкин") == "Александра Пушкина"
	assert make_genitive("Александра Пушкина") == "Александры Пушкиной"
	assert make_genitive("Алексей Навальный") == "Алексея Навального"

	# firstname + middlename + lastname
	assert make_genitive("Александр Сергеевич Пушкин") == "Александра Сергеевича Пушкина"
	# same for feminine
	assert make_genitive("Александра Сергеевна Пушкина") == "Александры Сергеевны Пушкиной"
	# some corner cases
	assert make_genitive("Николай Иосифович Эльяш") == "Николая Иосифовича Эльяша"
	assert make_genitive("Мария Михайловна Деркач") == "Марии Михайловны Деркач"

	# firstname + middle name + hyphened lastname
	assert make_genitive("Владимир Дмитриевич Бонч-Бруевич") == "Владимира Дмитриевича Бонч-Бруевича"
	assert make_genitive("Евгения Владимировна Еремина-Соленикова") == "Евгении Владимировны Ереминой-Солениковой"
