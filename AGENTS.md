# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

The Historical Dance Association (HDA) bibliography of historical dance sources,
served at https://bib.hda.org.ru (testing: https://bib-test.hda.org.ru).
The repo is mostly **data**
(BibLaTeX-like `.bib` files under `bib/`, Markdown transcriptions under `transcriptions/`,
docs under `docs/`)
plus a small Flask app and maintenance tools that read it.
Most commits are bibliography edits, not code changes.

## Commands

Python >= 3.14.
Run everything from the repo root.
`dancebooks` is installed editable via `pyproject.toml`,
and pytest uses `pythonpath = ["."]`, so `www` is importable.

- Setup: `make init` (installs `requirements.txt` + `pip install -e .`)
- Tests: `make test` (equivalent to `DANCEBOOKS_UNITTEST= pytest -v tests`)
- Single test: `DANCEBOOKS_UNITTEST= pytest -v tests/parser_test.py::test_name`
- Dev server: `make debug`
  (compiles translations, runs `python www/main.py` on 0.0.0.0:5000)
- Compile translations: `make translations` (`pybabel compile -d www/translations`).
  Sources are `www/translations/{en,ru}/LC_MESSAGES/messages.po`.
- Build docs: `make docs` (mkdocs, `strict: true`, outputs to untracked `www/static/docs`)
- Validate the bibliography: `python tools/validate.py`
  (flags: `--urls`, `--backups`, `--store-new-errors`, `--remove-missing-ids`).
  `--urls` and `--backups` are slow.
- Lint: `pyflakes` is in requirements.
  There is no configured linter target.
- `make requirements.txt` refreshes pinned versions from the current env.

`DANCEBOOKS_UNITTEST` must be set for tests (sets `config.unittest_mode`).
`LOGGING_CONFIG` env var overrides the logging config
(default `configs/logger.development.conf`).

## Architecture

**Config is loaded at import time.**
`dancebooks/config.py` reads `configs/dancebooks.json` (JSON5, comments allowed),
merges `configs/secrets.json` (untracked, see `secrets.example.json`) on top,
then sets up logging.
Any `from dancebooks.config import config` triggers this,
so scripts and tests need a valid secrets file.
`dancebooks.json` is the central schema definition:
which bib fields are lists / ints / years / dates / bools / markdown,
keyword taxonomy, blocked/allowed URL domains, search/index params,
and `id_redirections` (old id → new id, used for renamed entries).

**Data flow:**
`bib_parser.BibParser().parse_folder("bib")` parses every `.bib` file into `BibItem`s
(field typing driven by config, `source` = `file.bib:line`)
and builds an `index.Index` over the `index_params` from config.
`www/main.py` does this once at module import, so the whole bibliography is in memory.
`search.py` builds query predicates over items/index.
`markdown.py` renders `transcriptions/*.md` and `note` fields
(with `[entry_id]` cross-references resolved through the index).
`utils_flask.py` holds Jinja filters, error handlers and decorators
(`check_id_redirections`, `log_exceptions`, secret-cookie gating).
`db.py` (SQLAlchemy + psycopg 3, Postgres) is only for backup metadata.
Schema migrations are in `migrations/` (yandex-pgmigrate `V####__name.sql`).

**Tests run against the real bibliography.**
For example, `tests/handlers_test.py` imports `www.main`
and hard-codes real entry ids (`zarman_1905_russlav`, `wilson_1824`, ...).
Renaming/removing entries can break tests.
Add the old id to `id_redirections` when renaming.

**Validation (`tools/validate.py`)** is the main correctness gate for data edits:
field rules, ISBN/ISSN, URL domain rules,
filename conventions against the e-library on disk (`config.www.elibrary_dir`),
`added_on` vs. git history.
It persists known ids and known-erroneous ids
in untracked `tools/validate.json` on the local machine.
It refuses to update it when ids disappear without a redirection or new errors appear.

**Downloader (`tools/downloader/`)** fetches scans of books from digital libraries.
`main.py` is a click group with one command per source, named `<country>_<library>`
(e.g. `fr_gallica`, `de_bsb`, `it_vatlib`).
Invoke as `python tools/downloader/main.py fr-gallica --id ...` (click turns `_` into `-`).
Commands lazily import the per-country module (`at.py`, `de.py`, `fr.py`, ...),
which holds the source-specific `get_*` functions.
Modules import their siblings as top-level modules (`import utils`, `import iiif`),
so they only work when run through `main.py` (which puts its own directory on `sys.path`),
not as a package.
Shared protocol implementations:
`iiif.py` (IIIF manifests v2/v3, preferred when a library offers them),
`iip.py` (IIPImage), `deep_zoom.py`.
Tiled sources are sewn together with `utils.download_and_sew_tiles` and `dancebooks.img`.
`utils.py` also provides request helpers with retries, HAR-file session loading,
and Cloudflare / Anubis challenge handling.
Pages are written to `<source>_<id>/NNNN.<ext>` in the current directory.
Existing pages are skipped, so interrupted downloads can be resumed.

**Other tools:**
`tools/pdf.py` (click CLI: `assemble` scans into PDF, `optimize`, `optimize-suggest`).
`optimize-suggest` skips names listed in `tools/exceptions.txt`.
`tools/backup.py` (backup metadata in the DB).
`tools/lib.sh` is the legacy shell predecessor of `tools/downloader/`.
Add new sources to the downloader instead.

**Deployment:**
uwsgi + nginx + systemd configs in `configs/`, installed by `make configs-install*` (root).
`make reload-testing` / `make reload-production` build docs, run tests, compile translations,
then touch the uwsgi reload file and ping `/ping`.

## Conventions

- `.editorconfig`: **tabs** for indentation everywhere (including `.py` and `.bib`),
  except spaces in `configs/dancebooks.json` and `*.yml`.
- Bib entries: ids match `[a-z][a-z_0-9]+`, typically `author_year[_suffix]`.
  List fields are separated by ` | `.
  Every entry carries `added_on = {YYYY-MM-DD}`.
  `filename` paths follow the pattern
  `Library/.../[year, lang] Author - Title[, tome NN][ (incomplete|X copy)].pdf`
  (see `const.FILENAME_REGEXP`).
  `transcription` points into `transcriptions/`.
- Bibliographic conventions are documented in Russian in `docs/bib/index.md`
  (dating like `1890?` / `1700–1705?`, `altauthor` / `origauthor` / `pseudo_author`,
  what goes into `publisher`, multiple URLs).
  Follow them when editing entries.
  Year ranges use en dash (`year = {1803–1804}`),
  while `pages` uses a plain hyphen (`pages = {37-43}`, enforced by `tools/validate.py`).
- Library courtesy refers to the corresponding entry in `docs/common/libraries.md`.
  Scans obtained from a library are hosted only with its permission:
  - The correspondence granting the permission goes to `docs/common/libraries.md`
    under the `{ #ALIAS }` anchor.
    `ALIAS` is a short uppercase abbreviation of the library name (`BNF`, `NLS`, `RCM`).
  - The library is listed in `parser.bookkeepers` in `configs/dancebooks.json`
    as `"ALIAS": "the :ALIAS:"` (e.g. `"BNF": "the :BNF:"`).
    Private owners have `null` instead and need no courtesy.
  - The filename ends with `(ALIAS copy)` or `(Incomplete ALIAS copy)`.
  - The `note` contains `Courtesy of the :ALIAS:.`,
    rendered as a link to the library section.
    `tools/validate.py` checks the fullname is present in `note` for every self-served url,
    so changing a fullname requires updating all such notes.
  - Mentions of a library in entries whose copies are hosted elsewhere stay plain text.
  - Sections in `docs/common/libraries.md` are not sorted yet.
    Insert a new section into the longest run of consecutive sections
    already sorted by country (ISO code of the flag), then by alias.
    Hosting status is ✅ (allowed), 🚫 (denied) or ❓
    (`_Hosting capability was not evaluated yet._`).
- Docs are primarily Russian.
  The site UI is multilingual (`config.www.languages`, translated via `www/translations/`).

## Style

- Markdown (docs, this file): start every sentence on a new line,
  including clauses that would otherwise be joined with `;`.
- Keep lines short (roughly under 100 characters):
  break long sentences at clause boundaries or before parenthesized asides,
  as in `docs/bib/index.md`.
  Do not hard-wrap mid-phrase at a fixed width.
- Continuation lines inside list items are indented to stay within the item.
- Agent instructions live in `AGENTS.md`, not `CLAUDE.md`.
