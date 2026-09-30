# GNU make required (Linux: make; FreeBSD/macOS: gmake).
PREFIX ?= /usr/local
PYTHON ?= python3
BINNAME := m3utolocal
MANDIR ?= $(PREFIX)/share/man/man1
DESTDIR ?=

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
FRAGMENT_OS := linux
else ifeq ($(UNAME_S),FreeBSD)
FRAGMENT_OS := freebsd
else ifeq ($(UNAME_S),Darwin)
FRAGMENT_OS := darwin
else
$(error unsupported OS: $(UNAME_S))
endif

.PHONY: all build install uninstall test test-unit package \
	sync-freebsd test-freebsd clean help install-port \
	deb install-deb uninstall-deb

all: build

build:
	$(PYTHON) -m build

_effective_prefix = $(PREFIX)

install: 
	@prefix="$(PREFIX)"; \
	if [ -z "$(DESTDIR)" ]; then \
		if [ ! -d "$$prefix" ]; then \
			mkdir -p "$$prefix" 2>/dev/null || true; \
		fi; \
		if [ ! -w "$$prefix" ]; then \
			prefix="$(HOME)/.local"; \
			echo "PREFIX $(PREFIX) not writable; installing to $$prefix"; \
		fi; \
	fi; \
	if [ ! -d dist ] || ! ls dist/$(BINNAME)-*.whl >/dev/null 2>&1; then \
		$(PYTHON) -m build || $(PYTHON) -m pip wheel -w dist --no-deps .; \
	fi; \
	wheel=$$(ls -1 dist/$(BINNAME)-*.whl 2>/dev/null | tail -1); \
	if [ -z "$$wheel" ]; then \
		echo "error: no wheel in dist/; build failed" >&2; \
		exit 1; \
	fi; \
	root_args=""; \
	if [ -n "$(DESTDIR)" ]; then root_args="--root=$(DESTDIR)"; fi; \
	$(PYTHON) -m pip install $$root_args --prefix="$$prefix" --no-deps --force-reinstall --disable-pip-version-check "$$wheel"; \
	bindir="$(DESTDIR)$$prefix/bin"; \
	mkdir -p "$$bindir"; \
	cp scripts/$(BINNAME) "$$bindir/$(BINNAME)"; \
	chmod 755 "$$bindir/$(BINNAME)"; \
	mandir="$(DESTDIR)$$prefix/share/man/man1"; \
	mkdir -p "$$mandir"; \
	cp man/$(BINNAME).1 "$$mandir/"; \
	echo "Installed $(BINNAME) to $$bindir/$(BINNAME)"

uninstall:
	@prefix="$(PREFIX)"; \
	if [ -z "$(DESTDIR)" ] && [ ! -w "$$prefix/bin/$(BINNAME)" ] && [ -x "$(HOME)/.local/bin/$(BINNAME)" ]; then \
		prefix="$(HOME)/.local"; \
	fi; \
	rm -f "$(DESTDIR)$$prefix/bin/$(BINNAME)"; \
	rm -f "$(DESTDIR)$$prefix/share/man/man1/$(BINNAME).1"; \
	$(PYTHON) -c "import pathlib,sysconfig; p=pathlib.Path(sysconfig.get_path('purelib', vars={'base':'$$prefix','platbase':'$$prefix'}))/'m3utolocal'; import shutil; shutil.rmtree(p, ignore_errors=True); print('removed', p)"

test:
	$(PYTHON) -m pytest -q || python3 -m pytest -q

test-unit:
	$(PYTHON) -m pytest -q tests/unit || python3 -m pytest -q tests/unit

REMOTE ?= mlapointe@172.16.176.133
REMOTE_DIR ?= ~/src/m3utolocal

sync-freebsd:
	rsync -avz --delete \
		--exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '.idea' \
		-e ssh ./ $(REMOTE):$(REMOTE_DIR)/

test-freebsd: sync-freebsd
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && python3.12 -m pytest -q'

package:
ifeq ($(FRAGMENT_OS),linux)
	./scripts/build-deb
else ifeq ($(FRAGMENT_OS),freebsd)
	@echo "FreeBSD: copy ports/net/m3utolocal into the ports tree and run make package"
else ifeq ($(FRAGMENT_OS),darwin)
	@echo "macOS: brew install --formula packaging/homebrew/m3utolocal.rb"
endif

deb:
	./scripts/build-deb

install-deb: deb
	@deb=$$(ls -1t dist/$(BINNAME)_*.deb 2>/dev/null | head -1); \
	if [ -z "$$deb" ]; then \
		echo "error: no .deb found in dist/" >&2; \
		exit 1; \
	fi; \
	echo "Installing $$deb..."; \
	if [ "$$(id -u)" -eq 0 ]; then \
		apt install -y "./$$deb"; \
	elif command -v sudo >/dev/null 2>&1; then \
		sudo apt install -y "./$$deb"; \
	elif command -v doas >/dev/null 2>&1; then \
		doas apt install -y "./$$deb"; \
	else \
		apt install -y "./$$deb"; \
	fi

uninstall-deb:
	@echo "Removing $(BINNAME) package..."; \
	if [ "$$(id -u)" -eq 0 ]; then \
		apt remove -y $(BINNAME); \
	elif command -v sudo >/dev/null 2>&1; then \
		sudo apt remove -y $(BINNAME); \
	elif command -v doas >/dev/null 2>&1; then \
		doas apt remove -y $(BINNAME); \
	else \
		apt remove -y $(BINNAME); \
	fi

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

install-port:
	mkdir -p $(DESTDIR)/usr/ports/net/m3utolocal
	cp ports/net/m3utolocal/Makefile $(DESTDIR)/usr/ports/net/m3utolocal/
	cp ports/net/m3utolocal/pkg-descr $(DESTDIR)/usr/ports/net/m3utolocal/

help:
	@echo "Usage:"
	@echo "  make                 - build sdist and wheel"
	@echo "  make install         - install $(BINNAME) to PREFIX ($(PREFIX))"
	@echo "  make uninstall       - remove $(BINNAME)"
	@echo "  make deb             - build Debian package (.deb)"
	@echo "  make install-deb     - build and install Debian package (.deb)"
	@echo "  make uninstall-deb   - remove installed Debian package"
	@echo "  make test            - run pytest"
	@echo "  make package         - OS package ($(FRAGMENT_OS))"
	@echo "  make test-freebsd    - sync + pytest on app-test-001"
	@echo "  make && make install - build then install (use doas/sudo only for install)"
