import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


@dataclass
class Chunk:
    protocol_id: str
    source_file: str
    title: str
    icd_codes: list[str]
    text: str


def tokenize(text: str) -> List[str]:
    return [w.lower() for w in WORD_RE.findall(text)]


class BM25Index:
    def __init__(self, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

        self.chunks: List[Chunk] = chunks
        self.tfs: List[Dict[str, int]] = []   # per-chunk term frequencies
        self.dls: List[int] = []              # per-chunk doc length (tokens)
        self.df: Dict[str, int] = {}          # document frequency
        self.avgdl: float = 0.0

        self._build_stats()

    @staticmethod
    def _chunk_text(text: str, max_len: int = 1200, overlap: int = 150) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        if len(text) <= max_len:
            return [text]
        out = []
        i = 0
        while i < len(text):
            out.append(text[i:i + max_len])
            i += max_len - overlap
        return out

    @classmethod
    def build_from_jsonl(cls, jsonl_path: str | Path, max_len: int = 1200, overlap: int = 150):
        jsonl_path = Path(jsonl_path)
        chunks: List[Chunk] = []

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)

                protocol_id = obj.get("protocol_id", "")
                source_file = obj.get("source_file", "")
                title = obj.get("title", "")
                icd_codes = obj.get("icd_codes", []) or []
                full_text = obj.get("text", "") or ""

                for part in cls._chunk_text(full_text, max_len=max_len, overlap=overlap):
                    chunks.append(
                        Chunk(
                            protocol_id=protocol_id,
                            source_file=source_file,
                            title=title,
                            icd_codes=icd_codes,
                            text=part,
                        )
                    )

        return cls(chunks)

    def _build_stats(self):
        total_dl = 0
        self.tfs = []
        self.dls = []
        self.df = {}

        for ch in self.chunks:
            toks = tokenize(ch.text)
            dl = len(toks)
            self.dls.append(dl)
            total_dl += dl

            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            self.tfs.append(tf)

            # df counts each term once per document
            for t in tf.keys():
                self.df[t] = self.df.get(t, 0) + 1

        self.avgdl = (total_dl / max(len(self.chunks), 1)) if self.chunks else 0.0

    def idf(self, term: str) -> float:
        N = len(self.chunks)
        df = self.df.get(term, 0)
        if df == 0 or N == 0:
            return 0.0
        # standard BM25 idf
        return math.log(1.0 + (N - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: List[str], idx: int) -> float:
        tf = self.tfs[idx]
        dl = self.dls[idx]
        if dl == 0:
            return 0.0

        score = 0.0
        for t in query_tokens:
            f = tf.get(t, 0)
            if f == 0:
                continue
            idf = self.idf(t)
            denom = f + self.k1 * (1.0 - self.b + self.b * (dl / (self.avgdl + 1e-9)))
            score += idf * (f * (self.k1 + 1.0)) / (denom + 1e-9)
        return score

    def search(self, query: str, top_k: int = 6) -> List[Tuple[float, Chunk]]:
        q = tokenize(query)
        if not q:
            return []

        scored: List[Tuple[float, int]] = []
        for i in range(len(self.chunks)):
            s = self.score(q, i)
            if s > 0:
                scored.append((s, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: List[Tuple[float, Chunk]] = []
        for s, i in scored[:top_k]:
            out.append((s, self.chunks[i]))
        return out