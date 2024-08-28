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

all:  dragonlog/__version__.py ui_files i18n $(MD_FILES)

*.md:
	cp $@ dragonlog/data

ui_files:
	$(MAKE) -C ui_files

i18n:
	$(MAKE) -C i18n NO_OBSOLETE=$(NO_OBSOLETE)

dragonlog/__version__.py:
	echo __version__ = \'$(VERSION)\' > $@
	echo __version_str__ = \'$(VER)\' >> $@
	echo __branch__ = \'$(BRANCH)\' >> $@
	echo __unclean__ = $(UNCLEAN) >> $@

bdist_msi: NO_OBSOLETE=-no-obsolete
bdist_msi: clean all
	python setup_msi.py bdist -d dist_exe bdist_msi -d dist_exe;

dist: NO_OBSOLETE=-no-obsolete
dist: clean all
	python -m pip install --upgrade pip;
	python -m pip install --upgrade build;
	python -m build;

release:
	python -m pip install --upgrade twine;
	python -m twine upload dist/*;

.PHONY: dragonlog/__version__.py ui_files i18n $(MD_FILES)

clean:
	rm -rf build
	rm -rf dist
	rm -f dragonlog/__version__.py
	rm -f dragonlog/data/*.md
	$(MAKE) -C ui_files clean
	$(MAKE) -C i18n clean
