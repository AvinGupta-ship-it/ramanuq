.PHONY: test study figures report gates all

test:
	pytest

study:
	python scripts/run_studies.py

figures:
	python scripts/make_all_figures.py

report:
	python scripts/build_report.py

gates:
	ruff check .
	pytest

all: gates study figures report
