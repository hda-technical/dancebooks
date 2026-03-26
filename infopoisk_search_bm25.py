import numpy as np
from scipy.sparse import csr_matrix
from collections import Counter


def build_term_doc_matrix(corpus):
    doc_ids = list(corpus.keys())

    vocab = {}
    rows = []
    cols = []
    data = []

    for col, doc_id in enumerate(doc_ids):
        tokens = corpus[doc_id]
        counts = Counter(tokens)

        for token, tf in counts.items():
            if token not in vocab:
                vocab[token] = len(vocab)

            row = vocab[token]

            rows.append(row)
            cols.append(col)
            data.append(tf)

    matrix = csr_matrix((data, (rows, cols)), shape=(len(vocab), len(doc_ids)))

    return matrix, vocab, doc_ids


def compute_bm25_stats(matrix):
    N = matrix.shape[1]

    doc_len = np.array(matrix.sum(axis=0)).flatten()
    avgdl = doc_len.mean()

    df = np.diff(matrix.indptr)
    idf = np.log((N - df + 0.5) / (df + 0.5) + 1)

    return doc_len, avgdl, idf


def search_bm25(matrix, vocab, doc_ids, query_tokens,
                doc_len, avgdl, idf,
                k=5, k1=1.5, b=0.75):

    scores = np.zeros(matrix.shape[1])

    for token in query_tokens:
        if token not in vocab:
            continue

        term_id = vocab[token]
        tf = matrix.getrow(term_id).toarray().flatten()

        denom = tf + k1 * (1 - b + b * doc_len / avgdl)
        score = idf[term_id] * (tf * (k1 + 1)) / denom

        scores += score

    top_idx = np.argsort(scores)[::-1][:k]

    return [(doc_ids[i], scores[i]) for i in top_idx if scores[i] > 0]