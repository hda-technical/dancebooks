NAME := dancebooks
NAME_TESTING := $(NAME).testing

#Using testing conf-file in development environment
UNITTEST_CONFIG := $(shell readlink -f configs/dancebooks.unittest.conf)
DEVEL_CONFIG := $(shell readlink -f configs/dancebooks.development.conf)
PRODUCTION_CONFIG := $(shell readlink -f configs/dancebooks.production.conf)
LOGGING_CONFIG := $(shell readlink -f configs/logger.development.conf)

TOUCH_RELOAD_TESTING := /var/run/uwsgi/$(NAME_TESTING).reload
TOUCH_RELOAD_PRODUCTION := /var/run/uwsgi/$(NAME).reload
DHPARAM_TESTING := /etc/nginx/conf/bib-test.hda.org.ru/dh_param.pem
DHPARAM_PRODUCTION := /etc/nginx/conf/bib.hda.org.ru/dh_param.pem

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

validate:
	cd www && \
	$(DEVEL_ENV) \
	python _validate.py \
	$(ARGS)

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
	install --mode=775 --owner=www-data --group=www-data --directory /var/run/uwsgi
	install --mode 755 --owner www-data --group=www-data --directory /var/log/dancebooks
	#installing uwsgi configs
	install --owner=www-data --group=www-data configs/uwsgi.production.conf /etc/uwsgi/apps-available/$(NAME).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME).conf /etc/uwsgi/apps-enabled/$(NAME).conf
	#installing service configs
	install configs/service.production.conf /etc/init/$(NAME).conf
	initctl reload-configuration
	stop $(NAME); start $(NAME)
	#generating custom dh_param.pem if needed
	if [ ! -f "$(DHPARAM_PRODUCTION)" ]; \
	then \
		echo "Generating custom dh_param at /tmp/dh_param.pem"; \
		openssl dhparam -out "/tmp/dh_param.pem" 2048; \
		install --mode=600 --owner=www-data --group=www-data "/tmp/dh_param.pem" "$(DHPARAM_PRODUCTION)"; \
		rm "/tmp/dh_param.pem"; \
	fi
	#installing nginx configs
	install --owner=www-data --group=www-data configs/nginx.production.conf /etc/nginx/sites-available/$(NAME).conf
	ln -sf /etc/nginx/sites-available/$(NAME).conf /etc/nginx/sites-enabled/$(NAME).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	install configs/logrotate.production.conf /etc/logrotate.d/$(NAME).conf

www-configs-install-testing:
	install --mode=775 --owner=www-data --group=www-data --directory /var/run/uwsgi
	install --mode 755 --owner www-data --group=www-data --directory /var/log/dancebooks.testing
	#installing uwsgi configs
	install --owner=www-data --group=www-data configs/uwsgi.testing.conf /etc/uwsgi/apps-available/$(NAME_TESTING).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_TESTING).conf /etc/uwsgi/apps-enabled/$(NAME_TESTING).conf
	#installing service configs
	install configs/service.testing.conf /etc/init/$(NAME_TESTING).conf
	initctl reload-configuration
	stop $(NAME_TESTING); start $(NAME_TESTING)
	#generating custom dh_param.pem if needed
	if [ ! -f "$(DHPARAM_TESTING)" ]; \
	then \
		echo "Generating custom dh_param at /tmp/dh_param.pem"; \
		openssl dhparam -out "/tmp/dh_param.pem" 2048; \
		install --mode=600 --owner=www-data --group=www-data "/tmp/dh_param.pem" "$(DHPARAM_TESTING)"; \
		rm "/tmp/dh_param.pem"; \
	fi
	#installing nginx configs
	install --owner=www-data --group=www-data configs/nginx.testing.conf /etc/nginx/sites-available/$(NAME_TESTING).conf
	ln -sf /etc/nginx/sites-available/$(NAME_TESTING).conf /etc/nginx/sites-enabled/$(NAME_TESTING).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	install configs/logrotate.testing.conf /etc/logrotate.d/$(NAME_TESTING).conf

www-reload-testing: www-test www-translations
	@echo "Reloading"
	bash -c "time -p (touch $(TOUCH_RELOAD_TESTING) && sleep 1 && curl --max-time 60 'https://bib-test.hda.org.ru/ping')"

www-reload-production: www-test www-translations
	@echo "Reloading"
	bash -c "time -p (touch $(TOUCH_RELOAD_PRODUCTION) && sleep 1 && curl --max-time 60 'https://bib.hda.org.ru/ping')"

requirements.txt:
	pip freeze --local | sort --ignore-case | tee $@

# Ancillary targets

.PHONY: requirements.txt

test: www-test;
