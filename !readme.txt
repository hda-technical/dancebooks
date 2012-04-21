Библиография распространяется под свободной лицензией. Для получения детальной информации смотрите файл !license.txt

Для корректной работы необходимо подключить макросы (где-нибудь перед \begin{documant}:

%начало определений
%определение специфических кириллических символов
\newcommand{\И}{{\fontencoding{X2}\selectfont\CYRII}}
\newcommand{\и}{{\fontencoding{X2}\selectfont\cyrii}}
\newcommand{\Е}{{\fontencoding{X2}\selectfont\CYRYAT}}
\newcommand{\е}{{\fontencoding{X2}\selectfont\cyryat}}
\newcommand{\Ф}{{\fontencoding{X2}\selectfont\CYROTLD}} 
\newcommand{\ф}{{\fontencoding{X2}\selectfont\cyrotld}}
\newcommand{\Ы}{{\fontencoding{X2}\selectfont\CYRIZH}}
\newcommand{\ы}{{\fontencoding{X2}\selectfont\cyrizh}}

%определение команд верхнего и нижнего индекса без написания курсивом
\newcommand{\superscript}[1]{\ensuremath{^{\textrm{#1}}}}
\newcommand{\subscript}[1]{\ensuremath{_{\textrm{#1}}}}

%конец определений

Подключение файлов осуществляется следующим (пока что нерабочим образом):
\addcontentsline{toc}{section}{Список литературы}
\bibliographystyle{gost780s-local}
\bibliography{bib/literature,bib/dutch,bib/french,bib/russian,bib/deutch,bib/english,bib/spanish,bib/italian,bib/danish,bib/portuguese,bib/rothenfelser,bib/american,bib/australian,bib/czech}

Сюда же через запятую можно добавить любые дополнительные bib-файлы.