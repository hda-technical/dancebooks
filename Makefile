NAME := dancebooks
NAME_TESTING := $(NAME).testing

TOUCH_RELOAD_TESTING := /var/run/uwsgi/$(NAME_TESTING).reload
TOUCH_RELOAD_PRODUCTION := /var/run/uwsgi/$(NAME).reload
DHPARAM_TESTING := /etc/nginx/conf/bib-test.hda.org.ru/dh_param.pem
DHPARAM_PRODUCTION := /etc/nginx/conf/bib.hda.org.ru/dh_param.pem

TESTS := $(wildcard tests/*.py)
TEST_TARGETS := $(TESTS:.py=.mk)

debug: translations
	python www/main.py \

test: $(TEST_TARGETS);

tests/%.mk: tests/%.py
	DANCEBOOKS_UNITTEST= \
	python $^ -v \

translations:
	pybabel -v -q compile -d www/translations

# must be invoked as root
configs-install: configs-install-production configs-install-testing;

configs-install-production:
	#creating directory for logs
	install --mode=755 --owner=www-data --group=www-data --directory /var/log/uwsgi/app
	install --mode 755 --owner www-data --group=www-data --directory /var/log/$(NAME)
	#installing uwsgi configs
	install --owner=www-data --group=www-data configs/uwsgi.production.conf /etc/uwsgi/apps-available/$(NAME).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME).conf /etc/uwsgi/apps-enabled/$(NAME).conf
	#creating upstart/systemd service
	install --mode=644 configs/systemd.production.conf /etc/systemd/system/$(NAME).service
	$(shell systemctl daemon-reload && systemctl enable $(NAME).service && systemctl stop $(NAME).service; systemctl start $(NAME).service || true)
	#generating custom dh_param.pem if needed
	if [ ! -f "$(DHPARAM_PRODUCTION)" ]; \
	then \
		echo "Generating custom dh_param at /tmp/dh_param.pem"; \
		openssl dhparam -out "/tmp/dh_param.pem" 2048; \
		install --mode=700 --owner=www-data --group=www-data --directory "$(dir $(DHPARAM_PRODUCTION))"; \
		install --mode=600 --owner=www-data --group=www-data "/tmp/dh_param.pem" "$(DHPARAM_PRODUCTION)"; \
		rm "/tmp/dh_param.pem"; \
	fi
	#installing nginx configs
	install --owner=www-data --group=www-data configs/nginx.production.conf /etc/nginx/sites-available/$(NAME).conf
	ln -sf /etc/nginx/sites-available/$(NAME).conf /etc/nginx/sites-enabled/$(NAME).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	install configs/logrotate.production.conf /etc/logrotate.d/$(NAME).conf

configs-install-testing:
	#creating directory for logs
	install --mode=755 --owner=www-data --group=www-data --directory /var/log/uwsgi/app
	install --mode 755 --owner www-data --group=www-data --directory /var/log/$(NAME_TESTING)
	#installing uwsgi configs
	install --owner=www-data --group=www-data configs/uwsgi.testing.conf /etc/uwsgi/apps-available/$(NAME_TESTING).conf
	ln -sf /etc/uwsgi/apps-available/$(NAME_TESTING).conf /etc/uwsgi/apps-enabled/$(NAME_TESTING).conf
	#creating upstart/systemd service
	install --mode=644 configs/systemd.testing.conf /etc/systemd/system/$(NAME_TESTING).service
	$(shell systemctl daemon-reload && systemctl enable $(NAME_TESTING).service && systemctl stop $(NAME_TESTING).service; systemctl start $(NAME_TESTING).service || true)
	#generating custom dh_param.pem if needed
	if [ ! -f "$(DHPARAM_TESTING)" ]; \
	then \
		echo "Generating custom dh_param at /tmp/dh_param.pem"; \
		openssl dhparam -out "/tmp/dh_param.pem" 2048; \
		install --mode=700 --owner=www-data --group=www-data --directory "$(dir $(DHPARAM_TESTING))"; \
		install --mode=600 --owner=www-data --group=www-data "/tmp/dh_param.pem" "$(DHPARAM_TESTING)"; \
		rm "/tmp/dh_param.pem"; \
	fi
	#installing nginx configs
	install --owner=www-data --group=www-data configs/nginx.testing.conf /etc/nginx/sites-available/$(NAME_TESTING).conf
	ln -sf /etc/nginx/sites-available/$(NAME_TESTING).conf /etc/nginx/sites-enabled/$(NAME_TESTING).conf
	service nginx reload
	#installing logrotate configs (no reload / restart is required)
	install configs/logrotate.testing.conf /etc/logrotate.d/$(NAME_TESTING).conf

reload-testing: test translations
	@echo "Reloading"
	bash -c "time -p (touch $(TOUCH_RELOAD_TESTING) && sleep 1 && curl --max-time 60 'https://bib-test.hda.org.ru/ping')"

reload-production: test translations
	@echo "Reloading"
	bash -c "time -p (touch $(TOUCH_RELOAD_PRODUCTION) && sleep 1 && curl --max-time 60 'https://bib.hda.org.ru/ping')"

requirements.txt:
	pip list --local --format=freeze | sort --ignore-case | tee $@

# Ancillary targets

.PHONY: requirements.txt
