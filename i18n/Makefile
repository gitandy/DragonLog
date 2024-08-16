NO_OBSOLETE?=

TRANSLATIONS = de en templ
TS_FILES = $(foreach transl,$(TRANSLATIONS),DragonLog_$(transl).ts)
QM_FILES = $(TS_FILES:.ts=.qm)

all: $(QM_FILES)
	cp *.json ../dragonlog/data/i18n;

%.qm: %.ts
	pylupdate6 $(NO_OBSOLETE) ../dragonlog ../ui_files -ts $<;
	lrelease $< -qm $@;
	cp $@ ../dragonlog/data/i18n;

clean:
	rm -f *.qm
	rm -f ../dragonlog/data/i18n/*.qm
	rm -f ../dragonlog/data/i18n/*.json

