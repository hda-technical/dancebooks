# Common definitions

### Two-letter country codes

Используемые обозначения являются подмножеством кодов, описанных в [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2). Для неуказанных в стандарте географических сущностей введены собственные обозначения.

| Аббревиатура | Язык | Страна |
| ------------ | ---- | ------ |
| `ar` | испанский | Аргентина |
| `au` | английский | Австралия |
| `at` | немецкий | Австрия |
| `ca` | английский | Канада |
| `cz` | чешский | Чехия |
| `de` | немецкий | Германия |
| `dk` | датский | Дания |
| `en` | английский | Англия |
| `es` | испанский | Испания |
| `fr` | французский | Франция |
| `gr` | греческий | Греция |
| `ie` | английский | Ирландия |
| `it` | итальянский | Италия |
| `ln` | латынь | — |
| `nl` | голланский | Нидерланды |
| `pl` | польский | Польша |
| `pt` | португальский | Португалия |
| `ru` | русский | Российская Империя, СССР, Россия |
| `sc` | английский | Шотландия |
| `sw` | шведский | Швеция |
| `tr` | турецкий | Турция |
| `ua` | украинский | УССР |
| `us` | английский | США |

### Keywords

Теги имеют разветвлённую структуру типа «лес» (множество деревьев). Все теги пишутся маленькими латинскими буквами, без выносных элементов (аксанов). Дочерние теги отделяются от родительских двоеточием (`quadrille: first set`). В случае наличия у объекта дочерней метки ей также проставляются родительские метки в случае их наличия: : тег `quadrille: first set` имплицирует тег `quadrille`. Единственным дочерним тегом, не имеющим родительских, является тег `cotillon`.

Список тегов должен быть синхронизирован с [конфигурационным файлом библиографии](https://github.com/hda-technical/dancebooks/tree/master/configs).

Полный список меток приведён в таблице ниже:

| Тег / Keyword | Пояснение на русском | Commentary in English |
| ------------- | -------------------- | --------------------- |
| `pavane` |
| `allemande` |
| `courant` |
| `galliard` |
| `gavotte` |
| `folie d'espagne` |
| `landler` |
| `minuet` |
| `perigourdine` |
| `saraband` |
| `cancan` | Канкан, как танец из Moulen Rouge, так и как форма Французской кадрили |
| `circle` | Кадрили замкнутые в круг. Например, черкесский или сицилийский круги | Quadrille dances closed into a circle. Circassian and sicilian circles are well-known examples |
| `cotillon: 18th century` |
| `cotillon: potpourri` | Несколько фигур котильона, исполняемые одна за другой в рамках одного танца | Multiple cotillon figures danced one after another in a single dance |
| `cotillon: cracovienne` |
| `cotillon: doppel-quadrille` |
| `cotillon: douze` |
| `cotillon: seize` |
| `cotillon: vingt-quatre` |
| `cotillon: 19th century` | Включает в себя котильон (в значении бальной игры) и танец “Waltz Cotillon” с фиксированной схемой | Includes cotillon (in the meaning of ballroom game) and the Waltz Cotillon (fixed sequence of figures) |
| `la boulangere` |
| `le carillon de dunkerque` |
| `longway` | Любой контрданс в колонну. Музыкальная форма контрданса не ведёт к добавлению тегов (то есть, вальсовый контрданс не означает наличие тега `waltz`) | Any dance for a line of couples. Musical form of the country dance is not counted in keywords (i. e. waltz longway doesn't generate `waltz` keyword) |
| `longway: ecossaise in two columns` | Специальная форма экосеза для двух контрдансных колонн стоящих рядом | Special form of ecossaise for two linked columns standing side by side |
| `longway: ecossaise` | Разница между контрдансами в колонну и экосезами — отличная тема для диссертации | Differences between longway country dances and ecossaises are yet to be determined |
| `longway: francaise` | Особый вид контрдансов в колонну, танцующийся на сложных шагах (антраша, сиссон, баллоте, глиссад, па-де-ригодон и так далее) | Special kind of longway that make use of complicated ballet steps (entrechat, sissone, ballote, glissade, pas de rigodon, etc.) |
| `longway: matredour` |
| `longway: money musk` |
| `longway: pop goes the weasel` |
| `rustic reel` |
| `sir roger de coverly` |
| `spanish dance` |
| `swedish dance` |
| `tempete` |
| `virginia reel` |
| `allemande` |
| `bogentanz` |
| `character dance` |
| `fandango` |
| `folk dance` | В данный момент объединяет в себе следующие теги: reel, jig, strathspey, fling, fancy, hornpipe, clog | Currently includes: reel, jig, strathspey, fling, fancy, hornpipe, clog |
| `folk dance: country bumpkin` |
| `galop` |
| `grossvater` |
| `hongroise` |
| `landler` |
| `march` |
| `mazurka` | Включает в себя как кадрильную, так и котильонную мазурку | Includes mazurka dance as a quadrille, and as a cotillon |
| `minuet` |
| `monferine` |
| `polka` | В том числе вариации (например, Эсмеральда) | Including variations (e. g. Esmeralda) |
| `polka-mazurka` | В том числе вариации (например, полька-редова) | Including variations (e. g. polka-redowa) |
| `polonaise` |
| `quadrille` | Любая кадриль. Музыкальная форма кадрили ведёт к добавлению соответствующих тегов (то есть, шоттиш-кадриль приведёт к добавлению тега `schottische`). Американские котильоны (sets of cotillions) также получают этот тег | Any quadrille. Musical form of the quadrille is counted in keywords (i. e. schottische quadrille will generate `schottische` keyword). ets of cotillions (in the American meaning) are also tagged with this keyword |
| `quadrille: caledonians` |
| `quadrille: contredanse` | Одиночная фигура кадрили, описанная как самостоятельный танец | Indicates single quadrille figure described as an independent dance |
| `quadrille: first set` |
| `quadrille: grand rond` | Вариант финала французской кадрили: танцоры идут в общем кругу, исполняя фигуры под объявления распорядителя | First set finale figure variation: the dancers join hands in a circle, and perform figures according to conductor's commands |
| `quadrille: lancers` | Включает в себя многочисленные вариации кадрили (например, Saratoga Lancers) | Keywords includes numerous Lancers variations (like Saratoga Lancers) |
| `quadrille: london polka quadrille` |
| `quadrille: monster` | Французская кадриль, отличающая высокой вариативностью фигур и ведомая дирижёром | Form of first set with high amount of figure variations, lead by a conductor |
| `quadrille: polo` |
| `quadrille: prince imperial` |
| `quadrille: promiscuous figures` | Содержит описания фигур для замены фигур first set | Contains figures used to replace one from the first set |
| `quadrille: varietes parisiennes` |
| `redowa` |
| `schottische` | Шоттиш (включая вариации, например, military schottische) или па-де-катр | Either schottische (including variations like military schottische) or pas de quatre |
| `sequence` | Круговые танцы, содержащие несколько шагов или фигур. Тег включает в себя круговые танцы середины XIX века (горлица, сицилиана, вальс Целлариуса и т. д.) | Round dances containing more that one figure or step. Keyword includes round dances of the middle of 19th century (gorlitza, sicilienne, Cellarius valse, etc.) |
| `stage dance` | Балет, постановочные и показательные танцы (а также музыка написанная к таким танцам или взятая из них) | Ballet, scenic and show off dance (also the music for such dances, or taken from them) |
| `tango` | Танго середины XIX века, по-видимому, является обычным сиквенсом (насколько мне известно, никто не исследовал этот вопрос). Однако, поскольку танец пережил эпоху сиквенсов, ему был добавлен отдельный тег | Tango in the middle of 19th century is believed to be just a sequence dance (as far, as I know, nobody did a research on that). However, since the dance was able to pass through the sequence era, a separate keyword was added for it |
| `waltz` | Любой вальс | Any kind of waltz |
| `waltz: boston` | В том числе бостон-дип | Including boston dip |
| `waltz: canter` |
| `waltz: cellarius` |
| `waltz: deux temps` |
| `waltz: five steps` |
| `waltz: glide` |
| `waltz: hesitation` |
| `waltz: new trois temps` |
| `waltz: sautese` | Любой прыгающий вальс | Any kind of sautese |
| `waltz: trois temps` | Включает в себя медленный французский, медленный немецкий, также немецкие langsamer, rascher и geschwinder вальсы | Includes slow French, slow German, langsamer, rasher and geschwinder waltzes |
| `animal dance` | Любой танец, подражающий движениям животных | Any animal dance |
| `animal dance: grizzly bear` |
| `animal dance: turkey trot` |
| `animal dance: fox trot` |
| `big apple` |
| `cake-walk` |
| `castle walk` |
| `charleston` |
| `half and half` |
| `maxixe` |
| `mixer dance` |
| `one-step` |
| `palais glide` |
| `sequence` |
| `swing` |
| `three-step` |
| `two-step` |
| `antidance` |
| `belles-lettres` |
| `belles-lettres: dance song` | Источник содержит текст песни, использующейся в качестве аккомпанемента танца | Indicates that the source has lyrics being sung while dancing |
| `commentary` | В книге есть вступительная статья | Introductory article is present in the book |
| `dance description` | Источники, содержащие описание последовательности шагов и фигур танца | When source contains dance description (the sequence of steps and figures) |
| `dance description: short` | Источники, содержащие короткое описание последовательности шагов и фигур танца (несколько строк текста; основным содержанием источника является музыкальная нотация) | When source contains short dance description (i. e. few lines of a description, while main content of the book is the musical notation) |
| `dance education` | Источники, содержащие последовательные инструкции по обучению танцам | When source contains instructions how to learn dancing |
| `essay` | Источник, содержащий авторский взгляд на какую-то тему, связанную с танцем | Source containing author view on some dance-related subject |
| `etiquette` |
| `facsimile` |
| `first edition` | Художественная или мемуарная литература, а также эссеистика, впервые изданная на языке источника | Belles-lettres, memoirs and essays of the first known edition on the source language |
| `libretto` |
| `memoirs` |
| `music` |
| `not digitized` |
| `reissue` |
| `research` |
| `reverences` | В источнике есть описания поклонов перед танцем | Source containing description of révérences to be performed before the dance |
| `tempo` | В истонике имеются указания на темп исполнения музыки или танца | Any kind of useful tempo indication |
| `tempo: italian` | Темп музыки указан с использованием итальянских терминов (например, allegro assai) | Musical tempo is specified by Italian terminology (e. g. allegro assai) |
| `tempo: malzel` | Темп музыки указан при помощи числа ударов метронома Мельцеля | Musical tempo is specified by number of beats on Mälzel metronome |
| `useless` | Специальный тег для книг, не содержащих описания танцев и добавленных для полноты коллекции | Special keyword for the books lacking dance related parts, but added for collection completeness |

## Dating

Не всякий объект можно датировать точно. Зачастую с уверенностью можно назвать лишь десятилетие или другой доверительный интервал. Ситуации с невозможностью точной датировки отражаются следующим образом:

* [`1701`](https://bib.hda.org.ru/bib/books/feuillet_1701_choregraphie) — год известен точно (например, он стоит на титульном листе книги, в датировке цензора или в copyright statement),
* [`1890?`](https://bib.hda.org.ru/bib/books/lorenzova_1890) — год известен, но никаких явных доказательств в пользу такой датировки нет (например, это датировка библиотеки или одного из множества каталогов),
* [`1803–1804`](https://bib.hda.org.ru/bib/books/noverre_1803) — год известен точно, однако издание (например, многотомная книга) выходило на протяжении нескольких лет,
* [`1700–1705?`](https://bib.hda.org.ru/bib/books/beauchamp_1700) — год известен приблизительно, в поле `annotation` при этом хранится информация о том, почему была выбрана та или иная датировка.
