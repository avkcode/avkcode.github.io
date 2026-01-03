# avkcode blog

Simple, functional personal blog (Jekyll + GitHub Pages).

## Local preview

```sh
bundle install
bundle exec jekyll serve --livereload
```

## Writing posts

Create a file in `_posts/` named `YYYY-MM-DD-title.md` with front matter:

```yaml
---
layout: post
title: "Your title"
date: 2026-01-03 12:00:00 -0800
tags: [politics, life]
---
```

