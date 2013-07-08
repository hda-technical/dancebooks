mwe.pdf: mwe.tex mwe.bib
	@pdflatex --max-print-line=250 $<
	@biber '--listsep=|' --validate_datamodel --quiet ${@:.pdf=}
	@pdflatex --max-print-line=250 $<
	@grep -iqE "Datamodel" ${@:.pdf=.log} || true
	@echo "Build completed"
	
mwe.tar.gz: clean-mwe
	tar czvf $@ *
	
clean-mwe:
	@rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.cfg
	@echo "Clean mwe completed"
	
purge-mwe: clean-mwe
	@rm -f *.pdf
	@echo "Purge mwe completed"
	
rebuild-mwe: purge-mwe mwe.pdf
	