all: test dry-run

test:
	pytest

dry-run:
	./.travis_run.sh --dry-run

dry-run-verbose:
	./.travis_run.sh --dry-run -v
