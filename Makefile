all: test dry-run

test:
	pytest

dry-run:
	./sync_known_issues.py -c kselftests-production.yaml --dry-run
	./sync_known_issues.py -c ltp-production.yaml --dry-run
	./sync_known_issues.py -c libhugetlbfs-production.yaml --dry-run
