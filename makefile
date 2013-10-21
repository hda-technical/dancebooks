BIB_FILES := $(wildcard bib/*.bib)
URL_FILES := $(wildcard urls/*.txt)
MARKDOWN_FILES := $(wildcard transcriptions/*.md)

ANC_BIBLATEX_FILES := \
	dancebooks-biblatex.sty

ANC_MARKDOWN_FILES := \
	transcriptions/_markdown2.py \
	transcriptions/_reset.css \
	transcriptions/_style.css

HTML_FILES := $(MARKDOWN_FILES:.md=.html)

# PDF files related targets

default: test-biblatex.pdf

# LaTeX \filecontents isn't treadsafe — disabling parallelism here
test-biblatex-detailed.pdf: test-biblatex.pdf

%.pdf: %.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
	@rm -f $(@:.pdf=.bbl) biblatex-dm.cfg
	@pdflatex --max-print-line=250 $< &>/dev/null
	@biber --listsep=\| --namesep=\| --validate_datamodel --quiet $(@:.pdf=)
	@pdflatex --max-print-line=250 $< &>/dev/null
	@(grep -iE "Datamodel" $(@:.pdf=.log) || true) | tee validation-$(@:.pdf=.log)
	@echo "Build completed"

# Target which doesn't hide LaTeX output - useful for debugging stuff
debug: purge-pdfs test-biblatex.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
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
	@./transcriptions/_markdown2.py --input "$<" --output "$@"

transcriptions.mk: $(HTML_FILES)
	@echo "Compiling transcriptions completed"
	@touch $@

update-wiki: $(MARKDOWN_FILES)
	@echo "Updating wiki"
	@./transcriptions/_generate_wiki.py $(MARKDOWN_FILES)
	@cd wiki && git commit -am "Updated wiki" && git push origin master
	
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
	@cat $^ | grep -c "@"
	
clean: clean-pdfs
	@true
	
rebuild: purge-pdfs purge-transcriptions all.mk
	@echo "Rebuild completed"
