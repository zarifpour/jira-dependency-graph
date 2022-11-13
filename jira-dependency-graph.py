#!/usr/bin/env python

from __future__ import print_function

import argparse
import getpass
import os
import sys
import textwrap
from functools import reduce
from typing import Any, Dict, List, Literal, Optional, Tuple

import requests
from requests.models import Response

from schemas.issue_links import IssueLink, IssueRef, Status
from schemas.jira import Issue, IssueFields

GOOGLE_CHART_URL = "https://chart.apis.google.com/chart"
MAX_SUMMARY_LENGTH = 30

FETCHED_ISSUES: Dict[str, Issue] = {}


def log(*args) -> None:
    print(*args, file=sys.stderr)


class JiraSearch(object):

    """This factory will create the actual method used to fetch issues from JIRA. This is really just a closure that
    saves us having to pass a bunch of parameters all over the place all the time."""

    __base_url = None

    def __init__(self, url, auth, no_verify_ssl) -> None:
        self.__base_url = url
        self.url = url + "/rest/api/latest"
        self.auth = auth
        self.no_verify_ssl = no_verify_ssl
        self.fields = ",".join(
            [
                "key",
                "summary",
                "status",
                "description",
                "issuetype",
                "issuelinks",
                "subtasks",
            ]
        )

    def get(self, uri: str, params={}) -> Response:
        headers = {"Content-Type": "application/json"}
        url = self.url + uri

        if isinstance(self.auth, str):
            return requests.get(
                url,
                params=params,
                cookies={"JSESSIONID": self.auth},
                headers=headers,
                verify=self.no_verify_ssl,
            )
        else:
            return requests.get(
                url,
                params=params,
                auth=self.auth,
                headers=headers,
                verify=(not self.no_verify_ssl),
            )

    def get_issue(self, key: str) -> Issue:
        """Given an issue key (i.e. JRA-9) return the JSON representation of it. This is the only place where we deal
        with JIRA's REST API."""
        if key in FETCHED_ISSUES:
            log("Already fetched", key)
            return FETCHED_ISSUES[key]
        log("Fetching " + key)
        # we need to expand subtasks and links since that's what we care about here.
        response = self.get("/issue/%s" % key, params={"fields": self.fields})
        response.raise_for_status()
        ret = Issue.parse_obj(response.json())
        FETCHED_ISSUES[key] = ret
        return ret

    def query(self, query: str) -> Dict[Any, Any]:
        log("Querying " + query)
        response = self.get("/search", params={"jql": query, "fields": self.fields})
        content = response.json()
        return content["issues"]

    def list_ids(self, query: str) -> List[str]:
        log("Querying " + query)
        response = self.get(
            "/search", params={"jql": query, "fields": "key", "maxResults": 100}
        )
        return [issue["key"] for issue in response.json()["issues"]]

    def get_issue_uri(self, issue_key: str) -> str:
        return self.__base_url + "/browse/" + issue_key


def build_graph_data(
    start_issue_key,
    jira,
    excludes: List[str],
    show_directions: List[Literal["inward", "outward"]],
    directions: List[Literal["inward", "outward"]],
    includes,
    issue_excludes: List[str],
    ignore_closed: bool,
    ignore_epic: bool,
    ignore_subtasks: bool,
    traverse: bool,
    word_wrap: bool,
    merge_relates: bool,
):
    """Given a starting image key and the issue-fetching function build up the GraphViz data representing relationships
    between issues. This will consider both subtasks and issue links.
    """

    def get_status_color(status_field: Status) -> str:
        status = status_field.statusCategory.name.upper()
        if status == "IN PROGRESS":
            return "yellow"
        elif status == "DONE":
            return "green"
        return "white"

    def create_node_text(
        issue_key: str, fields: IssueFields, islink: bool = True
    ) -> str:
        summary = fields.summary
        status = fields.status

        if word_wrap == True:
            if len(summary) > MAX_SUMMARY_LENGTH:
                # split the summary into multiple lines adding a \n to each line
                summary = textwrap.fill(fields.summary, MAX_SUMMARY_LENGTH)
        else:
            # truncate long labels with "...", but only if the three dots are replacing more than two characters
            # -- otherwise the truncated label would be taking more space than the original.
            if len(summary) > MAX_SUMMARY_LENGTH + 2:
                summary = fields.summary[:MAX_SUMMARY_LENGTH] + "..."
        summary = summary.replace('"', '\\"')
        # log('node ' + issue_key + ' status = ' + str(status))

        if islink:
            return '"{}\\n({})"'.format(issue_key, summary)
        return '"{}\\n({})" [href="{}", fillcolor="{}", style=filled]'.format(
            issue_key, summary, jira.get_issue_uri(issue_key), get_status_color(status)
        )

    def process_link(
        fields: IssueFields, issue_key: str, link: IssueLink
    ) -> Optional[Tuple[str, Optional[str]]]:
        if link.outwardIssue is None and link.inwardIssue is None:
            return
        if link.outwardIssue is not None:
            direction = "outward"
            link_type = link.type.outward
            linked_issue = link.outwardIssue
        elif link.inwardIssue is not None:
            direction = "inward"
            link_type = link.type.inward
            linked_issue = link.inwardIssue

        if direction not in directions:
            return

        if linked_issue.key in issue_excludes:
            log("Skipping " + linked_issue.key + " - explicitly excluded")
            return

        if ignore_closed and (
            ((link.inwardIssue) and (link.inwardIssue.fields.status.name == "Closed"))
            or (
                (link.outwardIssue)
                and (link.outwardIssue.fields.status.name == "Closed")
            )
        ):
            log("Skipping " + linked_issue.key + " - linked key is Closed")
            return

        if includes not in linked_issue.key:
            return

        if link_type.strip() in excludes:
            return linked_issue.key, None

        arrow = " => " if direction == "outward" else " <= "
        log(issue_key + arrow + link_type + arrow + linked_issue.key)

        extra = ""
        if link_type == "blocks":
            extra = ',color="red"'
        elif link_type == "has to be done before":
            extra = ',color="orange"'
        elif link_type == "relates to" and merge_relates:
            extra = ", dir=both"

        skip_links = [
            "is blocked by",
            "has to be done after",
            "is child of",
            "tests",
            "duplicates",
            "created by",
            "clones",
            "is caused by",
            "split from",
        ]

        if direction not in show_directions or link_type in skip_links:
            node = None
        else:
            # log("Linked issue summary " + linked_issue['fields']['summary'])
            node = '{}->{}[label="{}"{}]'.format(
                create_node_text(issue_key, fields),
                create_node_text(linked_issue.key, linked_issue.fields),
                link_type,
                extra,
            )

        return linked_issue.key, node

    # since the graph can be cyclic we need to prevent infinite recursion
    seen = []

    def walk(issue_key: str, graph: List) -> Issue:
        """issue is the JSON representation of the issue"""
        issue: Issue = jira.get_issue(issue_key)
        children = []
        fields = issue.fields
        seen.append(issue_key)

        if ignore_closed and (fields.status.name == "Closed"):
            log("Skipping " + issue_key + " - it is Closed")
            return graph

        if not traverse and ((project_prefix + "-") not in issue_key):
            log("Skipping " + issue_key + " - not traversing to a different project")
            return graph

        graph.append(create_node_text(issue_key, fields, islink=False))

        if not ignore_subtasks:
            if fields.issuetype.name == "Epic" and not ignore_epic:
                issues: List[Dict[str, Any]] = jira.query(
                    '"Epic Link" = "%s"' % issue_key
                )
                for subtask_dict in issues:
                    subtask = IssueRef.parse_obj(subtask_dict)
                    log(subtask.key + " => references epic => " + issue_key)
                    node = "{}->{}[color=orange]".format(
                        create_node_text(issue_key, fields),
                        create_node_text(subtask.key, subtask.fields),
                    )
                    graph.append(node)
                    children.append(subtask.key)
            if fields.subtasks and not ignore_subtasks:
                for subtask in fields.subtasks:
                    log(issue_key + " => has subtask => " + subtask.key)
                    node: str = '{}->{}[color=blue][label="subtask"]'.format(
                        create_node_text(issue_key, fields),
                        create_node_text(subtask.key, subtask.fields),
                    )
                    graph.append(node)
                    children.append(subtask.key)

        if fields.issuelinks:
            for other_link in fields.issuelinks:
                if merge_relates:
                    remove_duplicate_links(issue_key, other_link, "Relates")
                result = process_link(fields, issue_key, other_link)
                if result is not None:
                    log("Appending " + result[0])
                    children.append(result[0])
                    if result[1] is not None:
                        graph.append(result[1])
        # now construct graph data for all subtasks and links of this issue
        for child in (x for x in children if x not in seen):
            walk(child, graph)
        return graph

    def remove_duplicate_links(
        issue_key: str, other_link: IssueLink, link_type: str
    ) -> None:
        outward_issue = other_link.outwardIssue
        inward_issue = other_link.inwardIssue
        if outward_issue is None and inward_issue is None:
            return
        # log(outward_issue, "\n\n", inward_issue)
        linked_issue_key = (
            outward_issue.key if outward_issue is not None else inward_issue.key
        )
        _ = jira.get_issue(linked_issue_key)
        if FETCHED_ISSUES[linked_issue_key].fields.issuelinks:
            for link in FETCHED_ISSUES[linked_issue_key].fields.issuelinks:
                if link.type.name == link_type and (
                    (link.outwardIssue and link.outwardIssue.key == issue_key)
                    or (link.inwardIssue and link.inwardIssue.key == issue_key)
                ):
                    FETCHED_ISSUES[linked_issue_key].fields.issuelinks.remove(link)

    project_prefix = start_issue_key.split("-", 1)[0]
    return walk(start_issue_key, [])


def create_graph_image(graph_data: List, file_name: str, node_shape: str) -> str:
    """Given a formatted blob of graphviz chart data[1], make the actual request to Google
    and store the resulting image to disk.

    [1]: http://code.google.com/apis/chart/docs/gallery/graphviz.html
    """
    digraph = "digraph{node [shape=" + node_shape + "];%s}" % ";".join(graph_data)

    response = requests.post(GOOGLE_CHART_URL, data={"cht": "gv", "chl": digraph})

    d = os.path.dirname(__file__)
    p = d + "/out/"
    gvp = p + "gv/"
    pngp = p + "png/"

    with open(gvp + file_name + ".gv", "w") as gv:
        print("Writing to " + gvp + file_name + ".gv")
        gv.write(digraph)
        gv.close()

    try:
        with open(pngp + file_name + ".png", "w+b") as image:
            print("Writing to " + pngp + file_name + ".png")
            binary_format = bytearray(response.content)
            image.write(binary_format)
            image.close()
    except Exception as ex:
        log("Failed to create image: " + ex)

    return file_name


def print_graph(graph_data: List, node_shape: str) -> None:
    print(
        "digraph{\nnode [shape=" + node_shape + "];\n\n%s\n}" % ";\n".join(graph_data)
    )


def parse_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u", "--user", dest="user", default=None, help="Username to access JIRA"
    )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        default=None,
        help="Password to access JIRA",
    )
    parser.add_argument(
        "-c",
        "--cookie",
        dest="cookie",
        default=None,
        help="JSESSIONID session cookie value",
    )
    parser.add_argument(
        "-N",
        "--no-auth",
        dest="no_auth",
        action="store_true",
        default=False,
        help="Use no authentication",
    )
    parser.add_argument(
        "-j",
        "--jira",
        dest="jira_url",
        default="http://jira.example.com",
        help="JIRA Base URL (with protocol)",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="image_file",
        default="issue_graph",
        help="Filename to write image to",
    )
    parser.add_argument(
        "-l",
        "--local",
        action="store_true",
        default=False,
        help="Render graphviz code to stdout",
    )
    parser.add_argument(
        "-e",
        "--ignore-epic",
        action="store_true",
        default=False,
        help="Do not follow an Epic into it's child issues",
    )
    parser.add_argument(
        "-x",
        "--exclude-link",
        dest="excludes",
        default=[],
        action="append",
        help="Exclude link type(s)",
    )
    parser.add_argument(
        "-ic",
        "--ignore-closed",
        dest="closed",
        action="store_true",
        default=False,
        help="Ignore closed issues",
    )
    parser.add_argument(
        "-i", "--issue-include", dest="includes", default="", help="Include issue keys"
    )
    parser.add_argument(
        "-xi",
        "--issue-exclude",
        dest="issue_excludes",
        action="append",
        default=[],
        help="Exclude issue keys; can be repeated for multiple issues",
    )
    parser.add_argument(
        "-s",
        "--show-directions",
        dest="show_directions",
        default=["inward", "outward"],
        help="Which directions to show (inward, outward)",
    )
    parser.add_argument(
        "-d",
        "--directions",
        dest="directions",
        default=["inward", "outward"],
        help="Which directions to walk (inward, outward)",
    )
    parser.add_argument(
        "--jql",
        dest="jql_query",
        default=None,
        help="JQL search for issues (e.g. 'project = JRADEV')",
    )
    parser.add_argument(
        "-ns",
        "--node-shape",
        dest="node_shape",
        default="box",
        help="Which shape to use for nodes (circle, box, ellipse, etc...)",
    )
    parser.add_argument(
        "-t",
        "--ignore-subtasks",
        action="store_true",
        default=False,
        help="Ignore sub-tasks issues",
    )
    parser.add_argument(
        "-T",
        "--dont-traverse",
        dest="traverse",
        action="store_false",
        default=True,
        help="Ignore other projects",
    )
    parser.add_argument(
        "-w",
        "--word-wrap",
        dest="word_wrap",
        default=False,
        action="store_true",
        help="Word wrap issue summaries instead of truncating them",
    )
    parser.add_argument(
        "--no-verify-ssl",
        dest="no_verify_ssl",
        default=False,
        action="store_true",
        help="Do not verify SSL certs for requests",
    )
    parser.add_argument(
        "issues", nargs="*", help="The issue key (e.g. JRADEV-1107, JRADEV-1391)"
    )
    parser.add_argument(
        "--no-merge-relates",
        dest="merge_relates",
        default=True,
        action="store_false",
        help="Do not merge 'relates to' edges",
    )
    return parser.parse_args()


def filter_duplicates(lst: List) -> List:
    # Enumerate the List to restore order lately; reduce the sorted List; restore order
    def append_unique(acc, item):
        return acc if acc[-1][1] == item[1] else acc.append(item) or acc

    srt_enum = sorted(enumerate(lst), key=lambda i_val: i_val[1])
    return [item[1] for item in sorted(reduce(append_unique, srt_enum, [srt_enum[0]]))]


def main() -> None:
    options = parse_args()

    if options.cookie is not None:
        # Log in with browser and use --cookie=ABCDEF012345 commandline argument
        auth = options.cookie
    elif options.no_auth is True:
        # Don't use authentication when it's not needed
        auth = None
    else:
        # Basic Auth is usually easier for scripts like this to deal with than Cookies.
        user = options.user if options.user is not None else input("Username: ")
        api_token = (
            options.password
            if options.password is not None
            else getpass.getpass("Password: ")
        )
        auth = (user, api_token)

    jira = JiraSearch(options.jira_url, auth, options.no_verify_ssl)

    if options.jql_query is not None:
        options.issues.extend(jira.list_ids(options.jql_query))

    graph = []
    for issue in options.issues:
        graph = graph + build_graph_data(
            issue,
            jira,
            options.excludes,
            options.show_directions,
            options.directions,
            options.includes,
            options.issue_excludes,
            options.closed,
            options.ignore_epic,
            options.ignore_subtasks,
            options.traverse,
            options.word_wrap,
            options.merge_relates,
        )

    if options.local:
        print_graph(filter_duplicates(graph), options.node_shape)
    else:
        create_graph_image(
            filter_duplicates(graph),
            options.image_file
            if options.image_file != "issue_graph"
            else "+".join(options.issues),
            options.node_shape,
        )


if __name__ == "__main__":
    main()
