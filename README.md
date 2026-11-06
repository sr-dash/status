# Pipeline status

Status of the sites at [sr-dash.github.io](https://sr-dash.github.io/) and the scheduled pipelines behind them, checked every hour: **https://sr-dash.github.io/status/**

For each repository (HelioField, HelioField imagery, HelioField movies, HelioFleet, CryoNIRSP Viewer, the homepage):

- the site answers;
- its latest GitHub Pages deployment;
- open pull requests (a monthly data update waiting to be merged, say);
- every workflow's latest run, and for scheduled ones, whether a run is overdue;
- how fresh each data feed is: HelioField's daily product, the imagery for the latest day (and panels waiting to be retried), the movies, HelioFleet's ephemerides and observation lists, the Cryo-NIRSP inventory.

**Alerts by email.** A failure, or a warning that holds for three checks in a row, opens an issue labelled `status-alert`, assigned to the owner, so GitHub sends an email. New problems add a comment; when all is clear the issue closes itself with a comment. Emails follow your GitHub notification settings (Settings → Notifications → Email).

`collect.py` gathers the status into `site/status.json` and `site/history.json` (14 days, read back from the published site each hour), `alert.py` manages the issue, and the `Status` workflow runs both and deploys `site/` to GitHub Pages. Add a site by adding it to `REPOS` (and a freshness check to `data_checks`) in `collect.py`.

MIT licence. Made by [Soumyaranjan Dash](https://sr-dash.github.io/).
