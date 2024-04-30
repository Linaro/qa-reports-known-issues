#!/usr/bin/env python3

import argparse
import logging
import os
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
        if "QA_REPORTS_KNOWN_ISSUE_TOKEN" in os.environ:
            connection_token = "Token %s" % os.environ["QA_REPORTS_KNOWN_ISSUE_TOKEN"]
            self.headers = {"Authorization": connection_token}

    def get_prepared_request(self, endpoint, method):
        URL = urlunsplit(
            (self.url_scheme, self.base_url, "api/%s" % endpoint, None, None)
        )
        req = requests.Request(method, URL, headers=self.headers)
        req.raise_for_status()
        return req.prepare()

    def download_list(self, endpoint, params=None):
        URL = urlunsplit(
            (self.url_scheme, self.base_url, "api/%s" % endpoint, None, None)
        )
        logger.debug(URL)
        response = requests.get(URL, params=params, headers=self.headers)
        response.raise_for_status()
        result_list = []
        response_json = response.json()
        result_list = response_json["results"]
        while response_json["next"] is not None:
            response = requests.get(response_json["next"], headers=self.headers)
            if response.status_code == 200:
                response_json = response.json()
                result_list = result_list + response_json["results"]
            else:
                break
        return result_list

    def download_object(self, url):
        if url is None:
            return None
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

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
        object_id = config.get("id")
        URL = urlunsplit(
            (
                self.url_scheme,
                self.base_url,
                "api/%s/%s/" % (endpoint, object_id),
                None,
                None,
            )
        )
        logger.debug(URL)
        logger.debug(config)
        response = requests.put(URL, data=config, headers=self.headers)
        response.raise_for_status()

    def delete_object(self, endpoint, config):
        object_id = config.get("id")
        URL = urlunsplit(
            (
                self.url_scheme,
                self.base_url,
                "api/%s/%s/" % (endpoint, object_id),
                None,
                None,
            )
        )
        logger.debug(URL)
        logger.debug(config)
        response = requests.delete(URL, data=config, headers=self.headers)
        response.raise_for_status()

    def post_object(self, endpoint, config):
        URL = urlunsplit(
            (self.url_scheme, self.base_url, "api/%s/" % endpoint, None, None)
        )
        logger.debug(URL)
        logger.debug(config)
        response = requests.post(URL, data=config, headers=self.headers)
        response.raise_for_status()


class SquadKnownIssueException(Exception):
    pass


class SquadKnownIssue(object):
    def __init__(
        self, config, test_name, squad_project_name, squad_projects, squad_environments
    ):
        self.test_name = test_name
        if self.test_name is None:
            raise SquadKnownIssueException("TestName not defined")
        self.title = squad_project_name + "/" + self.test_name
        self.url = config.get("url")
        self.notes = config.get("notes")
        self.active = config.get("active")
        self.intermittent = config.get("intermittent")
        self.squad_projects = squad_projects
        self.squad_environments = squad_environments

        # Environments belong to projects and may differ by project.
        self.projects_environments = {}

        matrix_apply = config.get("matrix_apply")
        if matrix_apply:
            for matrix in matrix_apply:
                self._build_environments_set(matrix)
            assert (
                config.get("projects") is None
            ), "Error, matrix_apply and projects defined in {}".format(self.__repr__())
            assert (
                config.get("environments") is None
            ), "Error, matrix_apply and projects defined in {}".format(self.__repr__())
        else:
            self._build_environments_set(config)

    def _build_environments_set(self, config):
        self.projects = config.get("projects")
        for project in self.projects:
            assert project in self.squad_projects, "Project not defined: %s" % project

            if project not in self.projects_environments:
                self.projects_environments[project] = set()
            for item in config.get("environments"):
                if item not in self.squad_environments:
                    raise SquadKnownIssueException(
                        "Incorrect environment for project %s: %s" % (project, item)
                    )
                self.projects_environments[project].add(item)

    def __repr__(self):
        return yaml.dump(
            {
                "title": self.title,
                "url": self.url,
                "active": self.active,
                "intermittent": self.intermittent,
                "projects_environments": self.projects_environments,
            },
            indent=4,
            width=80,
        )


class SquadProjectException(Exception):
    pass


class SquadProject(object):
    def __init__(self, config):
        self.name = config.get("name")
        self.url = config.get("url")
        if self.url is None:
            raise SquadProjectException("Project URL is empty")
        self.connection = SquadConnection(self.url)
        self.projects = config.get("projects")
        self.environments = config.get("environments")

        self.known_issues = []
        for conf in config.get("known_issues"):
            test_names = conf.get("test_names", [])
            assert isinstance(
                test_names, list
            ), "Error, string (not list) passed to test_names"
            test_name = conf.get("test_name")
            if test_name is not None:
                assert isinstance(
                    test_name, str
                ), "Error, test_name {} is not a string".format(test_name)
                test_names.append(test_name)
            if len(test_names) == 0:
                raise SquadKnownIssueException("test_name or test_names not defined")
            for test_name in test_names:
                self.known_issues.append(
                    SquadKnownIssue(
                        conf, test_name, self.name, self.projects, self.environments
                    )
                )

        self.check_for_dupe_tests()

    def check_for_dupe_tests(self):
        test_names = []
        for known_issue in self.known_issues:
            tn = known_issue.test_name
            assert tn not in test_names, "Error, test name {} defined twice".format(tn)
            test_names.append(tn)

    def has_known_issue(self, title):
        for known_issue in self.known_issues:
            if known_issue.title == title:
                return True
        return False


def parse_files(config_files):
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
    if "id" in x:
        del x["id"]
    if "id" in y:
        del y["id"]

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


def sync_known_issues(config_data, dry_run=True):
    for project_name, project in config_data.items():
        s = SquadProject(project)

        # validate if projects defined in the instance exist
        for squad_project in s.projects:
            squad_project_group, squad_project_name = squad_project.split("/", 1)
            api_project = s.connection.filter_object(
                "projects/",
                {"group__slug": squad_project_group, "slug": squad_project_name},
            )
            if api_project is None:
                raise SquadProjectException(
                    "Project %s doesn't exist in the instance %s"
                    % (squad_project, s.url)
                )

        api_projects = {}
        for known_issue in s.known_issues:
            # create/update the issues in remote instance
            # for each project defined in the known_issue
            # get the environment IDs based on the environment name
            api_known_issue = s.connection.filter_object(
                "knownissues/",
                {"title": known_issue.title, "test_name": known_issue.test_name},
            )
            affected_environments = []
            for (
                known_issue_project,
                known_issue_project_environments,
            ) in known_issue.projects_environments.items():
                group_name, project_name = known_issue_project.split("/", 1)
                api_project = api_projects.get(known_issue_project)
                if api_project is None:
                    api_project = s.connection.filter_object(
                        "projects/", {"group__slug": group_name, "slug": project_name}
                    )
                    api_projects[known_issue_project] = api_project
                assert api_project is not None, "api_project {} not found".format(
                    known_issue_project
                )
                api_environments = api_projects[known_issue_project].get("environments")
                if api_environments is None:
                    api_environments = s.connection.download_list(
                        "environments/", {"project": api_project["id"]}
                    )
                    api_projects[known_issue_project].update(
                        {"environments": api_environments}
                    )
                for api_env in api_environments:
                    if api_env["slug"] in known_issue_project_environments:
                        logger.debug(
                            "Adding env: %s to known issue: %s"
                            % (api_env["slug"], known_issue.title)
                        )
                        affected_environments.append(api_env)
            assert (
                len(affected_environments) > 0
            ), "Error, no affected environments found for {}".format(known_issue)

            known_issue_api_object = {
                "title": known_issue.title,
                "test_name": known_issue.test_name,
                "url": known_issue.url,
                "notes": known_issue.notes,
                "active": known_issue.active,
                "intermittent": known_issue.intermittent,
                "environments": [item["url"] for item in affected_environments],
            }

            if api_known_issue is None:
                print("Adding issue:")
                print(textwrap.indent(str(known_issue), "    "))
                if not dry_run:
                    # create new KnownIssue
                    s.connection.post_object("knownissues", known_issue_api_object)
            else:  # update case
                if issues_equal(api_known_issue, known_issue_api_object):
                    print("No changes to '{}'".format(api_known_issue["test_name"]))
                    continue

                print("Updating issue:")
                print(textwrap.indent(str(known_issue), "    "))
                if not dry_run:
                    # update existing KnownIssue
                    api_known_issue.update(known_issue_api_object)
                    s.connection.put_object("knownissues", api_known_issue)


def prune_known_issues(config_data, dry_run=True):
    """
    For each known issue in qa-reports, verify there is a matching known
    issue in the known issue file given. If there are any known issues in
    qa-reports that don't have a match in config_data (and are in the same
    project), report. Eventually, delete automatically instead of report.
    """

    all_api_known_issues = (
        {}
    )  # Cache api_known_issue lists here, based on project['url']

    for project_name, project in config_data.items():
        s = SquadProject(project)

        # Since I can't figure out how to filter on a partial title, retrieve all
        # known issues for a given url. Cache them so that subsequent projects won't
        # refetch the same list.
        if project["url"] not in all_api_known_issues:
            all_api_known_issues[project["url"]] = s.connection.download_list(
                "knownissues/"
            )

        for api_known_issue in all_api_known_issues[project["url"]]:
            if api_known_issue["title"].split("/")[0] != project_name:
                # Ensure project name matches
                continue
            if not s.has_known_issue(api_known_issue["title"]):
                if dry_run:
                    print(
                        "{} is in {} but not defined in project {}".format(
                            api_known_issue["title"],
                            project["url"],
                            project_name,
                        )
                    )
                else:
                    print(
                        "Deleting '{}'".format(
                            api_known_issue["title"],
                        )
                    )
                    # delete KnownIssue
                    s.connection.delete_object("knownissues", api_known_issue)


def main():
    assert not os.path.isfile(
        os.environ.get("HOME") + "/.netrc"
    ), "Error - remove ~/.netrc - see https://github.com/requests/requests/issues/3929"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-files",
        nargs="+",
        required=True,
        help="Instance config files",
        dest="config_files",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        default=False,
        help="Dry run",
        dest="dry_run",
    )
    parser.add_argument(
        "-v",
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug",
        dest="debug",
    )

    args = parser.parse_args()
    config_data = parse_files(args.config_files)
    if args.debug:
        # Not sure how else to set the log level when using a global logger.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)

    if "QA_REPORTS_KNOWN_ISSUE_TOKEN" not in os.environ:
        logger.error("Error: QA_REPORTS_KNOWN_ISSUE_TOKEN not set in environment")
        sys.exit(1)

    sync_known_issues(config_data, args.dry_run)
    prune_known_issues(config_data, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
