---
name: multi-agent-orchestration
description: >-
  Điều phối nhiều agent chạy song song trên một repo Git bằng git worktree +
  gitflow (feature → develop → release → main). Dùng skill này khi cần chia một
  khối việc thành nhiều task cho nhiều agent/worker làm đồng thời, quản dependency
  và scope để không giẫm nhau, và đưa qua GitHub (PR, CI, merge queue) an toàn.
  Kích hoạt khi người dùng nói tới: multi-agent, orchestrator, worker pool, chạy
  song song nhiều agent, git worktree cho agent, chia task cho agent, hoặc quản
  lý dependency/scope giữa các task song song.
---

# Multi-agent orchestration

Skill này chứa quy trình + công cụ để một ORCHESTRATOR (Claude) điều phối nhiều
WORKER (Claude/Codex/khác) làm việc song song trên một repo, an toàn cho production.

## Mô hình hai lớp cách ly

1. **worktree** — cách ly KỸ THUẬT: mỗi worker 1 thư mục + 1 branch `feature/<id>`,
   chung `.git`, không giẫm file nhau.
2. **gitflow + branch protection** — cách ly QUYỀN HẠN: worker chỉ chạm `feature/*`
   và merge vào `develop`; `main`/`release/*`/`hotfix/*` do người giữ.

`main` luôn phản chiếu PROD. Feature không bao giờ chạm main trực tiếp.

## Khi điều phối, LÀM theo thứ tự

1. Đọc `task-registry.json` (nguồn sự thật duy nhất — KHÔNG giữ state trong đầu).
2. Chạy `python3 scripts/check-registry.py` để: phát hiện dependency vòng, dep
   thiếu, scope overlap, và IN RA các wave song song. Không giao task khi registry FAIL.
3. Với mỗi task ở wave hiện tại: match `requires` (capability) với agent `idle`,
   kiểm tra scope không chồng task đang `in_progress`, rồi giao.
4. Gửi task cho worker theo `orchestrator/prompts/WORKER_PROTOCOL.md` (INPUT JSON).
5. Worker chạy `scripts/new-task.sh <id>` → code → `scripts/submit-task.sh` → mở PR.
6. GitHub gác cổng: CI (`.github/workflows/ci.yml`) + scope enforce
   (`registry-guard.yml`) + merge queue. Orchestrator KHÔNG merge vào vùng cấm.
7. PR merged → cập nhật registry, worker về `idle`, lặp lại từ bước 1.

## Hai loại dependency — phân biệt

- **Logic** (`depends_on`): phải chờ task kia `merged`. Topo-sort. Chặn chu trình.
- **Scope overlap** (`scope.allow` giao nhau): không phụ thuộc logic nhưng không
  chạy đồng thời được — nối tiếp hóa, hoặc tách phần chung ra task riêng làm trước.

## Ranh giới CỨNG (không vi phạm)

- Orchestrator/worker KHÔNG push/merge `main`/`release/*`/`hotfix/*`.
- Không nới `scope.allow` để cho xong — vượt scope thì DỪNG, báo người.
- CI là trọng tài, không tin lời worker "đã test rồi".
- Cắt release / duyệt PROD / hotfix là việc của người.

## File trong skill

- `orchestrator/prompts/ORCHESTRATOR.md` — luật vận hành đầy đủ của orchestrator
- `orchestrator/prompts/WORKER_PROTOCOL.md` — hợp đồng INPUT/OUTPUT cho worker
- `orchestrator/schema/task-registry.schema.json` — schema registry
- `scripts/check-registry.py` — validate + tính wave
- `scripts/enforce-scope.py` — chặn PR đổi file ngoài scope (dùng trong CI)
- `scripts/new-task.sh` / `submit-task.sh` / `cleanup-task.sh` — vòng đời worktree
- `docs/WORKFLOW.md` — full quy trình dev local → GitHub
- `docs/branch-protection.md` — cấu hình lớp chặn phía server

## Tham chiếu nhanh lệnh

```
just check-registry              # validate + in wave song song
./scripts/new-task.sh T-101      # tạo worktree + feature/T-101
./scripts/submit-task.sh         # rebase + gate + push (trong worktree)
./scripts/cleanup-task.sh T-101  # dọn sau merge (từ repo chính)
```
