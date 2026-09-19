"""Benchmark truy xuat cho corpus quy dinh thu vien VinUni.

Cong cu do cua rieng toi (khong nam trong 42 test cua src/).

Chay:
    python bench.py                 # chien luoc mac dinh
    python bench.py --strategy fixed
    python bench.py --strategy recursive
    python bench.py > ket_qua_benchmark.txt

Moi thanh vien trong nhom chi doi DUNG MOT dong -- bien CHUNKER duoi day --
sang chien luoc cua minh. Moi thu khac giu nguyen de so sanh cong bang.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from src import (
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    KnowledgeBaseAgent,
    RecursiveChunker,
    SentenceChunker,
    _mock_embed,
)

DATA_DIR = Path("data/thu-vien")
CACHE_PATH = Path(".embedding_cache.json")


# --------------------------------------------------------------------------
# Chien luoc cua toi: chunk theo tieu de / muc
# --------------------------------------------------------------------------
class HeadingChunker:
    """Chia nho van ban quy dinh theo tieu de Markdown (##, ###).

    Ly do thiet ke: van ban quy dinh duoc NGUOI SOAN chia san theo muc, moi muc
    da la mot don vi ngu nghia tron ven ("Overdue fines", "Renewal conditions").
    Cat theo ranh gioi do giu nguyen y dinh cua tac gia, thay vi cat theo so ky
    tu vo tinh xe doi mot dieu khoan.

    Hai chi tiet quan trong:

    1. Section dai hon max_chars thi ha xuong RecursiveChunker.
    2. Khi phai cat nho mot section, GAN LAI TIEU DE vao tung manh con. Khong co
       buoc nay, manh thu hai tro di mat ngu canh "day la muc noi ve cai gi" --
       chunk chi con "20,000 VND / day" ma khong biet la phi gi.
    """

    HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)

    def __init__(self, max_chars: int = 900) -> None:
        self.max_chars = max_chars
        self._fallback = RecursiveChunker(chunk_size=max_chars)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        starts = [m.start() for m in self.HEADING.finditer(text)]
        if not starts:
            return self._fallback.chunk(text)
        if starts[0] > 0:
            starts.insert(0, 0)

        sections: list[str] = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)

        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.max_chars:
                chunks.append(section)
                continue

            lines = section.splitlines()
            heading = lines[0].strip() if self.HEADING.match(lines[0]) else ""
            body = "\n".join(lines[1:]) if heading else section
            for piece in self._fallback.chunk(body):
                # Gan lai tieu de vao tung manh con
                chunks.append(f"{heading}\n\n{piece}".strip() if heading else piece)

        return [c for c in chunks if c.strip()]


STRATEGIES = {
    "heading": lambda: HeadingChunker(max_chars=900),
    "recursive": lambda: RecursiveChunker(chunk_size=900),
    "fixed": lambda: FixedSizeChunker(chunk_size=900, overlap=150),
    "sentence": lambda: SentenceChunker(max_sentences_per_chunk=5),
}

# >>> DOI DUNG MOT DONG NAY sang chien luoc cua ban <<<
DEFAULT_STRATEGY = "fixed"


# --------------------------------------------------------------------------
# 5 benchmark query cua nhom (thong nhat chung, moi nguoi chay cung bo nay)
# --------------------------------------------------------------------------
QUERIES = [
    {
        "id": 1,
        "query": "How long is my loan period and how many items can I borrow?",
        "kind": "tra so lieu / can loc doi tuong",
        "metadata_filter": {"audience": "student"},
        "gold_doc_ids": ["muon-tai-lieu-sinh-vien-dai-hoc",
                         "muon-tai-lieu-hoc-vien-sau-dai-hoc"],
        # chuoi dac trung PHAI xuat hien trong ngu canh truy xuat duoc
        "must_contain": ["2 weeks", "1 month"],
        "gold_answer": ("Sinh vien dai hoc: 3 cuon, 2 tuan, gia han 1 lan. "
                        "Hoc vien sau dai hoc: 5 cuon, 1 thang, gia han 1 lan. "
                        "KHONG phai 6 thang -- do la han muc cua giang vien."),
    },
    {
        "id": 2,
        "query": "How much is the overdue fine per day for a normal book?",
        "kind": "tra so lieu",
        "metadata_filter": None,
        "gold_doc_ids": ["phi-phat-qua-han"],
        "must_contain": ["20,000 VND"],
        "gold_answer": ("20.000 VND / ngay qua han / tai lieu doi voi tai lieu thuong. "
                        "Tai lieu course-specific va thiet bi la 20.000 VND / GIO."),
    },
    {
        "id": 3,
        "query": "Can I renew a book that is already overdue?",
        "kind": "hoi dieu kien (co/khong)",
        "metadata_filter": None,
        "gold_doc_ids": ["muon-tai-lieu-sinh-vien-dai-hoc", "phan-loai-tai-lieu-duoc-muon"],
        "must_contain": ["cannot be renewed", "no request"],
        "gold_answer": ("Khong. Tai lieu qua han khong duoc gia han. Gia han chi duoc "
                        "phep khi chua co nguoi khac yeu cau, va thoi han gia han bang "
                        "mot nua thoi han muon goc."),
    },
    {
        "id": 4,
        "query": "How long can a group book a study room and how far in advance?",
        "kind": "hoi quy trinh + gioi han",
        "metadata_filter": None,
        "gold_doc_ids": ["dat-phong-hoc-nhom"],
        "must_contain": ["2 hours per session", "1 week in advance"],
        "gold_answer": ("Toi da 2 gio / luot, 2 luot / ngay, 4 luot / tuan tinh chung "
                        "moi phong. Dat truoc toi da 1 tuan. Nhom phai co it nhat 2 nguoi. "
                        "Khong den trong 10 phut dau thi mat luot."),
    },
    {
        "id": 5,
        "query": "Which library materials cannot be borrowed and must be read in the library?",
        "kind": "liet ke",
        "metadata_filter": None,
        "gold_doc_ids": ["phan-loai-tai-lieu-duoc-muon"],
        "must_contain": ["Reference materials", "Uncirculated"],
        "gold_answer": ("Reference materials va print journals khong duoc muon "
                        "(uncirculated), chi doc tai thu vien. Sach Course Reserve co "
                        "muon duoc nhung chi 02 gio, 01 cuon/nguoi/luot."),
    },
]


# --------------------------------------------------------------------------
# Nap du lieu
# --------------------------------------------------------------------------
def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Tach YAML frontmatter thanh metadata, phan con lai thanh content."""
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def load_documents(chunker) -> list[Document]:
    """Doc .md -> tach frontmatter -> chunk phan than -> moi chunk mot Document."""
    docs: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        metadata, content = parse_frontmatter(path.read_text(encoding="utf-8"))
        for i, chunk in enumerate(chunker.chunk(content)):
            docs.append(
                Document(
                    id=f"{path.stem}#{i}",
                    content=chunk,
                    # Trai TOAN BO frontmatter vao MOI chunk, neu khong
                    # search_with_filter khong co gi de loc.
                    # doc_id tro ve TEN FILE GOC, khong phai id cua chunk.
                    metadata={**metadata, "doc_id": path.stem, "chunk_index": i},
                )
            )
    return docs


def build_embedder():
    """Chon backend theo .env, co cache theo hash noi dung de chay lai khong ton quota."""
    load_dotenv(override=False)
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()

    if provider == "gemini":
        from src import GeminiEmbedder
        base = GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"))
    elif provider == "local":
        from src import LocalEmbedder
        base = LocalEmbedder()
    elif provider == "openai":
        from src import OpenAIEmbedder
        base = OpenAIEmbedder()
    else:
        base = _mock_embed

    cache: dict[str, list[float]] = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    name = getattr(base, "_backend_name", "mock")

    def cached(text: str) -> list[float]:
        key = hashlib.sha256(f"{name}::{text}".encode("utf-8")).hexdigest()
        if key not in cache:
            cache[key] = base(text)
        return cache[key]

    cached._backend_name = name
    cached._save = lambda: CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    return cached


def demo_llm(prompt: str) -> str:
    """LLM gia lap: tra ve chinh ngu canh da truy xuat de kiem grounding."""
    body = prompt.split("NGU CANH:", 1)[-1].split("CAU HOI:", 1)[0].strip()
    return body[:700].replace("\n", " ")


# --------------------------------------------------------------------------
# Chay benchmark
# --------------------------------------------------------------------------
def show(results: list[dict], indent: str = "     ") -> None:
    if not results:
        print(f"{indent}(khong co ket qua)")
        return
    for rank, r in enumerate(results, 1):
        m = r["metadata"]
        head = r["content"].splitlines()[0][:64]
        print(f"{indent}{rank}. score={r['score']:+.4f}  {m['doc_id']}#{m.get('chunk_index')} "
              f"[audience={m.get('audience')}]  {head}")


def score_query(q: dict, results: list[dict], context: str) -> tuple[int, str]:
    """Cham hai muc: doc_id o top-3 VA ngu canh that su chua cau tra loi."""
    top_ids = [r["metadata"]["doc_id"] for r in results]
    hit_rank = next((i for i, d in enumerate(top_ids, 1) if d in q["gold_doc_ids"]), None)
    has_answer = all(s.lower() in context.lower() for s in q["must_contain"])

    if hit_rank is None:
        return 0, "gold KHONG co trong top-3"
    if hit_rank == 1 and has_answer:
        return 2, "gold o top-1 va ngu canh chua dap an"
    if has_answer:
        return 1, f"gold o top-{hit_rank}, ngu canh chua dap an"
    return 1, f"gold o top-{hit_rank} nhung ngu canh THIEU {q['must_contain']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=DEFAULT_STRATEGY, choices=sorted(STRATEGIES))
    args = ap.parse_args()

    chunker = STRATEGIES[args.strategy]()
    embedder = build_embedder()

    print("=" * 78)
    print(f"BENCHMARK TRUY XUAT -- corpus quy dinh thu vien VinUni")
    print(f"Sinh vien : Nguyen Thanh Duong (2A202602961) -- K4-DAY07")
    print(f"Chien luoc: {args.strategy} ({chunker.__class__.__name__})")
    print(f"Backend   : {embedder._backend_name}")
    print("=" * 78)

    docs = load_documents(chunker)
    store = EmbeddingStore(collection_name="vinuni_library", embedding_fn=embedder)
    store.add_documents(docs)
    agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)

    lengths = [len(d.content) for d in docs]
    n_files = len(list(DATA_DIR.glob("*.md")))
    print(f"\nDa nap {n_files} tai lieu -> {store.get_collection_size()} chunk")
    print(f"Do dai chunk: min={min(lengths)} / tb={sum(lengths)//len(lengths)} / max={max(lengths)}")

    total = 0
    for q in QUERIES:
        print("\n" + "-" * 78)
        print(f"[Q{q['id']}] {q['query']}")
        print(f"      dang: {q['kind']}  |  filter: {q['metadata_filter']}")

        results = store.search_with_filter(q["query"], top_k=3, metadata_filter=q["metadata_filter"])
        print("  Top-3:")
        show(results)

        context = "\n".join(r["content"] for r in results)
        points, why = score_query(q, results, context)
        total += points
        print(f"  => {points}/2 diem  ({why})")
        print(f"  Gold : {q['gold_answer']}")
        print(f"  Agent: {agent.answer(q['query'], top_k=3)[:220]}...")

        # A/B bat buoc cho cau can filter
        if q["metadata_filter"]:
            print("\n  --- A/B: chay lai KHONG filter ---")
            show(store.search(q["query"], top_k=3), indent="     ")

    print("\n" + "=" * 78)
    print(f"TONG DIEM CHAT LUONG TRUY XUAT: {total}/10  (chien luoc: {args.strategy})")
    print("=" * 78)

    if hasattr(embedder, "_save"):
        embedder._save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
