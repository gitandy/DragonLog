VENV_DIR = venv
VER = $(shell git describe --tags)
VERSION = $(firstword $(subst -, ,$(VER)))
ifeq ($(shell git diff --name-only),)
UNCLEAN = "False"
else
UNCLEAN = "True"
endif

BRANCH = $(shell git rev-parse --abbrev-ref HEAD)
MD_FILES = $(wildcard *.md)
NO_OBSOLETE=

ifeq ($(OS),Windows_NT)
VENV_BIN = $(VENV_DIR)/Scripts
ifeq ($(shell if test -d $(VENV_DIR); then echo "exist";fi),exist)
PYTHON = $(VENV_BIN)/python.exe
endif
else
VENV_BIN = $(VENV_DIR)/bin
ifeq ($(shell if test -d $(VENV_DIR); then echo "exist";fi),exist)
PYTHON = $(VENV_BIN)/python
endif
endif

all:  dragonlog/__version__.py ui_files i18n $(MD_FILES)

*.md: contests_md
	cp $@ dragonlog/data

contests_md:
	$(PYTHON) -m dragonlog.contest AVAILABLE_CONTESTS.md

ui_files:
	$(MAKE) -C ui_files VENV_BIN=../$(VENV_BIN)

i18n:
	$(MAKE) -C i18n NO_OBSOLETE=$(NO_OBSOLETE) VENV_BIN=../$(VENV_BIN)

dragonlog/__version__.py:
	echo __version__ = \'$(VERSION)\' > $@
	echo __version_str__ = \'$(VER)\' >> $@
	echo __branch__ = \'$(BRANCH)\' >> $@
	echo __unclean__ = $(UNCLEAN) >> $@

bdist_msi: NO_OBSOLETE=-no-obsolete
bdist_msi: clean all
	$(PYTHON) setup_msi.py bdist -d dist_exe bdist_msi -d dist_exe;

dist: NO_OBSOLETE=-no-obsolete
dist: clean all
	$(PYTHON) -m pip install --upgrade pip;
	$(PYTHON) -m pip install --upgrade build;
	$(PYTHON) -m build;

release:
	$(PYTHON) -m pip install --upgrade twine;
	$(PYTHON) -m twine upload dist/*;

.PHONY: dragonlog/__version__.py ui_files i18n $(MD_FILES)

clean:
	rm -rf build
	rm -rf dist
	rm -f dragonlog/__version__.py
	rm -f dragonlog/data/*.md
	$(MAKE) -C ui_files clean
	$(MAKE) -C i18n clean
