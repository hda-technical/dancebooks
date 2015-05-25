NAME_PRODUCTION := dancebooks.production
NAME_TESTING := dancebooks.testing

BIB_FILES := $(wildcard bib/*.bib)

ANC_BIBLATEX_FILES := \
	dancebooks-biblatex.sty

PDFLATEX := pdflatex --shell-escape
LUALATEX := lualatex --shell-escape
XELATEX  := xelatex  --shell-escape
LATEX ?= $(LUALATEX)

#biber command with delimeters specification (xsvsep expects regexp, other expects symbol)
BIBER := biber '--listsep=|' '--namesep=|' '--xsvsep=\s*\|\s*' '--mssplit=\#' --validate_datamodel

#Using testing conf-file in development environment
DEVEL_CONFIG := $(shell readlink -f configs/dancebooks.testing.conf)
PRODUCTION_CONFIG := $(shell readlink -f configs/dancebooks.production.conf)
LOGGING_CONFIG := $(shell readlink -f configs/logger.development.conf)

TOUCH_RELOAD_TESTING := /var/run/uwsgi/$(NAME_TESTING).reload
TOUCH_RELOAD_PRODUCTION := /var/run/uwsgi/$(NAME_PRODUCTION).reload

DEVEL_ENV := \
	CONFIG=$(DEVEL_CONFIG) \
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

validate:
	cd www && \
	$(DEVEL_ENV) \
	python _validate.py \
	$(ARGS)

added-on:
	cd www && \
	$(DEVEL_ENV) \
	python _added_on.py \

# www-related targets
www-debug: www-translations
	cd www && \
	$(DEVEL_ENV) \
	python main.py \

www-test: $(TEST_TARGETS);

www/tests/%.mk: www/tests/%.py
	cd www && \
	$(DEVEL_ENV) \
	python tests/`basename $<` -v \

www-translations:
	pybabel -v -q compile -d www/translations

# must be imvoked as root
www-configs-install: www-configs-install-production www-configs-install-testing;

www-configs-install-production:
	#creating required folders
	mkdir --mode=775 --parents /var/run/uwsgi
	chown www-data:www-data /var/run/uwsgi
	touch /var/run/uwsgi/$(NAME_PRODUCTION).reload
	chmod 664 /var/run/uwsgi/$(NAME_PRODUCTION).reload
	chown www-data:www-data /var/run/uwsgi/$(NAME_PRODUCTION).reload
	#installing uwsgi configs
	cp configs/uwsgi.production.conf /etc/uwsgi/apps-available/$(NAME_PRODUCTION).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_PRODUCTION).conf /etc/uwsgi/apps-enabled/$(NAME_PRODUCTION).conf
	#installing service configs
	cp configs/service.production.conf /etc/init/$(NAME_PRODUCTION).conf
	stop $(NAME_PRODUCTION); start $(NAME_PRODUCTION)
	#installing nginx configs
	cp configs/nginx.production.conf /etc/nginx/sites-available/$(NAME_PRODUCTION).conf
	ln -sf /etc/nginx/sites-available/$(NAME_PRODUCTION).conf /etc/nginx/sites-enabled/$(NAME_PRODUCTION).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	cp configs/logrotate.production.conf /etc/logrotate.d/$(NAME_PRODUCTION).conf

www-configs-install-testing:
	#creating required folders
	mkdir --mode=775 --parents /var/run/uwsgi
	chown www-data:www-data /var/run/uwsgi
	touch /var/run/uwsgi/$(NAME_TESTING).reload
	chmod 664 /var/run/uwsgi/$(NAME_TESTING).reload
	chown www-data:www-data /var/run/uwsgi/$(NAME_TESTING).reload
	#installing uwsgi configs
	cp configs/uwsgi.testing.conf /etc/uwsgi/apps-available/$(NAME_TESTING).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_TESTING).conf /etc/uwsgi/apps-enabled/$(NAME_TESTING).conf
	#installing service configs
	cp configs/service.testing.conf /etc/init/$(NAME_TESTING).conf
	stop $(NAME_TESTING); start $(NAME_TESTING)
	#installing nginx configs
	cp configs/nginx.testing.conf /etc/nginx/sites-available/$(NAME_TESTING).conf
	ln -sf /etc/nginx/sites-available/$(NAME_TESTING).conf /etc/nginx/sites-enabled/$(NAME_TESTING).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	cp configs/logrotate.testing.conf /etc/logrotate.d/$(NAME_TESTING).conf

www-reload-testing: www-test www-translations
	touch $(TOUCH_RELOAD_TESTING)

www-reload-production: www-test www-translations
	touch $(TOUCH_RELOAD_PRODUCTION)

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

distclean:
	git clean -f
	
rebuild: distclean all.mk;

test: www-test;
