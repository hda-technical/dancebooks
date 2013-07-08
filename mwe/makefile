mwe.pdf: mwe.tex
	pdflatex $<
	biber '--listsep=|' --validate_datamodel --quiet ${@:.pdf=}
	pdflatex $<
	echo "Build completed"
	
mwe.tar.gz: clean-mwe
	tar czvf $@ *
	
clean-mwe:
	rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.cfg 
	rm -f mwe.bib
	echo "Clean mwe completed"
	
purge-mwe: clean-mwe
	rm -f *.pdf
	echo "Purge mwe completed"
	
rebuild-mwe: purge-mwe mwe.pdf
	