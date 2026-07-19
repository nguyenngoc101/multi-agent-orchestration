# Multi-Agent Orchestration — Practice Project

Repo mẫu để **thực hành** điều phối nhiều agent chạy song song trên một codebase
Git, đưa qua GitHub an toàn cho production. Stack-agnostic: mọi lệnh build/test/lint
đi qua `just`/`make`, đổi stack chỉ sửa `justfile`.

## Ý tưởng cốt lõi — hai lớp cách ly

1. **git worktree** → cách ly KỸ THUẬT: mỗi agent một thư mục + branch riêng,
   chung `.git`, không giẫm file nhau.
2. **gitflow + branch protection** → cách ly QUYỀN HẠN: agent chỉ chạm `feature/*`
   + merge `develop`; `main`/`release/*`/`hotfix/*` do người giữ. `main` = PROD.

Điều phối theo mô hình **orchestrator (Claude) + worker pool** (Claude/Codex/khác),
giao task theo capability + agent đang idle, quản dependency và scope để song song
không thành hỗn loạn.

## Cấu trúc

```
AGENTS.md                      Luật cho mọi agent (đọc trước khi làm)
task-registry.json             Nguồn sự thật: task, scope, dependency, agent
justfile                       Điểm duy nhất định nghĩa lệnh stack

.claude/skills/
  multi-agent-orchestration/   SKILL.md — Claude tự nạp quy trình điều phối

orchestrator/
  prompts/ORCHESTRATOR.md      Luật vận hành orchestrator
  prompts/WORKER_PROTOCOL.md   Hợp đồng INPUT/OUTPUT cho worker
  schema/task-registry.schema.json

scripts/
  new-task.sh                  Tạo worktree + feature branch
  submit-task.sh               Rebase + gate + push
  cleanup-task.sh              Dọn sau merge
  check-registry.py            Validate registry + tính wave song song
  enforce-scope.py             Chặn PR đổi file ngoài scope (dùng trong CI)

.githooks/
  pre-commit / pre-push        Chặn cục bộ commit/push vào nhánh cấm

.github/
  workflows/ci.yml             Gate lint/test/build trên PR
  workflows/registry-guard.yml Validate registry + enforce scope
  pull_request_template.md
  CODEOWNERS
  merge-queue.md               Ghi chú bật merge queue

docs/
  WORKFLOW.md                  Full quy trình dev local → GitHub
  branch-protection.md         Cấu hình lớp chặn phía server
  PRACTICE.md                  Bài tập thực hành từng bước
  decisions/                   ADR — bộ nhớ CHUNG (project-context) cho mọi agent

examples/
  task-registry.sample.json    Registry mẫu 3 wave (dùng đối chiếu khi luyện)
```

## Cài đặt nhanh

```bash
# 1. Kích hoạt hook
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh scripts/*.py

# 2. Cài just (hoặc dùng Makefile) — https://github.com/casey/just

# 3. Repo mẫu tự kiểm tra bằng Python standard library. Khi áp dụng vào app,
#    mở rộng lint/test/build trong justfile/Makefile bằng lệnh stack của bạn.

# 4. Thử kiểm tra registry
just check-registry            # in ra các wave song song

# 5. (Trên GitHub) cấu hình branch protection + merge queue theo docs/
```

## Bắt đầu practice

Xem `docs/PRACTICE.md` — có 6 bài từ dễ tới khó, mô phỏng đủ tình huống:
worktree cơ bản, hai agent song song, dependency chờ nhau, scope conflict,
vi phạm scope bị CI chặn, và full vòng release.

## Lưu ý an toàn

Mô hình orchestrator mạnh nhưng **lead là điểm lỗi tập trung**. Giai đoạn đầu giữ
người ở khâu duyệt merge vào develop, quan sát vài chục task xem scope có sạch không,
rồi mới nới quyền tự động. Đừng full-auto từ ngày đầu.

Registry và script guard dùng để xét một PR luôn được đọc từ base SHA đáng tin cậy;
không chạy bản guard do chính PR cung cấp. Task mới phải được thêm vào `develop`
trước bằng PR control-plane có CODEOWNER duyệt, rồi worker mới mở feature PR.
