# BM25 Search Tool Documentation

This tool performs search queries on a corpus of dance-related bibliographic data using Term Frequency (TF) or BM25 scoring algorithms.

## Prerequisites

- Python 3.x installed
- Virtual environment set up in `.venv` folder
- Required dependencies installed (see `requirements.txt`)

## Activation

Activate the virtual environment before running the tool:

- **Command Prompt (cmd)**: `.venv\Scripts\activate.bat`
- **PowerShell**: `.venv\Scripts\Activate.ps1`

## Usage

Run the search from the command line:

```
python infopoisk_search_matrix.py "your search query"
```

### Options

- `query`: The search query string (required)
- `--type`: Search algorithm - `tf` (term frequency) or `bm25` (default: bm25)
- `--k`: Number of top results to return (default: 5)

### Examples

- Basic BM25 search: `python infopoisk_search_matrix.py "dance history"`
- TF search: `python infopoisk_search_matrix.py "ballroom" --type tf`
- Return 10 results: `python infopoisk_search_matrix.py "waltzing" --k 10`
- Combined: `python infopoisk_search_matrix.py "folk dance" --type bm25 --k 3`

## Output

Results are printed to the console in the format:
```
doc_id: score
```

Higher scores indicate better matches.

## Notes

- The tool processes all bibliographic data from the bib/ folder.
- Documents are preprocessed with lemmatization using the appropriate languages for each file as defined in the language mapping.
- Queries are preprocessed with lemmatization for Russian and English (default).
- No results are shown if the query matches no documents.