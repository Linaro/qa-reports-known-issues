import sync_known_issues
import pdb

import yaml

def test_parse_files():
    config_file = "test_data/test-issues.yaml"
    config_data = sync_known_issues.parse_files([config_file])

    assert 'LKFT-ltp-staging' in config_data
    assert len(config_data['LKFT-ltp-staging']['environments']) == 3
    assert 'known_issues' in config_data['LKFT-ltp-staging']



