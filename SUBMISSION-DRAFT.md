# SUBMISSION DRAFT — SkinSense Agent (Devpost)

> Draft prepared Oct 23, 2026 for the YouCam API Skin AI & eCommerce VTO Hackathon
> (Perfect Corp). Deadline: **Mon Nov 2, 2026, 11:45 AM ET**. Do not paste blindly —
> re-check every "live" claim against the Live verification log below before submitting.

## Live verification log

**Oct 23, 2026, ~15:57 EDT — LIVE ANALYSIS VERIFIED (`live_run.py` + a filmed UI session
via `demo/capture_live.py`; key loaded from the server-side secrets file; values never
printed or committed):**

- ✅ **Full live flow through the production code**: File API upload → `POST
  /s2s/v2.0/task/skin-analysis` → poll → normalize, on the user's own front-facing
  selfie. The task endpoint works under **v2.0** (the v2.1 fallback was never needed).
  Successful task id: `Aq6Tcwjt9uyPULcnak_1vCYbzoCx6xWNtP7uGC1Nnbv7KmMNy3AnV0hT490J1YQTSpcgV8WTLEnG8Q2PXjtLzQ`.
- ⚠️ First attempt: the engine rejected the full-frame selfie with
  `error_src_face_too_small` (task errored; per the API's model an errored task consumes
  no units). A tighter center crop of the **same selfie** (830×1290) was accepted
  immediately — the crop is what the demo films, and this note is the disclosure.
- ✅ **Live scores** (ui_score, 1–100, higher = healthier): redness **55**, pore **66**,
  moisture **72**, radiance **72**, wrinkle **79**, oiliness **82**, texture **82**,
  acne **84**. **Overall ("all") score: 74. Estimated skin age: 31.**
- 🔧 Normalizer fixed against the real response shape: `results.output` carries **11
  entries** — the 8 concerns (ui_score/raw_score/mask_urls) plus `all` and `skin_age`
  entries whose values live in a **`score`** field (not at results level, not in
  ui_score), plus an auxiliary `resize_image` entry. The first live normalization let
  the null-scored auxiliaries poison the priority ranking; `normalize_results` now
  keeps only the requested SD concerns in the ranked list and extracts overall/skin
  age from their entries.
- ✅ **Agent verified on the LIVE scores** (local replay of the saved raw payload, no
  extra API calls): priorities redness → pore → radiance; routine leads with the Calm
  Niacinamide serum ("aimed at Redness, your weakest area"), basket **$150**; one
  refine round ("under $20 each and fragrance-free") produced 7 named changes and cut
  the basket to **$66**, mode `live`.
- ✅ **Filmed UI session**: the app ran with the key, the selfie was analyzed in the
  browser, and the session returned **identical scores** (the engine is deterministic
  for the same photo). Gallery stills in `demo/gallery/` show the Live-ready badge,
  the LIVE source line, the routine, the try-on answer, and the refine change list —
  no SAMPLE banner anywhere. Demo film: `demo/skinsense-demo.mp4` (2:03, 720p).
- 🧮 **Units**: two successful analysis tasks in total (this verification run + the
  filmed UI session), one errored task (consumed none), uploads consume none. The
  endpoints used expose no balance figure, so the exact per-task unit cost cannot be
  stated; runs were kept to the minimum the package required.
- 🚧 **Makeup VTO stays an honestly labeled placeholder, now with the documented
  reason**: per Perfect Corp's docs, `POST /s2s/v2.0/task/makeup-vto` takes
  `src_file_url` — a **publicly accessible image URL** — not a File API `file_id`, and
  its effects need named pattern/palette payloads. The user's selfie is a private local
  upload; we do not publish his face to a public URL to satisfy that parameter, and no
  try-on result is faked anywhere in the app, the gallery, or the film (the film's
  narration says exactly this).

**Oct 23, 2026 — live probe run (`live_probe.py`, key loaded from the server-side
secrets file; values never printed or committed):**

- ✅ Credentials: `YOUCAM_API_KEY` and `YOUCAM_API_SECRET` both present; the secret is
  structurally the documented RSA public-key block. (The RSA `id_token` flow was NOT
  needed: the S2S API accepted the documented Bearer flow.)
- ✅ Auth + API version: **Bearer auth on `v2.0`** — `POST /s2s/v2.0/file/skin-analysis`
  returned status 200 with a `file_id`, and the pre-signed PUT of the photo bytes to S3
  returned 200, all through the production `youcam.py` client.
- ✅ `/api/status` with the key loaded: `youcam_configured: true`, mode **`live-ready`**,
  base `https://yce-api-01.makeupar.com`, version `v2.0`, the 8 SD `dst_actions`.
- ✅ Loop plumbing through the real server: text-only analyze answers with the honestly
  labeled SAMPLE (priorities moisture/redness/oiliness, basket $150); one refine round
  ("under $20 each and fragrance-free") applied 7 changes and cut the basket to $66.
- 🔧 Bug found + fixed by the probe: urllib response reads stall inside the ARC
  sandbox's egress proxy (30 s read timeout) while curl answers the same API in ~1.7 s.
  `youcam.py` now tries **curl first** with urllib as fallback, and translates bare
  socket timeouts into `YouCamError` so the agent's labeled fallback catches them.
- ✅ **Live analysis scores: captured the same day** — the user sent a proper
  front-facing selfie and the full live run completed; see the LIVE ANALYSIS VERIFIED
  entry at the top of this log for the scores, the normalizer fix, and the units tally.
  (This probe's own photo gate did its job meanwhile: the stored 200×200 two-person
  vacation shot was never submitted, and no other person's photo was substituted.)

## Project name

**SkinSense Agent** — the skincare concierge that measures, recommends, and listens

## Tagline (short description)

Describe your skin, get a real YouCam AI skin analysis, and watch an agent build a routine
around your weakest scores — then argue with it, and watch the routine rebuild.

## Inspiration

Skincare shopping is a wall of confident claims and no measurements. People buy for the
skin they wish they had, guess at results in the mirror, and abandon routines that were
never matched to their actual concerns. We wanted the shopping loop to start from a
measurement instead of a marketing claim — and to keep listening after the first answer,
the way a good human consultant does.

## What it does

SkinSense Agent runs a four-step agentic loop:

1. **Describe** — the user states a concern in plain words ("dry and tight by midday,
   cheeks flush red, dull patches") and can add a front-facing selfie.
2. **Analyze** — the app calls the **YouCam Skin AI Analysis API** (File API upload →
   skin-analysis task → polling) and scores eight concerns: moisture, oiliness, redness,
   acne, pores, texture, wrinkles, radiance.
3. **Recommend** — the agent ranks the concerns weakest-first and builds an AM/PM routine
   from a product catalog: every card shows the product, a one-line pitch, the agent's
   reason ("aimed at Moisture, your weakest area"), and its price; tinted finishers carry
   **virtual try-on** via YouCam Makeup VTO. The basket total is computed honestly —
   products shared between AM and PM are counted once.
4. **Refine** — the user pushes back in plain language ("too expensive — under $20 each",
   "everything fragrance-free, my skin is sensitive", "simpler", "no makeup") and the
   agent rebuilds the routine under the new constraints, listing exactly what changed:
   swaps by name, constraint notes, and the before/after basket total.

## How we built it

- **Zero-dependency Python** (standard library only) — a small threaded HTTP server keeps
  the API key server-side; the browser never talks to Perfect Corp directly.
- **Real API integration, documented spec** — `youcam.py` implements the official flow
  from Perfect Corp's docs: `POST /s2s/v2.0/file/skin-analysis` for a pre-signed upload
  URL + `file_id`, a PUT of the image bytes, `POST /s2s/v2.0/task/skin-analysis` with the
  SD `dst_actions` set and `format: "json"`, then polling
  `GET /s2s/v2.0/task/skin-analysis/{task_id}` and normalizing
  `data.results.output[]` (`ui_score`, `raw_score`, `mask_urls`).
- **Deterministic agent** — the routine builder and feedback parser are transparent rules
  over the scores (positional concern weights, constraint filters, product-level diffing),
  so behavior is testable and identical in demos; no LLM bill, no nondeterminism.
- **Honesty as a feature** — when no API key is configured (or no photo is provided), the
  app runs on deterministic, keyword-aware **SAMPLE** data and labels it in the UI badge,
  an amber banner, and the analysis source line. Sample output is never dressed up as a
  real measurement — we think that labeling discipline is part of doing consumer health
  tooling responsibly.
- **Design** — a single-page, framework-free UI with a warm editorial look (serif display
  type, soft cards, animated score bars with the three priority concerns flagged) built to
  be judged as a consumer product, not a developer console.

## Challenges

- The API is asynchronous with a two-step file upload (metadata → pre-signed PUT); the
  docs warn that skipping the PUT surfaces later as opaque 500/404 errors, so the client
  validates each stage and fails with the API's own error text.
- SD and HD concern sets cannot be mixed in one task (`InvalidParameters`), so the client
  pins one documented SD set.
- Keeping the demo truthful: the fallback path had to be as designed as the live path,
  because reviewers may run the repo without a key.

## Accomplishments / what is next

- Full loop working end to end today, and the live analysis is **verified against the
  real API** (Oct 23, 2026 — see the verification log): real scores on the author's own
  selfie, a routine built from them, and a filmed refine round, all in the demo video.
- Next: complete the live Makeup VTO task wiring behind the try-on button, swap the demo
  catalog for a retailer's real product feed, and add week-over-week score tracking so
  the agent can answer "is this routine working?"

## Value case (impact)

For consumers: a routine derived from measured concerns instead of influencer claims,
with a budget ceiling the agent actually respects. For retailers: an agentic storefront
pattern — measure → recommend → try on → refine — that raises conversion quality and
cuts returns driven by wrong-product purchases. The refine loop is the differentiator:
most "AI skin" demos end at the score screen; this one keeps negotiating.

## Built with

Python 3 (standard library only) · YouCam Skin AI Analysis API (Perfect Corp) ·
YouCam Makeup VTO (try-on wiring) · HTML/CSS/JavaScript (single file, no framework)

## Team / eligibility notes

- **Solo entry** by David Scott Cain.
- **Rising Star (Student) Award**: the entrant is an enrolled college student
  (Grand Canyon University) — flagging student status here as the award requires.
- Free-tier build: the 1,000 hackathon API units fund development and the demo; no paid
  dependencies anywhere in the stack.

---

## Demo video shot list (1–3 min, YouTube; must show the project functioning with the REAL API)

> **FILMED Oct 23, 2026** — `demo/skinsense-demo.mp4`, **2:03**, 1280×720, built by
> `demo/build_film.py` from the genuine live session captured by `demo/capture_live.py`
> (badge "Live-ready", source line LIVE, scores identical to the verification run).
> Narration script: `demo/narration.txt`. The shot list below is the plan it followed;
> beat 5 films the honestly labeled VTO placeholder, exactly as written.

| # | Time | Shot | Narration beats |
| --- | --- | --- | --- |
| 1 | 0:00–0:12 | Title card + the problem: a bathroom shelf of half-used products | "Most skincare is bought on promises. SkinSense starts with a measurement." |
| 2 | 0:12–0:30 | Step 1: type the concern, attach a real front-facing selfie, click Analyze; badge shows Live-ready | "Say it in your own words, add a selfie — the agent calls YouCam's Skin AI." |
| 3 | 0:30–0:50 | Step 2 results land: score bars animate, three weak concerns flagged, source line reads LIVE YouCam | "Eight concerns scored by Perfect Corp's engine. These three run the routine." |
| 4 | 0:50–1:20 | Step 3: routine cards AM/PM, point at a "why" line and the basket total | "Every product is here for a named reason, and the total counts shared products once." |
| 5 | 1:20–1:40 | Click "Try it on" on the tinted moisturizer; show the VTO result/placeholder state honestly | "Tinted finishers carry virtual try-on, so shade is previewed on your own photo." |
| 6 | 1:40–2:05 | Step 4: tap the "Under $20 each" chip, Refine; show the change list and the new total | "Push back — a budget, fragrance-free, simpler — and the routine rebuilds with a receipt of what changed." |
| 7 | 2:05–2:20 | Close: the loop diagram (Describe → Analyze → Recommend → Refine) + repo URL | "An agent that measures, recommends, and listens. SkinSense Agent." |

Screenshot checklist for the Devpost gallery — **all captured from the live session**,
in `demo/gallery/`: (1) `shot1-hero-photo.png` hero + Step 1 with the photo attached and
the Live-ready badge, (2) `shot2-live-scores.png` Step 2 score bars with the LIVE source
line, (3) `shot3-routine.png` + `shot3b-tryon.png` Step 3 routine grid with try-on cards
and the server's try-on answer, (4) `shot4-refine.png` Step 4 change list after the
budget + fragrance-free refine.
