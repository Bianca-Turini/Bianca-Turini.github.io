# Bianca Turini — personal research website

Plain HTML/CSS site, no build step. Served with GitHub Pages.

- `index.html` — all content (about, news, publications, talks, education, expertise, service)
- `style.css` — design (light by default, dark-mode toggle in the top bar)
- `assets/` — photos, video, favicon and the CV PDF

## Updating

1. Edit `index.html` and preview it by opening the file in a browser.
2. Regenerate the CV from the website content: `python3 tools/build_cv.py`
   (needs `beautifulsoup4` and Google Chrome).
3. Commit and push — GitHub Pages republishes automatically.

The favicon is drawn by `tools/make_favicon.py`.
