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
    * environments - list of environment slugs or architectures defined in the project
    * notes - free form text
    * url - optional URL to be used in SQUAD UI
    * test_name - name of the test to highlight. It should include the suite name
    * test_names - list of test names. May be used instead of test_name.
    * active - boolean field which can disable the highlight in SQUAD UI
    * intermittent - boolean field which can signal the flaky test

## Example

    projects:
    - name: LKFT
      projects:
      - lkft/linux-mainline-oe
      - lkft/linux-next-oe
      - lkft/linux-stable-rc-4.4-oe
      - lkft/linux-stable-rc-4.9-oe
      - lkft/linux-stable-rc-4.14-oe
      - lkft/linux-stable-rc-4.16-oe
      - lkft/linux-stable-rc-4.17-oe
      url: https://qa-reports.linaro.org
      environments:
      - hi6220-hikey
      - juno-r2
      - dragonboard-410c
      - x15
      - x86
      - qemu_x86_64
      - qemu_x86_32
      - qemu_arm
      - qemu_arm64
      known_issues:
      - environments: &id_allboards_001
        - hi6220-hikey
        - juno-r2
        - dragonboard-410c
        - x15
        - x86
        - qemu_x86_64
        - qemu_x86_32
        - qemu_arm
        - qemu_arm64
        notes: 'Adding skiplist according to the below ticket mainline kernel tests baselining'
        projects:
        - lkft/linux-stable-rc-4.4-oe
        - lkft/linux-stable-rc-4.9-oe
        - lkft/linux-stable-rc-4.14-oe
        - lkft/linux-stable-rc-4.16-oe
        - lkft/linux-stable-rc-4.17-oe
        - lkft/linux-mainline-oe
        test_names:
          - kselftests/test_maps
          - kselftests/test_progs
        test_name: kselftests/test_maps
        url: https://projects.linaro.org/projects/CTT/queues/issue/CTT-585
        active: true
        intermittent: false
      - environments: *id_allboards_001
        notes: 'LKFT: kselftest: test_progs: libbpf: failed to open ./test_pkt_access.o:
          No such file or directory'
        projects:
        - lkft/linux-stable-rc-4.4-oe
        - lkft/linux-stable-rc-4.9-oe
        - lkft/linux-stable-rc-4.14-oe
        - lkft/linux-stable-rc-4.16-oe
        - lkft/linux-stable-rc-4.17-oe
        - lkft/linux-mainline-oe
        test_name: kselftests/test_progs
        url: https://bugs.linaro.org/show_bug.cgi?id=3120
        active: true
        intermittent: false
