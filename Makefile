all: test dry-run flake8

test:
	pytest

flake8:
	flake8

dry-run:
	./.travis_run.sh --dry-run

dry-run-verbose:
	./.travis_run.sh --dry-run -v
