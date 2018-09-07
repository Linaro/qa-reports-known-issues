import sync_known_issues
import pdb
from random import shuffle

import yaml

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
    b['id'] = 10 # Set an 'id' field in b. Should still be equal
    shuffle(b['environments']) # Randomize environments list order
    b['notes'] = b['notes']+"\n" # Add newline to b's 'note'

    is_equal = sync_known_issues.issues_equal(a, b)
    assert is_equal

def test_issue_equal_not_equal():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    a = config_data['LKFT-ltp-staging']['known_issues'][0]

    b = a.copy()
    b['id'] = 10 # Set an 'id' field in b. Should still be equal
    b['title'] = "Foo is my Title"

    is_equal = sync_known_issues.issues_equal(a, b)
    assert not is_equal

