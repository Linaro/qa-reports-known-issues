# Known Issues for qa-reports.linaro.org

This repository contains YAML files with serialized known issues. Known issues
are meant to highlight failed tests in qa-reports.linaro.org so it is clear
that the failures were investigated.

## Known Issues sync

sync-known-issues.py script is used to transfer the serialized objects to
qa-reports.linaro.org SQUAD instance. It takes the following parameters

	usage: sync-known-issues.py [-h] -c CONFIG_FILES [CONFIG_FILES ...] -p
								PASSWORDS_FILE [-d] [-s] [-v]

	optional arguments:
	  -h, --help            show this help message and exit
	  -c CONFIG_FILES [CONFIG_FILES ...], --config-files CONFIG_FILES [CONFIG_FILES ...]
							Instance config files
	  -p PASSWORDS_FILE, --passwords-file PASSWORDS_FILE
							Passwords file in the .netrc form
	  -d, --dry-run         Dry run
	  -s, --sanity-check    Sanity check. Implies dry run.
	  -v, --debug           Enable debug

## YAML file format

Main key in the YAML file is `projects`. Each file may contain a list of projects.
Each project is identified by it's `name`. Project should also define:

* projects - list of `group/project` names from SQUAD instance
* url - location of the SQUAD instance
* environments - list of names and architectures from SQUAD. Since SQUAD doesn't
currently support architectures, it's just a convenient way of defining groups
of environments. Environment slugs should come from SQUAD instance
* known_issues - list of actual tests to highlight. Each known issue should contain
the following fileds:
    * environments - list of environment slugs or architectures defined in the project
    * notes - free form text
    * url - optional URL to be used in SQUAD UI
    * test_name - name of the test to highlight. It should include the suite name
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
	  - architecture: arm64
		slug: hi6220-hikey
	  - architecture: arm64
		slug: juno-r2
	  - architecture: arm64
		slug: dragonboard-410c
	  - architecture: arm32
		slug: x15
	  - architecture: x86_64
		slug: x86
	  - architecture: x86_64
		slug: qemu_x86_64
	  - architecture: x86
		slug: qemu_x86_32
	  - architecture: arm32
		slug: qemu_arm
	  - architecture: arm64
		slug: qemu_arm64
	  known_issues:
	  - environments: &id_allboards_001
		- slug: hi6220-hikey
		- slug: juno-r2
		- slug: dragonboard-410c
		- slug: x15
		- slug: x86
		- slug: qemu_x86_64
		- slug: qemu_x86_32
		- slug: qemu_arm
		- slug: qemu_arm64
		notes: 'Adding skiplist according to the below ticket mainline kernel tests baselining'
		projects:
		- lkft/linux-stable-rc-4.4-oe
		- lkft/linux-stable-rc-4.9-oe
		- lkft/linux-stable-rc-4.14-oe
		- lkft/linux-stable-rc-4.16-oe
		- lkft/linux-stable-rc-4.17-oe
		- lkft/linux-mainline-oe
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

