deps:
	[ -d .venv ] || python3 -m venv .venv
	.venv/bin/pip3 install -r requirements.txt
	.venv/bin/pip3 install -r requirements-dev.txt
	git submodule update --init

.PHONY: test

test:
	@./tests/test.sh

api:
	@npm run --silent api

lint:
	@.venv/bin/flake8 *.py --ignore=C901,E741 --exit-zero --max-complexity=10 --max-line-length=127 --statistics

fix:
	@.venv/bin/autopep8 --in-place *.py

