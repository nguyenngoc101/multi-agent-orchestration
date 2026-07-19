# justfile — điểm DUY NHẤT định nghĩa lệnh stack. Đổi stack chỉ sửa file này.
# Cài just: https://github.com/casey/just  (hoặc dùng Makefile tương đương)
#
# Các recipe dưới là PLACEHOLDER. Thay bằng lệnh stack thật của bạn:
#   Java/Maven:   mvn -q spotless:check | test | package
#   Node:         npm run lint | test | build
#   Go:           golangci-lint run | go test ./... | go build ./...
#   Python:       ruff check . | pytest | python -m build

# Cài dependency cho một worktree mới (mỗi worktree tự cài — file ngoài git không share)
bootstrap:
    @echo "TODO: cài dependency, vd 'npm ci' / 'mvn -q install -DskipTests'"

lint:
    @echo "TODO: thay bằng lệnh lint thật"
    @true

test:
    @echo "TODO: thay bằng lệnh test thật"
    @true

build:
    @echo "TODO: thay bằng lệnh build thật"
    @true

# Kiểm tra registry (chu trình, scope overlap, in wave)
check-registry:
    python3 scripts/check-registry.py task-registry.json

# In wave song song hiện tại (tiện xem nhanh)
waves:
    python3 scripts/check-registry.py task-registry.json
