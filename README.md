# GitHub status page

A status page for your GitHub repositories and the sites they publish, rebuilt every hour by GitHub Actions and served by GitHub Pages, with email alerts through a GitHub issue. No server, no database, no external service.

**Live example:** https://sr-dash.github.io/status/

What it checks, for each repository you list:

- **Site**: the page answers, and how fast.
- **Deploy**: the latest GitHub Pages deployment.
- **Pull requests**: open ones, flagged after two days (a data update waiting to be merged, say).
- **Workflows**: every workflow's latest run; for scheduled ones, whether a run is overdue, read from the workflow's own `cron` lines.
- **Data**: how fresh your published data is, from a timestamp in a JSON file, or any check you write in Python.

The page is complete HTML from the build, so search engines index it and it reads without JavaScript. In the browser it adds light and dark themes, filters, search, live times, a countdown to the next check, foldable panels, a 14-day history strip per site with tooltips, and refreshing in place. It carries a description, canonical link, Open Graph and Twitter cards, structured data (schema.org), a sitemap and, if you want, Google Analytics.

## Use it for your own repositories

1. **Use this template** (top of the page) to make your own copy, public or private.
2. Edit **`status.config.yml`**: your page title, description and URL, then the repositories to watch. Each needs `repo` and, if it has a site, `url`; add data checks as you like (below).
3. Turn on **GitHub Pages**: Settings → Pages → Source: **GitHub Actions**.
4. Run the **Status** workflow once from the Actions tab (it then runs every hour), and open `https://<you>.github.io/<repo>/`.
5. Optional: `python scripts/make_og.py` remakes the link-preview image (`web/og.png`) from your config.

Public repositories need no token. To watch private ones, add a fine-grained token with read access to their Actions, Deployments, Contents and Pull requests as the secret **`STATUS_TOKEN`**.

### Data checks

```yaml
repos:
  - repo: my-site
    url: https://me.github.io/my-site/
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

A custom check receives a context with helpers (`check`, `age_check`, `jget`, `parse`, `hours`, `now`, and `shared` for passing values between checks) and returns one check or a list. `custom_checks.py` here holds this page's own checks for HelioField; replace them with yours.

### Alerts by email

A failure alerts at once; a warning when it lasts `warn_after_checks` checks in a row (3 by default), so a brief delay does not. While anything is wrong, one issue labelled `status-alert` stays open in this repository, assigned to `alerts.assignee`: it opens with the list, each new problem adds a comment, and it closes itself with a comment when all is clear. GitHub emails you each time, following your notification settings (Settings → Notifications; "Participating" covers issues assigned to you). Set `alerts.enabled: false` to turn alerts off.

## How it fits together

| File | What it does |
|---|---|
| `status.config.yml` | Everything specific to your page and repositories |
| `collect.py` | Runs the checks; writes `site/status.json` and `site/history.json` (14 days, read back from the published page each hour) |
| `custom_checks.py` | Your own checks |
| `render.py` | Writes the page (`site/index.html`), sitemap and assets from `web/` |
| `web/` | `template.html`, `style.css`, `app.js`, `og.png` |
| `alert.py` | Opens, updates or closes the alert issue |
| `.github/workflows/status.yml` | Every hour: check, build, alert, deploy to Pages |

Run it locally: `pip install pyyaml && GITHUB_TOKEN=$(gh auth token) python collect.py --out site`, then serve `site/`.

MIT licence. Made by [Soumyaranjan Dash](https://sr-dash.github.io/).
