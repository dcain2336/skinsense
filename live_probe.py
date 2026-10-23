# live_probe.py - the SkinSense live-integration probe, run by the demo operator (never by the web app).  # Module header: what this file is.
# Purpose: prove, against the REAL YouCam API, that (a) the stored credentials load, (b) Bearer auth is accepted, (c) the documented File API upload step works, and (d) the app reports live-ready on /api/status.  # Scope: what this probe verifies.
# It deliberately stops BEFORE creating a skin-analysis task: an analysis task needs a proper front-facing selfie, and this probe only has the user's stored profile photo, which is a distant two-person vacation shot (see the suitability verdict it prints).  # Honesty gate: no task is created from an unsuitable photo.
# Credentials are read from ~/workspace/arc-secrets/.env into the process environment only; their values are never printed, logged, or returned.  # Secret hygiene: presence booleans only.
# Import base64 so the stored secret block can be structurally validated as an RSA public key without printing it.  # Library: base64.
import base64  # Decode-only use: check the DER shape of the public key block.
# Import json so the probe can talk to the app's JSON routes and print compact verdicts.  # Library: json.
import json  # The app API and this probe both speak JSON.
# Import os so the probe can read paths and set environment variables for itself and the app subprocess.  # Library: os.
import os  # Environment and filesystem access.
# Import subprocess so the probe can start the real app server and stop it afterwards.  # Library: subprocess.
import subprocess  # Used once, to run app.py on a scratch port.
# Import sys so the probe can reference its own interpreter and exit with a verdict code.  # Library: sys.
import sys  # Interpreter path plus the process exit code.
# Import time so the probe can wait politely for the app server to come up.  # Library: time.
import time  # Short sleeps while polling the status route.
# Import urllib.request so the probe can call the local app routes with only the standard library.  # Library: urllib.request.
import urllib.request  # Localhost HTTP calls to the app under test.
# Define the path of the shared ARC secrets file where the YouCam credentials live.  # Constant: secrets path.
SECRETS_PATH = os.path.expanduser("~/workspace/arc-secrets/.env")  # Mode-600 file; values are loaded, never echoed.
# Define the path of the user's stored profile photo, the only photo of the user this probe may touch.  # Constant: photo path.
PHOTO_PATH = os.path.expanduser("~/workspace/profile-images/user-profile-reference.jpg")  # A real photo of the user, checked below for analysis suitability.
# Define the scratch port the app under test listens on, away from the demo port 8770.  # Constant: test port.
TEST_PORT = "8771"  # 8771 avoids clashing with a demo server on 8770.
# Define the directory this probe lives in, which is also the app directory.  # Constant: base dir.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # app.py and youcam.py sit next to this file.
# Start the helper that loads selected variables from the secrets file into the process environment.  # Function: load_secrets.
def load_secrets():  # Define load_secrets, which returns a presence report (never values).
    # Track which variables were found so the caller can print booleans only.  # Step: init report.
    found = {"YOUCAM_API_KEY": False, "YOUCAM_API_SECRET": False}  # Both start as missing until seen.
    # Open the secrets file for reading.  # Step: open secrets.
    with open(SECRETS_PATH, "r", encoding="utf-8") as handle:  # The file is small; a plain read is fine.
        # Walk every line looking for simple KEY=value assignments.  # Loop: secret lines.
        for line in handle:  # One assignment per line in this file.
            # Split on the FIRST equals sign only, because base64 values may themselves contain equals padding.  # Step: split once.
            name, separator, value = line.strip().partition("=")  # partition never raises on a missing separator.
            # Only load the two YouCam variables this probe is allowed to touch.  # Branch: wanted variable.
            if separator and name in found:  # Ignore every other service's credentials entirely.
                # Store the value (with any surrounding quotes removed) in the environment for this process and its children.  # Step: store value.
                os.environ[name] = value.strip().strip('"').strip("'")  # Quotes appear in some .env styles; the API wants the bare value.
                # Record that the variable was present, without recording the value anywhere.  # Step: mark found.
                found[name] = True  # Boolean only, by design.
    # Return the presence report.  # Step: return report.
    return found  # The caller prints this verbatim; it contains no secret material.
# Start the helper that structurally validates the stored secret as an RSA public-key block.  # Function: secret_looks_like_rsa_public_key.
def secret_looks_like_rsa_public_key():  # Define the validator, which returns True/False and never the key material.
    # Read the secret value from the environment the loader just populated.  # Step: read secret.
    raw = os.environ.get("YOUCAM_API_SECRET", "")  # Empty string when absent.
    # Guard the decode so malformed input becomes a clean False.  # Step: guarded decode.
    try:  # Begin the guarded block.
        # Base64-decode the block into its DER bytes.  # Step: decode.
        der = base64.b64decode(raw, validate=True)  # validate=True rejects stray characters instead of guessing.
    # Any decode failure means the block is not the documented RSA public key.  # Handler: bad base64.
    except Exception:  # Deliberately broad: any failure is simply "not valid".
        # Report invalid without details.  # Step: return invalid.
        return False  # The caller prints this boolean only.
    # A DER SEQUENCE starts with byte 0x30; a SubjectPublicKeyInfo also embeds the rsaEncryption OID bytes.  # Step: shape check.
    return der[:1] == b"\x30" and b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01" in der  # Both markers must be present.
# Start the helper that verifies the photo's magic bytes and reads its pixel dimensions from the JPEG headers.  # Function: inspect_photo.
def inspect_photo():  # Define inspect_photo, which returns (is_jpeg, width, height, byte_count).
    # Read the whole photo into memory (it is small).  # Step: read photo.
    with open(PHOTO_PATH, "rb") as handle:  # Binary mode: we need the raw header bytes.
        # Keep the bytes for the header walk.  # Step: keep bytes.
        data = handle.read()  # The full JPEG file.
    # JPEG files start with the SOI marker FF D8 followed by a marker byte FF.  # Step: magic check.
    is_jpeg = data[:3] == b"\xff\xd8\xff"  # Three magic bytes are the file signature.
    # Start the dimension scan with unknown dimensions.  # Step: init dims.
    width, height = 0, 0  # Filled in when a Start-Of-Frame segment is found.
    # Walk the JPEG marker segments looking for SOF0 (C0) or SOF2 (C2), which carry the frame size.  # Step: segment walk.
    index = 2  # The first segment starts right after the SOI marker.
    # Continue while we have bytes left to read a marker and a length.  # Loop: segments.
    while index + 9 < len(data):  # Nine bytes cover marker, length, and the SOF payload we need.
        # Markers are introduced by an FF byte; anything else means the walk is lost.  # Branch: marker sync.
        if data[index] != 0xFF:  # Not at a marker boundary.
            # Stop the walk and keep whatever dimensions we have (possibly none).  # Step: bail out.
            break  # The magic check above already proved it is a JPEG.
        # Read the marker code that follows the FF byte.  # Step: marker code.
        marker = data[index + 1]  # C0/C2 are the frame headers we want.
        # Read the big-endian segment length, which includes its own two bytes.  # Step: segment length.
        seg_len = int.from_bytes(data[index + 2:index + 4], "big")  # JPEG lengths are big-endian.
        # SOF0 and SOF2 carry precision(1), height(2), width(2) right after the length.  # Branch: frame header.
        if marker in (0xC0, 0xC2):  # Baseline or progressive frame header.
            # Extract the height and width from the documented offsets.  # Step: read dims.
            height = int.from_bytes(data[index + 5:index + 7], "big")  # Height comes first in a SOF segment.
            # Extract the width the same way.  # Step: read width.
            width = int.from_bytes(data[index + 7:index + 9], "big")  # Width follows height.
            # Dimensions are known; stop walking.  # Step: done.
            break  # Nothing else in the headers matters here.
        # Advance to the next segment using its declared length.  # Step: advance.
        index += 2 + seg_len  # Marker bytes plus the segment payload.
    # Return the verdict pieces.  # Step: return verdict.
    return is_jpeg, width, height, len(data)  # The caller decides suitability from these facts.
# Start the helper that performs one JSON call against the local app under test.  # Function: app_call.
def app_call(method, path, payload=None):  # Define app_call with the HTTP method, the route path, and an optional JSON payload.
    # Build the full local URL on the scratch port.  # Step: build URL.
    url = "http://127.0.0.1:" + TEST_PORT + path  # Localhost only; the app never leaves this machine here.
    # Encode the payload when one was provided.  # Step: encode body.
    body = json.dumps(payload).encode("utf-8") if payload is not None else None  # GET calls pass no body.
    # Build the request object.  # Step: build request.
    request = urllib.request.Request(url, data=body, method=method)  # urllib fills in the length header.
    # Declare JSON when a body is present so the app parses it.  # Branch: has body.
    if body is not None:  # POST calls carry JSON.
        # Attach the content type the app's parser expects.  # Step: content type.
        request.add_header("Content-Type", "application/json")  # The app reads raw JSON regardless, but correctness is free.
    # Perform the call and parse the JSON answer.  # Step: perform call.
    with urllib.request.urlopen(request, timeout=30) as response:  # A hung app should fail the probe, not hang it.
        # Decode and parse the response body.  # Step: parse body.
        return json.loads(response.read().decode("utf-8"))  # App routes always answer JSON.
# Start the main probe sequence, run only when this file is executed directly.  # Block: main guard.
if __name__ == "__main__":  # Importing this file must never fire network calls.
    # Keep localhost traffic off any configured egress proxy so the app calls stay local.  # Step: proxy bypass.
    os.environ["no_proxy"] = "127.0.0.1,localhost"  # The sandbox proxy would otherwise try to relay loopback calls.
    # Load the stored credentials into this process (values stay in memory and in child env only).  # Step: load secrets.
    presence = load_secrets()  # Booleans only; safe to print.
    # Report which credentials were found, without values.  # Step: report presence.
    print("credentials present:", presence)  # Example: {"YOUCAM_API_KEY": True, "YOUCAM_API_SECRET": True}.
    # Report whether the secret is structurally the documented RSA public key.  # Step: report secret shape.
    print("secret is a structurally valid RSA public-key block:", secret_looks_like_rsa_public_key())  # Needed only if an endpoint demands the id_token flow.
    # Verify the user's photo: real JPEG magic plus its true pixel dimensions.  # Step: inspect photo.
    is_jpeg, photo_w, photo_h, photo_bytes = inspect_photo()  # Facts first; the suitability call comes next.
    # Report the photo facts.  # Step: report photo facts.
    print("photo: is_jpeg =", is_jpeg, "| dimensions =", str(photo_w) + "x" + str(photo_h), "| bytes =", photo_bytes)  # Small, distant shots fail the API's face requirements.
    # Judge suitability the way Perfect Corp's photo guidance does: skin analysis needs a close, front-facing face at usable resolution.  # Step: suitability rule.
    photo_suitable = is_jpeg and photo_w >= 480 and photo_h >= 480  # 480px is a floor, not a guarantee; framing is judged by the operator from the printed facts.
    # Report the suitability verdict explicitly, because it gates the analysis step below.  # Step: report suitability.
    print("photo suitable for skin analysis (resolution floor only):", photo_suitable)  # Framing (two people, sunglasses, full-body) is assessed in the run report.
    # Import the real client only after the environment carries the key, mirroring how app.py runs.  # Step: import client.
    import youcam  # Reads YOUCAM_API_KEY from the environment at call time.
    # Report the client's own configuration verdict.  # Step: report configured.
    print("youcam client configured (key seen):", youcam.is_configured())  # True means live calls are possible.
    # Exercise the documented File API upload step (metadata + pre-signed PUT) with the user's own photo bytes.  # Step: live upload probe.
    try:  # The upload step is the cheapest real call that proves Bearer auth end to end.
        # Read the photo bytes for the upload.  # Step: read photo bytes.
        with open(PHOTO_PATH, "rb") as handle:  # Binary read, as the client expects raw bytes.
            # Keep the bytes for the client call.  # Step: keep photo bytes.
            raw_photo = handle.read()  # Exactly what a browser upload would send.
        # Run steps 1-2 of the documented flow through the production client code.  # Step: upload via client.
        file_id = youcam.upload_image(raw_photo, "image/jpeg", "user-profile-reference.jpg")  # Returns the API-issued file_id on success.
        # Report upload success with the API-issued identifier (not a credential).  # Step: report upload.
        print("LIVE File API upload: OK, file_id =", file_id)  # Proves Bearer auth + the v2.0 file endpoint + the pre-signed PUT all work.
    # A client error here carries the API's own status and message, which decides the next move (e.g. auth flow).  # Handler: upload failure.
    except youcam.YouCamError as error:  # The client normalizes every failure into this type.
        # Report the failure verbatim (it contains status and API text, never the key).  # Step: report upload failure.
        print("LIVE File API upload: FAILED ->", str(error))  # The run report quotes this line.
    # A raw timeout escaping the client is itself a finding (a transport bug), so report it instead of crashing the probe.  # Handler: raw transport escape.
    except (TimeoutError, OSError) as error:  # The client was patched 2026-10-23 to translate these; an escape means the patch missed a path.
        # Report the escaped error type and message.  # Step: report escape.
        print("LIVE File API upload: RAW TRANSPORT ERROR ESCAPED ->", type(error).__name__, str(error))  # Should never print after the client fix.
    # State the analysis gate out loud so the log is self-explanatory.  # Step: analysis gate note.
    print("analysis task: NOT created by this probe (photo suitability gate; see run report)")  # The full analyze step runs once a proper front-facing selfie exists.
    # Start the real app server on the scratch port with the credentials in its environment.  # Step: start app.
    child_env = dict(os.environ)  # Copy the environment, credentials included, for the child process.
    # Point the child at the scratch port.  # Step: set child port.
    child_env["PORT"] = TEST_PORT  # app.py reads PORT at import time.
    # Launch app.py as a subprocess and keep the handle for shutdown.  # Step: launch app.
    server = subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "app.py")], cwd=BASE_DIR, env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # Output is silenced; the probe verifies behavior over HTTP instead.
    # Guard the HTTP checks so the server is always shut down afterwards.  # Step: guarded app checks.
    try:  # Begin the guarded block.
        # Poll the status route until the server answers or the wait budget runs out.  # Step: wait for server.
        status = None  # Filled by the first successful status call.
        # Try for up to about ten seconds.  # Loop: status wait.
        for _attempt in range(40):  # 40 tries at a quarter second each.
            # Attempt one status call.  # Step: guarded status call.
            try:  # The server may not be listening yet.
                # Fetch the status snapshot.  # Step: fetch status.
                status = app_call("GET", "/api/status")  # Raises until the server is up.
                # Success means we can stop waiting.  # Step: stop waiting.
                break  # Exit the wait loop.
            # Any connection error just means "not up yet" during the wait window.  # Handler: not up yet.
            except Exception:  # Deliberately broad: early connection failures are expected.
                # Wait a quarter second before the next try.  # Step: wait briefly.
                time.sleep(0.25)  # Gentle startup polling.
        # Report the status snapshot verbatim (it contains mode facts, never the key).  # Step: report status.
        print("/api/status:", json.dumps(status))  # mode should read "live-ready" with the key loaded.
        # Run a text-only analyze through the real app: with a key but no photo it must answer with an honestly labeled SAMPLE.  # Step: text-only analyze.
        analyze = app_call("POST", "/api/analyze", {"concern": "dry, tight and red by midday", "photo_data_url": ""})  # No photo on purpose: exercises the labeled fallback.
        # Report the analyze verdict pieces.  # Step: report analyze.
        print("/api/analyze (no photo): mode =", analyze.get("mode"), "| priorities =", [p.get("type") for p in analyze.get("priorities", [])], "| basket total =", analyze.get("routine", {}).get("total_price"))  # Mode must be "sample" with a clear notice.
        # Run one refine round against the returned state to prove the loop closes through the real server.  # Step: refine round.
        refined = app_call("POST", "/api/refine", {"feedback": "under $20 each and fragrance-free", "state": analyze.get("state", {})})  # Budget + fragrance constraints in one sentence.
        # Report the refine verdict pieces.  # Step: report refine.
        print("/api/refine: mode =", refined.get("mode"), "| changes =", len(refined.get("changes", [])), "| new basket total =", refined.get("routine", {}).get("total_price"))  # A nonzero change count plus a lower total proves the refine worked.
    # Always stop the app server, whatever happened above.  # Finally: shutdown.
    finally:  # Runs on success and on failure alike.
        # Terminate the child process politely.  # Step: terminate app.
        server.terminate()  # The probe never leaves a server running behind it.
        # Wait briefly for the child to exit so the port is free.  # Step: reap app.
        server.wait(timeout=5)  # Five seconds is ample for this tiny server.
    # Announce the end of the probe run.  # Step: done.
    print("probe complete")  # The run report is written by the operator from the lines above.
