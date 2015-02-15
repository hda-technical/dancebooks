NAME_PRODUCTION := dancebooks.production
NAME_TESTING := dancebooks.testing

BIB_FILES := $(wildcard bib/*.bib)

ANC_BIBLATEX_FILES := \
	dancebooks-biblatex.sty

PDFLATEX := pdflatex --shell-escape --max-print-line=250
LUALATEX := lualatex --shell-escape --max-print-line=250
XELATEX  := xelatex  --shell-escape --max-print-line=250
LATEX ?= $(LUALATEX)

#biber command with delimeters specification (xsvsep expects regexp, other expects symbol)
BIBER := biber '--listsep=|' '--namesep=|' '--xsvsep=\s*\|\s*' '--mssplit=\#' --validate_datamodel

#Using testing conf-file in development environment
DEVEL_CONFIG := $(shell readlink -f configs/dancebooks.testing.conf)
PRODUCTION_CONFIG := $(shell readlink -f configs/dancebooks.production.conf)
LOGGING_CONFIG := $(shell readlink -f configs/logger.development.conf)

DEVEL_ENV := \
	CONFIG=$(DEVEL_CONFIG) \
	LOGGING_CONFIG=$(LOGGING_CONFIG) \
	UNITTEST=true \
	PYTHONPATH=. \

PRODUCTION_TEST_ENV := \
	CONFIG=$(PRODUCTION_CONFIG) \
	LOGGING_CONFIG=$(LOGGING_CONFIG) \
	UNITTEST=true \
	PYTHONPATH=. \

TESTS := $(wildcard www/tests/*.py)
TEST_TARGETS := $(TESTS:.py=.mk)
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

pdf-clean:
	rm -f *.aux *.bbl *.bcf *.blg *.cfg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.vrb

pdf-distclean: pdf-clean
	rm -f *.pdf all.mk

validate:
	cd www && \
	$(DEVEL_ENV) \
	./_validate.py

added-on:
	cd www && \
	$(DEVEL_ENV) \
	./_added_on.py

# www-related targets
www-debug: www-translations
	cd www && \
	$(DEVEL_ENV) \
	./main.py

www-test: $(TEST_TARGETS);

www/tests/%.mk: www/tests/%.py
	cd www && \
	$(DEVEL_ENV) \
	python tests/`basename $<` -v

	cd www && \
	$(PRODUCTION_TEST_ENV) \
	python tests/`basename $<` -v

www-profile:
	cd www && \
	$(DEVEL_ENV) \
	./_profile.py

www-translations:
	pybabel -v -q compile -d www/translations

# must be imvoked as root
www-configs-install: www-configs-install-production www-configs-install-testing;

www-configs-install-production:
	#installing uwsgi configs
	cp configs/uwsgi.production.conf /etc/uwsgi/apps-available/$(NAME_PRODUCTION).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_PRODUCTION).conf /etc/uwsgi/apps-enabled/$(NAME_PRODUCTION).conf
	#installing service configs
	cp configs/service.production.conf /etc/init.d/$(NAME_PRODUCTION)
	chmod +x /etc/init.d/$(NAME_PRODUCTION)
	service $(NAME_PRODUCTION) restart
	#installing nginx configs
	cp configs/nginx.production.conf /etc/nginx/sites-available/$(NAME_PRODUCTION).conf
	ln -sf /etc/nginx/sites-available/$(NAME_PRODUCTION).conf /etc/nginx/sites-enabled/$(NAME_PRODUCTION).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	cp configs/logrotate.production.conf /etc/logrotate.d/$(NAME_PRODUCTION).conf

www-configs-install-testing:
	#installing uwsgi configs
	cp configs/uwsgi.testing.conf /etc/uwsgi/apps-available/$(NAME_TESTING).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_TESTING).conf /etc/uwsgi/apps-enabled/$(NAME_TESTING).conf
	#installing service configs
	cp configs/service.testing.conf /etc/init.d/$(NAME_TESTING)
	chmod +x /etc/init.d/$(NAME_TESTING)
	service $(NAME_TESTING) restart
	#installing nginx configs
	cp configs/nginx.testing.conf /etc/nginx/sites-available/$(NAME_TESTING).conf
	ln -sf /etc/nginx/sites-available/$(NAME_TESTING).conf /etc/nginx/sites-enabled/$(NAME_TESTING).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	cp configs/logrotate.testing.conf /etc/logrotate.d/$(NAME_TESTING).conf

www-distclean:
	rm -rf www/__pycache__ www/tests/__pycache__

requirements.txt: .PHONY
	pip freeze --local | sort --ignore-case | tee $@

# Ancillary targets

.PHONY:;

all.mk: test-biblatex.pdf;

entry-count: $(BIB_FILES)
	@echo "Items:" `cat $^ | grep -c -P '@[A-Z]+'`
	@echo "Digitized:" `cat $^ | grep -c -P '\tfilename = '`
	@echo "With keywords:" `cat $^ | grep -c -P '\tkeywords = '`

clean: pdf-clean;

distclean: pdf-distclean www-distclean;

rebuild: distclean all.mk;

test: www-test;
