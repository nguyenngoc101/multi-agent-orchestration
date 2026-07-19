# justfile — điểm DUY NHẤT định nghĩa lệnh stack. Đổi stack chỉ sửa file này.
# Cài just: https://github.com/casey/just  (hoặc dùng Makefile tương đương)
#
# Các recipe dưới kiểm tra chính tooling của repository. Khi nhúng workflow này
# vào application repo, mở rộng chúng bằng lệnh của stack tương ứng:
#   Java/Maven:   mvn -q spotless:check | test | package
#   Node:         npm run lint | test | build
#   Go:           golangci-lint run | go test ./... | go build ./...
#   Python:       ruff check . | pytest | python -m build

# Cài dependency cho một worktree mới (mỗi worktree tự cài — file ngoài git không share)
bootstrap:
    @echo "Không có dependency ngoài Python 3 standard library."

lint:
    PYTHONPYCACHEPREFIX=.cache/pyc python3 -m compileall -q scripts tests
    bash -n scripts/*.sh .githooks/*
    python3 scripts/check-skill-sync.py

test:
    python3 -m unittest discover -s tests -v

build:
    python3 scripts/check-registry.py task-registry.json

# Kiểm tra registry (chu trình, scope overlap, in wave)
check-registry:
    python3 scripts/check-registry.py task-registry.json

# In wave song song hiện tại (tiện xem nhanh)
waves:
    python3 scripts/check-registry.py task-registry.json

# Dispatcher bán tự động (dry-run): PR merged → đề xuất chuyển state + in wave kế
orchestrate:
    python3 scripts/orchestrate.py task-registry.json
