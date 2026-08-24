# Setup

Everything here goes into a repo named **exactly the same as your GitHub username**
(`github.com/<username>/<username>`). That magic repo's README is what shows on your profile.

---

## 1. Fill in the placeholders

```powershell
.\setup.ps1 -Username YOUR_USERNAME -Name "Your Name" -Image .\me.jpg -Circle -Animate
```

That rewrites `YOUR_USERNAME` / `YOUR NAME` across `README.md` and the workflows, draws the
radar charts, and dot-matrixes your photo. Then open `preview.html` in a browser to see the
local assets before you push anything.

Still to fill in by hand in `README.md`: `YOUR_LINKEDIN`, `YOUR_EMAIL`, `YOUR_PORTFOLIO`,
`YOUR_CF`, `YOUR_LEETCODE`, `PROJECT_ONE`…`PROJECT_FOUR`, and the "whoami" bullets.

## 2. Push it

```bash
git init && git branch -M main
git add -A && git commit -m "profile readme"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_USERNAME.git
git push -u origin main
```

The repo must be **public** — the SVG assets are loaded by URL, so a private repo shows
broken images.

## 3. Let Actions write to the repo

Repo → **Settings** → **Actions** → **General** → **Workflow permissions** →
select **Read and write permissions** → Save.

Without this the Radar and Snake workflows fail on push.

## 4. Add the metrics token

`lowlighter/metrics` needs its own token — the built-in `GITHUB_TOKEN` can't read profile data.

1. https://github.com/settings/tokens → **Generate new token (classic)**
2. Scopes: **`read:user`** (add **`repo`** too if you want private repos counted)
3. Expiry: whatever you're happy re-doing later
4. Copy it, then repo → **Settings** → **Secrets and variables** → **Actions** →
   **New repository secret** → name it **`METRICS_TOKEN`**, paste the value

## 5. Kick off the workflows

Repo → **Actions** tab → enable workflows if prompted, then run each one via
**Run workflow**:

| workflow | produces | lands in |
|---|---|---|
| **Metrics** | 3D isometric calendar, language mix, achievements | `assets/metrics.*.svg` on `main` |
| **Snake** | snake eating your contribution graph | the `output` branch |
| **Charts and cards** | both spider charts, stat card, repo cards | `assets/radar*.svg`, `assets/card-*.svg` on `main` |

First run takes a couple of minutes. After that they're on a schedule (metrics every 6h,
snake every 12h, radar daily).

> The snake images are referenced from the `output` branch via `raw.githubusercontent.com`,
> so they'll 404 until the Snake workflow has run once. That's expected.

---

## Tuning the artwork

### The portrait

The current one was made with:

```powershell
python scripts\dotify.py assets\jacket.png -o assets\portrait --cols 100 --equalize --detail 0.5 --color --reveal
```

Other looks from the same source:

```powershell
# green monochrome, matching the contribution-graph palette
python scripts\dotify.py assets\jacket.png -o assets\portrait --cols 88 --equalize --detail 0.5 --animate

# literal 0s and 1s instead of dots
python scripts\dotify.py assets\jacket.png -o assets\portrait --mode binary --cols 62 --equalize --detail 0.5

# plain text art — paste the .txt into a ``` code block in the README
python scripts\dotify.py assets\jacket.png -o assets\portrait --mode ascii --cols 80
python scripts\dotify.py assets\jacket.png -o assets\portrait --mode braille --cols 100
```

Worth knowing:

- **`--equalize` is the one that matters for a portrait.** A lit face against dark hair
  spans a far wider range than the ~10 tones a dot ramp can show, so a straight render
  blows the face into a flat blob and loses the hair entirely. Equalising against the
  subject's own histogram buys the shadow detail back.
- `--detail 0.5` then puts local facial structure back on top, since equalising flattens
  it. Above about 1.0 it starts looking noisy.
- `--color` keeps each dot's original pixel colour. Because the fills then come from the
  photo rather than a theme, it writes a single `portrait.svg` instead of a
  `-dark`/`-light` pair — the README references it directly.
- `--cols` is the whole quality/size dial. 60 is chunky and abstract, 100 is what's in
  use now (325 KB), 130 is more detailed but pushes past 500 KB.
- `--reveal` draws the portrait in row by row when the page loads, like a slow scan.
  `--reveal-time` is the full top-to-bottom sweep (2.5s), `--reveal-fade` is how long
  one row takes to appear (0.45s — this is what makes it a soft scan rather than a hard
  line), and `--reveal-dir up` sweeps the other way. It plays once per image load, so
  open `preview.html` and use the **replay the load-in** button to rewatch it.
- `--animate` adds a slow shimmer sweeping across the columns. It suits the green
  monochrome version; on the colour one it reads as vertical banding across the face,
  which is why it's off here. It composes with `--reveal` if you want both.
- `--square` crops to 1:1, with `--focus X,Y` to say which point should end up centred
  (`0.55,0.45` for a face sitting right of and above the middle). `jacket.png` was
  already square, so it isn't used.
- `--circle` masks to a circle and fades the edge. Good for a tight head shot, but it
  clips the shoulders on this framing.
- `--invert` if your subject is dark on a light background.

If the source has an alpha channel, it's treated as a subject cutout: nothing is drawn
outside it, and `--equalize` measures only the subject rather than a huge empty
background. `jacket.png` already has one, which is why the orange backdrop vanishes.

### The stat and repo cards

`scripts/cards.py` generates these into your own repo, on purpose. The usual choices —
`github-readme-stats`, `github-profile-trophy`, `streak-stats` — are shared public
instances, and when they fall over your profile shows broken images. At the time this
was set up they were returning 503, 402 (quota exhausted) and intermittent timeouts
respectively. A file in your repo has none of those failure modes.

```powershell
python scripts\cards.py --user jrohitofficial --out assets
```

- **Which repos get a card** is `assets/projects.json`. Stars, forks and language are
  fetched live on every run; the `description` there overrides the repo's own GitHub
  description, which is useful since none of these repos have one set. Setting them on
  GitHub too is worth doing — it helps anyone browsing your repo list, and then you can
  delete the overrides.
- **The contribution and streak tiles need a token**, because they come from the GraphQL
  API. The workflow passes `METRICS_TOKEN` for this. Run it locally without one and the
  card still renders, just with three tiles instead of six.
- Star and fork counts are the live numbers, so the cards genuinely track reality — they
  just do it on a daily schedule rather than on every page view.

### The radar

Edit `assets/skills.json` and re-run — values are 0-100 and entirely self-rated. Five to
eight axes reads best; past that the labels crowd each other.

The second radar (`radar-langs`) is generated from real language byte counts across your
public repos, so it needs no editing. Two knobs in `.github/workflows/radar.yml`:

- `--exclude` drops languages you don't want counted (HTML/CSS/Shell are out by default,
  otherwise generated files skew everything).
- `--curve` controls how hard a dominant language is compressed. Raw byte counts are
  brutally lopsided — if one language is 90% of your code, a linear radar is just a spike.
  `1.0` is linear, `0.5` is sqrt, `0.4` is the default here, `0.3` flattens it further.

---

## If something looks broken

**Images don't load on the profile.** The repo has to be public, and the paths in the
README are relative (`assets/…`) — those only resolve once the files are actually pushed.

**Metrics workflow fails.** Almost always the `METRICS_TOKEN` secret: missing, expired, or
created as a fine-grained token instead of a classic one.

**Snake images 404.** The Snake workflow hasn't completed yet, or step 3 (write permissions)
was skipped so it couldn't create the `output` branch.

**`github-readme-stats` cards show an error.** The public instance gets rate-limited during
busy hours. It usually resolves itself; if it keeps happening you can deploy your own copy
to Vercel in about five minutes.

**Stats look low.** `github-readme-stats` only counts public contributions by default.
`count_private=true` is already in the URL, but it only works on a self-hosted instance.
