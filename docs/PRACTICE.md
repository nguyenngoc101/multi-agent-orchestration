# PRACTICE — Bài tập thực hành

6 bài từ dễ tới khó. Mỗi bài có mục tiêu, bước làm, và điều cần quan sát.
Làm trên một repo test (có thể là repo rỗng + vài file giả) để an toàn.

Chuẩn bị:
```bash
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh scripts/*.py
# tạo vài file giả để có gì mà sửa
mkdir -p src/payment src/web/history db/migrations src/shared
echo "x" > src/payment/.keep; echo "x" > src/web/history/.keep
git add -A && git commit -m "seed"
git switch -c develop        # tạo nhánh develop nếu chưa có
```

---

## Bài 1 — Worktree cơ bản (1 agent)

Mục tiêu: hiểu cách một worktree cách ly khỏi repo chính.

```bash
./scripts/new-task.sh demo-a
git worktree list                  # thấy 2 dòng: repo chính + ../wt/demo-a
cd ../wt/demo-a
echo "code" > src/payment/refund.txt
git add -A && git commit -m "T: demo-a work"
```

Quan sát: repo chính KHÔNG thấy file `refund.txt` (khác working dir). Nhưng commit
thì cùng `.git`. Chạy `git log` ở cả hai nơi để thấy.

---

## Bài 2 — Hai agent song song (khác scope)

Mục tiêu: hai worktree chạy đồng thời, không đụng nhau.

```bash
./scripts/new-task.sh feat-payment
./scripts/new-task.sh feat-web
# sửa src/payment/** ở worktree 1, src/web/history/** ở worktree 2 — song song
```

Quan sát: `git worktree list` có 3 dòng. Hai agent sửa hai vùng file khác nhau,
commit độc lập, không conflict. Đây là song song "thật".

---

## Bài 3 — Dependency chờ nhau (check-registry)

Mục tiêu: thấy `check-registry.py` tính wave và chặn task chưa đủ dependency.

Sửa `task-registry.json` thành:
```json
{"agents":[],"tasks":[
  {"id":"T-1","title":"shared","scope":{"allow":["src/shared/**"]},"depends_on":[],"state":"backlog"},
  {"id":"T-2","title":"pay","scope":{"allow":["src/payment/**"]},"depends_on":["T-1"],"state":"backlog"},
  {"id":"T-3","title":"web","scope":{"allow":["src/web/**"]},"depends_on":["T-1"],"state":"backlog"}
]}
```
```bash
just check-registry
```
Quan sát: Wave 1 = T-1 (một mình); Wave 2 = T-2, T-3 (song song, sau khi T-1 xong).
Đổi T-1 state thành `merged` rồi chạy lại → Wave 1 giờ là T-2, T-3.

---

## Bài 4 — Phát hiện chu trình

Mục tiêu: thấy CI-guard chặn dependency vòng.

Thêm vào registry: T-2 `depends_on: ["T-3"]` và T-3 `depends_on: ["T-2"]`.
```bash
just check-registry            # → LỖI: Dependency VÒNG: T-2 → T-3 → T-2, exit 1
```
Quan sát: exit code 1 (CI sẽ fail). Đây là lỗi chia task, không phải lỗi code.

---

## Bài 5 — Vi phạm scope bị chặn

Mục tiêu: thấy `enforce-scope.py` chặn PR đổi file ngoài scope.

Registry có T-101 scope `allow: src/payment/**`, `deny: src/shared/**`, state `in_progress`.
```bash
BASE=$(git rev-parse develop)
git switch -c feature/T-101
echo "ok" > src/payment/ok.txt        # hợp lệ
echo "bad" > src/shared/bad.txt       # vi phạm
git add -A && git commit -m "mix"
HEAD=$(git rev-parse HEAD)
python3 scripts/enforce-scope.py --registry task-registry.json --task T-101 --base $BASE --head $HEAD
```
Quan sát: báo vi phạm `src/shared/bad.txt`, exit 1. Trên GitHub thật, đây là lúc
`registry-guard.yml` fail PR → worker phải DỪNG, báo người chia lại task.

---

## Bài 6 — Full vòng: feature → develop → release → main

Mục tiêu: đi hết gitflow một lần.

```bash
# feature vào develop
./scripts/new-task.sh feat-x
cd ../wt/feat-x && echo "x" > src/payment/x.txt
git add -A && git commit -m "feat-x"
git switch develop && git merge --no-ff feature/feat-x

# release cut
git switch -c release/2026.03
# (giả lập promote Dev→SIT→UAT→PROD)

# lên main + tag
git switch main && git merge --no-ff release/2026.03 && git tag v2026.03
git switch develop && git merge --no-ff release/2026.03   # sync ngược
```
Quan sát: `main` giờ trỏ đúng cái đã "lên PROD"; tag đánh dấu version; develop nhận
lại mọi thứ từ release. Thử `git log --oneline --graph --all` để thấy hình dạng.

---

## Thử thách mở rộng

- Bật hook rồi thử `git commit` khi đang ở nhánh `develop` → pre-commit chặn.
- Thử `git push origin develop` từ một feature branch giả → pre-push chặn.
- Viết thêm task vào registry sao cho có 3 wave, mỗi wave ≥2 task song song.
  Đối chiếu lời giải mẫu: `python3 scripts/check-registry.py examples/task-registry.sample.json`.
- Mô phỏng một worker "im lặng": để task ở `in_progress` mãi, tập viết luật cho
  orchestrator giải phóng agent (xem ORCHESTRATOR.md mục "Xử lý tình huống").
