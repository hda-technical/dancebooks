BIB_FILES=\
	bib/!missing.bib \
	bib/!problems.bib \
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
	bib/italian.bib \
	bib/journal-of-musicology.bib \
	bib/mexican.bib \
	bib/polish.bib \
	bib/portuguese.bib \
	bib/proceedings-rothenfelser.bib \
	bib/proceedings-spb.bib \
	bib/russian.bib \
	bib/spanish.bib \
	bib/swiss.bib \

ANC_FILES_BIBLATEX=\
	dancebooks-biblatex.sty \

MARKDOWN_FILES=\
	transcriptions/[1706,\ uk]\ Raoul-Auger\ Feuillet\ -\ Orchesography\ or\ The\ Art\ of\ Dancing.md \
	transcriptions/[1819,\ fr]\ J.\ H.\ Gourdoux-Daux\ -\ Requeil\ de\ genre\ nouveau\ de\ contredanses\ et\ walses.md \
	transcriptions/[1825,\ ru]\ Людовик\ Петровский\ -\ Правила\ для\ благородных\ общественных\ танцев.md \
	transcriptions/[1828,\ ru]\ Собрание\ фигур\ для\ котильона.md \
	transcriptions/[183-,\ uk]\ Thomas\ Wilson\ -\ The\ Fashionable\ Quadrille\ Preceptor.md \
	transcriptions/[1902,\ ru]\ Николай\ Людвигович\ Гавликовский\ -\ Руководство\ для\ изучения\ танцев,\ édition\ 2.md \
	transcriptions/[1965,\ ru]\ Юрий\ Алексеевич\ Бахрушин\ -\ История\ русского\ балета.md \
	transcriptions/[1987,\ ru]\ Людмила\ Дмитриевна\ Блок\ -\ Классический\ танец.\ История\ и\ современность.md \
	transcriptions/[2000,\ ru]\ Агриппина\ Яковлевна\ Ваганова\ -\ Основы\ классического\ танца.md \
	transcriptions/[2000,\ ru]\ Филипп\ Филиппович\ Вигель\ -\ Записки.md \
	transcriptions/[2007,\ ru]\ Жан\ Жорж\ Новерр\ -\ Письма\ о\ танце.md \
	transcriptions/[2011,\ ru]\ Оксана\ Захарова\ -\ Русский\ бал\ XVIII\ -\ начала\ XX\ века.md \
	

ANC_MARKDOWN_FILES=\
	transcriptions/_markdown2.py \
	transcriptions/_reset.css \
	transcriptions/_style.css \
	
HTML_FILES=$(MARKDOWN_FILES:.md=.html)

default: test-biblatex.pdf

%.pdf: %.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@pdflatex --max-print-line=250 $<
	@biber --validate_datamodel --quiet ${@:.pdf=}
	@pdflatex --max-print-line=250 $<
	@echo "Build log contains:"
	@grep -iE "Datamodel" ${@:.pdf=.log}
	@echo "Build completed"
	
debug: purge test-biblatex.tex $(BIB_FILES) $(ANC_FILES_BIBLATEX)
	@rm -f ${@:.pdf=.bbl} biblatex-dm.cfg
	@pdflatex --max-print-line=200 test-biblatex.tex
	@biber --validate_datamodel test-biblatex
	@pdflatex --max-print-line=200 test-biblatex.tex
	@echo "Build completed"

all.dependency: test-biblatex.pdf test-biblatex-detailed.pdf transcriptions
	@echo "Build all completed"
	@touch all.dependency

upload.dependency: test-biblatex.pdf test-biblatex-detailed.pdf
	chmod 644 $^
		scp -p $^ georg@iley.ru:/home/georg/leftparagraphs/static/files/
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
