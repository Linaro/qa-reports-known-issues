#!/bin/sh

set -ex

for issue_file in $(ls *.yaml); do
    ./sync_known_issues.py -c ${issue_file} $@
done
