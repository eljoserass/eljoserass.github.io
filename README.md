# eljoserass.github.io

Built with [Zola](https://www.getzola.org). Push to `master` and the GitHub Action deploys it.

## Writing

Drop a `.md` file into `content/notes/` or `content/things/`. That's it: no front matter needed.

- **title**: the first `# heading`, otherwise the file name
- **date**: the date the file was first committed; set `date: 2025-01-31` to override it
- **math**: `$inline$` and `$$display$$` work like in Obsidian
- **links**: `[[other note]]`, `[[other note|text]]`, `![[image.png]]` (images can live next to the note or in `static/`)

Optional front matter (Obsidian properties work):

```yaml
---
tags: [robots, neuromorphic]
date: 2025-01-31
draft: true        # or `publish: false`: not published
link: /neuron.html # the list links here instead of to the page
---
```

A new folder becomes a new section: copy `content/notes/_index.md` into it.

## Preview locally

Needs `zola` and `pip install pyyaml`.

```
make serve   # http://127.0.0.1:1111, re-run after editing notes
make build   # outputs ./public
```

`scripts/prepare.py` copies the site to `.build/` and fills in what Zola needs. Your notes are never modified.
