# Contributing

Thank you for helping. This status page is meant to work for anyone's repositories with no setup, so reports from other people's copies, new kinds of checks and fixes are all welcome. Everyone taking part is asked to follow the [code of conduct](CODE_OF_CONDUCT.md).

## Ways to help

- **Report something that looks wrong**: a check that says a site is failing when it is fine (or the reverse), a page that does not set itself up in your copy, a layout that breaks. Use the [issue forms](https://github.com/sr-dash/status/issues/new/choose) and include the address of your status page.
- **Suggest a check or a feature** with the feature form: a kind of data feed, a service or a signal a status page should watch.
- **Tell us you use it** with the "I use this" form, or show your page in [Show and tell](https://github.com/sr-dash/status/discussions/categories/show-and-tell).
- **Send a pull request** for a fix or a feature. For anything larger than a small fix, please open an issue first so we can agree on the approach.

Problems with the sites the page watches (HelioField, HelioFleet and the others) belong in those repositories, not here.

## Running it locally

```bash
pip install pyyaml pillow
GITHUB_TOKEN=$(gh auth token) python collect.py --out site     # check, then build the page
python -m http.server 8822 -d site                               # http://localhost:8822
```

To see what a copy of the template would set up for another account:

```bash
GITHUB_REPOSITORY=octocat/status GITHUB_TOKEN=$(gh auth token) python collect.py --out /tmp/copy
```

`python scripts/make_og.py` redraws `web/og.png` from `status.config.yml`.

## Guidelines

- **Keep it working with no setup.** A copy must still set itself up from `GITHUB_REPOSITORY` alone; anything specific to one page belongs in `status.config.yml` or `custom_checks.py`.
- **The page must read without JavaScript.** Everything a reader or a search engine needs is written by `render.py`; `web/app.js` only adds to it (theme, views, filters, live times, refresh).
- **Standard library first.** The checks use `urllib` and the GitHub REST API; the only dependencies are PyYAML and, for the preview image, Pillow.
- **Be gentle with the API.** A run should stay well inside the `GITHUB_TOKEN` limit (1,000 requests an hour); add a request per repository only when it earns its place.
- **Accessible and themed.** State is never shown by colour alone (each chip has a word and a shape), contrast holds in the light and dark themes, controls work from the keyboard, and motion respects reduced-motion settings.
- **Plain language** in the page and in messages: say what is wrong and what to do about it.

## Pull requests

- One change per pull request, with a short description of what and why.
- Run the collector locally, open the page, and check it at phone width and in both themes, with no console errors.
- Commit messages in the imperative, under 72 characters for the first line.

By contributing you agree that your contribution is released under the project's [MIT licence](LICENSE).
