# Deploying the Wayside site

The site is a single static page (`index.html` plus `assets/`). It makes zero
external requests, so any static host serves it perfectly. Two free options
below — both take minutes and cost nothing.

## Option A — GitHub Pages (permanent, free, tied to this repo)

1. Push this repository to GitHub (the `site/` folder must be on the branch
   you deploy from, e.g. `main`).
2. On GitHub, open the repository → **Settings** → **Pages**.
3. Under **Build and deployment**:
   - **Source**: "Deploy from a branch"
   - **Branch**: `main`, **Folder**: `/site` — if `/site` is not offered in
     the folder dropdown (GitHub only lists `/ (root)` and `/docs`), either:
     - rename the folder from `site/` to `docs/` and select `/docs`, or
     - use the small workflow in the note below.
4. Click **Save**. Within a minute or two the site is live at
   `https://<your-username>.github.io/<repo-name>/`.
5. Any later push to the branch redeploys automatically.

**Note — deploying `/site` without renaming it:** create
`.github/workflows/pages.yml` containing the standard
[`actions/deploy-pages`](https://github.com/actions/deploy-pages) flow with
`actions/upload-pages-artifact` pointed at `path: site`, and set
**Settings → Pages → Source** to "GitHub Actions". This keeps the folder
name and deploys on every push.

## Option B — Netlify Drop (the 2-minute alternative, no account required to try)

1. Open <https://app.netlify.com/drop> in a browser.
2. Drag the entire `site/` folder from your file manager onto the page.
3. Netlify uploads it and gives you a live URL immediately
   (something like `https://random-name-123abc.netlify.app`).
4. To keep the site longer than the anonymous 1-hour window, claim it with a
   free Netlify account, where you can also rename the subdomain
   (e.g. `wayside.netlify.app` if available).

## Buying a proper domain later

When the pilot is ready for a public face, buy a domain (for example
`wayside.org.in`, `waysideaid.org`, or similar) from any registrar —
Cloudflare Registrar and Porkbun sell at cost, typically £8–12 / ₹800–1,200
per year for a `.org` or `.in`.

- **GitHub Pages**: add the domain under **Settings → Pages → Custom domain**,
  then create a `CNAME` record at your registrar pointing to
  `<your-username>.github.io`. GitHub provisions HTTPS automatically.
- **Netlify**: **Site settings → Domain management → Add custom domain**, then
  follow the DNS instructions shown. HTTPS is automatic here too.

Nothing in the page itself needs to change for a custom domain — all asset
paths are relative.
