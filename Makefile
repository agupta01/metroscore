.PHONY : clean
clean:
	rm -rf ./.venv
	rm -rf ./metroscore.egg-info

.PHONY : docs
docs :
	rm -rf docs/build/
	sphinx-build -M linkcheck docs/source/ docs/build/
	sphinx-autobuild -b html --watch metroscore/ docs/source/ docs/build/

.PHONY : run-checks
run-checks :
	isort --check .
	black --check .
	flake8 .
	mypy .
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes --cov --doctest-modules tests/ metroscore/

.PHONY : precommit
precommit :
	isort .
	black .
	flake8 .
	mypy .
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes --cov --doctest-modules tests/ metroscore/

.PHONY : precommit-windows
precommit-windows :
	isort .
	black .
	flake8 .
	mypy .
	@set CUDA_VISIBLE_DEVICES= && pytest -v --color=yes --doctest-modules tests/ metroscore/

.PHONY : setup-dev
setup-dev :
	python -m venv .venv
	. .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pip install -r dev-requirements.txt && \
	pip install -e .

.PHONY : setup-dev-windows
setup-dev-windows :
	python -m venv .venv
	call .venv/Scripts/activate && \
	.venv\Scripts\python.exe -m pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pip install -r dev-requirements.txt && \
	pip install -e .
