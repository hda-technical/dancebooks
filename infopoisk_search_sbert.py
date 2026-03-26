"""
Multilingual semantic search using Sentence-Transformers.

Uses the 'paraphrase-multilingual-MiniLM-L12-v2' model (~120 MB, one-time
download), which supports 50+ languages including all languages present in
the dancebooks corpus (ru, en, fr, de, it, es, pt, pl, nl, cs, sv, da, fi,
nb, et, lv, uk, la).

Unlike Word2Vec / FastText, this model encodes entire texts as single
vectors rather than averaging word vectors, which gives much better
semantic coherence — especially for short bibliographic strings.

The model is downloaded automatically on first use by the sentence-transformers
library and cached in ~/.cache/torch/sentence_transformers/.

Install:
    pip install sentence-transformers
"""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    """
    Load the Sentence-Transformers model, downloading it on first use.

    :param model_name: any model name accepted by SentenceTransformer()
    :returns: loaded SentenceTransformer model
    """
    print(f"  Loading Sentence-Transformers model '{model_name}' …")
    print("  (Will download ~120 MB on first use)")
    return SentenceTransformer(model_name)


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_doc_vectors(
    raw_corpus: dict[str, str],
    model: SentenceTransformer,
    batch_size: int = 64,
) -> dict[str, np.ndarray]:
    """
    Encode every document in *raw_corpus* into a dense vector.

    Sentence-Transformers works on raw text, not pre-tokenised lists, so
    this function takes the original strings (not the lemmatised tokens used
    by BM25/W2V).  Encoding is batched for efficiency.

    :param raw_corpus: {doc_id: raw_text_string}
    :param model: loaded SentenceTransformer model
    :param batch_size: number of texts to encode per batch; tune down if OOM
    :returns: {doc_id: embedding_vector}
    """
    doc_ids = list(raw_corpus.keys())
    texts = [raw_corpus[doc_id] for doc_id in doc_ids]

    print(f"  Encoding {len(texts)} documents …")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-normalise so dot product == cosine
    )

    return dict(zip(doc_ids, embeddings))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_sbert(
    doc_vectors: dict[str, np.ndarray],
    query: str,
    model: SentenceTransformer,
    k: int = 5,
) -> list[tuple[str, float]]:
    """
    Return the top-*k* documents most semantically similar to *query*.

    Because embeddings are L2-normalised at index time, similarity is just
    a dot product, which is faster than computing full cosine similarity.

    :param doc_vectors: pre-built index from build_doc_vectors()
    :param query: raw query string in any supported language
    :param model: loaded SentenceTransformer model
    :param k: number of results to return
    :returns: list of (doc_id, cosine_score) sorted descending, score > 0
    """
    query_vec = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    doc_ids = list(doc_vectors.keys())
    # Stack into a matrix for a single vectorised dot product
    matrix = np.stack([doc_vectors[doc_id] for doc_id in doc_ids])
    scores = matrix @ query_vec                   # shape: (n_docs,)

    top_indices = np.argsort(scores)[::-1][:k]

    return [
        (doc_ids[i], float(scores[i]))
        for i in top_indices
        if scores[i] > 0
    ]
