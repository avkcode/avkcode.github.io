# avkcode blog

Simple, functional personal blog (Jekyll + GitHub Pages).

## Local preview

GitHub Pages builds the site for you. For local preview you’ll need a modern Ruby + Bundler (recommended via `rbenv`).

```sh
bundle install
bundle exec jekyll serve --livereload
```

If Ruby/Bundler is a hassle, you can also preview with Docker:

```sh
docker run --rm -it -p 4000:4000 -v "$PWD":/srv/jekyll jekyll/jekyll jekyll serve --livereload --host 0.0.0.0
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
