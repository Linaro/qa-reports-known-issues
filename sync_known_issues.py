#!/usr/bin/env python3

import argparse
import logging
import os
import pprint
import requests
import sys
import textwrap
import yaml

from deepdiff import DeepDiff

from urllib.parse import urlsplit, urlunsplit


FORMAT = "[%(funcName)20s() ] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)


class SquadConnectionException(Exception):
    pass


class SquadConnection(object):
    def __init__(self, url):
        self.url = url
        urlparts = urlsplit(self.url)
        self.base_url = urlparts.netloc
        self.url_scheme = urlparts.scheme

        # Note that QA_REPORTS_KNOWN_ISSUE_TOKEN is optional;
        # When unset, unauthenticated requests will still work (which are often
        # sufficient for --dry-run).
        self.headers = {}
        if 'QA_REPORTS_KNOWN_ISSUE_TOKEN' in os.environ:
            connection_token = "Token %s" % os.environ['QA_REPORTS_KNOWN_ISSUE_TOKEN']
            self.headers = {
                "Authorization": connection_token
            }

    def get_prepared_request(self, endpoint, method):
        URL = urlunsplit(
            (self.url_scheme,
             self.base_url,
             "api/%s" % endpoint,
             None,
             None))
        req = requests.Request(method, URL, headers=self.headers)
        return req.prepare()

    def download_list(self, endpoint, params=None):
        URL = urlunsplit(
            (self.url_scheme,
             self.base_url,
             "api/%s" % endpoint,
             None,
             None))
        logger.debug(URL)
        response = requests.get(URL, params=params, headers=self.headers)
        result_list = []
        if response.status_code == 200:
            response_json = response.json()
            result_list = response_json['results']
            while response_json['next'] is not None:
                response = requests.get(response_json['next'], headers=self.headers)
                if response.status_code == 200:
                    response_json = response.json()
                    result_list = result_list + response_json['results']
                else:
                    break
        else:
            logger.error(URL)
            logger.error(response.status_code)
            logger.error(response.text)
        return result_list

    def download_object(self, url):
        if url is None:
            return None
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def filter_object(self, endpoint, params):
        old_configs = self.download_list(endpoint, params)
        if len(old_configs) == 0:
            # the config is new
            return None
        if len(old_configs) != 1:
            logger.error("Found too many objects of type: %s" % endpoint)
            logger.error("Params: %s" % params)
            raise SquadConnectionException("Too many objects found")
        return old_configs[0]

    def put_object(self, endpoint, config):
        object_id = config.get('id')
        URL = urlunsplit(
            (self.url_scheme,
             self.base_url,
             "api/%s/%s/" % (endpoint, object_id),
             None,
             None))
        logger.debug(URL)
        logger.debug(config)
        response = requests.put(URL, data=config, headers=self.headers)
        if response.status_code != 200:
            logger.error(response.text)

    def post_object(self, endpoint, config):
        URL = urlunsplit((self.url_scheme, self.base_url, "api/%s/" % endpoint, None, None))
        logger.debug(URL)
        logger.debug(config)
        response = requests.post(URL, data=config, headers=self.headers)
        if response.status_code != 201:
            logger.error(response.text)


class SquadKnownIssueException(Exception):
    pass


class SquadKnownIssue(object):
    def __init__(self, config, squad_project):
        self.test_name = config.get('test_name')
        if self.test_name is None:
            raise SquadKnownIssueException("TestName not defined")
        self.title = squad_project.name + "/" + self.test_name
        self.url = config.get('url')
        self.notes = config.get('notes')
        self.active = config.get('active')
        self.intermittent = config.get('intermittent')
        self.projects = config.get('projects')
        for project in self.projects:
            if project not in squad_project.projects:
                # ignore projects that are not defined
                # in the SquadProject.projects
                self.projects.remove(project)
                raise SquadKnownIssueException("Project not defined: %s" % project)
        self.environments = set()
        for item in config.get('environments'):
            if item in squad_project.environments:
                self.environments.add(item)
            else:
                raise SquadKnownIssueException(
                    "Incorrect environment: %s" % item)

    def __repr__(self):
        return yaml.dump({'title': self.title,
                          'url': self.url,
                          'active': self.active,
                          'intermittent': self.intermittent,
                          'projects': self.projects,
                          'environments': list(self.environments),
                         },
                         indent=4,
                         width=80)


class SquadProjectException(Exception):
    pass


class SquadProject(object):
    def __init__(self, config):
        self.name = config.get('name')
        self.url = config.get('url')
        if self.url is None:
            raise SquadProjectException("Project URL is empty")
        self.connection = SquadConnection(self.url)
        self.projects = config.get('projects')
        self.environments = config.get('environments')
        self.known_issues = [SquadKnownIssue(conf, self) for conf in config.get('known_issues')]

def parse_files(config_files):
    config_data = {}
    for f in config_files:
        with open(f, 'r') as stream:
            try:
                loaded_config = yaml.load(stream)
                for project in loaded_config.get('projects'):
                    config_data.update({project['name']: project})
            except yaml.YAMLError as exc:
                logger.error(exc)
                sys.exit(1)
    return config_data

def issues_equal(a, b):
    """
        Compare two known issue dictionaries,
        return True if equal, else False

        Before comparing, normalization occurs:
        - the 'id' field may exist in one but not the other
          list, and shouldn't be used.
        - the 'environments' field is a list and sort order may differ
        - strip() notes field

        Note that both inputs are normalized so that order doesn't
        matter.

    """

    # Copy the dicts, so they may be modified
    x = a.copy()
    y = b.copy()

    # Remove 'id' for purpose of comparison
    if 'id' in x: del x['id']
    if 'id' in y: del y['id']

    # Remove any trailing newlines in notes
    if x['notes'] is not None:
        x['notes'] = x['notes'].strip()
    if y['notes'] is not None:
        y['notes'] = y['notes'].strip()

    # Ensure consistent sort order
    x['environments'].sort()
    y['environments'].sort()

    differences = DeepDiff(x, y)
    if not differences:
        return True

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--config-files",
                        nargs="+",
                        required=True,
                        help="Instance config files",
                        dest="config_files")
    parser.add_argument("-d",
                        "--dry-run",
                        action="store_true",
                        default=False,
                        help="Dry run",
                        dest="dry_run")
    parser.add_argument("-v",
                        "--debug",
                        action="store_true",
                        default=False,
                        help="Enable debug",
                        dest="debug")

    args = parser.parse_args()
    config_data = parse_files(args.config_files)
    if args.debug:
        # Not sure how else to set the log level when using a global logger.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)

    for project_name, project in config_data.items():
        s = SquadProject(project)

        # validate if projects defined in the instance exist
        for squad_project in s.projects:
            squad_project_group, squad_project_name = squad_project.split("/", 1)
            api_project = s.connection.filter_object(
                'projects/',
                {'group__slug': squad_project_group, 'slug': squad_project_name})
            if api_project is None:
                raise SquadProjectException(
                    "Project %s doesn't exist in the instance %s" % (squad_project, s.url))

        api_projects = {}
        for known_issue in s.known_issues:
            # create/uptade the issues in remote instance
            # for each project defined in the known_issue
            # get the environment IDs based on the environment name
            api_known_issue = s.connection.filter_object(
                'knownissues/',
                {'title': known_issue.title, 'test_name': known_issue.test_name})
            affected_environments = []
            for known_issue_project in known_issue.projects:
                group_name, project_name = known_issue_project.split('/', 1)
                api_project = api_projects.get(known_issue_project)
                if api_project is None:
                    api_project = s.connection.filter_object(
                        'projects/',
                        {'group__slug': group_name, 'slug': project_name})
                    api_projects[known_issue_project] = api_project
                if api_project is None:
                    continue
                api_environments = api_projects[known_issue_project].get('environments')
                if api_environments is None:
                    api_environments = s.connection.download_list(
                        'environments/',
                        {'project': api_project['id']})
                    api_projects[known_issue_project].update({'environments': api_environments})
                for api_env in api_environments:
                    if api_env['slug'] in known_issue.environments:
                        logger.debug(
                            "Adding env: %s to known issue: %s" % (
                                api_env['slug'],
                                known_issue.title))
                        affected_environments.append(api_env)

            known_issue_api_object = {
                'title': known_issue.title,
                'test_name': known_issue.test_name,
                'url': known_issue.url,
                'notes': known_issue.notes,
                'active': known_issue.active,
                'intermittent': known_issue.intermittent,
                'environments': [item['url'] for item in affected_environments]
            }

            if api_known_issue is None:
                print("Adding issue:")
                print(textwrap.indent(str(known_issue), "    "))
                if not args.dry_run:
                    # create new KnownIssue
                    s.connection.post_object(
                        'knownissues',
                        known_issue_api_object
                    )
            else: # update case
                if issues_equal(api_known_issue, known_issue_api_object):
                    print("No changes to '{}'".format(api_known_issue['test_name']))
                    continue

                print("Updating issue:")
                print(textwrap.indent(str(known_issue), "    "))
                if not args.dry_run:
                    # update existing KnownIssue
                    api_known_issue.update(known_issue_api_object)
                    s.connection.put_object(
                        'knownissues',
                        api_known_issue
                    )

if __name__ == '__main__':
    main()
