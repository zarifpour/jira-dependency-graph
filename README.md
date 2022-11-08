# jira-dependency-graph

Graph visualizer for dependencies between JIRA tickets (with subtasks and issue links).

* Uses JIRA rest API v2 for fetching information on issues.
* Uses [Google Chart API](https://developers.google.com/chart/) for graphical presentation.

<details>
  <summary>Requirements</summary>

* Python 2.7+ or Python 3+
* [requests](http://docs.python-requests.org/en/master/)

</details>

## Prerequisites

Create an API token from your Atlassian account:

1. Log in to <https://id.atlassian.com/manage-profile/security/api-tokens>.

2. Click Create API token.

3. From the dialog that appears, enter a memorable and concise Label for your token and click Create.

4. Click Copy to clipboard, then paste the token to your script, or elsewhere to save.

Refer to [Atlassian support](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) for more information.

## Usage

```shell
git clone https://github.com/zarifpour/jira-dependency-graph.git
cd jira-dependency-graph
poetry install
poetry shell
python jira-dependency-graph.py --user=<JIRA_EMAIL> --password=<JIRA_API_KEY> --jira=https://<YOUR_ORGANIZATION>.atlassian.net <JIRA_ISSUE_KEY>
```

> **Note**
>
> * Graphs are saved to `/out/gv/` (.gv) and `/out/png/` (.png)
> * If a filename is not specified, by default, the issue name(s) are used
> * Multiple issue-keys can be passed separated with spaces, i.e. `...atlassian.net JIRA-8 JIRA-11`

<details>
  <summary>Examples</summary>

```shell
python jira-dependency-graph.py --user=daniel.zarifpour@simbachain.com --password=A11P22I33K44E55Y --jira=https://simbachain.atlassian.net BLK-899

Fetching BLK-899
BLK-899 <= is blocked by <= BLK-3853
BLK-899 <= is blocked by <= BLK-3968
BLK-899 <= is blocked by <= BLK-3126
BLK-899 <= is blocked by <= BLK-2977
Fetching BLK-3853
BLK-3853 => blocks => BLK-899
BLK-3853 <= relates to <= BLK-3968
Fetching BLK-3968
BLK-3968 => blocks => BLK-899
BLK-3968 => relates to => BLK-3853
Fetching BLK-3126
BLK-3126 => blocks => BLK-899
BLK-3126 => testing discovered => BLK-3571
Fetching BLK-3571
BLK-3571 <= discovered while testing <= BLK-3126
Fetching BLK-2977
BLK-2977 => blocks => BLK-899

Writing to /path/to/jira-dependency-graph/out/gv/BLK-899.gv
Writing to /path/to/jira-dependency-graph/out/png/BLK-899.png
```

---

![Example graph](examples/issue_graph_complex.png)

</details>

## Useful flags

| Description       | Flag                      | Example     | Notes       |
| -----------       | -----------               | ----------- | ----------- |
| Exclude link      | `--exclude-link`          | `... JIRA-8 --exclude-link "blocks"` | Can be repeated to exclude multiple links - useful to ignore bi-directional edges.     |
| Ignore Epic       | `--ignore-epic`           | `... --ignore-epic JIRA-8` | Do not walk into issues of an Epic.  |
| Filter by issue prefix  | `--issue-include`   | `... JIRA-8 --issue-include BLK`  | Only display issues with specified prefix, in this example the prefix is "BLK". |
| Exclude issue(s)  | `--issue-exclude` / `-xi` | `... JIRA-8 --issue-exclude JIRA-2` | Can be repeated to exclude multiple issues. Use as last-resort when other exclusions not suitable.  |
| Use JQL           | `--jql` | `... --jql 'project = Blockchain'` | Instead of passing issue-keys, a Jira Query Language command can be passed
| Ignore closed     | `--ignore-closed`         | `... JIRA-8 --ignore-closed` | Ignore all tickets that are closed. |
| No merge relates to  | `--no-merge-relates`      | `... JIRA-8 --no-merge-relates` | Do not merge edges of related issues. |

> **Note**
> `...` is equivalent to `python jira-dependency-graph.py --user=<JIRA_EMAIL> --password=<JIRA_API_KEY> --jira=https://<YOUR_ORGANIZATION>.atlassian.net`

## Notes

This is a fork of [pawelrychlik/jira-dependency-graph](https://github.com/pawelrychlik/jira-dependency-graph), please refer to that repository for complete documentation. The old repo does not indicate that you must use your API key instead of your password to authenticate and enables duplicated relationships by default (i.e. nodes that are connected may have the relationship "blocks" and "is blocked by" pointing to each other). You may use that repo and exclude specific links, but this repo excludes some of them by default.
