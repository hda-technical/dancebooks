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

ANC_FILES_BIBTEX=\
	gost-authoryear.bst \
	dancebooks-bibtex.sty \
	Makefile \
	
ANC_FILES_BIBLATEX=\
	dancebooks-biblatex.sty \
	gost-authoryear.bbx \
	gost-authoryear.cbx \
	gost-standard.bbx \
	Makefile \
	russian-gost.lbx \
	
all: purge biblatex bibtex
	@echo "Build all completed"

biblatex: test-biblatex.tex $(BIB_FILES) $(ANC_FILES-BIBLATEX)
	rm -f test-biblatex.bbl
	pdflatex test-biblatex.tex
	biber test-biblatex
	pdflatex test-biblatex.tex
	pdflatex test-biblatex.tex
	echo "Build completed"
	
bibtex: test-bibtex.tex $(BIB_FILES) $(ANC_FILES_BIBTEX)
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
	rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml 
	echo "Clean completed"