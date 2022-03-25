#!/usr/bin/env python3

"""
Fetches all issues for an org and dumps to tabular formats.

25 Mar, 2022
Leland E. Vakarian
"""

__author__  = "Leland E. Vakarian"
__status__  = "production"
__date__    = "25 Mar, 2022"

import click
import os

from lib.utils import CONTEXT_SETTINGS


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, help="Show verbose output. Pass again for debug.")
@click.option('-f', '--force', is_flag=True, help="Skip asking to overwrite output.")
@click.option(
    '-l',
    '--save-logs',
    'save_logs',
    type=click.Path(),
    help="Capture logging output (at whatever verbosity level) to the specified path."
)
@click.option(
    '--token', prompt=True, prompt_required=False,
    default=lambda: os.environ.get("ST_GITHUB_TOKEN", ""),
    show_default="env: ST_GITHUB_TOKEN"
)
@click.argument('org')
@click.argument('output', type=click.Path())
@click.pass_context
def cli(ctx, verbose, force, save_logs, token, org, output):
    """Fetches all issues for an org and dumps to tabular formats.

    The token is a Personal Access Token for Github. It must be configured with read privileges for
    repositories. Configure for public/private access as needed.

    See https://github.com/settings/tokens to create and manage tokens for your Github account.

    \f

    This function serves as the entrypoint for the program when called on the CLI.

    Args:
        verbose (int): if 1, pretty-print output as the command runs. If 2, print debugging output
            in addition to level 1 output. If 0, prints nothing as the command runs. Defaults to 0.
        force (bool): if True, skip asking for permission to overwrite a file with output. Defaults
            to False.
        save_logs (str): a path to write captured logging output to.
    """
    import csv
    import json
    import logging
    import os
    import sys

    import requests
    from rich.live import Live
    from rich.table import Table

    from lib.utils import check_capture_logs
    from lib.utils import configure_logger
    from lib.utils import get_std_progress_bar
    from lib.utils import print_params_debug
    from lib.utils import user_allows_file_overwrite

    configure_logger(verbose=verbose, force=force, record=bool(save_logs))
    check_capture_logs(save_logs, force=force)

    print_params_debug(ctx)

    logger = logging.getLogger("rich")

    # check if overwrite is allowed
    if not user_allows_file_overwrite(output, force):
        sys.exit(1)

    api_url = "https://api.github.com/"

    ## fetch repo list

    logger.info("Fetching repo list...")

    repos_endpoint = f"orgs/{org}/repos"
    headers = {'Authorization': f'token {token}'}

    r = requests.get(os.path.join(api_url, repos_endpoint), headers=headers)
    if r.status_code == 200:

        try:

            repos_json = r.json()

        except json.decoder.JSONDecodeError:

            logger.error("Not a JSON response!")
            logger.error(r.text)
            sys.exit(1)

    elif r.status_code == 401:

        logger.error("Unauthorized. Did you set your token? Is it expired?")
        sys.exit(1)

    else:

        repos_json = None
        logger.error(f"Bad return code: {r.status_code}")
        sys.exit(1)

    repos = []
    for entry in repos_json:
        name = entry.get('name')
        if name:
            repos.append(name)

    logger.info(f"Found {len(repos)} repos.")

    ## fetch issues for each repo

    logger.info("Fetching issues for each repo...")
    progress = get_std_progress_bar()
    progress_table = Table.grid()
    progress_table.add_row(progress)

    issues = [
        [ # header row
            "repo", "issue #", "title", "filer", "assignees", "comments", "created_at",
            "updated_at", "closed_at", "labels", "milestone", "state", "locked", "draft",
        ]
    ]
    with Live(progress_table, refresh_per_second=10):
        for repo in progress.track(repos, description="Fetching Issues"):

            issues_endpoint = f"repos/{org}/{repo}/issues"
            headers = {'Authorization': f'token {token}'}

            r = requests.get(os.path.join(api_url, issues_endpoint), headers=headers)
            if r.status_code == 200:

                try:

                    issues_json = r.json()

                except json.decoder.JSONDecodeError:

                    logger.warning(f"Not a JSON response for repo {repo}!")
                    logger.warning(r.text)
                    continue

            elif r.status_code == 401:

                logger.error("Unauthorized. Did you set your token? Is it expired?")
                sys.exit(1)

            else:

                logger.warning(f"Bad return code for repo {repo}: {r.status_code}")
                continue

            for issue in issues_json:

                def __parse_username(dict_):
                    if dict_ and type(dict_) == dict:
                        return dict_.get("login")
                    return ""

                def __parse_label(dict_):
                    if dict_ and type(dict_) == dict:
                        return dict_.get("name")
                    return ""

                def __parse_milestone(dict_):
                    if dict_ and type(dict_) == dict:
                        return dict_.get("title")
                    return ""

                logger.debug(issue)

                row = [
                    repo, issue.get("number"), issue.get("title"),
                    __parse_username(issue.get("user")),
                    ", ".join([__parse_username(d) for d in issue.get("assignees") or []]),
                    issue.get("comments"), issue.get("created_at"), issue.get("updated_at"),
                    issue.get("closed_at"),
                    ", ".join([__parse_label(d) for d in issue.get("labels") or []]),
                    __parse_milestone(issue.get("milestone")), issue.get("state"),
                    issue.get("locked"), issue.get("draft"),
                ]
                issues.append(row)

    logger.info(f"Found {len(issues)-1} issues.")

    ## collect into spreadsheet

    logger.info("Tabulating...")
    with open(output, "w") as f:
        writer = csv.writer(f)
        for row in issues:
            writer.writerow(row)
    logger.info(f"Spreadsheet saved to {output}")

    ## emit logs

    if save_logs:
        capture_logs(save_logs)


if __name__ == '__main__':

    ## program proper

    cli()
