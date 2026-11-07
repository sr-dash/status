# GitHub status page

[![Pipeline status](https://sr-dash.github.io/status/badge.svg)](https://sr-dash.github.io/status/)
[![Status workflow](https://github.com/sr-dash/status/actions/workflows/status.yml/badge.svg)](https://github.com/sr-dash/status/actions/workflows/status.yml)
[![Use this template](https://img.shields.io/badge/use%20this-template-2ea44f?logo=github)](https://github.com/sr-dash/status/generate)
[![MIT licence](https://img.shields.io/badge/licence-MIT-1f4e87)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/sr-dash/status?style=social)](https://github.com/sr-dash/status/stargazers)
[![Using it? Tell me](https://img.shields.io/badge/using%20it%3F-tell%20me-2ea44f)](https://github.com/sr-dash/status/issues/new?template=i_use_this.yml)

A status page for your GitHub repositories and the sites they publish, rebuilt every hour by GitHub Actions and served by GitHub Pages, with email alerts through a GitHub issue. No server, no database, no external service, and no setup beyond turning on Pages.

**Live example:** https://sr-dash.github.io/status/

| Site | Status |
|---|---|
| [HelioField](https://sr-dash.github.io/heliofield/) | [![HelioField status](https://sr-dash.github.io/status/badges/heliofield.svg)](https://sr-dash.github.io/status/#heliofield) |
| [HelioField imagery](https://github.com/sr-dash/heliofield-imagery) | [![HelioField imagery status](https://sr-dash.github.io/status/badges/heliofield-imagery.svg)](https://sr-dash.github.io/status/#heliofield-imagery) |
| [HelioField movies](https://sr-dash.github.io/heliofield-movies/) | [![HelioField movies status](https://sr-dash.github.io/status/badges/heliofield-movies.svg)](https://sr-dash.github.io/status/#heliofield-movies) |
| [HelioFleet](https://sr-dash.github.io/heliofleet/) | [![HelioFleet status](https://sr-dash.github.io/status/badges/heliofleet.svg)](https://sr-dash.github.io/status/#heliofleet) |
| [CryoNIRSP Viewer](https://sr-dash.github.io/cryonirsp-viewer/) | [![CryoNIRSP Viewer status](https://sr-dash.github.io/status/badges/cryonirsp-viewer.svg)](https://sr-dash.github.io/status/#cryonirsp-viewer) |
| [Homepage](https://sr-dash.github.io/) | [![Homepage status](https://sr-dash.github.io/status/badges/sr-dash.github.io.svg)](https://sr-dash.github.io/status/#sr-dash.github.io) |

> [!TIP]
> **Using this template?** Please [star the repository](https://github.com/sr-dash/status/stargazers): it is the only way I can tell who finds it useful. Better still, [say what you use it for](https://github.com/sr-dash/status/issues/new?template=i_use_this.yml), or show your page in [Show and tell](https://github.com/sr-dash/status/discussions/categories/show-and-tell).

## How it compares

Status pages that, like this one, run on GitHub alone (Actions do the checking, Pages serves the page). Most watch whether URLs answer; this one watches the pipelines behind your sites: deployments, every workflow's runs and schedule, pull requests and how fresh your data is, and it sets itself up in a copy.

<!-- directory:start -->
| | How it runs | What it watches | |
|---|---|---|---|
| **[sr-dash/status](https://github.com/sr-dash/status)** (this one) | Python in Actions, a static page on Pages; alerts through an issue | Sites, Pages deployments, every workflow's runs and schedule, pull requests, data freshness | ![Stars](https://img.shields.io/github/stars/sr-dash/status?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/sr-dash/status?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://sr-dash.github.io/status/&label=live&up_message=up&down_message=down&style=flat)](https://sr-dash.github.io/status/) |
| **[Upptime](https://github.com/upptime/upptime)** | Actions on a schedule, a Svelte page on Pages, issues for incidents | URL uptime and response time | ![Stars](https://img.shields.io/github/stars/upptime/upptime?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/upptime/upptime?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://demo.upptime.js.org&label=live&up_message=up&down_message=down&style=flat)](https://demo.upptime.js.org) |
| **[cState](https://github.com/cstate/cstate)** | Hugo static site on Pages or Netlify; incidents as Markdown files | Incidents you write | ![Stars](https://img.shields.io/github/stars/cstate/cstate?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/cstate/cstate?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://cstate.mnts.lt&label=live&up_message=up&down_message=down&style=flat)](https://cstate.mnts.lt) |
| **[Statsig status page](https://github.com/statsig-io/statuspage)** | Plain HTML and JavaScript on Pages, a shell script in Actions | URL uptime | ![Stars](https://img.shields.io/github/stars/statsig-io/statuspage?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/statsig-io/statuspage?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://status.statsig.com&label=live&up_message=up&down_message=down&style=flat)](https://status.statsig.com) |
| **[Static status](https://github.com/Cyclenerd/static_status)** | A Bash script that writes a static page | Hosts, ports and URLs | ![Stars](https://img.shields.io/github/stars/Cyclenerd/static_status?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/Cyclenerd/static_status?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://cyclenerd.github.io/static_status/&label=live&up_message=up&down_message=down&style=flat)](https://cyclenerd.github.io/static_status/) |
| **[tinystatus](https://github.com/bderenzo/tinystatus)** | A small shell script that writes a static page | Hosts, ports and URLs | ![Stars](https://img.shields.io/github/stars/bderenzo/tinystatus?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/bderenzo/tinystatus?style=flat&label=updated) |
| **[Issue Status](https://github.com/tadhglewis/issue-status)** | A React page that reads incidents from GitHub issues | Incidents and components you write | ![Stars](https://img.shields.io/github/stars/tadhglewis/issue-status?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/tadhglewis/issue-status?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://tadhglewis.github.io/issue-status&label=live&up_message=up&down_message=down&style=flat)](https://tadhglewis.github.io/issue-status) |
| **[Fettle](https://github.com/mehatab/fettle)** | Actions, Pages and issues for incidents | URL uptime | ![Stars](https://img.shields.io/github/stars/mehatab/fettle?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/mehatab/fettle?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://fettle.mehatab.info&label=live&up_message=up&down_message=down&style=flat)](https://fettle.mehatab.info) |
| **[ClearStatus](https://github.com/weeblrpress/clearstatus)** | Hugo static site on Netlify; events from a Git repository | Incidents you write | ![Stars](https://img.shields.io/github/stars/weeblrpress/clearstatus?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/weeblrpress/clearstatus?style=flat&label=updated) |
| **[GitHub Status Page](https://github.com/Bullrich/Status-Page)** | Actions for the metrics, issues for incidents, Pages for the page | URL uptime | ![Stars](https://img.shields.io/github/stars/Bullrich/Status-Page?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/Bullrich/Status-Page?style=flat&label=updated) [![Live page](https://img.shields.io/website?url=https://bullrich.dev/Status-Page/&label=live&up_message=up&down_message=down&style=flat)](https://bullrich.dev/Status-Page/) |
<!-- directory:end -->

More, including serverless and self-hosted status pages and the status pages of services research software depends on, in **[DIRECTORY.md](DIRECTORY.md)** and on the [directory page](https://sr-dash.github.io/status/directory/), where every live page is checked each hour. Know one that is missing? [Suggest it](https://github.com/sr-dash/status/issues/new?template=directory.yml).

## What it checks

For each repository:

- **Site**: the page answers, and how fast (a 14-day response-time line).
- **Deploy**: the latest GitHub Pages deployment.
- **Pull requests**: open ones, flagged after two days (a data update waiting to be merged, say).
- **Workflows**: every workflow's latest run; for scheduled ones, whether a run is overdue, read from the workflow's own `cron` lines.
- **Data**: how fresh your published data is, from a timestamp in a JSON file, or any check you write in Python.

The page is complete HTML from the build, so search engines index it and it reads without JavaScript. In the browser it adds a ring of check states, a 14-day problems chart, per-site history strips and response-time lines with tooltips, detailed and compact views, filters, search, keyboard shortcuts (`?` lists them), light and dark themes, a countdown to the next check, and refreshing in place with a notice when a site changes state. It carries a description, canonical link, Open Graph and Twitter cards, structured data (schema.org), a sitemap, status badges (`badge.svg`, `badges/<repo>.svg`) and, if you want, Google Analytics.

## Use it for your own repositories

**With no setup.** Make your copy, turn on Pages, run it once:

1. **[Use this template](https://github.com/sr-dash/status/generate)** to make your own copy (public, so Pages is free).
2. Settings → Pages → Source: **GitHub Actions**.
3. Actions → **Status** → **Run workflow**. It then runs every hour.

Your copy sets itself up: it sees it is not `sr-dash/status`, sets the settings here aside, and watches your account's repositories that have a GitHub Pages site or were pushed to in the last 60 days, at `https://<you>.github.io/<copy>/`, with a preview image drawn for you. Alerts go to you.

**Your own way.** Edit `status.config.yml`: set `for_repository` to your copy (`you/status`), then your page title, description, URL and analytics ID, and the repositories to watch, each with `repo`, its site `url`, an `about` line and any data checks. With `repos: auto` your page settings stay and the list of repositories is still found for you. `python scripts/make_og.py` remakes the preview image from your settings.

Public repositories need no token. To watch private ones, add a fine-grained token with read access to their Actions, Deployments, Contents and Pull requests as the secret **`STATUS_TOKEN`**.

### Data checks

```yaml
repos:
  - repo: my-site
    url: https://me.github.io/my-site/
    about: What the site is, in a line.
    checks:
      - type: json_age            # a timestamp or date in a JSON file is fresh enough
        label: Daily data
        url: https://me.github.io/my-site/data/index.json
        path: dates[-1]           # dotted path, list indices allowed
        warn_hours: 30
        fail_hours: 54
      - type: json_due            # a "next update" time has not long passed
        label: Monthly catalogue
        url: https://me.github.io/my-site/manifest.json
        path: next_update
        made_path: generated      # optional: when it was made
        warn_hours: 48
        fail_hours: 168
      - type: custom              # a function of yours in custom_checks.py
        function: my_check
```

A custom check receives a context with helpers (`check`, `age_check`, `jget`, `parse`, `hours`, `now`, and `shared` for passing values between checks) and returns one check or a list. `custom_checks.py` holds this page's own checks for HelioField; replace them with yours.

### Alerts by email

A failure alerts at once; a warning when it lasts `warn_after_checks` checks in a row (3 by default), so a brief delay does not. While anything is wrong, one issue labelled `status-alert` stays open in your copy, assigned to `alerts.assignee` (you, when set up automatically): it opens with the list, each new problem adds a comment, and it closes itself with a comment when all is clear. GitHub emails you each time, following your notification settings (Settings → Notifications; "Participating" covers issues assigned to you). Set `alerts.enabled: false` to turn them off.

### Status badges

Each build writes `badge.svg` (the whole page) and `badges/<repo>.svg` (one site), coloured by the latest check. Put one in a README:

```markdown
[![Status](https://<you>.github.io/<copy>/badges/<repo>.svg)](https://<you>.github.io/<copy>/#<repo>)
```

The page's **Copy badge** buttons give you this, filled in.

## How it fits together

| File | What it does |
|---|---|
| `status.config.yml` | Everything specific to a page and its repositories |
| `collect.py` | Sets itself up in a copy; runs the checks; writes `site/status.json` and `site/history.json` (14 days, read back from the published page each hour) |
| `custom_checks.py` | Checks of your own |
| `render.py` | Writes the page (`site/index.html`), badges, sitemap and assets from `web/` |
| `web/` | `template.html`, `style.css`, `app.js`, `og.png` |
| `scripts/make_og.py` | The link-preview image |
| `alert.py` | Opens, updates or closes the alert issue |
| `.github/workflows/status.yml` | Every hour: check, build, alert, deploy to Pages |

Run it locally: `pip install pyyaml pillow && GITHUB_TOKEN=$(gh auth token) python collect.py --out site`, then serve `site/` (for example `python -m http.server -d site`). Set `GITHUB_REPOSITORY=you/copy` to see what a copy would set up.

## Contributing

Ideas, new check types and fixes are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md) and the [security policy](SECURITY.md).

MIT licence. Made by [Soumyaranjan Dash](https://sr-dash.github.io/).
