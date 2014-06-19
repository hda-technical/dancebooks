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
BIBER := biber '--listsep=|' '--namesep=|' '--xsvsep=\s*\|\s*' '--mssplit=\#' --validate_datamodel

TRANSCRIPTIONS_WIKI_PAGE := wiki/Transcriptions.md
TRANSCRIPTIONS_URL_PREFIX := https://github.com/georgthegreat/dancebooks-bibtex/blob/dev/transcriptions/

DEVEL_CONFIG := $(shell readlink -f configs/www.cfg)
LOGGING_CONFIG := $(shell readlink -f configs/logger-console.cfg)

DEVEL_ENV := \
	CONFIG=$(DEVEL_CONFIG) \
	LOGGING_CONFIG=$(LOGGING_CONFIG)

# PDF files related targets

default: test-biblatex.pdf

%.pdf: JOBNAME = $(@:.pdf=)

%.pdf: %.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
	rm -f $(JOBNAME).bbl biblatex-dm.cfg
	$(LATEX) $< &>/dev/null
	$(BIBER) --onlylog $(JOBNAME)
	$(LATEX) $< &>/dev/null
	(grep -iE "Datamodel" $(JOBNAME).blg || true) | cut -d ' ' -f 5- | sort | tee $(JOBNAME).validation.log

# Target which doesn't hide LaTeX output - useful for debugging stuff
pdf-debug: test-biblatex.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
	rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	$(LATEX) $<
	$(BIBER) $(<:.tex=)
	$(LATEX) $<

pdf-upload.mk: test-biblatex.pdf
	chmod 644 $^
	scp -p $^ georg@iley.ru:/home/georg/dancebooks-bibtex/www/static/files/
	touch $@

pdf-clean:
	rm -f *.aux *.bbl *.bcf *.blg *.cfg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.vrb

pdf-distclean: pdf-clean
	rm -f *.pdf all.mk upload-pdfs.mk

# Transcriptions related targets

%.html: %.md $(ANC_MARKDOWN_FILES)
	cd www && ./_markdown2.py \
		--input "../$<" \
		--output "../$@" \
		--css "../transcriptions/_style.css"

markdown.mk: $(HTML_FILES)
	touch $@

markdown-distclean:
	rm -f transcriptions/*.html markdown.mk

markdown-wiki.mk: $(MARKDOWN_FILES) $(ANC_WIKI_FILES)
	cd www && ./_generate_wiki.py \
		--folder ../transcriptions \
		--page "../$(TRANSCRIPTIONS_WIKI_PAGE)" \
		--url-prefix "$(TRANSCRIPTIONS_URL_PREFIX)"
	cd wiki && (git commit -am "Updated wiki" || true) && git push origin master
	touch $@

# www-related targets
www-debug:
	cd www && \
	$(DEVEL_ENV) \
	./main.py

www-test:
	cd www && \
	$(DEVEL_ENV) \
	nosetests tests

www-profile:
	cd www && \
	$(DEVEL_ENV) \
	./_profile.py

www-translations:
	pybabel -q compile -d www/translations
	
www-distclean:
	rm -rf www/__pycache__ www/tests/__pycache__

requirements.txt: .PHONY
	pip freeze --local > $@

.PHONY:;

# Ancillary targets

all.mk: test-biblatex.pdf $(HTML_FILES);

urls-upload.mk: $(URL_FILES)
	chmod 644 $^
	scp -p $^ georg@server.goldenforests.ru:/home/georg/urls/
	touch $@

entry-count: $(BIB_FILES)
	echo "Items:" `cat $^ | grep -c -P '@[A-Z]+'`
	echo "Digitized:" `cat $^ | grep -c -P '\tfilename = '`
	echo "With addition date:" `cat $^ | grep -c -P '\tadded_on = '`

clean: pdf-clean;

distclean: pdf-distclean www-distclean markdown-distclean;

rebuild: distclean all.mk;
