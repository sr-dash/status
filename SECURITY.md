# Security policy

This status page is a static site built by a GitHub Actions workflow. Every hour the workflow reads public information through the GitHub REST API (workflow runs, Pages deployments, pull requests) and fetches the watched sites and data files, then publishes HTML, JSON and SVG files to GitHub Pages and opens, updates or closes an alert issue. There is no server, no user account and no stored personal data.

## Supported versions

Only the current `main` branch receives fixes. Copies made from the template take fixes by pulling them in from this repository.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through GitHub instead: open the repository's [Security tab](https://github.com/sr-dash/status/security) and choose **Report a vulnerability** (or go straight to the [reporting form](https://github.com/sr-dash/status/security/advisories/new)). Only the maintainer can see the report, and the fix can be discussed and prepared there in private. If you cannot use GitHub, write to the maintainer, Soumyaranjan Dash, at <sdash@nso.edu>.

Please include what the problem is and where (a script, the workflow, the page), how to reproduce it, and what an attacker could do with it, if you know. You should receive a reply within a week. Once the problem is confirmed, a fix will be published as soon as practical, and you will be credited unless you prefer otherwise.

## What is in scope

- Text from the watched repositories or data files (repository descriptions, workflow and pull-request titles, JSON values) reaching the page or the alert issue without being escaped.
- The workflow's permissions and tokens: `GITHUB_TOKEN` is limited to reading Actions, deployments and pull requests, writing issues and deploying Pages; `STATUS_TOKEN`, if you add one, should be a fine-grained, read-only token.
- The page's script (`web/app.js`), including how it fetches and swaps in a newer page.

## Out of scope

- Problems in the sites the page watches; report those to their own repositories.
- Rate limits, outages or slowness of GitHub or of the watched sites.
