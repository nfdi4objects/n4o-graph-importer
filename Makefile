deps:
	[ -d .venv ] || python3 -m venv .venv
	.venv/bin/pip3 install -r requirements.txt
	.venv/bin/pip3 install -r requirements-dev.txt
	git submodule update --init

.PHONY: test

test:
	@. .venv/bin/activate && ./tests/test_api.sh && coverage report -m

api:
	@npm run --silent api

lint:
	@.venv/bin/flake8 *.py lib/*.py --ignore=C901,E741,W504 --exit-zero --max-complexity=10 --max-line-length=127 --statistics

fix:
	@.venv/bin/autopep8 --in-place *.py lib/*.py

tests/20533.concepts.ndjson:
	curl -s https://api.dante.gbv.de/export/download/kenom_material/default/kenom_material__default.jskos.ndjson | \
	jq -c 'del(.publisher,.qualifiedLiterals,.ancestors,.created,.modified,."@context",.issued,.mappings)' > $@
