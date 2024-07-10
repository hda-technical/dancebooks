﻿# HDA/Library

Электронная библиотека АИТ (далее — библиотека) включает в себя электронные копии всех доступных АИТ источников.

Этот файл включает в себя общую информацию о структуре директорий в библиотеке и ссылки на некоторые вспомогательные материалы.

Поиск по библиотеке доступен на [сайте библиографии](https://bib.hda.org.ru/bib). Для того, чтобы при поиске отображались относительные пути источников в библиотеке, откройте в браузере [ссылку](https://bib.hda.org.ru/bib/secret-cookie). Не все источники библиографии представлены в библиотеке: исключение составляют [неоцифрованные книги](https://bib.hda.org.ru/bib/advanced-search?keywords=not%20digitized) и источники доступные только в [транскрибированном варианте](https://bib.hda.org.ru/advanced-search?transcription=true). Обратите внимание: синхронизация файлов библиотеки происходит автоматически, а обновление библиографии — вручную; иногда между ними возможны несоответствия.

Кроме источников, включённых в библиографию, в директории `Ancillary sources (not in bibliography)` находятся дополнительные источники. Часть источников, доступных в сильно неполном варианте также не включена в библиографию. Эти источники находятся в директории `Leaflets (not in bibliography)`.

Структура оставшихся директорий в библиотеке такова (нужно понимать, что всякая попытка строгой классфикации условна, танцевальная традиция развивалась непрерывно):

01. `15th century` —  источники танцев по традиции XV века (1401–1550)
02. `16th century` — источники танцев по традиции XVI века (1551–1650)
03. `17th century` — источники эпохи раннего барокко (1651–1700)
04. `18th century` — источники эпох позднего барокко и рококо (1701–1791)
05. `19th century` — источники от ампира и регенства до викторианской эпохи и эпохи модерн (1792–1914)
06. `20th century` — источники с танцами XX века
07. `Belles lettres & memoires` — директория для художественной литературы с упоминаниями или описаниями танцев, а также мемуаристика
08. `Country dances` — директория для источников, не содержащих иных танцев, кроме английских контрдансов
09. `Music` — директория для источников, содержащих только музыкальные нотации танцев, но не содержащих из описания
10. `Periodical` — директория для журнальных статей посвящённых танцам (в случае статьи хранится выпуск журнала или газеты целиком). Современные исследовательские статьи находятся в поддиректории `Periodical/Modern`
11. `Proceedings` — директория для сборников статей с конференций
12. `Short descriptions` — директория для нот с короткими описаниями танцев

## Имена файлов

Имена файлов имеют формат `[YYYY, LL] AUTHORS - SHORT_TITLE OPTIONAL_STUFF.EXT`, где

* `YYYY` — год (в случае неточной датировки вместо последних цифр ставятся прочерки).
    В отличие [от библиографии](index.md#dating) для неточных датировок используется символ `-`.
* `LL` — двухбуквенный код основного языка книги или страны, в которой книга была выпущена (**то есть имеет место неоднозначность**, может включать в себя информацию о стране издания в случае, если язык является основным языком в нескольких странах). Возможные значения этого поля перечислены в [файле](#country-codes)
* `AUTHORS` — полные имена авторов (в меру их известности, поле может полностью отсутствовать, если источник анонимен), через запятую
* `SHORT_TITLE` — осмысленный префикс названия источника
* `OPTIONAL_STUFF` — опциональный постфикс может включать в себя (через запятую):
	* номер тома: `tome X`, 
	* номер издания `édition Y`, 
	* номер части `partie Z`, 
	* номер периодического или серийного издания `number N`,
	* пометку `(incomplete)` для источников с частично отсутствующими страницами,
	* пометку `(Someone's copy)` или для источников, известных в нескольких вариантах соответственно (также может использоваться для идентификации происхождения копии).
* `EXT` — расширение файла:
	* `pdf` для книг из [HDA/Library](https://github.com/hda-technical/docs/blob/master/library.md)
	* `md` для [транскрипций](https://github.com/hda-technical/docs/blob/master/transcriptions.md)

## ISO 3166-1 Country Codes { #country-codes }

Используемые в поле filename коды стран являются подмножеством кодов, описанных в [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2).
Для неуказанных в стандарте сущностей введены собственные обозначения.

| Аббревиатура | Язык | Страна |
| ------------ | ---- | ------ |
| `ar` | испанский | Аргентина |
| `au` | английский | Австралия |
| `at` | немецкий | Австрия |
| `ca` | английский | Канада |
| `cz` | чешский | Чехия |
| `de` | немецкий | Германия |
| `dk` | датский | Дания |
| `en` | английский | Англия |
| `es` | испанский | Испания |
| `fr` | французский | Франция |
| `gr` | греческий | Греция |
| `ie` | английский | Ирландия |
| `it` | итальянский | Италия |
| `ln` | латынь | — |
| `nl` | голланский | Нидерланды |
| `pl` | польский | Польша |
| `pt` | португальский | Португалия |
| `ru` | русский | Российская Империя, СССР, Россия |
| `sc` | английский | Шотландия |
| `sw` | шведский | Швеция |
| `tr` | турецкий | Турция |
| `ua` | украинский | УССР |
| `us` | английский | США |

## Особая танцевальная магия

Внимательный взгляд заметит, что имена файлов на сайте библиографии являются ссылками вида `bib://%путь в библиотеке%`. В данный момент реализована поддержка этой схемы в операционных системах семейства Windows.

Установка:
* В корневой директории библиотеки лежит скрипт `bib.vbs`. При его запуске без параметров будет выдан запрос на изменение параметров реестра Windows. На запрос нужно ответить утвердительно
* Если файл `bib.vbs` или корневая директория Яндекс.Диска будут перемещены, скрипт нужно будет запустить заново
* Для удаления нужно запустить `bib.vbs uninstall` и согласиться с внесением изменений в реестр, либо вручную удалить ветку реестра `HKEY_CLASSES_ROOT\bib`

**Кстати!** У библиографии тоже есть [документация](https://github.com/hda-technical/docs/blob/master/bibliography.md). RTFM!