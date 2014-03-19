BIB_FILES := $(wildcard bib/*.bib)
URL_FILES := $(wildcard urls/*.txt)
MARKDOWN_FILES := $(wildcard transcriptions/*.md)

ANC_BIBLATEX_FILES := \
	dancebooks-biblatex.sty

ANC_MARKDOWN_FILES := \
	www/_markdown2.py \
	transcriptions/_style.css
	
ANC_WIKI_FILES := \
	www/_generate_wiki.py

HTML_FILES := $(MARKDOWN_FILES:.md=.html)

PDFLATEX := pdflatex --shell-escape --max-print-line=250
LUALATEX := lualatex --shell-escape --max-print-line=250
XELATEX  := xelatex  --shell-escape --max-print-line=250
LATEX ?= $(LUALATEX)

#biber command with delimeters specification (xsvsep expects regexp, other expects symbol)
BIBER := biber '--listsep=|' '--namesep=|' '--xsvsep=\s*\|\s*' --validate_datamodel

TRANSCRIPTIONS_WIKI_PAGE := wiki/Transcriptions.md
TRANSCRIPTIONS_URL_PREFIX := https://github.com/georgthegreat/dancebooks-bibtex/blob/dev/transcriptions/

DEVEL_CONFIG := $(shell readlink -f configs/www.cfg)

# PDF files related targets

default: test-biblatex.pdf

%.pdf: JOBNAME = $(@:.pdf=)

%.pdf: %.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
	@rm -f $(JOBNAME).bbl biblatex-dm.cfg
	@$(LATEX) $< &>/dev/null
	@$(BIBER) --onlylog $(JOBNAME)
	@$(LATEX) $< &>/dev/null
	@(grep -iE "Datamodel" $(JOBNAME).blg || true) | cut -d ' ' -f 5- | sort | tee $(JOBNAME).validation.log

# Target which doesn't hide LaTeX output - useful for debugging stuff
debug-pdf: test-biblatex.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@$(LATEX) $<
	@$(BIBER) $(<:.tex=)
	@$(LATEX) $<

upload-pdf.mk: test-biblatex.pdf
	@chmod 644 $^
	@scp -p $^ georg@iley.ru:/home/georg/dancebooks-bibtex/www/static/files/
	@touch $@

clean-pdf:
	@rm -f *.aux *.bbl *.bcf *.blg *.cfg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.vrb

purge-pdf: clean-pdf
	@rm -f *.pdf all.mk upload-pdfs.mk
	
# Transcriptions related targets

%.html: %.md $(ANC_MARKDOWN_FILES)
	@cd www && ./_markdown2.py \
		--input "../$<" \
		--output "../$@" \
		--css "../transcriptions/_style.css"

transcriptions.mk: $(HTML_FILES)
	@touch $@

update-wiki.mk: $(MARKDOWN_FILES) $(ANC_WIKI_FILES)
	@cd www && ./_generate_wiki.py \
		--folder ../transcriptions \
		--page "../$(TRANSCRIPTIONS_WIKI_PAGE)" \
		--url-prefix "$(TRANSCRIPTIONS_URL_PREFIX)"
	@cd wiki && (git commit -am "Updated wiki" || true) && git push origin master
	@touch $@
	
purge-transcriptions: clean
	@rm -f transcriptions/*.html transriptions.mk

# www-related targets
debug-www:
	cd www && \
	CONFIG=$(DEVEL_CONFIG) \
	./main.py

test-www:
	cd www && \
	CONFIG=$(DEVEL_CONFIG) \
	nosetests tests

profile-www:
	@cd www && \
	CONFIG=$(DEVEL_CONFIG) \
	./_profile.py

translations-www:
	@pybabel -q compile -d www/translations

# Ancillary targets

all.mk: test-biblatex.pdf $(HTML_FILES)
	@touch $@

upload-urls.mk:	$(URL_FILES)
	@chmod 644 $^
	@scp -p $^ georg@server.goldenforests.ru:/home/georg/urls/
	@touch $@
	
entry-count: $(BIB_FILES)
	@echo "Items:" `cat $^ | grep -c -P '@[A-Z]+'`
	@echo "Digitized:" `cat $^ | grep -c -P '\tfilename = '`
	@echo "With addition date:" `cat $^ | grep -c -P '\tadded_on = '`
	
clean: clean-pdfs;
	
rebuild: purge-pdfs purge-transcriptions all.mk;
