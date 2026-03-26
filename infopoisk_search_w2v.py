import numpy as np
import gensim.downloader as api


def load_model():
    return api.load("glove-wiki-gigaword-100")


def text_to_vector(tokens, model):
    vectors = [model[token] for token in tokens if token in model]

    if not vectors:
        return np.zeros(model.vector_size)

    return np.mean(vectors, axis=0)


def cosine_similarity(a, b):
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def build_doc_vectors(corpus, model):
    doc_vectors = {}

    for doc_id, tokens in corpus.items():
        doc_vectors[doc_id] = text_to_vector(tokens, model)

    return doc_vectors


def search_w2v(doc_vectors, query_tokens, model, k=5):
    query_vec = text_to_vector(query_tokens, model)

    scores = []
    for doc_id, doc_vec in doc_vectors.items():
        score = cosine_similarity(query_vec, doc_vec)
        scores.append((doc_id, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    return [s for s in scores[:k] if s[1] > 0]