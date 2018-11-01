# Known Issues for qa-reports.linaro.org

[![Build Status](https://travis-ci.com/Linaro/qa-reports-known-issues.svg?branch=master)](https://travis-ci.com/Linaro/qa-reports-known-issues)

This repository contains YAML files with serialized known issues. Known issues
are meant to highlight failed tests in qa-reports.linaro.org so it is clear
that the failures were investigated.

## Known Issues sync

sync_known_issues.py script is used to transfer the serialized objects to
qa-reports.linaro.org SQUAD instance. It takes the following parameters

    usage: sync-known-issues.py [-h] -c CONFIG_FILES [CONFIG_FILES ...] -p
                                PASSWORDS_FILE [-d] [-s] [-v]

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG_FILES [CONFIG_FILES ...], --config-files CONFIG_FILES [CONFIG_FILES ...]
                            Instance config files
      -d, --dry-run         Dry run
      -v, --debug           Enable debug

## Authentication

sync_known_issues.py expects environment variable named
QA_REPORTS_KNOWN_ISSUE_TOKEN to exist and contain an authentication token to
use against the squad URL in the given config file.

## YAML file format

Main key in the YAML file is `projects`. Each file may contain a list of projects.
Each project is identified by it's `name`. Project should also define:

* projects - list of `group/project` names from SQUAD instance
* url - location of the SQUAD instance
* environments - list of names and architectures from SQUAD. Since SQUAD doesn't
currently support architectures, it's just a convenient way of defining groups
of environments. Environment slugs should come from SQUAD instance
* known_issues - list of actual tests to highlight. Each known issue should contain
the following fields:
    * environments - list of environments to apply known issue to
    * projects - list of projects to apply known issue to
    * matrix_apply - list of projects/environments to apply known issue to
    * notes - free form text
    * url - optional URL to be used in SQUAD UI
    * test_name - name of the test to highlight. It should include the suite name
    * test_names - list of test names. May be used instead of test_name.
    * active - boolean field which can disable the highlight in SQUAD UI
    * intermittent - boolean field which can signal the flaky test

## Example

See test_data/test-issues.yaml or one of the yaml files in this directory.

## Developing

See Makefile rules 'test' and 'dry-run'. Best practice is to simply run 'make'
before committing a change, which will run all unit tests and also run with
--dry-run against the local yaml files. --dry-run does not require
authentication to qa-reports.
