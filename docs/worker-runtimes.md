# Worker runtimes — trigger Codex vs Claude cho đúng

Ánh xạ `agents[].kind` → cách orchestrator *thực sự* spawn worker. Rút ra từ chạy thật;
đọc kèm mục "Định tuyến worker" trong `orchestrator/prompts/ORCHESTRATOR.md`.

## Nguyên tắc: Codex mặc định, Claude ngoại lệ

- **Codex (unlimited)** = động cơ throughput → worker mặc định cho task thường.
- **Claude (Pro, khan)** = orchestrator + reviewer + task nhạy cảm/khó → `claude-lead`.

## kind = "codex" — spawn qua plugin, worktree tạo sẵn

```
1. Tạo TRƯỚC worktree đúng nhánh feature/*:
     ./scripts/new-task.sh <task-id>          # → ../wt/<id> trên feature/<id>
2. Spawn Codex worker trỏ vào worktree đó:
     Agent(subagent_type="codex:codex-rescue", prompt=<INPUT JSON + đường dẫn worktree>)
3. Codex code + test trong scope, commit, (submit-task → PR).
```

**Hai gotcha bắt buộc biết (đã gặp khi chạy thật):**

1. **KHÔNG dùng `isolation:"worktree"` của harness cho Codex.** Worktree đó bị
   **auto-clean khi lần chạy đầu không có thay đổi** → resume mất chỗ làm. Ngoài ra
   tên nhánh của nó không phải `feature/*` nên worker tuân AGENTS.md sẽ tự chặn.
   → Luôn tạo worktree `feature/<id>` bằng `new-task.sh` và trỏ Codex vào.

2. **Sandbox Codex có thể chặn `git commit`** (không tạo được `index.lock`). Khi đó
   Codex viết code/test xong nhưng không tự commit → không hoàn tất `submit-task.sh`.
   → Chạy Codex ở chế độ ghi được (vd `--sandbox workspace-write` / nới approval cho
   thao tác git), HOẶC orchestrator commit hộ rồi mới để worker/CI tiếp.

## kind = "claude" — sub-agent với worktree của harness

```
Agent(subagent_type="general-purpose", isolation:"worktree", prompt=<INPUT JSON>)
```

Ở đây `isolation:"worktree"` OK vì Claude sub-agent làm việc + commit ngay trong lượt,
worktree có thay đổi nên không bị auto-clean. Dùng cho task escalate (nhạy cảm/kiến
trúc/Codex fail ≥2 lần).

## kind = "other"

Không có kênh gọi trực tiếp → orchestrator set `assigned`, in INPUT JSON, DỪNG chờ
người/agent đó tự lấy việc. "Available" ở đây là niềm tin vào registry, không verify.

## Kiểm Codex sẵn sàng

```
/codex:setup                        # kiểm CLI + auth; ready=true là dùng được
/codex:setup --enable-review-gate   # (tùy) bắt Claude review bản Codex trước khi dừng
```
