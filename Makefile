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
	dancebooks-bibtex.sty \
	dancebooks-biblatex.sty \
	Makefile \

all: purge biblatex bibtex
	@echo "Build all completed"

biblatex: test-biblatex.tex $(BIB_FILES) $(ANC_FILES)
	rm -f test-biblatex.bbl
	pdflatex test-biblatex.tex
	biber test-biblatex
	pdflatex test-biblatex.tex
	pdflatex test-biblatex.tex
	echo "Build completed"
	
bibtex: test-bibtex.tex $(BIB_FILES) $(ANC_FILES)
	rm -f test-bibtex.bbl
	pdflatex test-bibtex.tex
	bibtex8 --wolfgang -c cp1251 test-bibtex
	pdflatex test-bibtex.tex
	pdflatex test-bibtex.tex
	echo "Build completed"
	
purge: clean
	rm -f *.pdf
	echo "Purge completed"
	
clean:
	rm -f *.blg *.log *.aux *.bbl *.swp *.bcf *.toc
	echo "Clean completed"