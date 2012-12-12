BIB_FILES=\
	bib/american.bib \
	bib/australian.bib \
	bib/canadian.bib \
	bib/czech.bib \
	bib/danish.bib \
	bib/dutch.bib \
	bib/english.bib \
	bib/french.bib \
	bib/german.bib \
	bib/hda.bib \
	bib/italian.bib \
	bib/polish.bib \
	bib/portuguese.bib \
	bib/problems.bib \
	bib/rothenfelser.bib \
	bib/russian.bib \
	bib/spanish.bib \
	bib/spbconf.bib \

ANC_FILES_BIBTEX=\
	bst/gost-authoryear.bst \
	sty/dancebooks-bibtex.sty \
	Makefile \
	
ANC_FILES_BIBLATEX=\
	sty/dancebooks-biblatex.sty \
	lbx/czech.lbx \
	Makefile \
	
all: purge test-biblatex.pdf test-bibtex.pdf
	@echo "Build all completed"

test-biblatex.pdf: test-biblatex.tex $(BIB_FILES) $(ANC_FILES-BIBLATEX)
	@rm -f test-biblatex.bbl
	@pdflatex test-biblatex.tex
	@biber test-biblatex
	@pdflatex test-biblatex.tex
	@echo "Build completed"
	
test-bibtex.pdf: test-bibtex.tex $(BIB_FILES) $(ANC_FILES_BIBTEX)
	@rm -f test-bibtex.bbl
	@pdflatex test-bibtex.tex
	@bibtex8 --wolfgang -c cp1251 test-bibtex
	@pdflatex test-bibtex.tex
	@pdflatex test-bibtex.tex
	@echo "Build completed"

rebuild: purge all
	@echo "Rebuild completed"

purge: clean
	@rm -f *.pdf
	@echo "Purge completed"
	
clean:
	@rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml 
	@echo "Clean completed"
	