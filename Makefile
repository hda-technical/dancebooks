BIB_FILES=\
	russian.bib \
	german.bib \
	french.bib \
	english.bib \
	spanish.bib \
	italian.bib \
	danish.bib \
	portuguese.bib \
	rothenfelser.bib \
	spbconf.bib \
	dutch.bib \
	american.bib \
	australian.bib \
	polish.bib \
	czech.bib \

ANC_FILES=\
	style.bst \
	Makefile

test: test.tex $(BIB_FILES) $(ANC_FILES)
	rm -f test.bbl
	pdflatex test.tex
	bibtex8 --mwizfuns 4000 -c cp1251 test
	pdflatex test.tex
	pdflatex test.tex
	
purge: clean
	rm *.pdf
	
clean:
	rm -f *.blg *.log *.aux *.bbl