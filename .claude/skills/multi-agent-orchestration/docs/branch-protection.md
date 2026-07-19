# Branch protection — lớp chặn KHÔNG-THỂ-LÁCH

Hook cục bộ (`.githooks/`) là lớp phòng thủ đầu, nhưng agent (hoặc người) có thể
bỏ qua bằng `--no-verify`. Lớp thật sự cưỡng chế nằm ở SERVER. Cấu hình một lần.

## Nguyên tắc

| Nhánh | Push thẳng | Bắt buộc PR | Bắt buộc CI xanh | Bắt buộc review | Ai được merge |
|---|---|---|---|---|---|
| `main` | ❌ | ✓ | ✓ | ✓ (người) | Chỉ người/release manager |
| `release/*` | ❌ | ✓ | ✓ | ✓ (người) | Chỉ người |
| `develop` | ❌ | ✓ | ✓ | ✓ hoặc auto | Agent qua PR, sau khi CI xanh |
| `hotfix/*` | ❌ | ✓ | ✓ | ✓ (người) | Chỉ người |
| `feature/*` | ✓ (agent) | — | — | — | (branch riêng agent) |

Điểm cốt lõi: agent CHỈ có quyền tạo/push `feature/*` và mở PR vào `develop`.
Mọi nhánh còn lại server từ chối — kể cả khi agent cố `--no-verify`.

## GitHub — Rulesets (khuyến nghị) hoặc Branch protection

Với mỗi target (`main`, `develop`, `release/*`, `hotfix/*`):
- Require a pull request before merging (bật; với main/release yêu cầu ≥1 approval)
- Require status checks to pass → chọn các check CI (lint/test/build)
- Require branches to be up to date before merging
- Block force pushes
- Restrict who can push → chỉ team người (loại tài khoản agent) cho main/release/hotfix
- (main/release) Require review from Code Owners nếu dùng CODEOWNERS
- Bật merge queue cho `develop`; required workflows phải lắng nghe `merge_group`

Phân quyền agent: tạo một machine account / token cho agent, chỉ cấp quyền đủ để
push `feature/*` và tạo PR. KHÔNG cho quyền admin/bypass.

Thay owner mẫu trong `.github/CODEOWNERS` bằng team/user thật. Registry control-plane
phải qua PR được CODEOWNER duyệt trước khi feature branch tương ứng được tạo.

## GitLab — Protected branches + Push rules

- Settings → Repository → Protected branches:
  - `main`, `release/*`, `hotfix/*`: Allowed to push = No one; Allowed to merge = Maintainers (người)
  - `develop`: Allowed to push = No one; Allowed to merge = Developers+ (qua MR)
- Settings → Merge requests: bật "Pipelines must succeed" và "All discussions resolved"
- Push Rules: bật "Do not allow users to remove tags", chặn force push
- Wildcard `feature/*`: để mặc định (agent push được)

## Bitbucket / khác

Nguyên tắc như nhau: main/release/hotfix = merge-only qua PR, CI bắt buộc, chặn
force push, giới hạn người merge. Áp cùng ma trận quyền ở bảng trên.

## CI gate (mô tả, không gắn tool)

PR vào `develop` (và vào `main`/`release`) phải chạy 3 job và xanh mới merge được:

1. `lint`  — gọi `just lint`  (hoặc `make lint`)
2. `test`  — gọi `just test`  (hoặc `make test`)
3. `build` — gọi `just build` (hoặc `make build`)

Pipeline CHỈ gọi các task này, không tự viết lệnh stack — nhờ đó cấu hình CI
giống nhau bất kể repo dùng ngôn ngữ gì; đổi stack chỉ cần sửa `justfile`.

## Deploy gate (4 môi trường)

- Dev  : auto-deploy khi release branch cập nhật.
- SIT  : auto hoặc 1-click; chạy test tích hợp trên CÙNG artifact.
- UAT  : deploy để nghiệm thu; cần tester xác nhận.
- PROD : **manual approval gate** — chỉ người có quyền duyệt (có log ai/khi nào,
         phục vụ audit). Agent KHÔNG nằm trong luồng này.

Cùng một artifact được promote qua 4 env; không rebuild giữa các môi trường.
