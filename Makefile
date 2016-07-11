NAME := dancebooks
NAME_TESTING := $(NAME).testing

BIB_FILES := $(wildcard bib/*.bib)

ANC_BIBLATEX_FILES := \
	dancebooks-biblatex.sty

PDFLATEX := pdflatex --shell-escape
LUALATEX := lualatex --shell-escape
XELATEX  := xelatex  --shell-escape
LATEX ?= $(LUALATEX)

#Using testing conf-file in development environment
UNITTEST_CONFIG := $(shell readlink -f configs/dancebooks.unittest.conf)
DEVEL_CONFIG := $(shell readlink -f configs/dancebooks.development.conf)
PRODUCTION_CONFIG := $(shell readlink -f configs/dancebooks.production.conf)
LOGGING_CONFIG := $(shell readlink -f configs/logger.development.conf)

TOUCH_RELOAD_TESTING := /var/run/uwsgi/$(NAME_TESTING).reload
TOUCH_RELOAD_PRODUCTION := /var/run/uwsgi/$(NAME).reload

UNITTEST_ENV := \
	CONFIG=$(UNITTEST_CONFIG) \
	LOGGING_CONFIG=$(LOGGING_CONFIG) \
	PYTHONPATH=. \

DEVEL_ENV := \
	CONFIG=$(DEVEL_CONFIG) \
	LOGGING_CONFIG=$(LOGGING_CONFIG) \
	PYTHONPATH=. \

TESTS := $(wildcard www/tests/*.py)
TEST_TARGETS := $(TESTS:.py=.mk)
# PDF files related targets

default: test.pdf

%.pdf: JOBNAME = $(@:.pdf=)

%.pdf: %.tex $(BIB_FILES) $(ANC_BIBLATEX_FILES)
	rm -f $(JOBNAME).bbl biblatex-dm.cfg
	$(LATEX) $(JOBNAME).tex
	biber '--listsep=|' '--namesep=|' '--xsvsep=\s*\|\s*' --validate_datamodel $(JOBNAME)
	$(LATEX) $(JOBNAME).tex
	(grep -iE "Datamodel" $(JOBNAME).blg || true) | cut -d ' ' -f 5- | sort | tee $(JOBNAME).validation.log

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
	$(UNITTEST_ENV) \
	python tests/`basename $<` -v \

www-translations:
	pybabel -v -q compile -d www/translations

# must be imvoked as root
www-configs-install: www-configs-install-production www-configs-install-testing www-configs-install-autoupdate;

www-configs-install-autoupdate:
	cp configs/autoupdate.cron.conf /etc/cron.d/dancebooks-autoupdate

www-configs-install-production:
	#creating required folders
	mkdir --mode=775 --parents /var/run/uwsgi
	chown www-data:www-data /var/run/uwsgi
	touch $(TOUCH_RELOAD_PRODUCTION)
	chmod 664 $(TOUCH_RELOAD_PRODUCTION)
	chown www-data:www-data $(TOUCH_RELOAD_PRODUCTION)
	#installing uwsgi configs
	cp configs/uwsgi.production.conf /etc/uwsgi/apps-available/$(NAME).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME).conf /etc/uwsgi/apps-enabled/$(NAME).conf
	#installing service configs
	cp configs/service.production.conf /etc/init/$(NAME).conf
	initctl reload-configuration
	stop $(NAME); start $(NAME)
	#installing nginx configs
	cp configs/nginx.production.conf /etc/nginx/sites-available/$(NAME).conf
	ln -sf /etc/nginx/sites-available/$(NAME).conf /etc/nginx/sites-enabled/$(NAME).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	cp configs/logrotate.production.conf /etc/logrotate.d/$(NAME).conf

www-configs-install-testing:
	#creating required folders
	mkdir --mode=775 --parents /var/run/uwsgi
	chown www-data:www-data /var/run/uwsgi
	touch $(TOUCH_RELOAD_TESTING)
	chmod 664 $(TOUCH_RELOAD_TESTING)
	chown www-data:www-data $(TOUCH_RELOAD_TESTING)
	#installing uwsgi configs
	cp configs/uwsgi.testing.conf /etc/uwsgi/apps-available/$(NAME_TESTING).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_TESTING).conf /etc/uwsgi/apps-enabled/$(NAME_TESTING).conf
	#installing service configs
	cp configs/service.testing.conf /etc/init/$(NAME_TESTING).conf
	initctl reload-configuration
	stop $(NAME_TESTING); start $(NAME_TESTING)
	#installing nginx configs
	cp configs/nginx.testing.conf /etc/nginx/sites-available/$(NAME_TESTING).conf
	ln -sf /etc/nginx/sites-available/$(NAME_TESTING).conf /etc/nginx/sites-enabled/$(NAME_TESTING).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	cp configs/logrotate.testing.conf /etc/logrotate.d/$(NAME_TESTING).conf

www-reload-testing: www-test www-translations
	@echo "Reloading"
	bash -c "time -p (touch $(TOUCH_RELOAD_TESTING) && sleep 1 && curl --max-time 60 'http://bib-test.hda.org.ru/bib/ping')"

www-reload-production: www-test www-translations
	@echo "Reloading"
	bash -c "time -p (touch $(TOUCH_RELOAD_PRODUCTION) && sleep 1 && curl --max-time 60 'https://bib.hda.org.ru/bib/ping')"

requirements.txt: .PHONY
	pip freeze --local | sort --ignore-case | tee $@

# Ancillary targets

.PHONY:;

all.mk: test.pdf;

entry-count: $(BIB_FILES)
	echo "Items:" `cat $^ | grep -c -P '@[A-Z]+'`
	echo "Digitized:" `cat $^ | grep -c -P '\tfilename = '`
	echo "With keywords:" `cat $^ | grep -c -P '\tkeywords = '`

clean: pdf-clean;

rebuild: distclean all.mk;

test: www-test;
