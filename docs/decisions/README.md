# Decision Log (ADR-lite) — bộ nhớ CHUNG cho mọi agent

Thư mục này giữ **quyết định xuyên suốt** (cross-cutting) mà *nhiều* agent phải
tuân theo để không giẫm quy ước nhau: interface ở module dùng chung, quy ước đặt
tên, chọn thư viện/pattern, ranh giới kiến trúc.

## Vì sao cần

Registry giữ *task-context* (hẹp, cho một task). `docs/decisions/` giữ
*project-context* (rộng, cho mọi task). Nhiều agent song song có thể ra quyết định
**đúng cục bộ nhưng lệch toàn cục** — hai kiểu đặt tên, hai interface không khớp ở
ranh giới chung. ADR biến những quyết định đó thành **artifact đọc lại được**, thay
vì nằm trong đầu một agent hoặc trong lịch sử chat sẽ mất.

## Luật cho agent (BẮT BUỘC)

1. **Trước** khi ra quyết định ảnh hưởng nhiều module / ranh giới chung: ĐỌC thư mục
   này. Quyết định đã có ở đây thì TUÂN theo, không tự chọn khác.
2. Nếu cần một quyết định xuyên suốt MỚI (chưa có ADR): **DỪNG, đề xuất ADR** trong
   PR/issue — đừng quyết âm thầm trong một feature branch. Quyết định chung phải qua
   PR control-plane (nhánh `ops/*`) được CODEOWNER duyệt, rồi các feature mới build lên.
3. Tham chiếu ADR trong `task.log` và mô tả PR (vd "theo ADR-0002").

## Cách viết một ADR

- Copy `TEMPLATE.md` thành `NNNN-tieu-de-ngan.md` (số tăng dần, 4 chữ số).
- Điền: Status, Context, Decision, Consequences. Ngắn gọn — một màn hình là đủ.
- ADR là **bất biến sau khi Accepted**: muốn đổi thì viết ADR mới `Supersedes NNNN`,
  và đánh dấu ADR cũ `Superseded by MMMM`. Không sửa lịch sử quyết định.

## Danh mục

- [0001](0001-record-architecture-decisions.md) — Dùng ADR để ghi quyết định kiến trúc.
