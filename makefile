BIB_FILES := \
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

ANC_FILES_BIBLATEX := \
	dancebooks-biblatex.sty \

URL_FILES := \
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

MARKDOWN_FILES := \
	transcriptions/[155-,_it]_Giovannino_e_Il_Lanzino_e_Il_Papa_-_Manuscritto_di_baletti.md \
	transcriptions/[1589,_it]_Prospero_Luti_-_Opera_bellissima_di_gagliarda.md \
	transcriptions/[1706,_uk]_Raoul-Auger_Feuillet_-_Orchesography_or_the_Art_of_Dancing.md \
	transcriptions/[1749,_sc]_The_Register_of_Dances_at_Castle_Menzies.md \
	transcriptions/[1819,_fr]_J._H._Gourdoux-Daux_-_Requeil_de_genre_nouveau_de_contredanses_et_walses.md \
	transcriptions/[1824,_uk]_Thomas_Wilson_-_Danciad.md \
	transcriptions/[1825,_ru]_Людовик_Петровский_-_Правила_для_благородных_общественных_танцев.md \
	transcriptions/[1828,_ru]_Собрание_фигур_для_котильона.md \
	transcriptions/[183-,_uk]_Thomas_Wilson_-_The_Fashionable_Quadrille_Preceptor.md \
	transcriptions/[1902,_ru]_Николай_Людвигович_Гавликовский_-_Руководство_для_изучения_танцев,_édition_2.md \
	transcriptions/[1965,_ru]_Юрий_Алексеевич_Бахрушин_-_История_русского_балета.md \
	transcriptions/[2000,_ru]_Агриппина_Яковлевна_Ваганова_-_Основы_классического_танца.md \
	transcriptions/[2000,_ru]_Филипп_Филиппович_Вигель_-_Записки.md \
	transcriptions/[2007,_ru]_Жан_Жорж_Новерр_-_Письма_о_танце.md \
	transcriptions/[2011,_ru]_Оксана_Юрьевна_Захарова_-_Русский_бал_XVIII_-_начала_XX_века.md \

ANC_MARKDOWN_FILES := \
	transcriptions/_markdown2.py3k \
	transcriptions/_reset.css \
	transcriptions/_style.css \

HTML_FILES := $(MARKDOWN_FILES:.md=.html)

# PDF files related targets

default: test-biblatex.pdf

# \filecontents isn't treadsafe — disabling parallelism here
test-biblatex-detailed.pdf: test-biblatex.pdf

%.pdf: %.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@pdflatex --max-print-line=250 $< &>/dev/null
	@biber --listsep=\| --namesep=\| --validate_datamodel --quiet ${@:.pdf=}
	@pdflatex --max-print-line=250 $< &>/dev/null
	@grep -iE "Datamodel" ${@:.pdf=.log} || true
	@echo "Build completed"

debug: purge-pdfs test-biblatex.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@pdflatex --max-print-line=250 test-biblatex.tex
	@biber --listsep=\| --namesep=\| --validate_datamodel test-biblatex
	@pdflatex --max-print-line=250 test-biblatex.tex
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

BASE_TRANSCRIPTION_URL := https://github.com/georgthegreat/dancebooks-bibtex/blob/master/transcriptions/
update-wiki: $(MARKDOWN_FILES)
	@echo "Updating wiki"
	@rm -f wiki/Transcriptions.md
	@for MARKDOWN_FILE in $^; \
	do \
		BASENAME=`basename $$MARKDOWN_FILE .md`; \
		echo "* [$$BASENAME]($(BASE_TRANSCRIPTION_URL)$$BASENAME.md)" >> wiki/Transcriptions.md; \
	done
	cd wiki && git commit -am "Updated wiki" && git push origin master
	
purge-transcriptions: clean
	@rm -f transcriptions/*.html transriptions.mk
	@echo "Cleaning transcriptions completed"
	
# Ancillary targets

all.mk: test-biblatex.pdf test-biblatex-detailed.pdf $(HTML_FILES)
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
