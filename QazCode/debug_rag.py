from src.rag import BM25Index

INDEX = BM25Index.build_from_jsonl("./data/protocols_corpus.jsonl")

q = input("Query> ").strip()
hits = INDEX.search_diverse(q, top_k=6, per_protocol=1)

print("\nTop hits:\n")
for i, (s, ch) in enumerate(hits, 1):
    print(f"[{i}] score={s:.3f} protocol_id={ch.protocol_id} source={ch.source_file}")
    print("     icd_codes(sample)=", ch.icd_codes[:10])
    print("     text_preview=", ch.text[:220].replace("\n", " "), "\n")