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
	Makefile \

test.pdf: test.tex $(BIB_FILES) $(ANC_FILES)
	@rm -f test.bbl
	@pdflatex test.tex
	@bibtex8 --wolfgang -c cp1251 test
	@pdflatex test.tex
	@pdflatex test.tex
	@echo "Build completed"
	
purge: clean
	@rm -f *.pdf
	@echo "Purge completed"
	
clean:
	@rm -f *.blg *.log *.aux *.bbl *.swp *.bcf *.toc
	@echo "Clean completed"