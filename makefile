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

MARKDOWN_FILES := $(wildcard transcriptions/*.md)

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

BASE_TRANSCRIPTION_URL := https://github.com/georgthegreat/dancebooks-bibtex/blob/dev/transcriptions/
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
