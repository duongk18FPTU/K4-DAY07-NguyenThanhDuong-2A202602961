# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** 3c1lop3a
**Thành viên:** Võ Doanh Nhân (2A202602770) · Ngô Minh Trí (2A202602993) · Nguyễn Thanh Dương (2A202602961)
**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Quy định và dịch vụ **thư viện đại học** — VinUniversity Library (đúng ràng buộc L3A: dịch vụ/quy định đại học).

**Tại sao nhóm chọn chủ đề này?**

> Tiêu chí chọn của nhóm không phải "chủ đề nào hay" mà là **"chủ đề nào cho phép tách `audience` thành nhiều giá trị khác nhau trên cùng một nội dung"**. Ràng buộc L3A yêu cầu ít nhất một benchmark query phải *cần* `metadata_filter={"audience": "student"}` mới trả lời đúng; nếu corpus chỉ toàn `audience: student` thì filter không có gì để lọc và cả phần đánh giá trở nên vô nghĩa.
>
> Quy định thư viện thoả điều kiện đó tốt hơn mọi mảng khác: **cùng một câu hỏi "được mượn bao lâu" có bốn đáp án khác nhau** tuỳ đối tượng — sinh viên đại học 2 tuần, học viên sau đại học 1 tháng, giảng viên 6 tháng, nhân viên 2 tuần. Bốn tài liệu này dùng gần như y hệt từ vựng (`Circulation privilege`, `loan period`, `renewal`) nên embedding **không thể tự phân biệt**, buộc metadata phải làm việc thật.
>
> Ngoài ra nguồn VinUni phù hợp về mặt kỹ thuật: văn bản có cấu trúc mục rõ ràng (thuận cho chiến lược chunk theo heading), nhiều con số cụ thể và kiểm chứng được (20.000 VND/ngày, 19 phòng, 2 giờ/lượt) nên gold answer không phải suy đoán.

### Danh sách tài liệu (Data Inventory)

Thu thập bằng `scripts/fetch_public_pages.py` (kiểm `robots.txt`, giãn ≥1 giây/request), sau đó **làm sạch thủ công** để loại menu điều hướng, breadcrumb và footer — output thô của crawler giữ nguyên toàn bộ menu, một trang 3 KB nội dung ra file 11–13 KB. Xem `data/thu-vien/sources.csv`.

| # | Tên tài liệu (`doc_id`) | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | `muon-tai-lieu-sinh-vien-dai-hoc` | library.vinuni.edu.vn/borrowing-priviledge/ | 2026-09-19 / not-stated | 1.224 | `audience=student`, `user_group=undergraduate`, `category=borrowing` |
| 2 | `muon-tai-lieu-hoc-vien-sau-dai-hoc` | library.vinuni.edu.vn/borrowing-priviledge/ | 2026-09-19 / not-stated | 737 | `audience=student`, `user_group=graduate`, `category=borrowing` |
| 3 | `dat-phong-hoc-nhom` | library.vinuni.edu.vn/room-booking/ | 2026-09-19 / not-stated | 1.176 | `audience=student`, `category=facilities` |
| 4 | `muon-tai-lieu-giang-vien` | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | 948 | `audience=faculty`, `category=borrowing` |
| 5 | `muon-tai-lieu-nhan-vien-va-giang-vien-lien-ket` | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | 909 | `audience=staff`, `category=borrowing` |
| 6 | `doi-tuong-khong-duoc-muon` | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | 698 | `audience=all`, `user_group=visitor-guest-alumni` |
| 7 | `phan-loai-tai-lieu-duoc-muon` | library.vinuni.edu.vn/borrowing-priviledge/ | 2026-09-19 / not-stated | 1.483 | `audience=all`, `category=borrowing` |
| 8 | `phi-phat-qua-han` | library.vinuni.edu.vn/faq/ | 2026-09-19 / not-stated | 1.923 | `audience=all`, `category=fines` |
| 9 | `gio-mo-cua-va-quyen-ra-vao` | library.vinuni.edu.vn/about-us/hours-and-access/ | 2026-09-19 / not-stated | 1.154 | `audience=all`, `category=access` |
| 10 | `quy-dinh-chung-va-an-toan` | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | 2.151 | `audience=all`, `category=policy` |

**Phân bố `audience`:** `student` = 3 · `all` = 5 · `faculty` = 1 · `staff` = 1 → **4 giá trị khác nhau**.

**Quyết định tách file quan trọng nhất:** trang `borrowing-priviledge` của VinUni gộp bảng hạn mức cho **tất cả** đối tượng trong *một* trang. Nếu lưu thành một file `audience: all` thì `metadata_filter={"audience":"student"}` không lọc được gì — bốn đáp án nằm chung một tài liệu. Nhóm tách thành các file riêng theo đối tượng (mục 1, 2, 4, 5 ở bảng trên). Chính quyết định này là thứ làm cho phần A/B ở mục 3 có số liệu thật.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Corpus chỉ chứa nguồn công khai/được phép dùng, không có dữ liệu cá nhân, thông tin đăng nhập hay tài liệu nội bộ. Toàn bộ là trang công khai của VinUniversity, không có nội dung sau đăng nhập.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc `not-stated`). `sources.csv` khớp 1-1 với 10 file `.md`.
- [x] `robots.txt` của cả `library.vinuni.edu.vn` và `policy.vinuni.edu.vn` đều là `User-agent: * / Disallow:` (cho phép toàn bộ) — đã kiểm trực tiếp trước khi crawl.
- [x] Không bịa `document_version`: chỉ 4 tài liệu lấy từ trang policy mới ghi `POL-LLR-001-V4.0` (số hiệu do chính nguồn nêu), 6 tài liệu còn lại ghi `not-stated`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | enum | `student` / `faculty` / `staff` / `all` | **Trường quan trọng nhất.** Bốn tài liệu hạn mức mượn dùng cùng từ vựng nên embedding không phân biệt được; `audience` là chiều duy nhất tách đúng/sai theo đối tượng hỏi. |
| `user_group` | enum | `undergraduate` / `graduate` / `faculty` / `staff` | Tách mịn hơn `audience`. Cần vì cả sinh viên đại học (2 tuần) lẫn học viên sau đại học (1 tháng) đều là `student` nhưng khác đáp án. |
| `category` | enum | `borrowing` / `fines` / `access` / `facilities` / `policy` | Lọc theo loại câu hỏi. Câu hỏi về tiền phạt không cần lẫn với câu hỏi đặt phòng. |
| `doc_id` | string | `phi-phat-qua-han` | Trỏ về **file gốc** (không phải id chunk `file#3`). Cho phép `delete_document()` xoá cả cụm chunk và cho phép truy vết câu trả lời về đúng tài liệu. |
| `source_url` | url | `https://library.vinuni.edu.vn/faq/` | Agent in kèm trong ngữ cảnh → đáp ứng tiêu chí *Source Traceability*. Với corpus quy định thì truy nguồn là bắt buộc. |
| `document_version` | string | `POL-LLR-001-V4.0` / `not-stated` | Kiểm tra độ mới. Quy định thư viện đổi theo năm học; không có version thì không biết câu trả lời còn hiệu lực không. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Ba thành viên thử **ba chiến lược khác nhau** trên cùng bộ tài liệu, cùng 5 câu hỏi, cùng backend `gemini-embedding-001`. Mỗi người chỉ đổi **một dòng** — dòng chọn chunker trong `bench.py` — mọi thứ khác giữ nguyên để so sánh công bằng.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(body, chunk_size=900)` trên 3 tài liệu (đã **bỏ frontmatter** trước khi đo, nếu không là đang đo cả khối YAML):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `muon-tai-lieu-sinh-vien-dai-hoc` | FixedSizeChunker (`fixed_size`) | 2 | 656 | ❌ Cắt giữa mục `## Renewal conditions` |
| | SentenceChunker (`by_sentences`) | 4 | 304 | ⚠️ Giữ câu trọn vẹn nhưng tách rời bảng khỏi tiêu đề |
| | RecursiveChunker (`recursive`) | 2 | 610 | ⚠️ Tôn trọng đoạn nhưng vẫn gộp 2 mục khác nhau |
| | **HeadingChunker (custom)** | **5** | **243** | ✅ Mỗi mục quy định là một chunk trọn vẹn |
| `phi-phat-qua-han` | FixedSizeChunker | 3 | 701 | ❌ Bảng phí bị xé giữa hàng |
| | SentenceChunker | 4 | 478 | ⚠️ Bảng Markdown bị coi là một "câu" khổng lồ |
| | RecursiveChunker | 3 | 639 | ⚠️ Giữ bảng nhưng mất tiêu đề mục |
| | **HeadingChunker** | **4** | **479** | ✅ `## Overdue fines` giữ trọn cả bảng phí |
| `quy-dinh-chung-va-an-toan` | FixedSizeChunker | 3 | 777 | ❌ |
| | SentenceChunker | 6 | 356 | ⚠️ |
| | RecursiveChunker | 3 | 715 | ⚠️ |
| | **HeadingChunker** | **6** | **357** | ✅ |

**Đọc bảng:** HeadingChunker cho chunk **nhiều hơn và ngắn hơn** (243–479 ký tự so với 610–777 của recursive/fixed). Thoạt nhìn chunk ngắn có vẻ bất lợi, nhưng với văn bản quy định thì ngược lại: mỗi chunk tương ứng đúng **một điều khoản**, nên khi lọt top-k nó mang theo trọn vẹn quy tắc chứ không phải nửa quy tắc này cộng nửa quy tắc kia.

### Chiến lược của từng thành viên

**Thành viên 1 — Võ Doanh Nhân (2A202602770)**
- **Loại chiến lược:** `HeadingChunker` — **custom**, chunk theo tiêu đề/mục (vai bắt buộc của nhóm theo ràng buộc L3A)
- **Tham số:** `max_chars=900`, fallback `RecursiveChunker(900)`
- **Kết quả:** 10 tài liệu → **41 chunk**, min=20 / tb=300 / max=887 · **10/10 điểm**
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản quy định được **người soạn** chia sẵn theo mục (`## Overdue fines`, `## Renewal conditions`), mỗi mục đã là một đơn vị ngữ nghĩa trọn vẹn. Cắt theo ranh giới đó giữ nguyên ý định của tác giả, thay vì áp một con số ký tự tuỳ ý lên trên và vô tình xé đôi một điều khoản. Chi tiết dễ bỏ sót mà tôi có xử lý: khi một mục dài quá `max_chars` phải hạ xuống recursive, **gắn lại tiêu đề vào từng mảnh con** — không có bước này, mảnh thứ hai trở đi chỉ còn `"20,000 VND / day"` mà mất ngữ cảnh "đây là phí gì".
- **Code snippet:**
```python
class HeadingChunker:
    HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)

    def __init__(self, max_chars: int = 900) -> None:
        self.max_chars = max_chars
        self._fallback = RecursiveChunker(chunk_size=max_chars)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        starts = [m.start() for m in self.HEADING.finditer(text)]
        if not starts:
            return self._fallback.chunk(text)      # khong co heading -> ha xuong recursive
        if starts[0] > 0:
            starts.insert(0, 0)                    # giu phan mo dau truoc heading dau tien

        sections = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            if text[start:end].strip():
                sections.append(text[start:end].strip())

        chunks = []
        for section in sections:
            if len(section) <= self.max_chars:
                chunks.append(section)
                continue
            lines = section.splitlines()
            heading = lines[0].strip() if self.HEADING.match(lines[0]) else ""
            body = "\n".join(lines[1:]) if heading else section
            for piece in self._fallback.chunk(body):
                # GAN LAI TIEU DE vao tung manh con
                chunks.append(f"{heading}\n\n{piece}".strip() if heading else piece)
        return [c for c in chunks if c.strip()]
```

**Thành viên 2 — Ngô Minh Trí (2A202602993)**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=900)` — dùng class tự viết trong `src/chunking.py`
- **Kết quả:** 10 tài liệu → **20 chunk**, min=199 / tb=618 / max=877 · **9/10 điểm**
- **Mô tả & lý do chọn:** *(theo mô tả của Trí trong `REPORT_CANHAN.md` mục 2)* — "Thuật toán ưu tiên tách theo `\n\n`, rồi `\n`, `. `, khoảng trắng và cuối cùng là ký tự; các phần nhỏ được gộp lại đến gần `chunk_size`. Base case là đoạn đã không vượt `chunk_size`; nếu không còn separator, đoạn dài được cắt theo ký tự để bảo đảm không tạo chunk quá lớn." Ưu tiên ranh giới đoạn tự nhiên là lựa chọn hợp lý cho văn bản có cấu trúc, và kết quả cho chunk dài gấp đôi heading (tb 618 so với 300) nên mỗi chunk mang nhiều ngữ cảnh hơn.
- **Quan sát của Trí sau khi chạy:** *(trích nguyên văn)* — "Recursive chunking tạo ít chunk hơn, nhưng Q3 cho thấy một chunk rộng về phạt quá hạn có thể xếp trên điều khoản gia hạn cụ thể; vì vậy cần so sánh chiến lược theo từng loại câu hỏi, không chỉ theo điểm tổng."
- **Code snippet (nếu custom):** không — dùng `RecursiveChunker` trong `src/chunking.py` do Trí tự cài đặt

**Thành viên 3 — Nguyễn Thanh Dương (2A202602961)**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=900, overlap=150)` — đường cơ sở có chồng lấn
- **Kết quả:** 10 tài liệu → **20 chunk**, min=158 / tb=694 / max=900 · **9/10 điểm**
- **Mô tả & lý do chọn:** Cắt cứng theo số ký tự với `overlap=150` làm đường cơ sở để nhóm đo xem hai chiến lược "thông minh" hơn thắng được bao nhiêu. Overlap đặt ở mức ~17% `chunk_size` nhằm nhân bản vùng giáp ranh, cho mỗi thông tin hơn một cơ hội lọt top-k khi nó nằm vắt ngang ranh giới cắt. Số đo cho thấy chiến lược này sinh chunk dài nhất nhóm (tb 694) và là chiến lược duy nhất có chunk **chạm đúng trần 900** — dấu hiệu của việc cắt máy móc không theo ngữ nghĩa.
- **Kết luận của Dương sau khi chạy:** *(trích `REPORT_CANHAN.md` mục 5 của Dương)* — "Failure case duy nhất còn lại (Q3) là vấn đề **chunking**: chunk 900 ký tự quá lớn, nhồi nhiều chủ đề, khiến chunk 'phí phạt' (liên quan overdue) vượt chunk 'điều kiện gia hạn' về score. Giải pháp: dùng chunk nhỏ hơn hoặc `HeadingChunker` để tách riêng section 'Renewal conditions'."
- **Code snippet (nếu custom):** không — dùng `FixedSizeChunker` có sẵn trong `src/chunking.py`

> **Đáng chú ý:** Dương tự đi đến kết luận nên dùng `HeadingChunker` **từ phía đường cơ sở đi lên**, độc lập với việc Nhân chọn chiến lược đó **từ đầu** dựa trên cấu trúc văn bản. Hai hướng suy luận ngược nhau gặp nhau ở cùng một kết luận — đó là bằng chứng mạnh hơn nhiều so với việc chỉ một người khẳng định chiến lược của mình tốt.

### Đo riêng tác động của embedding backend (Dương)

Ngoài việc đổi chunker, Dương chạy thêm **cùng chiến lược `fixed` trên hai backend khác nhau** — đây là biến số mà ba chiến lược ở trên đều giữ cố định, nên nó tách được ảnh hưởng của embedding ra khỏi ảnh hưởng của chunking:

| Backend | Điểm | Q1 | Q2 | Q3 | Q4 | Q5 |
| --- | --- | --- | --- | --- | --- | --- |
| `MockEmbedder` (MD5 hash, 64 chiều) | **2/10** | 0 | 2 | 0 | 0 | 0 |
| `gemini-embedding-001` (3072 chiều) | **9/10** | 2 | 2 | 1 | 2 | 2 |

*(Nhóm đã chạy lại độc lập để xác nhận con số 2/10.)*

Với mock, Q5 trả về top-1 là `nhan-vien-va-giang-vien-lien-ket#0` (score +0.2404) cho câu hỏi về **tài liệu nào không được mượn** — hoàn toàn không liên quan, và tài liệu gold thậm chí không lọt top-3. Toàn bộ score nằm trong dải 0.20–0.24, tức **nhiễu quanh 0** đúng như kỳ vọng thống kê với vector ngẫu nhiên.

**Ý nghĩa cho việc so sánh chiến lược:** chênh lệch giữa ba chiến lược chunking là **1 điểm**, còn chênh lệch giữa mock và embedding thật là **7 điểm**. Nói cách khác, chọn đúng backend quan trọng gấp bảy lần chọn đúng chunker. Nếu nhóm chạy benchmark bằng mock thì mọi kết luận về chunking ở mục này đều vô nghĩa — ba chiến lược sẽ chỉ đang so xem cái nào may mắn hơn.

### So Sánh Giữa Các Thành Viên

Cả ba chạy cùng corpus (10 tài liệu), cùng 5 query, cùng backend `gemini-embedding-001`:

| Thành viên | Chiến lược | Số chunk | min / tb / max | Điểm | Q1 | Q2 | Q3 | Q4 | Q5 |
|-----------|----------|---------|-----------|------|----|----|----|----|----|
| **Võ Doanh Nhân** | **HeadingChunker (custom)** | **41** | 20 / **300** / 887 | **10/10** | 2 | 2 | **2** | 2 | 2 |
| Ngô Minh Trí | RecursiveChunker(900) | 20 | 199 / 618 / 877 | 9/10 | 2 | 2 | **1** | 2 | 2 |
| Nguyễn Thanh Dương | FixedSizeChunker(900, ov=150) | 20 | 158 / 694 / **900** | 9/10 | 2 | 2 | **1** | 2 | 2 |

| Thành viên | Điểm mạnh (đo được) | Điểm yếu (đo được) |
|---|---|---|
| Nhân | Mỗi chunk = một điều khoản trọn vẹn. Thắng Q3 vì giữ nguyên mục `## Renewal conditions` chứa cả hai vế của quy tắc gia hạn | Sinh gấp đôi số chunk (41 vs 20) → gấp đôi chi phí embedding. Phụ thuộc văn bản có heading; corpus không cấu trúc sẽ rơi về recursive và mất hết lợi thế |
| Trí | Chunk dài, ngữ cảnh dày, không có chunk vụn (min=199 — cao nhất nhóm, chứng tỏ bước gom mảnh nhỏ hoạt động đúng) | Gộp nhiều mục vào một chunk → Q3 để tài liệu tiền phạt chiếm cả top-1 lẫn top-2 |
| Dương | Overlap 150 giữ được thông tin vắt ngang ranh giới; đơn giản nhất, không phụ thuộc cấu trúc văn bản | Chunk dài nhất (tb 694) và **chạm trần 900** — cắt máy móc giữa bảng Markdown, chunk mất tính đọc được. Q3 hỏng giống Trí |

**Trạng thái phần cá nhân của ba thành viên** (mỗi người nộp `REPORT_CANHAN.md` riêng, ghi ở đây để nhóm nắm tiến độ chung):

| Thành viên | `pytest tests/ -v` | Python | Điểm tự đánh giá cá nhân |
|---|---|---|---|
| Võ Doanh Nhân | 42/42 | 3.12.10 | 60/60 |
| Ngô Minh Trí | 42/42 | — | *(chưa điền bảng tự đánh giá)* |
| Nguyễn Thanh Dương | 42/42 | 3.10.8 | 57/60 |

Cả ba đều đạt 42/42 trên ba máy và ba phiên bản Python khác nhau, nên bộ test không phụ thuộc môi trường.

**Một quan sát bất ngờ về mặt kỹ thuật:** ba thành viên viết `src/` **hoàn toàn độc lập** (Trí còn giữ cả nhánh ChromaDB mà Nhân đã bỏ, và prompt agent của ba người khác hẳn nhau), nhưng khi chạy cùng một chiến lược thì **điểm cosine trùng nhau đến 4 chữ số thập phân** — ví dụ Q1 top-1 của Dương và bản `fixed` đối chứng của Nhân đều là `+0.7042`; Q3 top-1 của Trí và bản `recursive` đối chứng đều là `+0.6908`. Điều đó xác nhận rằng đặc tả trong docstring của lab đủ chặt để các cài đặt độc lập hội tụ về cùng hành vi, và khác biệt điểm số giữa ba người **hoàn toàn đến từ lựa chọn chiến lược**, không phải từ lỗi cài đặt.

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> **HeadingChunker thắng, nhưng chênh lệch chỉ đúng 1 điểm và nằm gọn ở một câu hỏi — chính chỗ đó mới đáng nói.**
>
> Cả ba chiến lược đều đạt 2/2 ở Q1, Q2, Q4, Q5. Khác biệt duy nhất là **Q3: *"Can I renew a book that is already overdue?"***
>
> | | Top-1 | Top-2 | Top-3 | Điểm |
> |---|---|---|---|---|
> | Nhân (heading) | `sinh-vien-dai-hoc#2` **`## Renewal conditions`** +0.7563 | `hoc-vien-sau-dai-hoc#2` +0.7257 | `phi-phat-qua-han#1` +0.7099 | **2/2** |
> | Trí (recursive) | `phi-phat-qua-han#0` +0.6908 | `phi-phat-qua-han#1` +0.6674 | `sinh-vien-dai-hoc#1` +0.6630 | 1/2 |
> | Dương (fixed) | `phi-phat-qua-han#0` +0.6973 | `phi-phat-qua-han#1` +0.6561 | `sinh-vien-dai-hoc#1` +0.6529 | 1/2 |
>
> Với recursive và fixed, top-1 và top-2 đều là tài liệu **tiền phạt** — đúng chủ đề "overdue" nhưng **không chứa quy tắc gia hạn**; tài liệu gold chỉ lọt hạng 3, và chunk lọt được lại là đoạn nói về *recall* chứ không phải *renewal*. Ngữ cảnh trả về **không hề chứa** chuỗi `"cannot be renewed"`, nên agent không có căn cứ để trả lời "Không".
>
> HeadingChunker thắng vì mục `## Renewal conditions` trong tài liệu gốc chứa **cả hai vế** — *"renewal period is half of the original loan period... only allowed if there has been no request"* **và** *"Overdue items cannot be renewed"* — và chunker giữ nguyên cả mục làm một chunk. Hai chiến lược kia cắt ở ranh giới ~900 ký tự rơi vào giữa hai vế đó.
>
> **Bài học tổng quát hơn điểm số:** với văn bản quy định, ranh giới ngữ nghĩa **đã được người soạn đánh dấu sẵn bằng heading**. Chiến lược nào tôn trọng dấu đó thì thắng; chiến lược nào áp một con số ký tự tuỳ ý lên trên thì thỉnh thoảng cắt trúng chỗ hiểm. Nếu đổi sang chủ đề không có cấu trúc mục (email hỗ trợ, transcript hội thoại), HeadingChunker sẽ tự rơi về recursive và lợi thế biến mất — đây không phải chiến lược tốt phổ quát, mà là chiến lược **khớp với hình dạng của dữ liệu**.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> Đúng 5 câu, đa dạng dạng hỏi, gold answer **trích được từ tài liệu**, không suy đoán quy định của trường. Khai báo trong `bench.py` để cả ba thành viên chạy cùng một bộ.

| # | Câu hỏi (Query) | Dạng | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|------|-------------------------------|--------------------------|
| 1 | *How long is my loan period and how many items can I borrow?* **(cần `metadata_filter={"audience":"student"}`)** | tra số liệu | Sinh viên đại học: **3 cuốn, 2 tuần**, gia hạn 1 lần. Học viên sau đại học: **5 cuốn, 1 tháng**, gia hạn 1 lần. **Không phải 6 tháng** — đó là hạn mức giảng viên. | `muon-tai-lieu-sinh-vien-dai-hoc`, `muon-tai-lieu-hoc-vien-sau-dai-hoc` (mục `## Circulation privilege`) |
| 2 | *How much is the overdue fine per day for a normal book?* | tra số liệu | **20.000 VND / ngày quá hạn / tài liệu** với tài liệu thường. Tài liệu course-specific và thiết bị tính **20.000 VND / GIỜ**. | `phi-phat-qua-han` (mục `## Overdue fines`) |
| 3 | *Can I renew a book that is already overdue?* | hỏi điều kiện (có/không) | **Không.** Tài liệu quá hạn không được gia hạn. Gia hạn chỉ được phép khi chưa có người khác yêu cầu, và thời hạn gia hạn bằng **một nửa** thời hạn mượn gốc. | `muon-tai-lieu-sinh-vien-dai-hoc` (mục `## Renewal conditions`) |
| 4 | *How long can a group book a study room and how far in advance?* | hỏi quy trình + giới hạn | Tối đa **2 giờ/lượt, 2 lượt/ngày, 4 lượt/tuần** tính chung mọi phòng. Đặt trước tối đa **1 tuần**. Nhóm phải có ít nhất 2 người. Không đến trong **10 phút** đầu thì mất lượt. | `dat-phong-hoc-nhom` |
| 5 | *Which library materials cannot be borrowed and must be read in the library?* | liệt kê | **Reference materials và print journals** không được mượn (uncirculated), chỉ đọc tại thư viện. Sách Course Reserve mượn được nhưng chỉ **02 giờ**, 01 cuốn/người/lượt. | `phan-loai-tai-lieu-duoc-muon` (bảng phân loại) |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).
>
> **Nhóm chấm ở hai mức, không chỉ một.** Kiểm `doc_id` gold có trong top-3 là chưa đủ — một chiến lược có thể chiếm cả ba slot từ đúng tài liệu mà không chunk nào chứa câu trả lời. Nên mỗi query khai báo thêm một **chuỗi đặc trưng bắt buộc** (`must_contain`) và `bench.py` kiểm chuỗi đó có thật trong ngữ cảnh truy xuất được hay không.

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Loan period (cần filter) | Cả 3 đều 2/2 | ✅ top-1 ở cả ba | Nhưng **chỉ khi có filter** — xem A/B bên dưới |
| 2 | Overdue fine | Cả 3 đều 2/2 | ✅ top-1 ở cả ba | Score cao nhất bộ (+0.7964 heading); câu hỏi có từ khoá đặc trưng |
| 3 | Renew when overdue | **Chỉ HeadingChunker đạt 2/2** | ✅ heading top-1 / ⚠️ recursive & fixed gold chỉ ở top-3 | **Câu phân loại chiến lược.** Xem phân tích lỗi mục 4 |
| 4 | Study room booking | Cả 3 đều 2/2 | ✅ top-1 ở cả ba | Tài liệu riêng biệt, không cạnh tranh với ai |
| 5 | Materials cannot borrow | Cả 3 đều 2/2 | ✅ top-1 ở cả ba | |

**Tổng điểm theo thành viên:** Nhân (heading) **10/10** · Trí (recursive) **9/10** · Dương (fixed) **9/10**.
*(Đối chứng thêm: SentenceChunker cũng 9/10, hỏng đúng Q3 như hai chiến lược trên.)*

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> **Có, và chỉ ở Q1 — nhưng ở đó nó quyết định đúng/sai chứ không phải hay/dở.**
>
> Q1 cố tình **không nêu người hỏi là ai** ("**my** loan period"), trong khi corpus có bốn tài liệu cùng chủ đề, cùng từ vựng `Circulation privilege`, nhưng khác `audience` và **khác đáp án**. Chạy A/B trên cả ba chiến lược, nhìn riêng **slot thứ 3**:
>
> | Thành viên | Slot 3 **CÓ** filter | Slot 3 **KHÔNG** filter |
> |---|---|---|
> | Nhân (heading) | `hoc-vien-sau-dai-hoc#2` +0.6965 `student` | **`muon-tai-lieu-giang-vien#1` +0.7002 `faculty`** ⚠️ |
> | Trí (recursive) | — | **`nhan-vien-va-giang-vien-lien-ket#0` +0.6775 `staff`** ⚠️ |
> | Dương (fixed) | `sinh-vien-dai-hoc#1` +0.6729 `student` | **`muon-tai-lieu-giang-vien#0` +0.6825 `faculty`** ⚠️ |
>
> **Cả ba chiến lược đều bị tài liệu sai đối tượng chen vào slot 3 khi bỏ filter** — dù là ba chunker khác nhau, cho ra ba "kẻ đột nhập" khác nhau (faculty, staff, faculty). Tài liệu giảng viên ghi *"5 items, 6 months"*; sinh viên đọc câu trả lời dựa trên ngữ cảnh đó có thể kết luận mình được mượn 6 tháng, **sai gấp 12 lần** so với 2 tuần thực tế.
>
> Con số đáng chú ý nhất: ở bản của Nhân, chênh lệch giữa chunk faculty (+0.7002) và chunk graduate (+0.6965) chỉ là **0.0037**. Hai tài liệu này nói cùng chủ đề, dùng cùng từ vựng, chỉ khác đối tượng áp dụng — embedding **không có cách nào** phân biệt được ở mức chênh lệch đó. Đây chính xác là khoảng trống mà metadata lấp vào: **similarity phân biệt theo chủ đề, metadata phân biệt theo đối tượng.**
>
> Ở Q2–Q5 filter không cần thiết vì mỗi câu chỉ có một tài liệu ứng viên thật sự. Nhóm coi đó là kết quả đúng chứ không phải thiếu sót — lọc khi không cần chỉ làm tăng nguy cơ loại nhầm (đánh đổi precision/recall).

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

1. **Chọn backend quan trọng gấp 7 lần chọn chunker.** Ba chiến lược chunking chênh nhau 1 điểm (10 / 9 / 9). Nhưng cùng một chiến lược `fixed` chạy trên mock so với Gemini chênh **7 điểm** (2/10 → 9/10). Nhóm suýt phân tích nhầm: nếu chạy benchmark bằng mock thì mọi kết luận về chunking đều là so xem chiến lược nào may mắn hơn.
2. **Hai cách chấm cho kết quả khác nhau, và cách dễ hơn thì sai.** Nếu chỉ kiểm `doc_id` gold có trong top-3, cả ba thành viên đều 10/10 và buổi lab không học được gì. Kiểm thêm chuỗi đặc trưng trong ngữ cảnh mới lộ ra Q3 phân loại được chiến lược. Sai lầm này **thật sự đã xảy ra trong nhóm**: một thành viên khi đọc lại output đã ghi rằng chunk gold ở top-3 "chứa `Overdue items cannot be renewed`", trong khi kiểm lại nội dung chunk thì câu đó nằm ở chunk khác — chunk lọt top-3 chỉ nói về *recall*. Chính `must_contain` bắt được chỗ mà mắt người đọc lướt qua.
3. **Metadata filter cứu đúng một câu, nhưng là câu mà sai thì hậu quả lớn nhất.** Hai chunk cách nhau 0.0037 điểm cosine mà một cái đúng một cái sai hoàn toàn với người hỏi — similarity không thể tự giải quyết, phải có chiều dữ liệu khác. Và cả ba chiến lược đều dính lỗi này khi bỏ filter.
4. **Ba cài đặt độc lập hội tụ về cùng số liệu.** Ba người viết `src/` khác nhau (khác cả prompt agent lẫn việc giữ hay bỏ nhánh ChromaDB) nhưng cùng chiến lược thì score trùng đến 4 chữ số. Nhờ vậy nhóm chắc chắn khác biệt điểm là do **chiến lược**, không phải do bug.

**Phân tích lỗi (Failure Analysis)**

**Ca lỗi: Q3 — *"Can I renew a book that is already overdue?"* — hỏng ở 2/3 thành viên.**

- **Hỏng thế nào:** Trí và Dương đều có top-1 và top-2 là tài liệu `phi-phat-qua-han` (+0.6908/+0.6674 và +0.6973/+0.6561). Tài liệu gold chỉ lọt hạng 3, và chunk lọt được lại nói về *recall* chứ không phải *renewal*. Ngữ cảnh không chứa `"cannot be renewed"` → agent không có căn cứ trả lời "Không". Cả hai bị trừ xuống 1/2.
- **Tại sao:** câu hỏi chứa từ `"overdue"`, và tài liệu `phi-phat-qua-han` **dày đặc từ đó** ("overdue fine", "overdue items", "30 days after the due date"). Cosine đo **độ giống chủ đề**, không đo **mật độ thông tin trả lời được** — nên chunk nói rất nhiều về "quá hạn" nhưng không trả lời được câu hỏi vẫn thắng chunk chứa đúng một câu đáp án. Cộng thêm việc cắt ở ~900 ký tự rơi đúng vào giữa hai vế của mục `## Renewal conditions`, tách rời "gia hạn = ½ thời hạn, chỉ khi chưa ai yêu cầu" khỏi "tài liệu quá hạn không được gia hạn".
- **Đề xuất cải thiện:** (a) chunk theo heading để mục quy định không bị xé — đã chứng minh hiệu quả, đưa Q3 từ 1 lên 2 điểm; (b) nếu phải giữ chunker theo kích thước thì tăng `overlap` lên ≥ 250 (Dương đang dùng 150, vẫn không đủ vì hai vế cách nhau xa hơn thế); (c) về lâu dài, similarity đơn thuần không đủ cho câu hỏi dạng có/không — cần thêm bước re-rank kiểm xem chunk có chứa **mệnh đề trả lời được** hay không, chứ không chỉ cùng chủ đề.

**Hai lỗi phát hiện trong công cụ của lab (ngoài phạm vi bài nhưng ảnh hưởng trực tiếp tới dữ liệu):**

1. **`robots_allowed()` báo cấm nhầm toàn bộ URL.** `RobotFileParser.read()` tải `robots.txt` bằng User-Agent mặc định của Python chứ không dùng UA mà script khai báo. Hai domain VinUni trả **403** cho UA đó, `read()` nuốt lỗi và đặt `disallow_all = True` → cả 8 URL bị báo `disallowed by robots.txt` dù `robots.txt` thật là `User-agent: * / Disallow:` (cho phép tất cả). Nhóm sửa để tải `robots.txt` bằng đúng UA đã khai báo — **không giả mạo UA trình duyệt**, chỉ để script tự danh nhất quán.
2. **`yaml_value()` bọc nháy vô điều kiện.** Mọi file crawler sinh ra đều có `doc_id: "ten-file"`. Script kiểm tra CHECKPOINT 2 của lab dùng regex `^(\w+):\s*(.+)$` nên bắt cả dấu nháy vào giá trị, khiến `fm['doc_id']` không bao giờ bằng `p.stem` → **mọi file bị báo `THIEU METADATA` dù metadata đủ cả**. Nhóm sửa để chỉ bọc nháy khi YAML thật sự cần (giá trị rỗng, chứa `": "`, hoặc trông giống số/ngày như `2026.1`).

**Một quan sát về chất lượng nguồn:** hai nguồn chính thức của cùng một trường **mâu thuẫn nhau về giờ mở cửa** — trang `library.vinuni.edu.vn` ghi thứ 2–6 mở lúc **8:45**, trong khi văn bản `POL-LLR-001-V4.0` trên `policy.vinuni.edu.vn` ghi **8:00**. Nhóm **cố ý không tự chọn một con số**, mà giữ cả hai trong hai tài liệu riêng kèm `source_url` và `document_version` của chúng. Đây là lý do thực tế để bắt agent trích dẫn nguồn: khi nguồn mâu thuẫn, việc đúng không phải chọn hộ người đọc mà là chỉ ra cả hai và cho biết mỗi con số đến từ đâu.

**Bài học rút ra khi so sánh trong nhóm:**

> Cùng corpus, cùng 5 câu hỏi, cùng backend embedding, ba chiến lược chỉ chênh nhau **1 điểm trên 10** — và toàn bộ chênh lệch nằm ở **một câu duy nhất**. Điều đó nói rằng phần lớn câu hỏi trong lab này "dễ" với mọi chiến lược, vì mỗi câu chỉ có một tài liệu ứng viên thật sự. Chiến lược chunking chỉ trở nên quan trọng đúng ở chỗ **hai tài liệu cạnh tranh nhau, hoặc câu trả lời nằm sát ranh giới cắt**. Nếu nhóm chỉ viết 5 câu hỏi "dễ" thì sẽ kết luận nhầm rằng chọn chunker thế nào cũng như nhau — đúng như Trí tổng kết: *"cần so sánh chiến lược theo từng loại câu hỏi, không chỉ theo điểm tổng."*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

> **Một:** thiết kế câu hỏi khó hơn ngay từ đầu. 4/5 câu của nhóm chỉ có một tài liệu ứng viên nên không phân loại được chiến lược. Lần sau sẽ cố ý viết nhiều câu mà **hai tài liệu cùng cạnh tranh**, như Q1 đã làm với `audience` và Q3 vô tình làm được với cặp "tiền phạt" ↔ "gia hạn".
>
> **Hai:** họp chốt corpus và bộ query **trước** khi ai bắt đầu code. Lần này nhóm không họp kịp nên một người dựng sẵn corpus + benchmark rồi chia lại; cách đó vẫn ra số liệu thật nhưng mất đi góc nhìn "mỗi người tự đọc dữ liệu thì sẽ chọn tham số khác nhau" — hiện cả ba đều dùng `chunk_size=900` vì đó là giá trị người đầu tiên đặt.
>
> **Ba:** bổ sung tài liệu tiếng Việt và **đo hẳn khả năng xuyên ngôn ngữ**. Corpus hiện tại toàn tiếng Anh vì nguồn VinUni công khai là tiếng Anh, trong khi câu hỏi thật của sinh viên sẽ đặt bằng tiếng Việt. Dương đã chạm vào vấn đề này ở phần dự đoán similarity — cặp *"Phi phat qua han 20.000 VND/ngay"* ↔ *"Late return fee is 20,000 VND per day"* là cặp Việt–Anh cùng nghĩa — nhưng mới đo trên mock nên chỉ chứng minh được mock không hiểu gì, chưa chứng minh được Gemini hiểu. Lần sau nhóm sẽ đặt cả 5 benchmark query bằng tiếng Việt trên corpus tiếng Anh, vì đó mới là tình huống sử dụng thật.
>
> **Bốn:** thống nhất định dạng file kết quả từ đầu. Một thành viên xuất `ket_qua_benchmark.txt` bằng PowerShell nên file ra **UTF-16**, mở bằng editor thường thấy chữ cách quãng từng ký tự. Quy ước chung nên là đặt `PYTHONIOENCODING=utf-8` trước khi redirect.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | — (chấm tại buổi demo) |
| **Tổng phần nhóm** | **35 / 35 + demo** |
