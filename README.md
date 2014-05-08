﻿# dancebooks-bibtex

Данный проект ставит целью собрание наиболее полной библиографии по историческим танцам. База данных хранится в формате `.bib` и предполагает интеграцию с пакетами обработки языка разметки LaTeX.

Обработка библиографической базы данных в LaTeX выполняется двумя программами: фронтэндом (на стороне LaTeX) и бэкэндом (именно бэкэнд считывает базу данных и преобразует её в формат, понятный LaTeX'у). Теоретически, можно использовать любую существующую связку (фронтэнд + бэкэнд), официально поддерживается `(biblatex + biber)`. Кроме базы данных, реализованы собственные стилевые файлы.

Для удобства пользования базой данных запущен [специальный сайт](http://bib.hda.org.ru/bib/index.html).

Кроме этого в проект включены некоторые транскрипции танцевальных источников в формате [markdown](http://daringfireball.net/projects/markdown/syntax). Некоторые правила оформления данных источников описаны ниже.

## Использование в LaTeX

Нужно установить `biblatex-2.8`, `biblatex-gost-0.9` и `biber-1.8` (про установку данных пакетов можно будет прочесть ниже. Стилевой файл подключается так:

	\newcommand{\rootfolder}{%folderpath%}
	\usepackage[root=\rootfolder]{\rootfolder/dancebooks-biblatex}

Опционально доступен параметр `usedefaults`, принимающий значения `true` и `false`. При указании значения `false` источники танцевальной библиографии (`.bib`-файлы из состава проекта) не подключаются. Позволяет использовать стилевой файл из дистрибутива в других проектах. Пример использования опции:

	\newcommand{\rootfolder}{%folderpath%}
	\usepackage[usedefaults=false,root=\rootfolder]{\rootfolder/dancebooks-biblatex}

После подключения становятся доступны макросы цитирования `\cite`, `\footcite`, `\parencite`, `\nocite`, `\volcite`. Работа макросов описана в [руководстве по biblatex](http://mirrors.ctan.org/macros/latex/contrib/biblatex/doc/biblatex.pdf). Стандартный макрос печати библиографии в `biblatex` -- `\printbibliography`, без параметров. Дополнительные библиографические источники можно добавить стандартной командой `\addbibresource{hello.bib}` (расширение `.bib` необходимо указывать явно).

Порядок компиляции такой:

1. `pdflatex project.tex`
2.	`biber --listsep=\| --namesep=\| --quiet project` (в POSIX окружении)
	
	`biber "--listsep=|" "--namesep=|" "test-biblatex"` (в Windows)
3. `pdflatex project.tex`
4. `pdflatex project.tex`

В версии 1.9 была добавлена поддержка `lualatex` (в качестве лингвистического фреймворка используется `Πολυγλωσσια` (`Polyglossia`)). Порядок компиляции аналогичен:

1. `lualatex project.tex`
2.	`biber '--listsep=|' '--namesep=|' '--xsvsep=\s*\|\s*' --mssplit=# project` (в POSIX окружении)
	
	`biber "--listsep=|" "--namesep=|" "test-biblatex" "--xsvsep=\s*\|\s*" "--mssplit=#" project` (в Windows)
3. `lualatex project.tex`
4. `lualatex project.tex`

Пункт №4 может быть опущен в случае документов без оглавления.

### Установка дополнительных пакетов. `biblatex`

Скачать можно [по этому адресу](http://sourceforge.net/projects/biblatex/files/), вот [прямая ссылка на последнюю версию](http://sourceforge.net/projects/biblatex/files/latest/download).

Пакет есть в стандартном репозитории.

### Установка дополнительных пакетов. `biber`

Скачать бэкэнд можно [по этому адресу](http://sourceforge.net/projects/biblatex-biber/files/biblatex-biber/), вот [прямая ссылка на последнюю версию](http://sourceforge.net/projects/biblatex-biber/files/latest/download). Внимание! Не всякая версия biber подходит для конкретной версии biblatex. Изучите, пожалуйста, информацию о необходимой вам версии biber.

Необходимо положить исполняемый файл в любую папку, после чего добавить эту папку в `%PATH%`, если этого не было сделано раньше.

Для x86-дистрибутивов пакет есть в стандартном репозитории (для MiKTeX он называется `miktex-biber-bin`).

### Установка дополнительных пакетов. `biblatex-gost`

Скачать последнюю версию гостовских стилей можно [по этому адресу](http://sourceforge.net/projects/biblatexgost/files/), вот [прямая ссылка на последнюю версию](http://sourceforge.net/projects/biblatexgost/files/latest/download).

Скачанный архив нужно распаковать (с сохранением структуры директорий) в любую из корневых папок вашего дистрибутива.

После установки пакета нужно выполнить команду обновления кэша (команда зависит от вашего дистрибутива, для MiKTeX – `initexmf -u`).

## Правила навешивания тегов

* `antidance` — понятно из перевода,
* `belle danse` — понятно из перевода,
* `commentary` вешается на все издания, в которых есть вступительная статья,
* `facsimile` вешается на «новые» переиздания, которые содержат факсимиле оригинала,
* `markdown` ставится у книг, для которых доступна оцифрованная транскрипция (смотри ниже),
* `not digitized` — понятно из перевода,
* `reissue` вешается на все переиздания, относящиеся к другой исторической эпохе, нежели оригинал,
* `research` вешается на все исследования по теме танцев или балета,
* `transcription` вешается на все издания, которые не содержат факсимиле оригинала, но содержат его текст,
* `translation` вешается на переиздания, которые содержат перевод оригинального издания.

## Поддержка множества ссылок

Библиография поддерживает множество ссылок на одну и ту же книгу. Правила расстановки таковы:

1. Если книга не выложена в свободный доступ, то ссылка отсутствует.
2. Если книга доступна на ресурсах-агрегаторах ([archive.org](https://archive.org), [Google Books](http://books.google.com)), ставится ссылка на ресурс-агрегатор. Таких ссылок может быть не больше одной.
3. Если книга лежит на официальном сайте какой-либо библиотеки. Таких ссылок может быть больше, чем одна.
4. Если ссылки из пункта 3 не имеют известных дефектов, такие ссылки вытесняют ссылку из пункта 2. Информация о дефектах заносится в поле annotation.

## О транскрипциях

Все транскрипции хранятся в формате [`markdown`](http://daringfireball.net/projects/markdown/syntax).

Файлы транскрипций находятся в кодировке utf-8-with-BOM.

Для просмотра файлов можно установить расширения браузера: [Firefox Markdown Viewer](https://addons.mozilla.org/en-US/firefox/addon/markdown-viewer/) (стоит отметить, что для больших файлов расширение работает довольно медленно), или использовать скрипт `transcriptions/_markdown2.py3k` (потребуется `python3` с установленным модулем [`markdown2`](https://pypi.python.org/pypi/markdown2)).

Доступен и альтернативный способ просмотра транскрицпий — прямо на [github.com](https://github.com/georgthegreat/dancebooks-bibtex/wiki/Transcriptions).

### Правила расстановки заголовков таковы:

* \# – ставится у названия книги,
* \#\# – ставится у автора книги или авторов, если их несколько,
* \#\#\# – ставится у всех прочих заголовков других уровней.

После символов форматирования в разметке присутствует пробел.

### Правила, применяемые при оформлении транскрипций:

Вот короткий список изменений, которые я провожу с текстом транскрипции:

* удаляются номера страниц и символы переноса внутри слов,
* \<, &lt; и \>, &gt; заменяются на ‹ и › соответственно,
* тире ставятся в соответствии с правилами русской орфографии независимо от языка оригинала,
* в словах (по возможности) ставится буква ё вместо е там, где это необходимо,
* инициалы пишутся через пробел,
* стихи и отрывки из произведений оформляются как цитаты (> ),
* короткие (однострочные) сноски вносятся прямо в текст, остальные ограничиваются горизонтальными линиями сверху и снизу (\*\*\*),
* в конце заголовков удаляются точки, в коцне абзацев — наоборот, добавляются,
* в конце строк обрезаются пробельные символы,
* неочевидная расшифровка аббревиатур и опечаток помещается в круглые скобки,
* транскрипции книг, выпущенных после 1800 года переводятся в современные орфографии.

Возможны и некоторые другие специфичные для каждой транскрипции в отдельности изменения.