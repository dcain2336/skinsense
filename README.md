# SkinSense Agent

An agentic skincare concierge built on Perfect Corp's **YouCam Skin AI API**: describe a skin
concern (and optionally add a selfie) → the agent runs a real AI skin analysis → builds a
personalized AM/PM routine around your weakest scores → presents shoppable product cards,
including tinted finishers with **virtual try-on** → and **refines the routine when you push
back** ("fragrance-free", "under $20 each", "simpler", "no makeup").

Built for the **YouCam API Skin AI & eCommerce VTO Hackathon** (Perfect Corp, Devpost,
deadline Nov 2, 2026). Solo entry by a college student (Rising Star eligible).

## The agentic loop

1. **Describe** — free-text concern, optional front-facing photo.
2. **Analyze** — the server uploads the photo through the documented YouCam File API,
   creates a Skin Analysis task (SD concerns: moisture, oiliness, redness, acne, pore,
   texture, wrinkle, radiance), and polls it to completion. Scores are the API's real
   `ui_score`/`raw_score` values (1–100, higher = healthier).
3. **Recommend** — a deterministic routine builder ranks concerns weakest-first and picks
   catalog products per step (cleanse → treat → moisturize → protect, plus tinted
   finishers), with a plain-language reason on every card and an honest basket total.
4. **Try on** — tinted products carry a YouCam Makeup VTO effect mapping (`foundation`,
   `lip_color`); the try-on button is wired to the server and reports its status honestly
   (see "Current state" below).
5. **Refine** — feedback becomes constraints (fragrance-free, per-product price cap,
   minimal routine, no makeup); the routine rebuilds and the UI lists exactly what
   changed, including product swaps and the before/after basket total.

## Quick start

```bash
# No key needed for the SAMPLE-mode demo:
python3 app.py                      # http://localhost:8770

# Live mode (real YouCam analysis; requires a photo with each analyze):
YOUCAM_API_KEY=<your key> python3 app.py
```

Zero dependencies — Python 3 standard library only. Configuration is environment-only
(see `.env.example`): `YOUCAM_API_KEY`, optional `YOUCAM_API_BASE`,
`YOUCAM_API_VERSION` (default `v2.0`), and `PORT` (default `8770`).

## Honest mock mode (please read)

If `YOUCAM_API_KEY` is unset — or a request has no photo, or a live call fails — the app
runs on **SAMPLE data** and says so everywhere it matters: an amber SAMPLE banner, a
"SAMPLE mode" badge, a "Source: SAMPLE data" line, and a notice explaining why. Sample
scores come from `mock_data.py`: deterministic, keyword-aware (mentioning dryness lowers
the sample moisture score), and shaped exactly like real results so the whole loop can be
judged end to end. **Sample output is never presented as a real API result.** Live results
are labeled `LIVE` and carry `source: "youcam-live"`.

## API implementation notes

`youcam.py` implements the flow from Perfect Corp's official documentation
(the "Skin Analysis API Usage Guide" at yce.perfectcorp.com/document and
docs.perfectcorp.com), verified 2026-10-23:

- Host `https://yce-api-01.makeupar.com`; auth header `Authorization: Bearer <API_KEY>`.
- `POST /s2s/v2.0/file/skin-analysis` → pre-signed URL + `file_id`; PUT the image bytes.
- `POST /s2s/v2.0/task/skin-analysis` with `src_file_id`, `dst_actions` (SD set),
  `miniserver_args.enable_mask_overlay=false`, `format: "json"` → `task_id`.
- Poll `GET /s2s/v2.0/task/skin-analysis/{task_id}` until `task_status` is
  `success`/`error`; normalize `data.results.output[]` (`type`, `ui_score`, `raw_score`,
  `mask_urls`). Units are consumed only on success.
- **Verified live on 2026-10-23** (see `live_probe.py`): with the real key, the File API
  step succeeds end to end through this client — Bearer auth accepted, `v2.0` file path
  correct, pre-signed PUT lands — and `/api/status` reports `live-ready`. One transport
  lesson from that run: in the ARC sandbox, urllib response reads stall inside the egress
  proxy, so the client tries **curl first** (same call: 1.7 s via curl vs a 30 s read
  timeout via urllib) and keeps urllib as the fallback for normal networks.
- Former TODOs, **resolved live on 2026-10-23**: the task endpoint accepts `v2.0` (the
  `YOUCAM_API_VERSION` override remains, unused), and the JSON task response carries the
  overall and skin age as their own `output[]` entries (`{"type": "all", "score": 74.0}`
  and `{"type": "skin_age", "score": 31}` in the verified run) alongside the eight
  concerns and an auxiliary `resize_image` entry. `normalize_results` extracts all of
  this; one engine lesson is baked into `live_run.py`'s notes — a full-frame selfie was
  rejected as `error_src_face_too_small`, and a tighter center crop of the same photo
  was accepted.

## Current state

- ✅ Full loop works offline in SAMPLE mode (analyze → routine → refine → try-on status).
- ✅ Live client **verified against the real API** (Oct 23, 2026): credentials load,
  Bearer auth accepted, File API upload step completes, `/api/status` reads `live-ready`.
- ✅ Live *analysis* **verified end to end** (Oct 23, 2026): a real task on the author's
  own front-facing selfie returned all eight scores (weakest: redness 55, pore 66,
  radiance 72), overall 74, skin age 31; the agent's routine and refine were verified
  on those live scores, and a filmed UI session reproduced identical results. Gallery
  stills and the 2:03 demo film live in `demo/` (see the verification log in
  `SUBMISSION-DRAFT.md`).
- 🚧 Makeup VTO: the try-on endpoint is an honestly labeled placeholder. The documented
  task (`POST /s2s/v2.0/task/makeup-vto`) takes a **publicly accessible image URL**
  (`src_file_url`) plus named pattern/palette effects — not a File API `file_id` — so
  wiring it for a private local selfie would mean publishing the user's face photo to
  a public URL. We don't; the button reports its placeholder status verbatim instead,
  and no try-on result is faked anywhere.
- 🚧 Product catalog is a demo catalog with invented brands (clearly labeled); a retailer
  feed can replace `catalog.py` data without agent changes.

## Layout

| File | Role |
| --- | --- |
| `app.py` | Stdlib HTTP server: `/`, `/api/status`, `/api/analyze`, `/api/refine`, `/api/tryon` |
| `youcam.py` | Documented YouCam REST client (upload → task → poll → normalize) |
| `agent.py` | The agentic loop: priorities, routine builder, feedback parser, refine diffing |
| `catalog.py` | Demo product catalog (invented brands, real-shaped data) |
| `mock_data.py` | Deterministic, keyword-aware SAMPLE analysis generator |
| `static/index.html` | The single-page UI (all CSS/JS inline, design-forward) |
| `SUBMISSION-DRAFT.md` | Devpost description draft + demo-video shot list |

## Privacy note

Photos are sent only to the YouCam API for analysis and, per Perfect Corp's docs, uploaded
files and results are retained by the API for 24 hours. This prototype stores nothing
server-side; session state lives in the browser tab.
