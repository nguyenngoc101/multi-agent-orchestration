# 0001 — Dùng ADR để ghi quyết định kiến trúc

- **Status:** Accepted
- **Date:** 2026-07-19
- **Deciders:** CODEOWNER (@your-team)

## Context

Nhiều agent (Claude/Codex/khác) làm song song trên cùng repo. Mỗi agent có context
window riêng, phù du, và phân kỳ tức thì. Nếu quyết định xuyên suốt (interface chung,
quy ước) chỉ nằm trong đầu một agent hoặc trong lịch sử chat, các agent khác không
thấy → ra quyết định lệch nhau, vỡ tích hợp ở ranh giới chung mà CI file-scope không
bắt được (mỗi PR đúng scope của nó, nhưng ghép lại không khớp).

## Decision

Mọi quyết định **cross-cutting** được ghi thành ADR trong `docs/decisions/`, đánh số
tăng dần, bất biến sau khi Accepted. Agent BẮT BUỘC đọc thư mục này trước khi ra
quyết định ảnh hưởng nhiều module, và không tự chọn khác với ADR đang Accepted. ADR
mới đi qua PR control-plane (`ops/*`) được CODEOWNER duyệt.

## Consequences

- (+) Project-context tái dựng được từ artifact, không phụ thuộc trí nhớ agent.
- (+) Coherence giữa các task song song không còn chỉ trông vào reviewer bắt lệch.
- (−) Thêm một bước: quyết định chung phải viết ra + duyệt trước khi feature build lên.
  Đây là chi phí có chủ đích — đổi lấy tính nhất quán khi đông agent.
- Ranh giới đã chốt trong ADR là "sự thật đã merged" mà các task khác build lên trên;
  interface ở module dùng chung nên là một task tiền đề (`depends_on`), không để hai
  agent tự định nghĩa song song.
