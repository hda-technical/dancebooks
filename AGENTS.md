# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

The Historical Dance Association (HDA) bibliography of historical dance sources, served at https://bib.hda.org.ru (testing: https://bib-test.hda.org.ru).
The repo is mostly **data** (BibLaTeX-like `.bib` files under `bib/`, Markdown transcriptions under `transcriptions/`, docs under `docs/`) plus a small Flask app and maintenance tools that read it.
Most commits are bibliography edits, not code changes.

## Commands

Python >= 3.14.
Run everything from the repo root (`dancebooks` is installed editable via `pyproject.toml`; pytest uses `pythonpath = ["."]` so `www` is importable).

- Setup: `make init` (installs `requirements.txt` + `pip install -e .`)
- Tests: `make test` (equivalent to `DANCEBOOKS_UNITTEST= pytest -v tests`)
- Single test: `DANCEBOOKS_UNITTEST= pytest -v tests/parser_test.py::test_name`
- Dev server: `make debug` (compiles translations, runs `python www/main.py` on 0.0.0.0:5000)
- Compile translations: `make translations` (`pybabel compile -d www/translations`); edit `www/translations/{en,ru}/LC_MESSAGES/messages.po`
- Build docs: `make docs` (mkdocs, `strict: true`, outputs to untracked `www/static/docs`)
- Validate the bibliography: `python tools/validate.py` (flags: `--urls`, `--backups` are slow; `--store-new-errors`, `--remove-missing-ids`)
- Lint: `pyflakes` is in requirements; there is no configured linter target.
- `make requirements.txt` refreshes pinned versions from the current env.

`DANCEBOOKS_UNITTEST` must be set for tests (sets `config.unittest_mode`).
`LOGGING_CONFIG` env var overrides the logging config (default `configs/logger.development.conf`).

## Architecture

**Config is loaded at import time.**
`dancebooks/config.py` reads `configs/dancebooks.json` (JSON5, comments allowed) and merges `configs/secrets.json` (untracked; see `secrets.example.json`) on top, then sets up logging.
Any `from dancebooks.config import config` triggers this, so scripts and tests need a valid secrets file.
`dancebooks.json` is the central schema definition: which bib fields are lists / ints / years / dates / bools / markdown, keyword taxonomy, blocked/allowed URL domains, search/index params, and `id_redirections` (old id → new id, used for renamed entries).

**Data flow:**
`bib_parser.BibParser().parse_folder("bib")` parses every `.bib` file into `BibItem`s (field typing driven by config; `source` = `file.bib:line`) and builds an `index.Index` over the `index_params` from config.
`www/main.py` does this once at module import, so the whole bibliography is in memory.
`search.py` builds query predicates over items/index.
`markdown.py` renders `transcriptions/*.md` and `note` fields (with `[entry_id]` cross-references resolved through the index).
`utils_flask.py` holds Jinja filters, decorators (`check_id_redirections`, `log_exceptions`, secret-cookie gating), and error handlers.
`db.py` (SQLAlchemy + psycopg 3, Postgres) is only for backup metadata; schema migrations are in `migrations/` (yandex-pgmigrate `V####__name.sql`).

**Tests run against the real bibliography.**
For example, `tests/handlers_test.py` imports `www.main` and hard-codes real entry ids (`zarman_1905_russlav`, `wilson_1824`, ...).
Renaming/removing entries can break tests; add the old id to `id_redirections` when renaming.

**Validation (`tools/validate.py`)** is the main correctness gate for data edits: field rules, ISBN/ISSN, URL domain rules, filename conventions against the e-library on disk (`config.www.elibrary_dir`), `added_on` vs. git history.
It persists known ids and known-erroneous ids in untracked `tools/validate.json` on the local machine and refuses to update it when ids disappear without a redirection or new errors appear.

**Other tools:**
`tools/pdf.py` (click CLI: `assemble` scans into PDF, `optimize`, `optimize-suggest` — skips names listed in `tools/exceptions.txt`).
`tools/backup.py` (backup metadata in the DB).
`tools/lib.sh` (shell helpers for downloading tiled images).

**Deployment:**
uwsgi + nginx + systemd configs in `configs/`, installed by `make configs-install*` (root).
`make reload-testing` / `make reload-production` build docs, run tests, compile translations, then touch the uwsgi reload file and ping `/ping`.

## Conventions

- `.editorconfig`: **tabs** for indentation everywhere (including `.py` and `.bib`), except spaces in `configs/dancebooks.json` and `*.yml`.
- Bib entries: ids match `[a-z][a-z_0-9]+`, typically `author_year[_suffix]`.
  List fields are separated by ` | `.
  Every entry carries `added_on = {YYYY-MM-DD}`.
  `filename` paths follow the pattern `Library/.../[year, lang] Author - Title[, tome NN][ (incomplete|X copy)].pdf` (see `const.FILENAME_REGEXP`).
  `transcription` points into `transcriptions/`.
- Bibliographic conventions (dating like `1890?` / `1700–1705?`, `altauthor` / `origauthor` / `pseudo_author`, what goes into `publisher`, multiple URLs) are documented in Russian in `docs/bib/index.md`.
  Follow them when editing entries.
  Use en dash `–` in ranges.
- Docs and site UI are primarily Russian.

## Style

- Markdown (docs, this file): start every sentence on a new line; do not hard-wrap at a fixed width.
  Long sentences may additionally break at clause boundaries, as in `docs/bib/index.md`.
  Continuation lines inside list items are indented to stay within the item.
- Agent instructions live in `AGENTS.md`, not `CLAUDE.md`.
