# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Tênis Ideal** — a Brazilian (pt-BR) affiliate-marketing site that recommends running shoes ("tênis") via a quiz and earns commission on outbound store links (Amazon Associates, Netshoes, Awin). It is a **static site with no build step**, plus a set of standalone Python automation scripts run on a schedule by GitHub Actions. Almost all user-facing text, commit messages, and docs are in Portuguese — match that when editing.

## Architecture: the data pipeline is the core

The single source of truth for shoe data is a **Google Sheet** (`SHEET_ID = 1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y`, tab "Catálogo"), *not* the repo. Data flows one direction:

```
Google Sheet "Catálogo"
   └─ fetch_shoes_from_sheets.py   (the canonical sync script)
        ├─> frontend/shoes_data.js   (var SHOES = [...]; loaded by index.html)
        └─> shoes-fallback.json      (loaded by fetch() if SHOES is undefined)
```

`fetch_shoes_from_sheets.py` does more than copy: it parses Brazilian price strings (`R$ 1.313,78` → `1313.78`), keeps per-store prices for the price comparator, dedupes brand+model rows (validating official links by following redirects), and infers empty quiz fields (budget/nível/pisada/terreno/distância). **To change shoe data, edit the Sheet and re-run the sync — do not hand-edit `shoes_data.js` or `shoes-fallback.json`.**

The `sincronizar-site-diario.yml` workflow runs this daily and auto-commits the two generated files back to the repo.

## The frontend

- `index.html` (repo root, ~130KB) is the live site: a multi-step quiz that filters the global `SHOES` array by the user's answers and renders recommendation cards with affiliate "COMPRAR" buttons. Quiz logic lives inline near the `pool = SHOES.filter(...)` blocks.
- It loads data via `<script src="frontend/shoes_data.js">` and falls back to `fetch('./shoes-fallback.json')` if `SHOES` is undefined.
- Other top-level `.html` files are SEO landing/review pages (`melhores-tenis-*.html`, `*-review.html`, `tenis-ate-500.html`, etc.). `_redirects` maps clean URLs to them.
- **Duplication caveat:** a `frontend/` directory contains an older parallel copy of `index.html` and the landing pages. The **repo root is what gets published** (see `netlify.toml` → `publish = "."`); `frontend/` is only consumed for its generated `shoes_data.js`. When editing the live site, edit root files. `index.html.backup` / `index.html.bak` are stale backups — ignore them.

## Deployment (dual host)

Deployed to **both** Netlify and Vercel from the repo root (static). Both set the same security headers.

- **Netlify** (`netlify.toml`): publishes `.`, serverless functions in `netlify/functions/` (`products.js`, `send-email-sequence.js`, `check-metrics.js`, `anthropic.mjs`). The site calls these at `/.netlify/functions/<name>`.
- **Vercel** (`vercel.json`): `cleanUrls`, function in `api/subscribe.js` (adds a contact to Brevo). The site calls `/api/subscribe`.

Functions keep API keys server-side (env vars) so they're never exposed in the static HTML.

## Python automation (GitHub Actions)

Standalone scripts, each run by a workflow in `.github/workflows/`. There is **no shared package or test suite** — each script is self-contained and invoked as `python3 <script>.py`. Dependencies are installed ad-hoc per workflow (e.g. `pip install Pillow`, `pip install gspread google-auth requests`), so `requirements.txt` (requests, playwright) is not authoritative for all scripts.

| Workflow | Schedule (UTC) | Runs | Purpose |
|---|---|---|---|
| `sincronizar-site-diario.yml` | `0 11 * * *` | `fetch_shoes_from_sheets.py` | Sheet → site data, auto-commit |
| `cupons-awin-diario.yml` | `0 11 * * *` | `gerar_cupons_awin.py` → `enviar_cupons_email.py` | Fetch Awin coupons, email them |
| `arte-instagram-diaria.yml` | `30 11 * * *` | `gerar_arte_instagram.py` | Generate Instagram art (Pillow) + caption, email |
| `verificar-precos-diario.yml` | `0 16 * * *` | `verificar_precos.py` | Compare Sheet price vs. live store, email alerts |
| `newsletter-semanal.yml` | `0 12 * * 1` | `gerar_campanha_email.py` | Weekly Brevo newsletter draft |

Emails go through **Brevo**; coupons/products come from the **Awin** API (publisher ID `2800712`). Affiliate IDs are centralized in `config_afiliados.json`.

### Required env vars / secrets (set as GitHub repo secrets)
`GOOGLE_CREDENTIALS` (service-account JSON, written to `credenciais.json` at runtime), `AWIN_API_TOKEN`, `AWIN_PUBLISHER_ID`, `BREVO_API_KEY`, `BREVO_LIST_ID`, `EMAIL_CUPONS`, `EMAIL_REMETENTE`, `GEMINI_API_KEY`, `MAX_CUPONS`.

`credenciais.json`, `.venv/`, and generated artifacts (`email_campanha.html`, `cupons_hoje.txt`, `arte_*.png`) are gitignored. Never commit credentials.

## Running things locally

```bash
# Serve the static site (any static server works)
python3 -m http.server 8000          # then open http://localhost:8000/index.html

# Run a sync / automation script (needs the relevant env vars + credenciais.json)
pip install gspread google-auth requests
python3 fetch_shoes_from_sheets.py    # regenerates frontend/shoes_data.js + shoes-fallback.json

# Brevo/Awin scripts read env vars; export them first, e.g.
AWIN_API_TOKEN=... AWIN_PUBLISHER_ID=2800712 python3 gerar_cupons_awin.py
```

There is **no test suite, linter, or build** — `npm test` is a placeholder. Validate changes by serving the site and running the affected Python script directly.

## Where to look

The repo also contains extensive planning/spec docs (`SPEC.md`, `DATA_MODEL.md`, `API_IMPLEMENTATION.md`, `FRONTEND_IMPLEMENTATION.md`, `ROADMAP.md`, `RESUMO_FINAL.md`, etc.). These describe intended/aspirational design and a richer backend that is **not all implemented** — treat them as context, not as a description of current behavior. The actual running system is: static HTML at root + the five Python scripts above + the serverless functions.
