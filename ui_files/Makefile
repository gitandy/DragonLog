UI_FILES = $(wildcard *.ui)
PYUI_FILES = $(UI_FILES:.ui=_ui.py)

all:  $(PYUI_FILES)

%_ui.py: %.ui
	pyuic6 -o $@ $<;
	cp $@ ../dragonlog;

clean:
	rm -f *_ui.py
	rm -f ../dragonlog/*_ui.py
