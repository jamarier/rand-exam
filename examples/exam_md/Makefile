# ls exam.yaml bank/* Makefile| entr make clean all

BINDIR=../..

.PHONY: all
all:
	$(BINDIR)/rand-exam.py exam.yaml
	pandoc exam_english.md -o exam_english.pdf
	pandoc exam_spanish.md -o exam_spanish.pdf


.PHONY: clean
clean:
	rm -rf *_english*.md
	rm -rf *_spanish*.md
	rm -rf *.pdf

.PHONY: install
install:
	rm -rf env 
	python -mvenv env
	. ./env/bin/activate && pip install -r $(BINDIR)/requirements.txt

