"""
Multilingual semantic search using pretrained FastText word vectors.

Uses Facebook's pretrained Common Crawl models in compressed form
(cc.XX.300.ftz, ~300 MB each) instead of the full .bin files (~4 GB each).
FastText's subword embeddings mean every token gets a vector — even
historical spelling variants that are out-of-vocabulary for GloVe/W2V.

Pretrained models can be downloaded from:
https://fasttext.cc/docs/en/crawl-vectors.html

On first use, load_models() will download the full .bin, compress it to
.ftz via fasttext.util.reduce_model(), then delete the .bin automatically.

Expected directory layout (configure MODEL_DIR below or pass it explicitly):
    <MODEL_DIR>/
        cc.en.300.ftz
        cc.ru.300.ftz
        cc.fr.300.ftz
        ... etc.
"""

import os
from pathlib import Path

import numpy as np
import fasttext
import fasttext.util

# Default directory where *.bin model files are stored.
# Override by passing model_dir to load_models().
MODEL_DIR = Path(os.getenv("FASTTEXT_MODEL_DIR", "fasttext_models"))

# Dimensionality of the pretrained cc.XX.300 vectors.
VECTOR_DIM = 300


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _model_path(lang: str, model_dir: Path) -> Path:
    return model_dir / f"cc.{lang}.300.ftz"


def load_models(langs: list[str], model_dir: Path = MODEL_DIR) -> dict[str, object]:
    """
    Load one FastText model per language from *model_dir*.

    If a model file is not present, fasttext.util.download_model() is used
    to download it automatically. Only languages present in the corpus are
    loaded so startup time stays proportional to actual corpus coverage.

    :param langs: list of ISO 639-1 language codes, e.g. ["en", "ru", "fr"]
    :param model_dir: directory that contains / will receive the .bin files
    :returns: dict mapping language code -> fasttext model object
    """
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    models = {}
    for lang in langs:
        ftz_path = _model_path(lang, model_dir)
        bin_path = model_dir / f"cc.{lang}.300.bin"

        if not ftz_path.exists():
            print(f"  Downloading FastText model for '{lang}' …")
            original_dir = Path.cwd()
            os.chdir(model_dir)
            try:
                fasttext.util.download_model(lang, if_exists="ignore")
            finally:
                os.chdir(original_dir)

            # download_model always fetches the full .bin; compress it and
            # remove the large original to save ~3.7 GB per language.
            print(f"  Compressing to .ftz …")
            model_tmp = fasttext.load_model(str(bin_path))
            fasttext.util.reduce_model(model_tmp, 100)
            model_tmp.save_model(str(ftz_path))
            del model_tmp
            bin_path.unlink()
            print(f"  Removed {bin_path.name}")

        print(f"  Loading {ftz_path.name} …")
        models[lang] = fasttext.load_model(str(ftz_path))

    return models


# ---------------------------------------------------------------------------
# Vectorisation helpers
# ---------------------------------------------------------------------------

def _token_vector(token: str, models: dict[str, object]) -> np.ndarray | None:
    """
    Return the first non-zero vector found for *token* across all models.

    FastText always returns a vector (subword fallback), so the only way to
    get a zero vector is for a completely empty string — we guard against
    that. We try languages in insertion order, which for a well-constructed
    lang_map entry matches frequency of use.
    """
    for model in models.values():
        vec = model.get_word_vector(token)
        if np.linalg.norm(vec) > 0:
            return vec
    return None


def text_to_vector(tokens: list[str], models: dict[str, object]) -> np.ndarray:
    """
    Compute a document/query vector as the mean of per-token FastText vectors.

    Unlike GloVe/W2V, FastText never returns zero for real words, so the
    coverage rate across historical multilingual text is much higher.

    :param tokens: pre-lemmatised token list produced by infopoisk_data_prep
    :param models: language-keyed model dict from load_models()
    :returns: mean vector of shape (VECTOR_DIM,), or zero vector if no tokens
              produced a usable embedding
    """
    vectors = []
    for token in tokens:
        vec = _token_vector(token, models)
        if vec is not None:
            vectors.append(vec)

    if not vectors:
        return np.zeros(VECTOR_DIM)

    return np.mean(vectors, axis=0)


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_doc_vectors(
    corpus: dict[str, list[str]],
    doc_lang_map: dict[str, list[str]],
    all_models: dict[str, object],
) -> dict[str, np.ndarray]:
    """
    Build a vector for every document in *corpus*.

    Each document is vectorised using only the models for the languages
    declared in *doc_lang_map* for that document's source file.  This is
    more accurate than always using all models and avoids spurious cross-
    language matches.

    :param corpus: {doc_id: token_list} as produced by infopoisk_cli.build_corpus
    :param doc_lang_map: {doc_id: [lang_code, ...]} mapping built alongside
                         the corpus (see build_corpus_with_lang_map() below)
    :param all_models: full model dict from load_models()
    :returns: {doc_id: mean_vector}
    """
    doc_vectors = {}
    for doc_id, tokens in corpus.items():
        langs = doc_lang_map.get(doc_id, list(all_models.keys()))
        models_for_doc = {l: all_models[l] for l in langs if l in all_models}
        doc_vectors[doc_id] = text_to_vector(tokens, models_for_doc)
    return doc_vectors


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_fasttext(
    doc_vectors: dict[str, np.ndarray],
    query_tokens: list[str],
    models: dict[str, object],
    k: int = 5,
) -> list[tuple[str, float]]:
    """
    Return the top-*k* documents most similar to the query.

    The query is embedded with all available models so a user can query in
    any of the corpus languages and still find relevant documents.

    :param doc_vectors: pre-built index from build_doc_vectors()
    :param query_tokens: pre-lemmatised query tokens
    :param models: model dict — pass all loaded models so the query benefits
                   from full multilingual coverage
    :param k: number of results to return
    :returns: list of (doc_id, cosine_score) sorted descending, score > 0
    """
    query_vec = text_to_vector(query_tokens, models)

    scores = [
        (doc_id, cosine_similarity(query_vec, doc_vec))
        for doc_id, doc_vec in doc_vectors.items()
    ]

    scores.sort(key=lambda x: x[1], reverse=True)

    return [(doc_id, score) for doc_id, score in scores[:k] if score > 0]