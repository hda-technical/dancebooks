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
	bst/gost-authoryear.bst \
	dancebooks-bibtex.sty \
	Makefile \
	
ANC_FILES_BIBLATEX=\
	dancebooks-biblatex.sty \
	lbx/czech.lbx \
	Makefile \
	
all: purge biblatex bibtex
	@echo "Build all completed"

biblatex: test-biblatex.tex $(BIB_FILES) $(ANC_FILES-BIBLATEX)
	@rm -f test-biblatex.bbl
	@pdflatex test-biblatex.tex 2>&1 #| cat > /dev/null
	@biber test-biblatex 2>&1 #| grep -q  -E "INFO|WARN|ERR" || true
	@pdflatex test-biblatex.tex 2>&1 #| grep -q -E "Warning|Error" || true
	@echo "Build completed"
	
bibtex: test-bibtex.tex $(BIB_FILES) $(ANC_FILES_BIBTEX)
	@rm -f test-bibtex.bbl
	@pdflatex test-bibtex.tex 2>&1 | cat > /dev/null
	@bibtex8 --wolfgang -c cp1251 test-bibtex
	@pdflatex test-bibtex.tex 2>&1 | cat > /dev/null
	@pdflatex test-bibtex.tex 2>&1  | grep -q -E "Warning|Error" || true
	@echo "Build completed"

rebuild: purge all
	@echo "Rebuild completed"

purge: clean
	@rm -f *.pdf
	@echo "Purge completed"
	
clean:
	@rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml 
	@echo "Clean completed"
	