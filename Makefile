PREFIX ?= /usr/local
# FreeBSD default after Python ports upgrade; override on Linux if needed
PYTHON ?= python3.12
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/share/man/man1
PORTSDIR ?= /usr/ports
REMOTE ?= mlapointe@172.16.176.133
REMOTE_DIR ?= ~/src/m3utolocal

.PHONY: all install uninstall run clean help install-port install-deps \
	install-freebsd install-ubuntu install-generic test test-unit \
	sync-freebsd test-freebsd

all: help

install: install-deps
	mkdir -p $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(MANDIR)
	sed "1s|.*|#!$$(command -v $(PYTHON) \|\| command -v python3)|" main.py > $(DESTDIR)$(BINDIR)/m3utolocal
	chmod 755 $(DESTDIR)$(BINDIR)/m3utolocal
	cp utils.py tui.py download_manager.py downloader.py $(DESTDIR)$(BINDIR)/
	cp -R m3utolocal $(DESTDIR)$(BINDIR)/
	chmod 644 $(DESTDIR)$(BINDIR)/utils.py $(DESTDIR)$(BINDIR)/tui.py \
		$(DESTDIR)$(BINDIR)/download_manager.py $(DESTDIR)$(BINDIR)/downloader.py
	cp man/m3utolocal.1 $(DESTDIR)$(MANDIR)/
	chmod 644 $(DESTDIR)$(MANDIR)/m3utolocal.1

install-deps:
	@if [ "$$(uname -s)" = "FreeBSD" ]; then \
		$(MAKE) install-freebsd; \
	elif [ "$$(uname -s)" = "Linux" ]; then \
		if [ -f /etc/os-release ] && grep -qi ubuntu /etc/os-release; then \
			$(MAKE) install-ubuntu; \
		else \
			$(MAKE) install-generic; \
		fi \
	else \
		$(MAKE) install-generic; \
	fi

install-freebsd:
	@echo "Installing dependencies for FreeBSD (Python 3.12)..."
	pkg install -y python312 py312-requests

install-ubuntu:
	@echo "Installing dependencies for Ubuntu..."
	apt-get update && apt-get install -y python3-requests python3-pytest || true
	$(PYTHON) -m pip install -r requirements.txt || python3 -m pip install -r requirements.txt

install-generic:
	@echo "Installing dependencies via pip..."
	$(PYTHON) -m pip install -r requirements.txt || python3 -m pip install -r requirements.txt

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/m3utolocal
	rm -f $(DESTDIR)$(BINDIR)/utils.py
	rm -f $(DESTDIR)$(BINDIR)/tui.py
	rm -f $(DESTDIR)$(BINDIR)/download_manager.py
	rm -f $(DESTDIR)$(BINDIR)/downloader.py
	rm -rf $(DESTDIR)$(BINDIR)/m3utolocal
	rm -f $(DESTDIR)$(MANDIR)/m3utolocal.1

run:
	./main.py $(ARGS)

test:
	$(PYTHON) -m pytest -q || python3 -m pytest -q

test-unit:
	$(PYTHON) -m pytest -q tests/unit || python3 -m pytest -q tests/unit

sync-freebsd:
	rsync -avz --delete \
		--exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '.idea' \
		-e ssh ./ $(REMOTE):$(REMOTE_DIR)/

test-freebsd: sync-freebsd
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && python3.12 -m pytest -q'

clean:
	rm -rf downloads/
	rm -f *.tmp_*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:
	@echo "Usage:"
	@echo "  make install         - Install m3utolocal to $(BINDIR)"
	@echo "  make uninstall       - Remove m3utolocal"
	@echo "  make test            - Run pytest"
	@echo "  make sync-freebsd    - rsync to app-test-001"
	@echo "  make test-freebsd    - sync + pytest on FreeBSD host"
	@echo "  make run ARGS='...'  - Run locally"
	@echo "  make clean           - Remove temp artifacts"
	@echo "  make install-port    - Copy port files to $(PORTSDIR)"

install-port:
	mkdir -p $(DESTDIR)$(PORTSDIR)/net/m3utolocal
	cp ports/net/m3utolocal/Makefile $(DESTDIR)$(PORTSDIR)/net/m3utolocal/
	cp ports/net/m3utolocal/pkg-descr $(DESTDIR)$(PORTSDIR)/net/m3utolocal/
