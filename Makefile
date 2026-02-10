PREFIX ?= /usr/local
PYTHON ?= python3.11
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/share/man/man1
PORTSDIR ?= /usr/ports

.PHONY: all install uninstall run clean help install-port

all: help

install:
	mkdir -p $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(MANDIR)
	sed "1s|.*|#!$$(which $(PYTHON))|" main.py > $(DESTDIR)$(BINDIR)/m3utolocal
	chmod 755 $(DESTDIR)$(BINDIR)/m3utolocal
	cp man/m3utolocal.1 $(DESTDIR)$(MANDIR)/
	chmod 644 $(DESTDIR)$(MANDIR)/m3utolocal.1
	$(PYTHON) -m pip install -r requirements.txt

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/m3utolocal
	rm -f $(DESTDIR)$(MANDIR)/m3utolocal.1

run:
	./main.py $(ARGS)

clean:
	rm -rf downloads/
	rm -f *.tmp_*

help:
	@echo "Usage:"
	@echo "  make install      - Install m3utolocal to $(BINDIR)"
	@echo "  make uninstall    - Remove m3utolocal"
	@echo "  make run ARGS='...' - Run the script locally"
	@echo "  make clean        - Remove downloads and temp files"
	@echo "  make install-port - Install port files to $(PORTSDIR)"

install-port:
	mkdir -p $(DESTDIR)$(PORTSDIR)/net/m3utolocal
	cp ports/net/m3utolocal/Makefile $(DESTDIR)$(PORTSDIR)/net/m3utolocal/
	cp ports/net/m3utolocal/pkg-descr $(DESTDIR)$(PORTSDIR)/net/m3utolocal/
	cp LICENSE $(DESTDIR)$(PORTSDIR)/net/m3utolocal/
