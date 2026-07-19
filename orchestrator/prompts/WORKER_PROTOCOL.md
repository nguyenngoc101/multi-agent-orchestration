# WORKER_PROTOCOL.md — Hợp đồng cho MỌI worker (Claude / Codex / khác)

Protocol trung lập với loại agent. Orchestrator giao task theo format INPUT;
worker trả về theo format OUTPUT. Không dựa vào đặc thù của bất kỳ agent nào.

## INPUT — orchestrator giao cho worker

```json
{
  "task_id": "T-101",
  "title": "Thêm endpoint refund cho payment",
  "branch": "feature/T-101",
  "base": "origin/develop",
  "scope": {
    "allow": ["src/payment/**", "test/payment/**"],
    "deny":  ["src/shared/**"]
  },
  "acceptance": [
    "POST /payments/{id}/refund trả 200 và tạo bản ghi refund",
    "Có test cho case thành công và case số tiền vượt quá"
  ],
  "commands": { "lint": "just lint", "test": "just test", "build": "just build" }
}
```

## Ràng buộc worker PHẢI tuân (bất kể loại agent)

1. CHỈ sửa file khớp `scope.allow`, KHÔNG đụng `scope.deny` hay file ngoài allow.
   Cần đụng ngoài scope → DỪNG, trả OUTPUT với `status=blocked` + lý do. Không tự nới.
2. Làm trong worktree của `branch` đã cấp. Không checkout nhánh khác.
3. Trước khi báo xong: rebase lên `base`, chạy `commands.lint/test/build`, phải xanh.
4. Không `git stash`, không force-push, không đụng main/develop/release/hotfix.
5. Commit nhỏ, message rõ, tham chiếu `task_id`.
6. Context nằm ở ARTIFACT, không ở trí nhớ: nếu bị giao lại, đọc `task.log`, branch
   của bạn, và comment PR để tái dựng — đừng giả định nhớ phiên trước.
7. Quyết định xuyên suốt (interface chung, quy ước) → ĐỌC `docs/decisions/` trước
   và tuân ADR đang Accepted. Cần một quyết định chung MỚI → DỪNG, đề xuất ADR
   (status=blocked, nêu ở `notes`); KHÔNG tự chốt trong feature branch.

## OUTPUT — worker trả về orchestrator

```json
{
  "task_id": "T-101",
  "status": "pr_open",        // pr_open | blocked | failed
  "branch": "feature/T-101",
  "pr": "https://github.com/org/repo/pull/210",
  "files_changed": ["src/payment/refund.*", "test/payment/refund.*"],
  "checks": { "lint": "pass", "test": "pass", "build": "pass" },
  "notes": "Ghi chú cho reviewer; hoặc lý do nếu blocked/failed",
  "out_of_scope_needed": []   // liệt kê file ngoài scope nếu bị chặn
}
```

## Quy tắc trạng thái

- `pr_open`  → orchestrator chuyển task sang `in_review`, chờ CI + review.
- `blocked`  → orchestrator đọc `out_of_scope_needed` / `notes`, báo người chia lại.
- `failed`   → orchestrator có thể giao lại (cùng worker để giữ context, hoặc worker
  idle khác nếu task độc lập).

## Sau review

Nếu reviewer/CI yêu cầu sửa: orchestrator gửi lại cùng INPUT + mảng `feedback`
(danh sách điểm cần sửa). Worker sửa TRONG branch cũ, push lại, trả OUTPUT mới.
