# ObeliskFarm: EXE/Desktop → Web App Migration Guide

This document describes how ObeliskFarm was migrated from a Windows EXE (Python GUI) to a browser-based web app (GitHub Pages), and which pitfalls we hit along the way.

## Goals (Why migrate?)

- **Trust & safety**: users are understandably wary of running random `.exe` files.
- **Zero install**: open a link, use the tool, done.
- **Cross-platform**: works on Windows/macOS/Linux and mobile.

## High-level approach

We did **not** “convert Python to React automatically”.

Instead we:

- kept the original Python app as-is (EXE build stays possible)
- created a dedicated **`web` branch**
- added a self-contained **`web/`** project (Vite + React + TypeScript)
- **ported** only the required domain logic from Python to TypeScript (constants, simulation, optimizer)
- deployed to **GitHub Pages** via GitHub Actions, triggered by pushes to the `web` branch

## Step-by-step migration (what we actually did)

### 1) Split concerns

- **UI layer**: rewritten in React (forms, buttons, layout, tooltips).
- **Domain logic**: ported from `ObeliskGemEV/event/*` to `web/src/lib/event/*`.
- **Persistence**: desktop JSON file → `localStorage` autosave in browser.

### 2) Create a `web/` project

We used Vite + React + TypeScript:

- `web/package.json`
- `web/vite.config.ts`
- `web/src/*`

Local dev:

```bash
cd web
npm install
npm run dev
```

### 3) Port the “Event Budget Optimizer” module first

Pick one “vertical slice” and ship it:

- constants → `web/src/lib/event/constants.ts`
- stats model → `web/src/lib/event/stats.ts`
- simulation loop → `web/src/lib/event/simulation.ts`
- optimizer(s) → `web/src/lib/event/optimizer.ts` and `web/src/lib/event/monteCarloOptimizer.ts`

### 4) Keep the UI responsive (critical)

Monte Carlo is CPU-heavy. In a browser, running it on the main thread will freeze the UI.

Solution:

- run the Guided MC optimizer in a **Web Worker**
- show progress in the UI (runs done, best wave, etc.)

Implementation:

- `web/src/workers/mc.worker.ts`

### 5) Web savegames (autosave)

Desktop version saved to a JSON file (`event_budget_save.json`).

Web version uses:

- `localStorage` autosave
- same schema conceptually: `prestige`, `upgrade_levels`, `gem_levels`

Key differences:

- browser saves are per-device/per-browser-profile
- clearing browser data removes saves

### 6) Tooltips via “?” only

Desktop had hover tooltips. On web we used a consistent `?` trigger to avoid accidental popups:

- `web/src/components/Tooltip.tsx`

### 7) Deploy to GitHub Pages

We created a Pages workflow:

- `.github/workflows/pages-web.yml`
- runs on **push to `web`**
- builds the Vite app with correct base path for project pages:
  - `BASE_PATH="/ObeliskFarm/"`

## Asset handling (sprites/icons)

Desktop used `ObeliskGemEV/sprites/...`.

For web, we need static assets in `web/public/`.

We implemented a copy step:

- `web/scripts/copy-assets.mjs`
- runs automatically before dev/build (`npm run prepare-assets`)
- copies from `ObeliskGemEV/sprites/*` → `web/public/sprites/*`

Pitfall: if you don’t copy assets, icons will be missing at runtime.

## Pitfalls we hit (and fixes)

## Error log snippets (for future debugging)

These are representative snippets we saw during the migration. They’re useful for quick recognition when something breaks again.

### npm not installed locally

```
npm: The term 'npm' is not recognized as a name of a cmdlet, function, script file, or executable program.
```

### `npm ci` lockfile mismatch (CI)

```
npm error `npm ci` can only install packages when your package.json and package-lock.json or npm-shrinkwrap.json are in sync.
npm error Missing: @types/node@25.0.10 from lock file
npm error Missing: undici-types@7.16.0 from lock file
```

### TypeScript build failures (CI)

```
src/App.tsx(...): error TS2304: Cannot find name 'monteCarloOptimizeGuided'.
src/App.tsx(...): error TS7006: Parameter 'cur' implicitly has an 'any' type.
```

### GitHub Pages environment protection

```
Branch "web" is not allowed to deploy to github-pages due to environment protection rules.
The deployment was rejected or didn't satisfy other protection rules.
```

### 1) “localhost doesn’t open”

Cause: no dev server running or `npm` not installed.

Fix:

- install Node.js LTS (includes npm)
- run `npm run dev` inside `web/`

### 2) `npm ci` failing on CI

`npm ci` is strict: it requires `package.json` and `package-lock.json` to be perfectly in sync.

We hit errors like:

- missing `@types/node` / `undici-types` in lock file

Fix options:

- best: regenerate and commit a correct `package-lock.json` (run `npm install`, commit lockfile)
- pragmatic: use `npm install` in CI until dependencies stabilize

### 3) GitHub Pages “environment protection rules”

Deploy can be rejected if the `github-pages` environment only allows specific branches.

Fix:

- GitHub → Settings → Environments → `github-pages`
- allow branch `web` (or allow all branches)

### 4) Missing/hidden build errors in Actions logs

Sometimes Actions output looked “truncated” and didn’t show the real TypeScript error.

Fix:

- run build steps explicitly:
  - `npx tsc -b`
  - `npx vite build --debug`
- upload npm logs as artifacts on failure

### 5) TypeScript strictness surprises

CI can fail on issues that “seem fine” locally, e.g.:

- missing imports (`Cannot find name ...`)
- implicit `any` parameters in callbacks

Fix:

- keep `strict: true`
- type callback parameters explicitly

### 6) GitHub Pages base path

For project pages, the app is served under:

`https://<user>.github.io/<repo>/`

If the app is built with base `/`, asset URLs and routing can break.

Fix:

- set Vite `base` via env (we use `BASE_PATH`)
- build with `BASE_PATH="/ObeliskFarm/"`

### 7) Browser sandbox ≠ “automatically safe”

Running in a browser reduces access compared to an EXE, but web apps can still be malicious (phishing, token theft, etc.).

Mitigation:

- be transparent about what the app does
- keep everything client-side where possible
- avoid collecting credentials/secrets

## Recommended workflow going forward

- Desktop EXE releases: tag `vX.Y.Z` → CI builds release asset
- Web app updates: commit to `web` → push → Pages auto-deploys

## Checklist for adding another module

- Identify core logic (pure functions) and port to `web/src/lib/<module>/`.
- Keep UI in React and run any heavy loops in a Worker.
- Decide save schema and migrate from file to localStorage.
- Add tooltips via `?` icons only.
- Ensure assets are copied into `web/public/`.
- Ensure Pages build uses correct `BASE_PATH`.

