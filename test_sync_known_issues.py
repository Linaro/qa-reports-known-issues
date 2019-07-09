import sync_known_issues
import pytest
from random import shuffle


def test_parse_files():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    assert 'LKFT-ltp-staging' in config_data
    assert len(config_data['LKFT-ltp-staging']['environments']) == 3
    assert 'known_issues' in config_data['LKFT-ltp-staging']


def test_issue_equal_is_equal():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = config_data['LKFT-ltp-staging']['known_issues'][0]

    b = a.copy()
    b['id'] = 10  # Set an 'id' field in b. Should still be equal
    shuffle(b['environments'])  # Randomize environments list order
    b['notes'] = b['notes']+"\n"  # Add newline to b's 'note'

    is_equal = sync_known_issues.issues_equal(a, b)
    assert is_equal


def test_issue_equal_not_equal():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = config_data['LKFT-ltp-staging']['known_issues'][0]

    b = a.copy()
    b['id'] = 10  # Set an 'id' field in b. Should still be equal
    b['title'] = "Foo is my Title"

    is_equal = sync_known_issues.issues_equal(a, b)
    assert not is_equal


def test_issue_url_note_null():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = config_data['LKFT-ltp-staging']['known_issues'][0]

    b = a.copy()
    b['url'] = None
    b['notes'] = None

    is_equal = sync_known_issues.issues_equal(a, b)
    assert not is_equal


def test_squad_known_issue_happy_path():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = sync_known_issues.SquadProject(config_data['LKFT-ltp-staging'])
    assert a.projects == ['lkft/linux-mainline-oe',
                          'lkft/linux-next-oe',
                          'lkft/linux-stable-rc-4.17-oe']
    assert a.environments == ['hi6220-hikey', 'juno-r2', 'x86']
    assert len(a.known_issues) == 6


def test_squad_known_issue_happy_path_2():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = sync_known_issues.SquadProject(config_data['LKFT-ltp-staging'])

    # Find issue named ltp-syscalls-tests/fork10 in the list
    for issue in a.known_issues:
        if issue.test_name == 'ltp-syscalls-tests/fork10':
            break
    else:
        assert False, "test_name ltp-syscalls-tests/fork10 not found"

    assert issue.active
    assert issue.intermittent is None
    assert issue.projects_environments == {
        'lkft/linux-mainline-oe': {'x86', 'hi6220-hikey', 'juno-r2'},
        'lkft/linux-next-oe': {'hi6220-hikey'},
        'lkft/linux-stable-rc-4.17-oe': {'hi6220-hikey'}
    }


def test_squad_known_issue_dupe_detection():
    config_file = "test_data/dupe-issue.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    with pytest.raises(AssertionError,
                       message="Error, test name ltp-syscalls-tests/fork13 defined twice"):
        sync_known_issues.SquadProject(config_data['LKFT-ltp-staging'])


def test_matrix_apply_kselftest_bug():
    config_file = "test_data/test-issues-2.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = sync_known_issues.SquadProject(config_data['LKFT'])

    # Find issue named ltp-syscalls-tests/fork10 in the list
    for issue in a.known_issues:
        if issue.test_name == 'kselftest/bpf_test_align':
            break
    else:
        assert False, "test_name kselftest/bpf_test_align not found"

    assert issue.projects_environments == {
        'lkft/linux-stable-rc-4.14-oe':
            {'dragonboard-410c', 'hi6220-hikey', 'i386', 'x86', 'qemu_arm64',
             'qemu_x86_64', 'qemu_arm', 'qemu_i386', 'x15', 'juno-r2'},
        'lkft/linux-stable-rc-4.9-oe':
            {'dragonboard-410c', 'hi6220-hikey', 'i386', 'x86', 'qemu_arm64',
             'qemu_x86_64', 'qemu_arm', 'qemu_i386', 'x15', 'juno-r2'},
        'lkft/linux-stable-rc-4.4-oe':
            {'dragonboard-410c', 'hi6220-hikey', 'i386', 'x86', 'qemu_arm64',
             'qemu_x86_64', 'qemu_arm', 'qemu_i386', 'x15', 'juno-r2'},
        'lkft/linaro-hikey-stable-rc-4.4-oe':
            {'dragonboard-410c', 'hi6220-hikey', 'i386', 'x86', 'qemu_arm64',
             'qemu_x86_64', 'qemu_arm', 'qemu_i386', 'x15', 'juno-r2'},
        'lkft/linux-mainline-oe': {'qemu_i386', 'x15', 'qemu_arm', 'i386'},
        'lkft/linux-stable-rc-4.19-oe': {'qemu_i386', 'x15', 'qemu_arm', 'i386'},
        'lkft/linux-stable-rc-5.1-oe': {'qemu_i386', 'x15', 'qemu_arm', 'i386'},
        'lkft/linux-stable-rc-5.2-oe': {'qemu_i386', 'x15', 'qemu_arm', 'i386'}
        }


def test_test_names_as_string():
    config_file = "test_data/test-names-as-string.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    with pytest.raises(AssertionError,
                       message="Error, string (not list) passed to test_names"):
        sync_known_issues.SquadProject(config_data['LKFT-ltp-staging'])
