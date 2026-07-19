# WORKFLOW — Full quy trình dev local → GitHub

Đi từ lúc orchestrator chia task tới lúc code lên PROD. Mọi lệnh stack đi qua
`just` (hoặc `make`) nên không gắn ngôn ngữ.

## Bức tranh tổng

```
ORCHESTRATOR (Claude)
   │  đọc registry → check wave → match worker idle → giao task
   ▼
WORKER (local)                         GITHUB
  new-task.sh  ─ worktree+branch        ┌───────────────────────────┐
  code                                  │ PR  → CI (lint/test/build) │
  submit-task.sh ─ rebase+gate+push ──► │     → registry-guard       │
                                        │     → merge queue          │
                                        │     → merge vào develop     │
                                        └───────────┬───────────────┘
                                                    ▼
                                     release cut (người) → Dev→SIT→UAT→PROD
                                                    ▼
                                        merge vào main + tag (=PROD)
```

## Giai đoạn 1 — Orchestrator chia & giao (local hoặc CI)

1. Tạo PR control-plane chỉ đổi `task-registry.json`: thêm task với `scope.allow`,
   `requires`, `depends_on`. PR này phải được CODEOWNER duyệt và merge vào `develop`
   trước khi tạo feature branch; worker không được tự thêm/nới policy của mình.
2. `just check-registry` — phải OK, xem các wave. FAIL (chu trình/dep thiếu) thì sửa.
3. Orchestrator chọn task ở wave hiện tại, match agent idle, giao theo WORKER_PROTOCOL.

## Giai đoạn 2 — Worker làm việc (dev local)

```bash
# 1. Tạo môi trường cách ly
./scripts/new-task.sh T-101          # worktree ../wt/T-101 + branch feature/T-101
cd ../wt/T-101
export GIT_AUTHOR_NAME="agent-T-101" GIT_AUTHOR_EMAIL="agent-T-101@local"
just bootstrap                       # cài dependency cho worktree này

# 2. Code — CHỈ trong scope.allow của T-101. Commit nhỏ, thường xuyên.

# 3. Chuẩn bị PR
./scripts/submit-task.sh             # rebase origin/develop + lint+test+build + push
```

Lần push đầu script rebase để giữ lịch sử thẳng. Nếu branch đã có trên remote,
script merge `origin/develop` thay vì rebase để không cần force-push lịch sử đã công bố.

Hook cục bộ (`.githooks/pre-commit`, `pre-push`) chặn nếu lỡ commit/push vào nhánh cấm.

## Giai đoạn 3 — GitHub (tự động)

Mở PR `feature/T-101 → develop` (submit-task gợi ý lệnh `gh pr create`).

Trên PR chạy song song:
- **ci.yml** — lint/test/build phải xanh.
- **registry-guard.yml** — validate registry + `enforce-scope.py` chặn nếu PR đổi
  file ngoài `scope.allow` của T-101.
- **CODEOWNERS** — nếu PR đụng vùng nhạy cảm (`src/shared`, `db/migrations`...),
  bắt buộc người review.

PR xanh + được duyệt → vào **merge queue**. Queue ghép từng PR lên develop mới nhất,
chạy lại CI, merge tuần tự (squash). Đây là chỗ nối tiếp hóa để song song an toàn.
Guard và registry policy dùng để xét feature PR được checkout từ base SHA, nên PR
không thể sửa chính trọng tài hoặc scope của mình để vượt kiểm tra.

## Giai đoạn 4 — Dọn & lặp

```bash
cd <repo chính>
./scripts/cleanup-task.sh T-101      # gỡ worktree + branch
```
Orchestrator cập nhật registry: T-101 = `merged`, worker về `idle`, mở khóa task
phụ thuộc T-101 (vào wave sau).

## Giai đoạn 5 — Release (người, KHÔNG phải agent)

```bash
git switch develop && git pull
git switch -c release/2026.03        # cắt khi gom đủ feature
# CI/CD promote CÙNG một artifact: Dev → SIT → UAT (nghiệm thu) → PROD (duyệt tay)
git switch main && git merge --no-ff release/2026.03 && git tag v2026.03
git switch develop && git merge --no-ff release/2026.03   # sync ngược
```

## Giai đoạn 6 — Hotfix (người)

```bash
git switch main && git switch -c hotfix/2026.03.1
# fix → promote qua env → deploy PROD
git switch main    && git merge --no-ff hotfix/2026.03.1 && git tag v2026.03.1
git switch develop && git merge --no-ff hotfix/2026.03.1   # sync ngược BẮT BUỘC
```

## Ai được làm gì

| Hành động | Agent | Người |
|---|---|---|
| feature/* + PR vào develop | ✓ | ✓ |
| merge vào develop | ✓ (nếu protection cho phép, CI xanh) | ✓ |
| cắt release/* | ✗ | ✓ |
| merge vào main, tag | ✗ | ✓ |
| duyệt PROD | ✗ | ✓ |
| hotfix | ✗ | ✓ |
