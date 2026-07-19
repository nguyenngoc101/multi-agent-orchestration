# AGENTS.md — Luật làm việc cho AI agent (BẮT BUỘC)

Đọc file này TRƯỚC khi chạy bất kỳ lệnh git nào. Vi phạm sẽ bị hook/branch
protection chặn — nhưng bạn phải tự tuân thủ, đừng để bị chặn.

## 0. Nguyên tắc tối cao

- Bạn CHỈ làm việc trong worktree hiện tại, trên branch `feature/<task>` của bạn.
- Bạn CHỈ được merge (qua PR) vào `develop`.
- Bạn TUYỆT ĐỐI KHÔNG chạm: `main`, `release/*`, `hotfix/*`.
  Các nhánh này do con người kiểm soát (cắt release, duyệt PROD, hotfix).

## 1. Ranh giới branch

| Nhánh | Bạn được phép | Ghi chú |
|---|---|---|
| `feature/<task>` | Toàn quyền (branch của bạn) | 1 task = 1 branch = 1 worktree |
| `develop` | Chỉ merge vào qua PR | Nhánh tích hợp |
| `main` | ❌ Cấm | = PROD, người giữ |
| `release/*` | ❌ Cấm | Ổn định hóa, người giữ |
| `hotfix/*` | ❌ Cấm | Vá PROD, người giữ |

## 2. Ranh giới file (scope)

- Chỉ sửa file trong scope được giao ở prompt/issue của bạn.
- Nếu cần đổi file NGOÀI scope: DỪNG LẠI, báo lại trong PR/issue, chờ xác nhận.
  Không tự ý sửa lan sang module khác — đó là nguồn conflict giữa các agent.

## 3. Quy trình làm việc

1. Tạo worktree + branch bằng script chuẩn (KHÔNG tự gõ `git worktree add`):
   ```
   ./scripts/new-task.sh <task-name>
   ```
2. Code, commit nhỏ và thường xuyên, message rõ ràng.
3. Trước khi mở PR, chạy script submit (nó tự rebase + kiểm tra + push):
   ```
   ./scripts/submit-task.sh <task-name>
   ```
4. Mở PR **target = `develop`**, điền theo template.
5. Sau khi PR được merge, dọn:
   ```
   ./scripts/cleanup-task.sh <task-name>
   ```

## 4. Lệnh CẤM tuyệt đối

- `git checkout main` / `develop` / `release/*` / `hotfix/*` để commit lên đó
- `git push` thẳng vào `main` / `develop` / `release/*` / `hotfix/*`
- `git push --force` / `--force-with-lease` lên bất kỳ nhánh chung nào
- `git stash` (stash dùng chung toàn repo giữa các worktree — dễ pop nhầm)
- `git config` local để đổi user/email (config dùng chung repo — dùng biến môi
  trường `GIT_AUTHOR_*` do script set sẵn)
- `git worktree remove --force` khi còn thay đổi chưa commit
- Sửa lịch sử branch đã push (`rebase -i` rồi force push)

## 5. Rebase & conflict

- Rebase lên `origin/develop` TRƯỚC khi push và trước mọi task dài:
  ```
  git fetch origin && git rebase origin/develop
  ```
- Rebase sớm, rebase thường: conflict nhỏ dễ giải hơn conflict dồn cục.
- Ưu tiên `rebase` hơn `merge` để lịch sử branch của bạn thẳng.
- Nếu conflict vượt scope của bạn (đụng file module khác): DỪNG, báo người.

## 6. Trước khi mở PR — checklist tự kiểm

- [ ] Đã rebase lên `origin/develop` mới nhất
- [ ] Lint xanh:  `<LINT_CMD>`
- [ ] Test xanh:  `<TEST_CMD>`
- [ ] Build xanh: `<BUILD_CMD>`
- [ ] Chỉ đụng file trong scope
- [ ] Commit message rõ, PR mô tả đủ: làm gì, đụng file nào, cách test

> `<LINT_CMD>` / `<TEST_CMD>` / `<BUILD_CMD>` được định nghĩa trong `justfile`
> hoặc `Makefile` của repo (xem mục 7). Đừng hardcode lệnh của một stack cụ thể.

## 7. Lệnh build/test/lint — qua một điểm duy nhất

Repo định nghĩa mọi lệnh qua `just` (hoặc `make`). Bạn CHỈ gọi tên task, không
gọi thẳng công cụ stack:

```
just lint      # hoặc: make lint
just test      # hoặc: make test
just build     # hoặc: make build
```

Nếu chưa có `justfile`/`Makefile`, hỏi người bổ sung — đừng đoán lệnh stack.

## 8. Config theo môi trường

- KHÔNG hardcode giá trị theo môi trường (DB URL, endpoint, secret) vào code
  hay theo branch. Config Dev/SIT/UAT/PROD nằm ngoài code (biến môi trường /
  config store), inject lúc deploy. Cùng một artifact chạy mọi môi trường.
