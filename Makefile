.PHONY: bootstrap lint test build check-registry waves orchestrate

bootstrap:
	@echo "Không có dependency ngoài Python 3 standard library."

lint:
	PYTHONPYCACHEPREFIX=.cache/pyc python3 -m compileall -q scripts tests
	bash -n scripts/*.sh .githooks/*
	python3 scripts/check-skill-sync.py

test:
	python3 -m unittest discover -s tests -v

build check-registry waves:
	python3 scripts/check-registry.py task-registry.json

orchestrate:
	python3 scripts/orchestrate.py task-registry.json
