#!/bin/sh

set -ex

./sync_known_issues.py -c *.yaml $@
