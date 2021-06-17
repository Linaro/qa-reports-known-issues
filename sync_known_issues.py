#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import yaml
from collections import defaultdict

from squad_client.core.models import Squad, KnownIssue, ALL
from squad_client.core.api import SquadApi
from squad_client import utils


logger = logging.getLogger(__name__)
formatter = logging.Formatter('[%(levelname)s] %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


class Cache:
    def __init__(self):
        # group_slug/project_slug => project (object)
        self.projects = {}

        # group_slug/project_slug => {env_slug => env (object)}
        self.environments = {}

        # knownissue.title => knownissue (object)
        self.knownissues = {}

        self.config_knownissues = {}

SquadApi.configure('https://qa-reports.linaro.org')
cache = Cache()
squad = Squad()


def new_knownissue(config_knownissue):
    k = KnownIssue()
    k.__fill_object__(config_knownissue)
    return k


def issues_equal(title):
    backend = cache.knownissues[title]
    config = cache.config_knownissues[title]

    equals = backend.notes == config.get('notes')
    equals &= backend.test_name == config.get('test_name')
    equals &= backend.active == config.get('active')
    equals &= backend.intermittent == config.get('intermittent')

    # Get environments urls from knownissue in config
    config_env_urls = []
    for project_slug in config['projects']:
        for env_slug in config['environments']:
            env = cache.environments[project_slug][env_slug]
            config_env_urls.append()

    equals &= len(set(backend.environments) ^ )

    # Remove any trailing newlines in notes
    if x["notes"] is not None:
        x["notes"] = x["notes"].strip()
    if y["notes"] is not None:
        y["notes"] = y["notes"].strip()

    # Ensure consistent sort order
    x["environments"].sort()
    y["environments"].sort()

    differences = DeepDiff(x, y)
    if not differences:
        return True

    return False


def load_cache(config_data):
    logger.debug('Loading cache data')

    all_projects_x_environments = defaultdict(lambda: defaultdict(set))
    all_projects_slugs = set()
    all_environments_slugs = set()
    for title, config in config_data.items():

        # Make sure that there's no duplicate of known issues' titles
        for knownissue in config['known_issues']:

            # Known issues can have a single "test_name" string or an array of "test_names"
            test_names = knownissue.get('test_names') or []
            if knownissue.get('test_name'):
                test_names.append(knownissue.get('test_name'))

            # TODO: take care o matrix_apply
            # for each matrix_apply, generate a list of environments
            # maybe normalize the environments right here, to make it normalized elsewhere in the code

            for test_name in test_names:
                full_title = f'{title}/{test_name}'
                assert full_title not in cache.config_knownissues.keys(), f'E: "{full_title}" is duplicated!'
                cache.config_knownissues[full_title] = knownissue.copy()

        # Generate a dictionary like
        # all_projects_x_environments = {
        #     'group': {
        #         'project': {'env1', 'env2'}
        #     }
        # }
        for group_project_slug in config['projects']:
            envs = set(config['environments'])
            group_slug, project_slug = utils.split_group_project_slug(group_project_slug)
            all_projects_x_environments[group_slug][project_slug] |= envs
            all_projects_slugs.add(group_project_slug)
            all_environments_slugs |= envs

    # Get all known issues at once from backend
    # All known issues managed by this script have titles starting with
    # the "name" tag, so we'll use that as filter
    logger.debug('  Loading all known issues')
    for title in config_data.keys():
        knownissues = squad.knownissues(title__startswith=title, count=ALL).values()
        logger.debug('    %d for %s' % (len(knownissues), title))
        cache.knownissues.update({k.title: k for k in knownissues})
    logger.debug('  Loaded %d' % (len(cache.knownissues.keys()),))

    # Get all projects/environments at once from backend
    cache.environments = defaultdict(dict)
    found_environments_slugs = set()
    for group_slug, projects_slugs in all_projects_x_environments.items():
        logger.debug(f'  Loading projects for {group_slug}')
        projects = squad.group(group_slug).projects(slug__in=','.join(projects_slugs.keys()), count=ALL)
        cache.projects = {'%s/%s' % (group_slug, p.slug): p for p in projects.values()}

        for project in projects.values():
            logger.debug(f'    Loading environments for {project.slug}')
            comma_sepparated_envs = ','.join(list(all_projects_x_environments[group_slug][project.slug]))
            environments = project.environments(slug__in=comma_sepparated_envs, count=ALL)
            for env in environments.values():
                cache.environments[f'{group_slug}/{project.slug}'][env.slug] = env
                found_environments_slugs.add(env.slug)

    # Check if there is any project in config files not found in the backend
    diff = set(all_projects_slugs) ^ set(cache.projects.keys())
    assert len(diff) == 0, 'E: Some projects do not exist in the backend: {diff}'

    diff = set(all_environments_slugs) ^ set(found_environments_slugs)
    assert len(diff) == 0, 'E: Some environments do not exist in the backend: {diff}'


def sync_known_issues(config_data, dry_run=True):
    # Load data only once
    load_cache(config_data)

    logger.debug('Syncing known issues')

    # Transform knownissues into 
    backend_set = set(cache.knownissues.keys())
    config_set = set(cache.config_knownissues.keys())

    # First step syncing: check if there's any new known issue
    config_extra = config_set - backend_set
    if len(config_extra):
        logger.warn(f'Config files have extra known issues: {config_extra}')
        for knownissue_title in config_extra:
            logger.debug(f'  Adding {knownissue_title}')
            k = new_knownissue(cache.config_knownissues[knownissue_title])
            cache.knownissues[k.title] = k
            if not dry_run:
                pass
                # k.save()

    # Second step syncing: check if config files removed any known issues
    backend_extra = backend_set - config_set
    if len(backend_extra):
        logger.warn(f'Backend has extra known issues: {backend_extra}')
        for knownissue_title in backend_extra:
            logger.debug(f'  Removing {knownissue_title}')
            k = cache.knownissues[knownissue_title]
            del cache.knownissues[knownissue_title]
            if not dry_run:
                pass
                # k.delete()

    # There shouldn't be any difference in number of known issues between backend and config files now
    diff = set(cache.knownissues.keys()) ^ set(cache.config_knownissues)
    assert len(diff) == 0, f'E: there are still mismatching knownissues: {diff}'

    # Third (last) step syncing: now known issues in the backend and config files should be the same
    # what's left now is checking if there are known issues changed internally
    for title in config.config_knownissues.keys():
        issues_equal(title)
        

def parse_files(config_files):
    """
        The output will be like:

        {
            'LKFT-<known-issues-group-name>': {
                'name': '<same as parent.key>',
                'url': 'https://qa-reports.linaro.org',
                'projects': [<list-of-all-projects-of-this-known-issue-group>],
                'environments': [<list-of-all-environments-of-this-known-issue-group>],
                'known_issues': [{
                    'environments': [<list-of-environments-of-this-known-issue>],
                    'projects': [<list-of-projects-of-this-known-issue>],
                    'test_names': [<list-of-test-names-of-this-known-issues>],
                    'notes': 'the note for this known issue',
                    'url': 'url of this known issue',
                    'active': true|false,
                    'intermittent': true|false
                }]
            }
        }
    """
    logger.debug(f'Loading config files: {config_files}')
    config_data = {}
    for f in config_files:
        with open(f, "r") as stream:
            try:
                loaded_config = yaml.load(stream, Loader=yaml.SafeLoader)
                for project in loaded_config.get("projects"):
                    config_data.update({project["name"]: project})
            except yaml.YAMLError as exc:
                logger.error(exc)
                sys.exit(1)
    return config_data


def main():

    assert not os.path.isfile(
        os.environ.get("HOME") + "/.netrc"
    ), "Error - remove ~/.netrc - see https://github.com/requests/requests/issues/3929"

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config-files", nargs="+", required=True, help="Instance config files")
    parser.add_argument("-d", "--dry-run", action="store_true", default=False, help="Dry run")
    parser.add_argument("-v", "--debug", action="store_true", default=False, help="Enable debug")

    args = parser.parse_args()
    config_data = parse_files(args.config_files)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not args.dry_run and "QA_REPORTS_KNOWN_ISSUE_TOKEN" not in os.environ:
        logger.error("Error: QA_REPORTS_KNOWN_ISSUE_TOKEN not set in environment")
        sys.exit(1)

    sync_known_issues(config_data, args.dry_run)


if __name__ == "__main__":
    main()
