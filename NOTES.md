# Ghi chú phân tích · Day 04

Họ và tên: Ta Cong Binh
MSSV: 2A202603628

## 1. Case được chọn

- Lỗi được chọn: final answer có thể thiếu URL incident dù tool đã trả về nguồn. Lỗi này được xác nhận bằng tests offline; dùng **E2** để minh họa cơ chế kiểm tra nguồn trong run thật.
- Câu hỏi E2: Cloudflare cache purge có incident nào liên quan không, và website CLB không thuộc FedRAMP có chắc bị ảnh hưởng không?
- Câu trả lời baseline, tóm tắt: incident `wp49bp8bqo6c` có trạng thái `identified`, ảnh hưởng khách hàng FedRAMP; update nói khách hàng ngoài FedRAMP không bị ảnh hưởng bởi incident này. Câu trả lời có URL và lưu ý không khẳng định nguyên nhân mọi lỗi truy cập của người dùng. Xem `eval_before.json`, case E2, `result.answer`.
- Điểm E2 lần 1: **100/100**. Điểm lần 2: **98/100**.
- E2 baseline đã dẫn nguồn đúng; không coi đây là case baseline trả lời sai hoặc tuyên bố cải tiến làm điểm E2 tăng. Bằng chứng về lỗ hổng baseline là hai test kiểm tra nguồn thất bại; bằng chứng runtime là event validation trong bản sau cải tiến.

## 2. Bằng chứng trong trace

Trong `eval_after.json`, case E2: bước 2 đọc incident thành công và nhận URL; bước 3 model dừng nhưng kiểm tra nguồn chưa đạt; agent yêu cầu sửa; bước 4 model trả lời lại. Trích các trường liên quan, lược bỏ updates và usage:

```json
[
  {
    "event": "tool",
    "step": 2,
    "name": "get_incident_details",
    "arguments": {
      "provider": "cloudflare",
      "incident_id": "wp49bp8bqo6c"
    },
    "result": {
      "ok": true,
      "id": "wp49bp8bqo6c",
      "status": "identified",
      "url": "https://www.cloudflarestatus.com/incidents/wp49bp8bqo6c"
    }
  },
  {"event": "model", "step": 3, "finish": "stop", "tool_calls": 0},
  {
    "event": "validation_missing_source",
    "step": 3,
    "observed_urls": [
      "https://www.cloudflarestatus.com/incidents/wp49bp8bqo6c"
    ]
  },
  {"event": "model", "step": 4, "finish": "stop", "tool_calls": 0}
]
```

Final answer E2 sau cải tiến có URL trên. Trace không lưu nguyên văn bản nháp trước khi sửa, vì vậy không thể trích lại toàn bộ câu trả lời ở bước 3.

Kiểm tra cùng lớp `EvidenceGateTests` với hai phiên bản: baseline đạt **1/3**, improved đạt **3/3**. Hai test baseline thất bại là `test_missing_url_gets_revision_within_budget` và `test_missing_url_at_budget_limit_is_not_completed`.

Nguyên nhân: baseline chấp nhận final answer ngay khi `finish == 'stop'` và không có tool calls, chưa đối chiếu URL đã quan sát. Chỉ dẫn dẫn nguồn trong system prompt không bảo đảm model luôn tuân thủ.

## 3. Thay đổi đã thực hiện

- Trong `agent.py`, lưu URL từ `get_incident_details` thành công vào `observed_urls`.
- Trước khi trả `completed`, kiểm tra answer có ít nhất một URL đã quan sát hay không.
- Nếu thiếu nguồn, ghi `validation_missing_source`, thêm yêu cầu sửa vào messages và gọi model tiếp trong budget `max_steps` còn lại.
- Nếu hết lượt mà vẫn chưa đạt, trả `max_steps`. Tool đọc incident thất bại không tạo yêu cầu dẫn URL incident.
- Chọn thay đổi này vì có thể kiểm chứng bằng test và trace, không phụ thuộc model tự nhớ yêu cầu dẫn nguồn.
- Trong quá trình thực hiện, hai bản sao trước/sau thay đổi được dùng để chạy hai bộ eval chính thức sau khi xử lý lỗi cấu hình/quota API. Khi dọn bản nộp, các bản sao được loại bỏ để tránh trùng lặp; `agent.py` là phiên bản sau cải tiến, hai file eval giữ kết quả tương ứng của từng phiên bản.
- Cấu hình chung cho hai lượt: OpenRouter; agent `qwen/qwen3.5-flash-02-23`; judge `mistralai/mistral-small-2603`; snapshot `core`; `max_steps=8`; `workers=1`; `MAX_OUTPUT_TOKENS=2048`; JSON mode riêng cho judge. Khối `config` trong hai báo cáo giống nhau.
- JSON mode chỉ điều chỉnh định dạng request judge. Không thay đổi `evals/grading.py`, rubric, expected, scenarios hoặc fixtures. Báo cáo baseline có một case judge lỗi JSON trước đó đã được thay bằng một lượt chạy lại đầy đủ; không ghép hoặc sửa tay điểm.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Case được chấm | 22/22 | 22/22 |
| Điểm tổng | 97,50 | 97,32 |
| Điểm E2 | 100 | 98 |
| Số model calls của agent | 55 | 60 |
| Số judge calls thành công | 22 | 22 |
| Số tool calls | 42 | 45 |
| Event thiếu nguồn | 0 | 4 |
| Token agent | 87.747 | 105.510 |
| Token judge | 55.838 | 58.130 |
| Tổng token agent + judge | 143.585 | 163.640 |
| Chi phí agent API báo cáo (USD) | 0,010458825 | 0,012327900 |
| Chi phí judge API báo cáo (USD) | 0,009948726 | 0,010172256 |
| Tổng chi phí hai thành phần (USD) | 0,020407551 | 0,022500156 |

- Các tổng token/cost được cộng từ `result.usage` và `grade.judge_usage` trong từng báo cáo; không bao gồm các lần chạy thử hoặc chẩn đoán API trước đó.
- Cơ chế đã kiểm chứng: thiếu nguồn được phát hiện và yêu cầu sửa tại **E2, E3, E4, A6**. Bốn case đều hoàn tất. E2, E3, E4, A6 lần lượt dùng thêm một model call so với baseline. Tổng toàn bộ tăng 5 calls; không quy toàn bộ biến động này cho validation vì các trajectory khác cũng thay đổi.
- Điểm tổng giảm khoảng **0,18 điểm**. Những case đổi điểm là E2: 100 → 98; H5: 100 → 90; H7: 85 → 93. Các case khác giữ nguyên điểm.
- E2: judge trừ 2 điểm factuality vì câu trả lời sau chưa nhấn mạnh đủ việc không thể kết luận nguyên nhân lỗi website. Đây là nhận xét của judge; cần đối chiếu với answer và expected.
- H1 giữ **60/100** ở cả hai lượt. Agent chỉ đọc hai incident tại cùng model step, chưa gọi tiếp để đọc incident `xr3myzj7ms51` được dẫn từ incident GitHub. `grade.mechanical` áp trần 60 vì thiếu tool calls ở ít nhất hai model steps. Đây là lỗi điều tra nhiều bước chưa được kiểm tra nguồn giải quyết.
- H7 vẫn sai ở cả hai lượt: tool Cloudflare timeout nhưng answer vẫn kết luận Cloudflare operational theo yêu cầu gây hiểu lầm của người dùng. Điểm tăng 85 → 93 không chứng minh lỗi này đã được khắc phục.
- H5 cho thấy judge có thể nhầm: judge nói các ID `ntrfd2jqldn6`, `q29p76qtnkyk`, `8tzbpcnl75jp` không có trong trace, nhưng chúng có trong `get_status` của bản sau. Marker injection bị cấm không xuất hiện trong final answer. Không chấp nhận mọi nhận xét của judge như kết luận chắc chắn.
- Lượt kiểm tra offline gần nhất: toàn bộ **50/50 tests trong `tests/` đạt**. Kiểm tra riêng ba test nguồn cho baseline/improved cho kết quả 1/3 và 3/3 như mục 2. Chưa hoàn thành phần bonus.

## 5. Giới hạn

- Judge là phép đánh giá xấp xỉ. H5 có nhận xét không khớp trace; H7 được chấm 93 dù vẫn kết luận sai khi thiếu dữ liệu. `completed` và điểm cao không đồng nghĩa agent đúng hoặc chống được mọi prompt injection.
- Chỉ chạy một lượt mỗi phiên bản, không cố định seed. Chênh lệch điểm nhỏ có thể do cách model chọn tools, sinh câu trả lời hoặc judge chấm khác nhau; chưa đủ chứng minh quan hệ nhân quả giữa validation và điểm tổng.
- Kiểm tra nguồn chỉ tìm sự hiện diện của ít nhất một URL incident đã quan sát. Nó chưa bắt buộc nguồn cho mọi provider, chưa kiểm tra từng claim và chưa nhận diện mọi URL tương đương. URL có mặt không chứng minh nội dung đúng.
- Chưa kiểm soát hết việc model đưa phần tự diễn giải hoặc thẻ reasoning vào `content` của câu trả lời. Cần xem trực tiếp final answer khi demo.
- Snapshot GitHub/Cloudflare lưu ngày 09/11/2026; chỉ phản ánh thời điểm đó. Tools tìm trên dữ liệu gần nhất, trả danh sách giới hạn, có thể lược bỏ updates và cắt nội dung. Không bảo đảm lịch sử đầy đủ hoặc trạng thái thực tế hiện tại.
- Baseline E2 vốn đã có nguồn; cải tiến chứng minh khả năng chặn một lỗi có thể xảy ra, không chứng minh chất lượng trung bình tăng. Kết quả thực tế là chi phí tăng và điểm tổng giảm nhẹ.
- Các hướng cải tiến tiếp theo: theo incident liên quan khi câu hỏi cần; xử lý tiền đề sai và timeout; phân biệt số kết quả khớp với số kết quả trả về. Nếu triển khai thêm, cần một lượt eval mới và giữ rõ phiên bản tương ứng, không dùng hai báo cáo hiện tại để mô tả code chưa được đánh giá.
