BIB_FILES=\
	american.bib \
	australian.bib \
	czech.bib \
	danish.bib \
	dutch.bib \
	english.bib \
	french.bib \
	german.bib \
	hda.bib \
	images.bib \
	italian.bib \
	polish.bib \
	portuguese.bib \
	problems.bib \
	rothenfelser.bib \
	russian.bib \
	spanish.bib \
	spbconf.bib \

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
	rm -f *.blg *.log *.aux *.bbl *.swp