BIB_FILES=\
	bib/american.bib \
	bib/anuario-musical.bib \
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
	bib/journal-of-musicology.bib \
	bib/polish.bib \
	bib/portuguese.bib \
	bib/problems.bib \
	bib/proceedings-rothenfelser.bib \
	bib/proceedings-spb.bib \
	bib/russian.bib \
	bib/spanish.bib \

ANC_FILES_BIBLATEX=\
	dancebooks-biblatex.sty \

MARKDOWN_FILES=\
	transcriptions/[1706,\ uk]\ Raoul-Auger\ Feuillet\ -\ Orchesography\ or\ The\ Art\ of\ Dancing.md \
	transcriptions/[1825,\ ru]\ Людовик\ Петровский\ -\ Правила\ для\ благородных\ общественных\ танцев.md \
	transcriptions/[2011,\ ru]\ Оксана\ Захарова\ -\ Русский\ бал\ XVIII\ -\ начала\ XX\ века.md \
	transcriptions/[2000,\ ru]\ Агриппина\ Яковлевна\ Ваганова\ -\ Основы\ классического\ танца.md

ANC_MARKDOWN_FILES=\
	transcriptions/_markdown2.py \
	transcriptions/_reset.css \
	transcriptions/_style.css \
	
HTML_FILES=$(MARKDOWN_FILES:.md=.html)

test-biblatex.pdf: test-biblatex.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f test-biblatex.bbl biblatex-dm.cfg
	@pdflatex test-biblatex.tex
	@biber --validate_datamodel --quiet test-biblatex
	@pdflatex test-biblatex.tex
	@echo "Build completed"

test-biblatex-detailed.pdf: test-biblatex-detailed.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f test-biblatex-detailed.bbl biblatex-dm.cfg
	@pdflatex test-biblatex-detailed.tex
	@biber --validate_datamodel --quiet test-biblatex-detailed
	@pdflatex test-biblatex-detailed.tex
	@echo "Build completed"

all.dependency: test-biblatex.pdf test-biblatex-detailed.pdf transcriptions
	@echo "Build all completed"
	@touch all.dependency

upload.dependency: test-biblatex.pdf test-biblatex-detailed.pdf
	chmod 644 test-biblatex.pdf
	chmod 644 test-biblatex-detailed.pdf
	scp -p \
		test-biblatex.pdf \
		test-biblatex-detailed.pdf \
		georg@iley.ru:/home/georg/leftparagraphs/static/files/
	@touch upload.dependency

%.html: %.md $(ANC_MARKDOWN_FILES)
	./transcriptions/_markdown2.py --input "$<" --output "$@"

transcriptions: $(HTML_FILES)
	@echo "Compiling transcriptions completed"

entrycount: $(BIB_FILES)
	@cat $(BIB_FILES) | grep -c --color '@'
	
rebuild: purge all.dependency
	@echo "Rebuild completed"

purge: clean
	@rm -f *.pdf *.dependency transcriptions/*.html
	@echo "Purge completed"

clean:
	@rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml *.cfg
	@echo "Clean completed"
