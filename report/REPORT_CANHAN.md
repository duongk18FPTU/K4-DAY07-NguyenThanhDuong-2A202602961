# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thanh Dương
**Mã sinh viên:** 2A202602961
**Ngày:** 2026-09-19

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine similarity cao nghĩa là hai vector embedding có hướng gần nhau, nên hai đoạn văn được mô hình biểu diễn là gần nhau về mặt ngữ nghĩa. Giá trị càng gần `1` thì mức tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên có thể đặt phòng học nhóm trực tuyến.
- Câu B: Người học được phép đăng ký chỗ thảo luận qua mạng.
- Tại sao tương đồng: Hai câu dùng từ vựng khác nhau nhưng cùng diễn đạt việc sinh viên đặt một không gian học nhóm bằng hình thức trực tuyến.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Thư viện áp dụng phí phạt đối với tài liệu trả quá hạn.
- Câu B: Mạng nơ-ron sâu học đặc trưng qua nhiều tầng.
- Tại sao khác: Hai câu thuộc hai chủ đề và mục đích hoàn toàn khác nhau: quy định thư viện và kỹ thuật học máy.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine tập trung vào góc giữa hai vector, tức hướng biểu diễn ngữ nghĩa, và ít bị ảnh hưởng bởi độ lớn vector do độ dài câu hoặc cách biểu diễn. Khoảng cách Euclid phụ thuộc cả độ lớn nên hai câu cùng nghĩa vẫn có thể bị xem là xa nhau; với vector đã chuẩn hóa, dot product cũng chính là cosine similarity.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: `ceil((10,000 - 50) / (500 - 50)) = ceil(9,950 / 450) = ceil(22.111...) = 23`.
> Đáp án: **23 chunks**. Kết quả kiểm tra bằng `FixedSizeChunker` cũng trả về `23`.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi `overlap=100`, số chunk là `ceil((10,000 - 100) / (500 - 100)) = ceil(9,900 / 400) = 25`, tức tăng từ 23 lên 25; kết quả chạy `FixedSizeChunker` cũng là `25`. Overlap lớn hơn giúp giữ ngữ cảnh nằm sát ranh giới giữa hai chunk và giảm nguy cơ tách rời câu hỏi khỏi thông tin trả lời, đổi lại phải lưu và tìm kiếm nhiều chunk hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex lookbehind `(?<=[.!?])(?:[ \t]+|\n+)` để tách tại khoảng trắng hoặc xuống dòng nằm sau dấu kết câu, nhờ đó dấu `.`, `!`, `?` vẫn được giữ lại. Sau khi loại khoảng trắng thừa, các câu được gom theo `max_sentences_per_chunk`; text rỗng hoặc chỉ có khoảng trắng trả về `[]`. Edge case chưa xử lý hoàn toàn là chữ viết tắt như `TS.`, `v.v.` và số thập phân có thể bị nhận nhầm là ranh giới câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử separator theo thứ tự từ ranh giới lớn đến nhỏ; mảnh còn dài hơn `chunk_size` được đệ quy với các separator còn lại, sau đó các mảnh nhỏ liền kề được gom lại tới sát giới hạn. Ba base case là: text rỗng trả `[]`, text đã đủ ngắn trả một chunk, và khi hết separator (hoặc gặp separator rỗng) thì cắt cứng theo `chunk_size`. Separator được giữ lại trong lúc chia để tránh làm mất dấu câu và ranh giới đoạn.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Store chỉ dùng danh sách in-memory; `_make_record` copy metadata, bổ sung `doc_id` gốc nếu thiếu, rồi lưu content cùng embedding. `add_documents` xem mỗi `Document` là một record và không tự chunk. `search` gọi helper chung `_search_records`, tính dot product giữa query embedding và từng record, sắp xếp score giảm dần và không đưa vector embedding vào output.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc toàn bộ ứng viên theo tất cả cặp key-value trong metadata trước, rồi mới similarity search và lấy top-k; cách này tránh để tài liệu sai metadata chiếm các vị trí top-k. `delete_document` loại mọi record có `metadata['doc_id']` khớp tài liệu gốc và trả `True` khi kích thước store giảm, ngược lại trả `False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent truy xuất top-k, dựng mỗi chunk thành khối `[1]`, `[2]`, `[3]` kèm `source_url`, `source` hoặc `doc_id`, rồi đưa các khối này vào phần `Context` của prompt. Prompt yêu cầu chỉ dùng ngữ cảnh được cung cấp, trích dẫn bằng số nguồn và nói rõ khi không tìm thấy thông tin. Nếu store không trả kết quả, agent trả thông báo ngay và không gọi LLM.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.10.8, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\VinAI20K\K4-DAY07-NguyenThanhDuong-2A202602961
plugins: anyio-4.15.1
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.07s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế (MockEmb) | Nhận xét |
|------|-----------|-----------|---------|----------------------|----------|
| 1 | "Sinh vien muon toi da 3 cuon, 2 tuan." | "Undergraduate: borrow up to 3 items, 2 weeks." | cao | **+0.1503** | Đúng hướng — hai câu cùng chủ đề mượn sách |
| 2 | "Phi phat qua han 20.000 VND/ngay." | "Late return fee is 20,000 VND per day." | cao | **−0.1102** | Bất ngờ — mock không hiểu ngữ nghĩa, hash ngẫu nhiên |
| 3 | "Sinh vien duoc muon 3 cuon." | "Thu vien dong cua luc 5 gio chieu." | thấp | **−0.1275** | Đúng — hai câu khác chủ đề hoàn toàn |
| 4 | "Can I renew an overdue book?" | "Overdue items cannot be renewed." | cao | **−0.1375** | Bất ng᷑ — mock không nhận ra cùng từ “renew/overdue” |
| 5 | "Study room booking rules." | "Phi phat tai lieu qua han." | thấp | **−0.1555** | Đúng hướng — hai chủ đề khác nhau |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> **Cặp 2 và 4 bất ngờ nhất**: Cặp 2 gồm hai câu cùng nghĩa (tiếng Việt và tiếng Anh về phí phạt) nhưng MockEmbedder trả về **−0.11** (tương phản), chứng tỏ MD5 hash hoàn toàn không biết “phí phạt” và “fine” là cùng nghĩa. Cặp 4 có từ trùng nhau (“renew”, “overdue”) nhưng vẫn cho score âm. Điều này xác nhận rằng: **MockEmbedder đo độ giống chuỗi ký tự ngẫu nhiên, không phải ngữ nghĩa**. Chỉ semantic embedding thật (Gemini/Local) mới cho cặp 2 và 4 score cao như dự đoán.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên chiến lược cá nhân. File kết quả: `ket_qua_benchmark.txt`.

**Thông tin benchmark:**
- Chiến lược: `FixedSizeChunker(chunk_size=900, overlap=150)` — `DEFAULT_STRATEGY = "fixed"`
- Backend: **`gemini-embedding-001`** (semantic embedding thật)
- Số chunk nạp: **20 chunk** từ 10 file | min=158 / tb=694 / max=900 ký tự

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được | Score | Liên quan? | Điểm (/2) |
|---|-------|--------------------------------|-------|-----------|------------|
| 1 | How long is my loan period? *(filter: student)* | `muon-tai-lieu-sinh-vien-dai-hoc#0` — Borrowing privilege - Undergraduate | +0.7042 | ✅ gold top-1 | 2/2 |
| 2 | How much is the overdue fine per day for a normal book? | `phi-phat-qua-han#0` — Overdue fines and replacement fees | +0.7632 | ✅ gold top-1 | 2/2 |
| 3 | Can I renew a book that is already overdue? | `phi-phat-qua-han#0` — Overdue fines and replacement fees | +0.6973 | ⚠️ gold ở top-3, thiếu chuỗi `cannot be renewed` | 1/2 |
| 4 | How long can a group book a study room and how far in advance? | `dat-phong-hoc-nhom#0` — Study room booking | +0.7717 | ✅ gold top-1 | 2/2 |
| 5 | Which library materials cannot be borrowed? | `phan-loai-tai-lieu-duoc-muon#0` — Circulation regulations | +0.7104 | ✅ gold top-1 | 2/2 |

**Tổng điểm chất lượng truy xuất: 9/10**

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Phân tích failure case Q3 (1/2):**
> Câu Q3 hỏi về điều kiện gia hạn sách quá hạn. Gold doc (`muon-tai-lieu-sinh-vien-dai-hoc`) lọt top-3 nhưng **đó là chunk #1** — nội dung chunk này chỉ nói về **recall** ("All loans are subject to recall after one week's usage..."), không chứa quy tắc gia hạn. Câu "Overdue items cannot be renewed" thực ra nằm ở **chunk #0** nhưng chunk #0 không vào top-3 vì bị `phi-phat-qua-han#0` (score 0.6973) và `phi-phat-qua-han#1` (0.6561) đẩy ra. Kết quả: gold lọt top-3 về doc_id nhưng ngữ cảnh truy xuất được không chứa câu trả lời đúng — đây chính là lý do benchmark trừ điểm `must_contain`.

**Điều hay nhất tôi học được qua kết quả này:**
> So sánh mock vs Gemini cùng chiến lược `fixed`: **2/10 → 9/10**. Embedding thật giải quyết hoàn toàn failure case Q2, Q4, Q5 vốn là nhiễu do MD5 hash. Failure case duy nhất còn lại (Q3) là vấn đề **chunking**: chunk 900 ký tự quá lớn, nhồi nhiều chủ đề, khiến chunk "phí phạt" (liên quan overdue) vượt chunk "điều kiện gia hạn" về score. Giải pháp: dùng chunk nhỏ hơn hoặc `HeadingChunker` để tách riêng section "Renewal conditions".

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 9 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 4 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 9 / 10 |
| **Tổng phần cá nhân** | **57 / 60** |
