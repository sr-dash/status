## What this changes

<!-- A short description of the change and why it is needed. Link the issue it addresses, e.g. "Closes #12". -->

## How it was checked

<!-- What you ran and looked at: the collector against your own repositories or against GITHUB_REPOSITORY=someone/copy, the page at phone width and on a wide screen, in light and dark. Screenshots help for visual changes. -->

## Checklist

- [ ] `python collect.py --out site` runs and the page opens with no errors in the browser console
- [ ] A copy still sets itself up: `GITHUB_REPOSITORY=octocat/status python collect.py --out /tmp/copy` gives a page for that owner, with none of `status.config.yml`'s page settings
- [ ] The page reads without JavaScript (the content is in the HTML from `render.py`)
- [ ] It works at phone width and in the light and dark themes; state is shown by a word and a shape, not colour alone
- [ ] New settings or check types are described in the README and in `status.config.yml`
- [ ] I have read the [contributing guidelines](https://github.com/sr-dash/status/blob/main/CONTRIBUTING.md) and the [code of conduct](https://github.com/sr-dash/status/blob/main/CODE_OF_CONDUCT.md)
