# BUILD-LOG — SkinSense Agent

Newest first. Every entry is written from the run's own output, not from memory.

## 2026-10-23 (evening) — LIVE end-to-end verified; submission package completed

- **Live analysis run** (`live_run.py`, new): loaded the key from the server-side
  secrets file (value never printed), uploaded Scott's front-facing selfie through the
  production `youcam.py` client. First task errored with `error_src_face_too_small`
  (full-frame selfie; an errored task consumes no units). Retry with a center crop of
  the same selfie (830×1290, kept outside the repo in `../demo-assets/`) succeeded:
  task `Aq6Tcwjt9uyPULcnak_1vCYbzoCx6xWNtP7uGC1Nnbv7KmMNy3AnV0hT490J1YQTSpcgV8WTLEnG8Q2PXjtLzQ`
  under API **v2.0** (the v2.1 fallback was never needed).
- **Live scores**: redness 55, pore 66, moisture 72, radiance 72, wrinkle 79,
  oiliness 82, texture 82, acne 84; **overall 74; skin age 31**.
- **Normalizer fix** (`youcam.py`): the real `results.output` has 11 entries — the 8
  concerns plus `all` / `skin_age` entries whose values live in a `score` field, plus
  an auxiliary `resize_image` entry. The old normalizer read overall/skin_age at
  results level (always null live) and let the null-scored auxiliaries poison
  `rank_priorities`. Now: concerns are filtered to the requested SD actions, overall
  and skin age are extracted from their entries. Verified by replaying the saved raw
  payload locally (zero extra API calls): priorities redness → pore → radiance,
  routine basket $150, refine ("under $20 each and fragrance-free") → 7 changes,
  $66, mode `live`.
- **Gallery + film** (`demo/capture_live.py`, `demo/build_film.py`, new): one filmed
  UI session with the key — identical scores to the verification run (deterministic
  engine). Six stills in `demo/gallery/` (title, hero + Live-ready badge + photo,
  LIVE scores, routine, routine + try-on answer, refine change list; no SAMPLE banner
  anywhere). First capture attempt failed on a scrubbed child env (no proxy variables
  → server transport stalled → SAMPLE fallback → the LIVE wait timed out with no task
  created); fixed by inheriting the proxy variables and adding page-state diagnostics.
  Film: `demo/skinsense-demo.mp4`, **2:03**, 1280×720, 9 narrated segments quoting
  the real session numbers (`demo/narration.txt`).
- **Makeup VTO verdict**: stays an honestly labeled placeholder. Docs check
  (yce.perfectcorp.com/document): `POST /s2s/v2.0/task/makeup-vto` requires
  `src_file_url` (a publicly accessible image URL) plus named pattern/palette
  effects — not the session `file_id`. Publishing the user's face photo to a public
  URL to satisfy that is a hard no; nothing is faked. Documented in README and
  SUBMISSION-DRAFT.
- **Units tally**: 2 successful analysis tasks total (verification run + filmed UI
  session), 1 errored task (consumed none), uploads consume none. The endpoints used
  expose no balance figure.
- Docs updated: SUBMISSION-DRAFT.md verification log flipped to LIVE with the full
  entry; README API notes + Current state corrected.

## 2026-10-23 — live probe (commit a70ce7a)

- Bearer auth + the v2.0 File API upload verified with the real key (pre-signed PUT
  lands; `/api/status` reads `live-ready`). Curl-first transport fix after urllib
  reads stalled in the sandbox egress proxy. Live analysis deliberately NOT run: the
  only stored photo was a 200×200 two-person vacation shot. Units consumed: 0.

## 2026-10-23 — skeleton (commit 4ec2aff)

- SkinSense Agent built from the documented spec: stdlib server, `youcam.py` REST
  client (upload → task → poll → normalize), deterministic agent (priorities,
  routine, feedback refine with named swap diffs), 13-product demo catalog (invented
  brands, two VTO-mapped tints), keyword-aware SAMPLE fallback labeled everywhere,
  Devpost submission draft.
