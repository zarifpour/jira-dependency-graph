# jira-dependency-graph

Graph visualizer for dependencies between JIRA tickets (with subtasks and issue links).

* Uses JIRA rest API v2 for fetching information on issues.
* Uses [Google Chart API](https://developers.google.com/chart/) for graphical presentation.

![Example graph](examples/issue_graph_new.svg)

<details>
  <summary>Requirements</summary>

* Python 2.7+ or Python 3+
* [poetry](https://github.com/python-poetry/poetry) (recommended)
* [requests](https://github.com/psf/requests)
* ...

</details>

## Prerequisites

Create an API token from your Atlassian account:

1. Log in to <https://id.atlassian.com/manage-profile/security/api-tokens>.

2. Click **Create API token**.

3. From the dialog that appears, enter a memorable and concise **Label** for your token and click **Create**.

4. Click **Copy to clipboard**, then paste the token to your script, or elsewhere to save.

Refer to [Atlassian support](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) for more information.

## Usage

```shell
git clone https://github.com/zarifpour/jira-dependency-graph.git
cd jira-dependency-graph
poetry install
poetry shell
python jira-dependency-graph.py --user=<JIRA_EMAIL> --password=<JIRA_API_KEY> --jira=https://<YOUR_ORGANIZATION>.atlassian.net <JIRA_ISSUE_KEY> --show-directions outward
```

> [!Note]
>
> * Graphs are saved to `/out/gv/` (.gv) and `/out/png/` (.png)
> * If a filename is not specified, by default, the issue name(s) are used
> * Multiple issue-keys can be passed separated with spaces, i.e. `...atlassian.net JIRA-8 JIRA-11`

<details>
  <summary>Examples</summary>

```shell
python jira-dependency-graph.py --user=daniel.zarifpour@simbachain.com --password=A11P22I33K44E55Y --jira=https://simbachain.atlassian.net JIRA-899

🐕 Fetching issues.../

Graphs written to:

 - /path/to/jira_tree/out/gv/JIRA-899.gv
 - /path/to/jira_tree/out/png/JIRA-899.png

🎉 Woohoo, it's done!       %
```

---

![Example graph](examples/issue_graph_new.svg)

</details>

## Useful flags

| Description       | Flag                      | Example     | Notes       |
| -----------       | -----------               | ----------- | ----------- |
| Show directions      | `--show-directions`          | `... JIRA-8 --show-directions outward` | Only display outward/inward links. **Useful to avoid cycles (recommended)**.     |
| Exclude link      | `--exclude-link`          | `... JIRA-8 --exclude-link "blocks"` | Exclude specified links, repeatable for multiple links. Useful to ignore bi-directional edges.     |
| Ignore Epic       | `--ignore-epic`           | `... --ignore-epic JIRA-8` | Skip issues in an Epic.  |
| Filter by issue prefix  | `--issue-include`   | `... JIRA-8 --issue-include BLK`  | Display issues with a specific prefix. In this example the prefix is "BLK". |
| Exclude issue(s)  | `--issue-exclude` / `-xi` | `... JIRA-8 --issue-exclude JIRA-2` | Exclude specific issues, repeatable. Use as last-resort when other exclusions not suitable.  |
| Use JQL           | `--jql` | `... --jql 'project = Blockchain'` | Use Jira Query Language command instead of issue-keys.
| Ignore closed     | `--ignore-closed`         | `... JIRA-8 --ignore-closed` |  Ignore closed tickets. |
| No merge "relates to"  | `--no-merge-relates`      | `... JIRA-8 --no-merge-relates` | Avoid merging related issue edges (creates cycles). |
| PNG only  | `--png`      | `... JIRA-8 --png` | Save graph as ".png" only (Google API). |
| Graphviz only  | `--gv`      | `... JIRA-8 --gv` | Save graph as ".gv" only (does not hit Google API). |
| Filename               | `--file`                  | `... JIRA-8 --file=graphimg`         | Specify a custom file name for saving output. If not used, output is saved as a concatenated list of JIRA issue keys, which may cause errors if the list is too long. |

> **Note**
> `...` is equivalent to `python jira-dependency-graph.py --user=<JIRA_EMAIL> --password=<JIRA_API_KEY> --jira=https://<YOUR_ORGANIZATION>.atlassian.net`

## Contributing

To make this tool even more awesome, consider some of the following when contributing.

### Schemas

Schemas makes data much easier to consume... To add a schema from the [JIRA API](https://docs.atlassian.com/software/jira/docs/api/REST/9.3.1/#api/2/):

1. Copy-paste one of the [JIRA json schemas](https://docs.atlassian.com/software/jira/docs/api/REST/9.3.1/#api/2/issue-getIssue) into `schemas/json/<SCHEMA>.json`.
2. Autogenerate the pydantic schemas with the [datamodel-codegen](https://github.com/koxudaxi/datamodel-code-generator) tool (see code sample below).
3. Replace `constr(...)` - in most cases - with `Any` from the typing package.
4. Try fetching and processing some data from the API and update the schemas as you learn more about them.

```shell
datamodel-codegen  --input schemas/json/<SCHEMA>.json --input-file-type jsonschema --output schemas/<SCHEMA>.py
```

### Pre-commit

The [pre-commit](https://pre-commit.com/) ensures code quality. Several checks are done upon each commit, including:

* [black](https://github.com/psf/black)
* [mypy](https://github.com/python/mypy)
* [flake8](https://github.com/PyCQA/flake8)
* [isort](https://github.com/PyCQA/isort)
* [conventional-commit](https://github.com/nebbles/gitcommit)

If these requirements are not satisfied, you will not be able to commit.

Alternatively, if the pre-commit checks are interrupting your workflow, use the following command:

```shell
git commit . -m '<COMMIT_MSG>' --no-verify
```

#### Conventional Commit

The [pre-commit](https://pre-commit.com/) enforces the [Conventional Commits](https://www.conventionalcommits.org/) standard for git commit messages. This is a lightweight convention that creates an explicit commit history, which makes it easier to write automated tools on top of.

To use the commit CLI run the command:

```sh
gitcommit
```

If you are using VS Code the extension [Commitizen Support](https://github.com/KnisterPeter/vscode-commitizen.git) streamlines this process.

## Notes

This is a fork of [pawelrychlik/jira-dependency-graph](https://github.com/pawelrychlik/jira-dependency-graph), please refer to that repository for complete documentation (some features may be deprecated). The old repo's method of authentication (using a password) has been deprecated and you must now use your API key instead. It also enables duplicated relationships by default (i.e. nodes that are connected may have the relationship "blocks" and "is blocked by" pointing to each other). You may continue to use that repo and exclude these types of duplicated links - this repo excludes some of them by default.

### Changes

* Documented auth (API Key)
* Opinionated exclusion of duplicate edges
* Added poetry for simplified virtual environment management
* Added pydantic schemas for clearer data parsing and validation
* Added mypy typing to verify soundness of types
* Added other code quality stuff...
* Added support for Epics in team-managed projects
* Added bearer token
* Added storage of gv files without using google api
* Fixed Dockerfile

### Contributors

<details>
  <summary>
    Everyone from <a href="https://github.com/pawelrychlik/jira-dependency-graph" target="_blank">pawelrychlik/jira-dependency-graph</a>
  </summary>
  <ul>
    <li>Thank you 🌈</li>
  </ul>
</details>

<details>
  <summary>
    Changes by <a href="https://github.com/jlinkohr" target="_blank">jlinkohr</a>
  </summary>
  <ul>
    <li>Added bearer token</li>
    <li>Added storage of gv files without using google api</li>
    <li>Fixed Dockerfile</li>
  </ul>
</details>

<details>
  <summary>
    Changes by <a href="https://github.com/svscorp" target="_blank">svscorp</a>
  </summary>
  <ul>
    <li>Improve compatibility with Python versions</li>
  </ul>
</details>

---

<a href = "https://github.com/zarifpour/jira-dependency-graph/graphs/contributors">
  <img src = "https://contrib.rocks/image?repo=zarifpour/jira-dependency-graph"/>
</a>
