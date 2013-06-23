BIB_FILES=\
	bib/!missing.bib \
	bib/!problems.bib \
	bib/american.bib \
	bib/australian.bib \
	bib/austrian.bib \
	bib/canadian.bib \
	bib/czech.bib \
	bib/danish.bib \
	bib/dutch.bib \
	bib/english.bib \
	bib/french.bib \
	bib/german.bib \
	bib/italian.bib \
	bib/mexican.bib \
	bib/polish.bib \
	bib/portuguese.bib \
	bib/proceedings-rothenfelser.bib \
	bib/proceedings-spb.bib \
	bib/russian.bib \
	bib/spanish.bib \
	bib/swiss.bib \

ANC_FILES_BIBLATEX=\
	dancebooks-biblatex.sty \

URL_FILES=\
	urls/[1690,_fr]_Andre_Philidor.txt \
	urls/[175-,_fr]_Denis_Diderot,_Jean_d_Alembert.txt \
	urls/[1800,_de]_Johann_Heinrich_Kattfuss.txt \
	urls/[1803,_fr]_Jean-Georges_Noverre.txt \
	urls/[1823,_en]_The_Harmonicon.txt \
	urls/[1824,_en]_The_Harmonicon.txt \
	urls/[1838,_en]_Skene.txt \
	urls/[1884,_en]_Jane_Austen.txt \
	urls/[1701,_fr]_S.-I.txt \
	urls/[1791,_fr]_Nicolas_Etienne_Framery.txt \
	urls/[1824,_en]_A_Dictionary_of_Musicians.txt \
	urls/[1827,_en]_A_Dictionary_of_Musicians.txt \
	urls/[1913,_fr]_Rudolf_Apponyi.txt \

MARKDOWN_FILES=\
	transcriptions/[1589,\ it]\ Prospero\ Luti\ -\ Opera\ bellissima\ di\ gagliarda.md \
	transcriptions/[1620,\ fr]\ Barthélémy\ de\ Montagut\ -\ Louange\ de\ la\ danse.md \
	transcriptions/[1706,\ uk]\ Raoul-Auger\ Feuillet\ -\ Orchesography\ or\ the\ Art\ of\ Dancing.md \
	transcriptions/[1819,\ fr]\ J.\ H.\ Gourdoux-Daux\ -\ Requeil\ de\ genre\ nouveau\ de\ contredanses\ et\ walses.md \
	transcriptions/[1824,\ uk]\ Thomas\ Wilson\ -\ Danciad.md \
	transcriptions/[1825,\ ru]\ Людовик\ Петровский\ -\ Правила\ для\ благородных\ общественных\ танцев.md \
	transcriptions/[1828,\ ru]\ Собрание\ фигур\ для\ котильона.md \
	transcriptions/[183-,\ uk]\ Thomas\ Wilson\ -\ The\ Fashionable\ Quadrille\ Preceptor.md \
	transcriptions/[1902,\ ru]\ Николай\ Людвигович\ Гавликовский\ -\ Руководство\ для\ изучения\ танцев,\ édition\ 2.md \
	transcriptions/[1965,\ ru]\ Юрий\ Алексеевич\ Бахрушин\ -\ История\ русского\ балета.md \
	transcriptions/[1987,\ ru]\ Людмила\ Дмитриевна\ Блок\ -\ Классический\ танец.\ История\ и\ современность.md \
	transcriptions/[2000,\ ru]\ Агриппина\ Яковлевна\ Ваганова\ -\ Основы\ классического\ танца.md \
	transcriptions/[2000,\ ru]\ Филипп\ Филиппович\ Вигель\ -\ Записки.md \
	transcriptions/[2007,\ ru]\ Жан\ Жорж\ Новерр\ -\ Письма\ о\ танце.md \
	transcriptions/[2011,\ ru]\ Оксана\ Захарова\ -\ Русский\ бал\ XVIII\ -\ начала\ XX\ века.md \

ANC_MARKDOWN_FILES=\
	transcriptions/_markdown2.py3k \
	transcriptions/_reset.css \
	transcriptions/_style.css \

HTML_FILES=$(MARKDOWN_FILES:.md=.html)

# PDF files related targets

default: test-biblatex.pdf

%.pdf: %.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@pdflatex --max-print-line=250 $<
	@biber --listsep=\| --validate_datamodel --quiet ${@:.pdf=}
	@pdflatex --max-print-line=250 $<
	@grep -iqE "Datamodel" ${@:.pdf=.log} || true
	@echo "Build completed"

debug: purge test-biblatex.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@pdflatex --max-print-line=200 test-biblatex.tex
	@biber --listsep=\| --validate_datamodel test-biblatex
	@pdflatex --max-print-line=200 test-biblatex.tex
	@echo "Build completed"

upload-pdfs.mk: test-biblatex.pdf test-biblatex-detailed.pdf
	@chmod 644 $^
	@scp -p $^ georg@iley.ru:/home/georg/leftparagraphs/static/files/
	@touch $@

clean-pdfs:
	@rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.cfg
	@echo "Clean pdfs completed"

purge-pdfs: clean-pdfs
	@rm -f *.pdf all.mk upload-pdfs.mk
	@echo "Purge pdfs completed"
	
# Transcriptions related targets

%.html: %.md $(ANC_MARKDOWN_FILES)
	@echo "Compiling \"$<\""
	@./transcriptions/_markdown2.py3k --input "$<" --output "$@"

transcriptions.mk: $(HTML_FILES)
	@echo "Compiling transcriptions completed"
	@touch $@
	
purge-transcriptions: clean
	@rm -f transcriptions/*.html transriptions.mk
	
# Ancillary targets

all.mk: test-biblatex.pdf test-biblatex-detailed.pdf transcriptions.mk
	@echo "Build all completed"
	@touch $@

upload-urls.mk:	$(URL_FILES)
	@chmod 644 $^
	@scp -p $^ georg@server.goldenforests.ru:/home/georg/urls/
	@touch $@
	
entry-count: $(BIB_FILES)
	@cat $(BIB_FILES) | grep -c --color '@'

clean: clean-pdfs
	@true
	
rebuild: purge-pdfs purge-transcriptions all.mk
	@echo "Rebuild completed"
