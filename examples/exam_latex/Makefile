# ls exam.yaml bank/* Makefile| entr make clean all

BINDIR=../..

.PHONY: all
all: catalogo_profesor.pdf catalogo_alumno.pdf catalogo_pantalla_alumno.pdf

catalogo_profesor.tex catalogo_alumno.tex: catalogo.yaml
	$(BINDIR)/rand-exam.py $<

catalogo_pantalla_profesor.tex catalogo_pantalla_alumno.tex: catalogo_pantalla.yaml
	$(BINDIR)/rand-exam.py $<

%.pdf: %.tex
	pdflatex $< 

.PHONY: clean
clean:
	rm -rf *.aux *.log *.out
	rm -rf *.tex
	rm -rf *.pdf

.PHONY: install
install:
	rm -rf env 
	python -mvenv env
	. ./env/bin/activate && pip install -r $(BINDIR)/requirements.txt

