BINDIR=../..

.PHONY: all
all:
	$(BINDIR)/rand-exam.py exam.yaml

.PHONY: clean
clean:
	rm -rf *_description*.txt
	rm -rf *_notes*.txt

.PHONY: install
install:
	rm -rf env 
	python -mvenv env
	. ./env/bin/activate && pip install -r $(BINDIR)/requirements.txt

