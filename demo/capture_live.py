# capture_live.py - drive the REAL SkinSense app in live mode and capture the gallery stills + film frames.  # Module header: what this file is.
# Written 2026-10-23 for the YouCam API Skin AI & eCommerce VTO Hackathon submission package. Demo tooling, not part of the shipped app.  # Provenance: demo tooling.
# Honesty contract: the server runs WITH the real YOUCAM_API_KEY, the browser attaches the user's own selfie (the center-cropped copy the engine accepted), and every frame below shows the app's genuine live session - the LIVE source line must be on screen before any results frame is taken. Exactly ONE live analysis task runs in this session; the refine round is local agent math and costs no units.  # Honesty: one real session, labeled by the app itself.
# The session's /api/analyze payload (which contains face mask URLs) is saved OUTSIDE the repo under ../../demo-assets/, never in this demo folder.  # Privacy: face data stays out of git.
# Import the JSON module so the session payload and capture notes can be saved.  # Library: json.
import json  # Make the json module available.
# Import the OS module so paths and environment variables can be handled.  # Library: os.
import os  # Make the os module available.
# Import the subprocess module so the app server can be started and stopped as a child process.  # Library: subprocess.
import subprocess  # The server lifecycle is managed here.
# Import the sys module so the same interpreter can run the server and the script can exit with a verdict.  # Library: sys.
import sys  # sys.executable points at this Python.
# Import the time module so the server startup can be polled with small sleeps.  # Library: time.
import time  # Used only for the health-check poll.
# Import urllib.request so the app's status route can be polled with the standard library.  # Library: urllib.request.
import urllib.request  # Localhost calls only.
# Import the synchronous Playwright API, our browser driver for the screenshots.  # Library: playwright.
from playwright.sync_api import sync_playwright  # The sync API keeps the shot sequence readable top to bottom.
# Define the folder this script lives in (the demo folder).  # Constant: demo folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of demo/.
# Define the project root (one level up from demo/).  # Constant: project root.
PROJECT = os.path.dirname(HERE)  # app.py and the modules live here.
# Define the folder that will hold the gallery stills (inside the repo, part of the submission package).  # Constant: gallery folder.
GALLERY = os.path.join(HERE, "gallery")  # Devpost gallery images go here.
# Define the private assets folder (outside the repo) that holds the selfie and the face-bearing payloads.  # Constant: assets folder.
ASSETS = os.path.join(PROJECT, "..", "demo-assets")  # The selfie and session payload stay out of git.
# Define the path of the cropped selfie the engine accepted in the verification run.  # Constant: photo path.
PHOTO_PATH = os.path.join(ASSETS, "scott-selfie-crop.jpg")  # A center crop of the user's own selfie - the same photo the live run verified.
# Define the path of the shared ARC secrets file where the YouCam key lives.  # Constant: secrets path.
SECRETS_PATH = os.path.expanduser("~/workspace/arc-secrets/.env")  # Mode-600 file; the value is loaded, never echoed.
# Define the local base URL of the running app.  # Constant: app URL.
APP_URL = "http://127.0.0.1:8770"  # app.py's default port, via the numeric loopback.
# Define the feedback sentence the filmed refine round uses (the demo's signature pushback).  # Constant: feedback text.
FEEDBACK_TEXT = "under $20 each and fragrance-free"  # Matches the verification run: 7 changes, basket $150 -> $66.
# Create the gallery folder if it does not exist yet.  # Step: prepare folder.
os.makedirs(GALLERY, exist_ok=True)  # Safe to re-run.
# Start the helper that loads the API key from the secrets file (value never printed).  # Function: load_api_key.
def load_api_key():  # Define load_api_key, which returns the key for the child env or exits loudly.
    # Open the secrets file for reading.  # Step: open secrets.
    with open(SECRETS_PATH, "r", encoding="utf-8") as handle:  # The file is small; a plain read is fine.
        # Walk every line looking for the YouCam key assignment.  # Loop: secret lines.
        for line in handle:  # One assignment per line in this file.
            # Split on the FIRST equals sign only, because values may contain equals padding.  # Step: split once.
            name, separator, value = line.strip().partition("=")  # partition never raises on a missing separator.
            # Only the API key variable is read by this script.  # Branch: wanted variable.
            if separator and name == "YOUCAM_API_KEY":  # Every other credential is ignored.
                # Return the bare value for the child process environment.  # Step: return value.
                return value.strip().strip('"').strip("'")  # The API wants the bare key.
    # Raise a loud failure when the key is absent, before any server or task starts.  # Step: fail loudly.
    raise SystemExit("YOUCAM_API_KEY not found in the secrets file; capture aborted")  # No key, no live capture - never a silent SAMPLE substitute.
# Start the helper that waits until the app's status route answers.  # Function: wait_for_server.
def wait_for_server():  # Poll /api/status until the child server is up.
    # Try for up to fifteen seconds before giving up.  # Step: poll loop.
    for _attempt in range(75):  # 75 tries at 0.2 s is a 15 s budget.
        # Attempt one status probe, tolerating connection errors while the server boots.  # Step: probe.
        try:  # The first probes usually fail because nothing listens yet.
            # Fetch the status snapshot.  # Step: fetch status.
            with urllib.request.urlopen(APP_URL + "/api/status", timeout=5) as response:  # The app answers on loopback.
                # Parse and return the snapshot for the caller's mode check.  # Step: return status.
                return json.loads(response.read().decode("utf-8"))  # mode must read "live-ready".
        # Any connection problem just means "not yet".  # Handler: not up yet.
        except Exception:  # Deliberately broad: early connection failures are expected.
            # Wait a beat and try again.  # Step: wait briefly.
            time.sleep(0.2)  # Gentle startup polling.
    # Raise if the server never came up, so the failure is loud and precise.  # Step: give up loudly.
    raise RuntimeError("app.py did not answer /api/status within 15 seconds")  # The server log explains why.
# Start the main capture sequence, executed only when this file is run directly.  # Block: main guard.
if __name__ == "__main__":  # Importing this file must never start a server or a browser.
    # Keep localhost traffic off any configured egress proxy so the app calls stay local.  # Step: proxy bypass.
    os.environ["no_proxy"] = "127.0.0.1,localhost"  # The sandbox proxy would otherwise try to relay loopback calls.
    # Load the API key for the server child process (value stays in memory and child env only).  # Step: load key.
    api_key = load_api_key()  # Never printed by this script.
    # Build the server child's environment: the basics plus the key, the demo port, and the proxy variables.  # Step: child env.
    child_env = {"PATH": os.environ.get("PATH", ""), "PORT": "8770", "LANG": "C.UTF-8", "YOUCAM_API_KEY": api_key}  # The key and port are set explicitly; proxies are inherited next.
    # Inherit the sandbox's egress-proxy variables: without them the server's curl transport goes direct, stalls, and the app falls back to SAMPLE (the first capture attempt died on exactly this).  # Step: inherit proxies.
    for proxy_name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy", "no_proxy", "NO_PROXY"):  # Both cases: different tools read different spellings.
        # Copy each proxy variable that the operator's shell actually carries.  # Branch: proxy present.
        if os.environ.get(proxy_name):  # Absent variables stay absent.
            # Pass the value through untouched (proxy addresses are configuration, not credentials).  # Step: copy proxy.
            child_env[proxy_name] = os.environ[proxy_name]  # The server's curl and urllib both honor these.
    # Start the real app server as a child process.  # Step: start server.
    server = subprocess.Popen([sys.executable, os.path.join(PROJECT, "app.py")], cwd=PROJECT, env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # Output is silenced; behavior is verified over HTTP and on screen.
    # Guard the whole session so the server is always shut down afterwards.  # Step: guarded session.
    try:  # Begin the guarded block.
        # Wait for the server and read its status snapshot.  # Step: wait for server.
        status = wait_for_server()  # Raises when the app never comes up.
        # Prove the server is in live-ready mode before spending a task in the browser.  # Branch: mode check.
        if status.get("mode") != "live-ready":  # Anything else means the key did not reach the child.
            # Fail loudly instead of filming a SAMPLE session dressed as live.  # Step: fail loudly.
            raise RuntimeError("server mode is " + str(status.get("mode")) + ", not live-ready; capture aborted")  # Honesty gate.
        # Report the status snapshot (mode facts only, never the key).  # Step: report status.
        print("status:", json.dumps(status))  # The status evidence for the run log.
        # Hold the /api/analyze payload when the browser receives it.  # State: session payload.
        session = {}  # Filled by the response listener below.
        # Start the browser session.  # Step: browser session.
        with sync_playwright() as playwright:  # The context manager closes everything on exit.
            # Launch headless Chromium.  # Step: launch browser.
            browser = playwright.chromium.launch()  # The proven local capture browser.
            # Open a 1280x720 page (the film's frame size).  # Step: new page.
            page = browser.new_page(viewport={"width": 1280, "height": 720})  # Gallery stills and film frames share this geometry.
            # Listen for the analyze response so the genuine session payload is saved verbatim.  # Step: response listener.
            def capture_response(response):  # Define the listener with the response object Playwright passes in.
                # Only the analyze route carries the session payload.  # Branch: analyze route.
                if "/api/analyze" in response.url:  # Other routes are ignored.
                    # Store the parsed payload for the save step after the session.  # Step: store payload.
                    session["analyze"] = response.json()  # Verbatim server response, mask URLs included - saved outside the repo.
                    # ALSO write it to disk immediately, so a later capture failure can never lose the one live session.  # Step: persist payload now.
                    with open(os.path.join(ASSETS, "live-ui-session.json"), "w", encoding="utf-8") as handle:  # demo-assets, beside the raw run record.
                        # Serialize the payload verbatim.  # Step: serialize now.
                        json.dump(session["analyze"], handle, indent=2)  # The record copy survives even if a screenshot step fails.
            # Register the listener on the page.  # Step: register listener.
            page.on("response", capture_response)  # Playwright calls it for every response.
            # Load the app.  # Step: load page.
            page.goto(APP_URL + "/")  # The single-page UI.
            # Wait until the mode badge settles on its live-ready wording.  # Step: wait badge.
            page.wait_for_function("document.getElementById('mode-badge').textContent.includes('Live-ready')", timeout=15000)  # The badge is the on-screen status proof.
            # Attach the user's selfie through the real file input, exactly like a user would.  # Step: attach photo.
            page.set_input_files("#photo-input", PHOTO_PATH)  # The cropped copy the engine accepts.
            # Wait until the photo preview is actually rendered.  # Step: wait preview.
            page.wait_for_function("!document.getElementById('photo-preview').classList.contains('hidden') || document.getElementById('photo-preview').style.display !== 'none'", timeout=10000)  # Best-effort visibility check.
            # Give the preview image a beat to paint.  # Step: settle.
            page.wait_for_timeout(800)  # A screenshot taken mid-paint would look broken.
            # Capture shot 1: the hero (with the Live-ready badge) plus the Step 1 card with the photo attached.  # Step: shot 1.
            hero_box = page.locator("header.hero").bounding_box()  # The hero's on-page rectangle (badge included).
            # Measure the Step 1 card the same way.  # Step: measure step 1.
            step1_box = page.locator("#step-describe").bounding_box()  # The describe card's rectangle.
            # Screenshot the union clip of hero + Step 1.  # Step: clip shot 1.
            page.screenshot(path=os.path.join(GALLERY, "shot1-hero-photo.png"), clip={"x": 0, "y": hero_box["y"], "width": 1280, "height": (step1_box["y"] + step1_box["height"]) - hero_box["y"]})  # One frame: brand, badge, concern, photo.
            # Click Analyze - this fires the session's ONE live task.  # Step: click analyze.
            page.click("#analyze-btn")  # The server uploads, creates the task, and polls.
            # Wait until the source line says LIVE, polling the page's own status texts so a failure explains itself.  # Step: wait results.
            live_seen = False  # Flips true only when the LIVE source line is really on screen.
            # Poll for up to three minutes (the verified live run took about ten seconds).  # Loop: wait polls.
            for _wait_round in range(90):  # 90 rounds at 2 s is a 180 s budget.
                # Read the three texts that together say what the app is doing.  # Step: read page state.
                page_state = page.evaluate("({source: document.getElementById('analysis-source').textContent, status: document.getElementById('analyze-status').textContent, banner: document.getElementById('sample-banner').textContent})")  # Source line, progress line, and SAMPLE banner in one read.
                # The LIVE source line ends the wait successfully.  # Branch: live landed.
                if "LIVE" in page_state["source"]:  # The exact wording the UI sets for a live result.
                    # Mark the success and stop polling.  # Step: live confirmed.
                    live_seen = True  # The frames below are a genuine live session.
                    # Leave the poll loop.  # Step: stop polling.
                    break  # Results are on screen.
                # Keep waiting quietly while the app works.  # Step: wait a round.
                page.wait_for_timeout(2000)  # Two seconds between reads.
            # A non-LIVE outcome stops the capture with the page's own words as the evidence.  # Branch: never live.
            if not live_seen:  # SAMPLE fallback, an error line, or a hang - all are reported, none are filmed over.
                # Fail loudly with the diagnostics attached.  # Step: fail with diagnostics.
                raise RuntimeError("analysis never reached LIVE; page state: " + json.dumps(page_state) + " | session mode: " + str(session.get("analyze", {}).get("mode")))  # The first attempt's silent 180 s timeout taught us to print this.
            # Let the score bars finish their animation.  # Step: settle scores.
            page.wait_for_timeout(1500)  # Bars animate on render; the still must show final values.
            # Capture shot 2: the Step 2 analysis card with the LIVE source line and every score bar.  # Step: shot 2.
            page.locator("#step-analysis").screenshot(path=os.path.join(GALLERY, "shot2-live-scores.png"))  # Element framing keeps the card crisp.
            # Capture shot 3: the Step 3 routine card with the product grid, try-on buttons, and basket total.  # Step: shot 3.
            page.locator("#step-routine").screenshot(path=os.path.join(GALLERY, "shot3-routine.png"))  # The routine as built from the live scores.
            # Click the first try-on button so the film can show the honestly labeled VTO state.  # Step: click try-on.
            page.locator("[data-tryon]").first.click()  # The Skin Veil tinted moisturizer card.
            # Wait until the try-on message line carries the server's answer.  # Step: wait try-on.
            page.wait_for_function("document.getElementById('tryon-message').textContent.length > 10", timeout=15000)  # The placeholder wording, verbatim from the server.
            # Capture shot 3b: the routine card again, now with the try-on answer visible.  # Step: shot 3b.
            page.locator("#step-routine").screenshot(path=os.path.join(GALLERY, "shot3b-tryon.png"))  # Same card, honest VTO state on screen.
            # Type the filmed feedback into the refine box.  # Step: type feedback.
            page.fill("#feedback-input", FEEDBACK_TEXT)  # Budget + fragrance-free in one sentence.
            # Click Refine (local agent math on the live scores; no new task, no units).  # Step: click refine.
            page.click("#refine-btn")  # The routine rebuilds under the new constraints.
            # Wait until the change list renders its items.  # Step: wait changes.
            page.wait_for_function("document.querySelectorAll('#change-list li').length > 0", timeout=15000)  # The receipt of what changed.
            # Capture shot 4: the Step 4 card with the full change list.  # Step: shot 4.
            page.locator("#step-refine").screenshot(path=os.path.join(GALLERY, "shot4-refine.png"))  # Feedback in, changes listed.
            # Build the title card as a tiny self-contained page and screenshot it at film size.  # Step: title card.
            title_html = "<html><body style='margin:0;background:#f7f1e6;font-family:Georgia,serif;color:#33402f;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center;max-width:900px'><div style='font-size:64px;font-weight:bold'>SkinSense Agent</div><div style='font-size:28px;margin-top:18px'>The skincare concierge that measures, recommends &mdash; and listens.</div><div style='font-size:20px;margin-top:34px;color:#7a6a53'>Live demo &middot; a real YouCam Skin AI analysis &middot; YouCam API Hackathon 2026</div></div></body></html>"  # Inline styles only; no external assets.
            # Render the title card into the same page.  # Step: render title.
            page.set_content(title_html)  # Replaces the app UI in this tab only.
            # Screenshot the title card at exactly 1280x720.  # Step: shoot title.
            page.screenshot(path=os.path.join(GALLERY, "shot0-title.png"))  # The film's opening frame.
            # Close the browser.  # Step: close browser.
            browser.close()  # The session is complete.
        # Save the genuine session payload outside the repo (it carries face mask URLs).  # Step: save session.
        with open(os.path.join(ASSETS, "live-ui-session.json"), "w", encoding="utf-8") as handle:  # demo-assets, beside the raw run record.
            # Serialize the payload verbatim.  # Step: serialize session.
            json.dump(session.get("analyze", {}), handle, indent=2)  # The record copy of what the UI actually received.
        # Report the session's headline facts for the film narration (scores are the user's own results).  # Step: report session.
        analyze = session.get("analyze", {})  # The payload the listener captured.
        # Print the mode and the normalized facts the narration will quote.  # Step: print facts.
        print("session mode:", analyze.get("mode"), "| overall:", analyze.get("analysis", {}).get("overall"), "| skin_age:", analyze.get("analysis", {}).get("skin_age"))  # Must read live / 74 / 31 if the engine is deterministic for the same photo.
        # Print the live priorities the narration names.  # Step: print priorities.
        print("session priorities:", [(item.get("type"), item.get("ui_score")) for item in analyze.get("priorities", [])])  # Weakest three, in order.
        # Print the routine totals the narration quotes.  # Step: print totals.
        print("session basket:", analyze.get("routine", {}).get("total_price"))  # The refine total appears in the change list on shot 4.
        # Announce the end of the capture.  # Step: done.
        print("capture complete")  # Gallery stills are in demo/gallery/.
    # Always stop the app server, whatever happened above.  # Finally: shutdown.
    finally:  # Runs on success and on failure alike.
        # Terminate the child process politely.  # Step: terminate app.
        server.terminate()  # The capture never leaves a server running behind it.
        # Wait briefly for the child to exit so the port is free.  # Step: reap app.
        server.wait(timeout=5)  # Five seconds is ample for this tiny server.
