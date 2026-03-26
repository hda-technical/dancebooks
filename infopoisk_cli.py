import time

from dancebooks.config import config
import infopoisk_data_prep

from infopoisk_search_bm25 import (
    build_term_doc_matrix,
    compute_bm25_stats,
    search_bm25,
)
from infopoisk_search_w2v import (
    load_model as load_w2v_model,
    build_doc_vectors as build_doc_vectors_w2v,
    search_w2v,
)
from infopoisk_search_sbert import (
    load_model as load_sbert_model,
    build_doc_vectors as build_doc_vectors_sbert,
    search_sbert,
)


def preprocess(text, lang=("ru", "en")):
    return infopoisk_data_prep.lemmatize_with_cleaning(text, lang)


def build_corpus():
    """
    Parse all .bib files and return:
      - corpus     : {doc_id: token_list}  — for BM25 and W2V
      - raw_corpus : {doc_id: raw_string}  — for SBERT (needs unlemmatised text)
    """
    print("\n[1/4] Сбор корпуса документов...")

    param_list = [
        'title', 'author', 'altauthor', 'booktitle', 'incipit',
        'journaltitle', 'keywords', 'langid', 'location',
        'origauthor', 'origlanguage', 'pseudo_author',
        'translator', 'type',
    ]

    folder_data = infopoisk_data_prep.parse_folder_into_json(
        config.parser.bibdata_dir,
        param_list,
    )

    corpus = {}      # lemmatised tokens — BM25 / W2V
    raw_corpus = {}  # original strings  — SBERT

    for filename, data_dict in folder_data.items():
        langs = tuple(infopoisk_data_prep.lang_map.get(filename, ["en"]))

        for doc_id, text in data_dict.items():
            corpus[doc_id] = preprocess(text, lang=langs)
            raw_corpus[doc_id] = text

    print(f"✔ Корпус собран: {len(corpus)} документов")
    return corpus, raw_corpus


def choose_search_type():
    print("\n[2/4] Выбор типа поиска:")
    print("1 — BM25        (классический поиск по словам, точный и быстрый)")
    print("2 — Word2Vec    (семантический поиск, только английский)")
    print("3 — SBERT       (семантический поиск, многоязычный, 50+ языков)")

    while True:
        choice = input("Введите 1, 2 или 3: ").strip()
        if choice == "1":
            return "bm25"
        elif choice == "2":
            return "w2v"
        elif choice == "3":
            return "sbert"
        else:
            print("⚠ Неверный ввод. Попробуйте ещё раз.")


def get_query():
    print("\n[3/4] Ввод запроса")
    print("Пример: dance history, ballet, folk dance\n")

    while True:
        query = input("Введите поисковый запрос: ").strip()
        if query:
            return query
        print("⚠ Запрос не должен быть пустым.")


def get_k():
    print("\nСколько результатов показать? (по умолчанию 5)")
    value = input("Введите число: ").strip()

    if not value:
        return 5
    if value.isdigit():
        return int(value)

    print("⚠ Некорректное число, используется значение 5")
    return 5


def main():
    print("======================================")
    print("🔎 Поисковая система по библиотеке танцев")
    print("======================================")

    corpus, raw_corpus = build_corpus()

    search_type = choose_search_type()

    # ------------------------------------------------------------------ #
    # Index / model setup                                                  #
    # ------------------------------------------------------------------ #
    if search_type == "bm25":
        print("\n[Подготовка BM25 индекса...]")
        matrix, vocab, doc_ids = build_term_doc_matrix(corpus)
        doc_len, avgdl, idf = compute_bm25_stats(matrix)
        print("✔ Индекс готов")

    elif search_type == "w2v":
        print("\n[Загрузка Word2Vec модели...]")
        model = load_w2v_model()
        doc_vectors = build_doc_vectors_w2v(corpus, model)
        print("✔ Модель загружена и вектора построены")

    elif search_type == "sbert":
        print("\n[Загрузка SBERT модели...]")
        model = load_sbert_model()
        doc_vectors = build_doc_vectors_sbert(raw_corpus, model)
        print("✔ Модель загружена и вектора построены")

    # ------------------------------------------------------------------ #
    # Search loop                                                          #
    # ------------------------------------------------------------------ #
    while True:
        query = get_query()
        k = get_k()

        print("\n[4/4] Выполнение поиска...")
        start_time = time.perf_counter()

        if search_type == "bm25":
            query_tokens = preprocess(query)
            results = search_bm25(
                matrix, vocab, doc_ids,
                query_tokens,
                doc_len, avgdl, idf,
                k=k,
            )

        elif search_type == "w2v":
            query_tokens = preprocess(query)
            results = search_w2v(
                doc_vectors,
                query_tokens,
                model,
                k=k,
            )

        elif search_type == "sbert":
            # SBERT takes the raw query string — no preprocessing needed
            results = search_sbert(
                doc_vectors,
                query,
                model,
                k=k,
            )

        end_time = time.perf_counter()

        print("\n📄 Результаты поиска:")
        if not results:
            print("Ничего не найдено 😢")
        else:
            for doc_id, score in results:
                print(f"{doc_id}: {score:.4f}")

        print(f"\n⏱ Время поиска: {end_time - start_time:.6f} сек")

        print("\nХотите выполнить ещё один поиск?")
        again = input("y / n: ").strip().lower()

        if again != "y":
            print("\n👋 Завершение работы. Спасибо!")
            break


if __name__ == "__main__":
    main()
