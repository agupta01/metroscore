.PHONY : docs
docs :
	rm -rf docs/build/
	sphinx-autobuild -b html --watch metroscore/ docs/source/ docs/build/

.PHONY : run-checks
run-checks :
	isort --check .
	black --check .
	flake8 .
	mypy .
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes --doctest-modules tests/ metroscore/

.PHONY : precommit
precommit :
	isort .
	black .
	flake8 .
	mypy .
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes --doctest-modules tests/ metroscore/

.PHONY: setup-dev
setup-dev:
	python3 -m venv .venv
	. .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pip install -r dev-requirements.txt && \
	pip install -e .
