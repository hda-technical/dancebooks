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
	bib/proceedings-rothenfelser.bib \
	bib/proceedings-spb.bib \
	bib/russian.bib \
	bib/spanish.bib \

ANC_FILES_BIBTEX=\
	bst/gost-authoryear.bst \
	sty/dancebooks-bibtex.sty \

ANC_FILES_BIBLATEX=\
	sty/dancebooks-biblatex.sty \

MARKDOWN_FILES=\
	transcriptions/[15--,\ it]\ Giovanni\ e\ Il\ Lanzino\ e\ Il\ Papa\ -\ Manuscritto\ di\ baletti.md \
	transcriptions/[1706,\ uk]\ Raoul-Auger\ Feuillet\ -\ Orchesography\ or\ The\ Art\ of\ Dancing.md \
	transcriptions/[1819,\ fr]\ J.\ H.\ Gourdoux-Daux\ -\ Requeil\ de\ genre\ nouveau\ de\ contredanses\ et\ walses.md \
	transcriptions/[1825,\ ru]\ Людовик\ Петровский\ -\ Правила\ для\ благородных\ общественных\ танцев.md \
	transcriptions/[1828,\ ru]\ Собрание\ фигур\ для\ котильона.md \
	transcriptions/[183-,\ uk]\ The\ Fashionable\ Quadrille\ Preceptor.md \
	transcriptions/[2011,\ ru]\ Оксана\ Захарова\ -\ Русский\ бал\ XVIII\ -\ начала\ XX\ века.md \

ANC_MARKDOWN_FILES=\
	transcriptions/_markdown2.py \
	transcriptions/_reset.css \
	transcriptions/_style.css \
	
HTML_FILES=$(MARKDOWN_FILES:.md=.html)

test-biblatex.pdf: test-biblatex.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	#double pdflatex run is required
	@rm -f test-biblatex.bbl
	@pdflatex test-biblatex.tex
	@biber --quiet test-biblatex
	@pdflatex test-biblatex.tex
	@echo "Build completed"

test-biblatex-detailed.pdf: test-biblatex-detailed.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	#double pdflatex run is required
	@rm -f test-biblatex-detailed.bbl
	@pdflatex test-biblatex-detailed.tex
	@biber --quiet test-biblatex-detailed
	@pdflatex test-biblatex-detailed.tex
	@echo "Build completed"

test-bibtex.pdf: test-bibtex.tex $(BIB_FILES) $(ANC_FILES_BIBTEX)
	#triple pdflatex run is required
	@rm -f test-bibtex.bbl
	@pdflatex test-bibtex.tex
	@bibtex8 --wolfgang -c cp1251 test-bibtex
	@pdflatex test-bibtex.tex
	@pdflatex test-bibtex.tex
	@echo "Build completed"

all.dependency: test-biblatex.pdf test-bibtex.pdf test-biblatex-detailed.pdf transcriptions
	@echo "Build all completed"
	@touch all.dependency

upload.dependency: test-biblatex.pdf test-bibtex.pdf test-biblatex-detailed.pdf
	chmod 644 test-biblatex.pdf
	chmod 644 test-biblatex-detailed.pdf
	chmod 644 test-bibtex.pdf
	scp -p \
		test-bibtex.pdf \
		test-biblatex.pdf \
		test-biblatex-detailed.pdf \
		georg@iley.ru:/home/georg/leftparagraphs/static/files/
	@touch upload.dependency

%.html: %.md $(ANC_MARKDOWN_FILES)
	./transcriptions/_markdown2.py --input "$<" --output "$@"

transcriptions: $(HTML_FILES)
	@echo "Compiling transcriptions completed"

rebuild: purge all.dependency
	@echo "Rebuild completed"

purge: clean
	@rm -f *.pdf *.dependency transcriptions/*.html
	@echo "Purge completed"

clean:
	@rm -f *.aux *.bbl *.bcf *.blg *.log *.nav *.out *.snm *.swp *.toc *.run.xml
	@echo "Clean completed"
