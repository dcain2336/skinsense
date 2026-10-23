# youcam.py - the YouCam (Perfect Corp) Skin AI API client for SkinSense Agent.  # Module header: what this file is.
# This client implements the REAL documented YouCam V2 server-to-server flow, read from Perfect Corp's own docs on 2026-10-23.  # Provenance: official documentation, not guesswork.
# Documentation sources: the "Skin Analysis API Usage Guide" at https://yce.perfectcorp.com/document/index.html and the current docs portal at https://docs.perfectcorp.com/develop/introduction (API version v1.16).  # Sources: where the spec below came from.
# The flow has four steps: (1) POST the file metadata to the File API to get a pre-signed upload URL plus a file_id, (2) PUT the image bytes to that URL, (3) POST a skin-analysis task with the file_id, (4) poll the task until it succeeds.  # Flow summary: upload, task, poll.
# Authentication is a single header on every API call: Authorization: Bearer <YOUCAM_API_KEY>; the V2 API has no separate login endpoint.  # Auth: one bearer header, per the docs.
# LIVE VERIFICATION 2026-10-23: with the real key, the FULL flow succeeded end to end through this client - File API upload, the v2.0 task endpoint, polling, and normalization - on the user's own front-facing selfie (see live_run.py and the verification log in SUBMISSION-DRAFT.md). Verified response facts the normalizer relies on: results.output carries 11 entries (the 8 SD concerns with ui_score/raw_score/mask_urls, plus "all" and "skin_age" entries whose values live in a "score" field, plus an auxiliary "resize_image" entry). One engine lesson: the full-frame selfie was rejected with error_src_face_too_small; a tighter center crop of the same photo was accepted.  # Provenance: live probe + live run, 2026-10-23.
# TRANSPORT NOTE 2026-10-23: api_request and put_presigned try curl first because urllib response reads stall inside the ARC sandbox's egress proxy (the same call took 1.7s via curl vs a 30s read timeout via urllib); urllib remains the fallback and is the normal path on unrestricted networks.  # Why two transports exist.
# The API key is read from the environment only, so it never appears in source code, the browser, or git history.  # Secret hygiene: env var only.
# Import the JSON module so request and response bodies can be encoded and decoded.  # Library: json.
import json  # Make the json module available.
# Import the OS module so the client can read its configuration from environment variables.  # Library: os.
import os  # Make the os module available.
# Import the subprocess module so the transport can shell out to curl, the proven HTTPS carrier in restricted sandboxes.  # Library: subprocess.
import subprocess  # Used by the curl-first transport below; the app still needs no pip installs.
# Import the time module so the polling loop can sleep between status checks.  # Library: time.
import time  # Make the time module available.
# Import urllib.request so the client can make HTTPS calls with only the standard library.  # Library: urllib.request.
import urllib.request  # The standard-library HTTP client.
# Import urllib.error so HTTP failures can be caught and reported cleanly.  # Library: urllib.error.
import urllib.error  # HTTP error types live here.
# Define the default API host exactly as documented (the "YouCam API server" in the docs).  # Constant: API host.
DEFAULT_BASE_URL = "https://yce-api-01.makeupar.com"  # Documented server: https://yce-api-01.makeupar.com.
# Define the base URL actually used, allowing an environment override for staging or testing.  # Constant: active base URL.
BASE_URL = os.environ.get("YOUCAM_API_BASE", DEFAULT_BASE_URL).rstrip("/")  # Env override wins; otherwise the documented host.
# Define the API version segment used in task paths; the official usage guide documents v2.0 for every step.  # Constant: API version.
API_VERSION = os.environ.get("YOUCAM_API_VERSION", "v2.0")  # Default "v2.0" per the official guide.
# VERIFIED LIVE 2026-10-23: the task endpoint accepts v2.0 (a task was created and completed under it), so the v2.1 fallback stays only as an env override and was never needed.  # Version question: settled by the live run.
# Define the feature name used in both the File API path and the Task API path.  # Constant: feature slug.
FEATURE = "skin-analysis"  # The docs require the exact feature identifier in the path.
# Define the standard-definition (SD) skin concerns this app requests, exactly as named in the docs.  # Constant: requested concerns.
DST_ACTIONS = ["moisture", "oiliness", "redness", "acne", "pore", "texture", "wrinkle", "radiance"]  # Eight SD concerns; never mix SD and HD (hd_*) actions in one task, the API rejects mixed calls.
# Define how long the client will poll a task before giving up, in seconds.  # Constant: poll timeout.
POLL_TIMEOUT_SECONDS = 150  # Skin tasks usually finish in well under a minute; 150s is a safe ceiling.
# Define the pause between two task-status polls, in seconds.  # Constant: poll interval.
POLL_INTERVAL_SECONDS = 3  # The docs allow flexible polling because results are retained for 24 hours.
# Define the per-request network timeout, in seconds.  # Constant: HTTP timeout.
HTTP_TIMEOUT_SECONDS = 30  # No single call should hang longer than this.
# Define a browser-like user agent, because some networks reject the default Python user agent.  # Constant: user agent.
USER_AGENT = "curl/8.0"  # A plain user agent string that passes picky egress proxies.
# Start the exception type every client failure is reported through.  # Class: YouCamError.
class YouCamError(Exception):  # Define YouCamError so callers can catch one error type.
    pass  # The exception carries only its message; no extra state is needed.
# Start the helper that reads the API key from the environment.  # Function: get_api_key.
def get_api_key():  # Define get_api_key, which returns the configured key or an empty string.
    # Read the key fresh each call so a restarted shell or rotated key is picked up.  # Step: read env.
    return os.environ.get("YOUCAM_API_KEY", "").strip()  # Empty string means "not configured" and triggers mock mode upstream.
# Start the helper that reports whether live mode is possible.  # Function: is_configured.
def is_configured():  # Define is_configured, a simple yes/no used by the status endpoint.
    # Live mode exists only when a non-empty key is present.  # Step: check key.
    return bool(get_api_key())  # True when YOUCAM_API_KEY is set.
# Start the low-level helper that performs one JSON HTTP call against the API.  # Function: api_request.
def api_request(method, path, payload=None):  # Define api_request with the HTTP method, the API path, and an optional JSON payload.
    # Build the full URL from the configured base plus the path.  # Step: build URL.
    url = BASE_URL + path  # Every documented path starts with /s2s/.
    # Encode the payload as JSON bytes when one was provided.  # Step: encode body.
    body = json.dumps(payload).encode("utf-8") if payload is not None else None  # GET calls pass no body.
    # Try the curl transport first: in the ARC sandbox, urllib reads stall inside the egress proxy (verified live 2026-10-23), while curl answers the same API in under two seconds.  # Step: curl transport.
    raw_text = _curl_request(method, url, body)  # Returns the response text, None when curl is unusable, and raises YouCamError on a real HTTP error.
    # Fall back to urllib when curl is missing or the proxy refused the connection outright; normal machines take this path too.  # Branch: urllib fallback.
    if raw_text is None:  # None is the "curl could not carry this call" signal, distinct from an empty 200 body.
        # Build the HTTP request object with the method and body.  # Step: build request.
        request = urllib.request.Request(url, data=body, method=method)  # urllib derives Content-Length from the body.
        # Attach the documented bearer authorization header.  # Step: auth header.
        request.add_header("Authorization", "Bearer " + get_api_key())  # Header shape: "Authorization: Bearer <API_KEY>".
        # Declare that the body (when present) is JSON, as every documented example does.  # Step: content type.
        request.add_header("Content-Type", "application/json")  # The documented examples always send this header.
        # Attach the user agent so restrictive networks let the call through.  # Step: user agent.
        request.add_header("User-Agent", USER_AGENT)  # Mirrors the header the docs' curl examples effectively send.
        # Guard the network call so failures become YouCamError with a readable message.  # Step: guarded call.
        try:  # Begin the guarded network block.
            # Open the request and read the whole response body.  # Step: perform request.
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # The context manager closes the connection for us.
                # Decode the response body from UTF-8 bytes to text.  # Step: decode body.
                raw_text = response.read().decode("utf-8")  # API responses are JSON text.
        # Catch HTTP-level failures (4xx and 5xx) and translate them.  # Handler: HTTP error.
        except urllib.error.HTTPError as error:  # urllib raises HTTPError for non-2xx statuses.
            # Read whatever error body the API returned, because it carries the documented error_code.  # Step: read error body.
            error_text = error.read().decode("utf-8", errors="replace")  # Replace undecodable bytes instead of crashing.
            # Raise a client error that preserves the status and the API's own message.  # Step: raise translated error.
            raise YouCamError("YouCam API HTTP " + str(error.code) + ": " + error_text[:400])  # Truncate long bodies for readable logs.
        # Catch transport-level failures (DNS, TLS, timeouts) and translate them too.  # Handler: transport error.
        except urllib.error.URLError as error:  # URLError covers connection problems without an HTTP status.
            # Raise a client error describing the transport problem.  # Step: raise transport error.
            raise YouCamError("YouCam API unreachable: " + str(error.reason))  # The reason string explains the failure.
        # Catch bare socket timeouts and OS errors, which urllib lets escape unwrapped during response reads.  # Handler: raw timeout.
        except (TimeoutError, OSError) as error:  # A stalled proxy read lands here, not in URLError (seen live 2026-10-23).
            # Raise a client error instead of leaking a traceback through the agent.  # Step: raise timeout error.
            raise YouCamError("YouCam API transport failed: " + str(error))  # The agent turns this into the labeled SAMPLE fallback.
    # Parse the JSON text into a dictionary.  # Step: parse JSON.
    parsed = json.loads(raw_text) if raw_text else {}  # An empty body becomes an empty dictionary.
    # The documented envelope carries a numeric "status"; anything but 200 is an API-level error.  # Step: check envelope.
    if parsed.get("status") not in (None, 200):  # Some endpoints omit status on success, so None is acceptable.
        # Raise with the API's documented "error" and "error_code" fields when present.  # Step: raise API error.
        raise YouCamError("YouCam API error " + str(parsed.get("error_code", parsed.get("status"))) + ": " + str(parsed.get("error", "unknown")))  # Example documented shape: {"status": 400, "error": "...", "error_code": "InvalidParameters"}.
    # Return the parsed envelope to the caller.  # Step: return envelope.
    return parsed  # Callers read the "data" member of the envelope.
# Start the curl transport helper used first by api_request and put_presigned.  # Function: _curl_request.
def _curl_request(method, url, body=None, extra_headers=None):  # Define _curl_request with the method, URL, optional body bytes, and optional caller-supplied headers.
    # Build the curl command: silent progress, errors shown, a hard per-call ceiling so a wedged proxy fails fast instead of hanging the app.  # Step: build command.
    command = ["curl", "-sS", "--max-time", str(HTTP_TIMEOUT_SECONDS), "-X", method, url]  # -sS hides progress but keeps real error text.
    # Attach the documented bearer header unless the caller is hitting a pre-signed URL (those must NOT carry it).  # Branch: bearer or not.
    if extra_headers is None:  # API calls pass no extra headers and get the bearer header.
        # Attach the authorization header the same way the urllib path does.  # Step: bearer header.
        command += ["-H", "Authorization: Bearer " + get_api_key()]  # Header shape: "Authorization: Bearer <API_KEY>".
        # Declare JSON bodies, matching every documented example.  # Step: content type.
        command += ["-H", "Content-Type: application/json"]  # Harmless on GET calls too.
    # Otherwise attach exactly the caller-supplied headers (the pre-signed PUT contract).  # Branch: caller headers.
    else:  # Pre-signed PUTs land here with their signed header set.
        # Copy each required header into the command.  # Loop: signed headers.
        for header_name, header_value in extra_headers.items():  # The signed URL is valid only with these exact headers.
            # Append one header argument pair.  # Step: append header.
            command += ["-H", header_name + ": " + str(header_value)]  # Values arrive as strings in the documented example.
    # Attach the user agent so restrictive networks treat curl like the documented examples.  # Step: user agent.
    command += ["-H", "User-Agent: " + USER_AGENT]  # Same reasoning as the urllib path.
    # Pipe the request body through stdin so no payload (and no credential) ever sits in a temp file or a shell string.  # Branch: has body.
    stdin_bytes = None  # Stays None for plain GET calls.
    # Only attach a body when the caller provided one.  # Branch: body present.
    if body is not None:  # POST calls and the image PUT land here.
        # Tell curl to read the body from stdin verbatim.  # Step: stdin body flag.
        command += ["--data-binary", "@-"]  # @- means standard input, byte for byte.
        # Remember the bytes for the subprocess call below.  # Step: keep body.
        stdin_bytes = body  # bytes for API JSON, raw image bytes for the PUT.
    # Ask curl to append the numeric HTTP status on its own trailer line so the helper can judge success itself.  # Step: status trailer.
    command += ["-w", "\n__HTTP_STATUS__:%{http_code}"]  # The marker line is stripped before the body is returned.
    # Guard the subprocess so every failure mode becomes either a YouCamError or the None "use urllib instead" signal.  # Step: guarded curl.
    try:  # Begin the guarded subprocess block.
        # Run curl with the body on stdin and a subprocess ceiling slightly above curl's own.  # Step: run curl.
        result = subprocess.run(command, input=stdin_bytes, capture_output=True, timeout=HTTP_TIMEOUT_SECONDS + 15)  # capture keeps curl chatter out of the app's logs.
    # A missing curl binary means this machine cannot use the fast path at all.  # Handler: no curl.
    except FileNotFoundError:  # shutil lookups fail this way when the binary is absent.
        # Signal the caller to use urllib.  # Step: signal fallback.
        return None  # None means "curl unusable", never an API verdict.
    # A subprocess-level timeout means curl itself hung past its own ceiling.  # Handler: subprocess timeout.
    except subprocess.TimeoutExpired:  # Should not happen given --max-time, but belt and braces.
        # Signal the caller to use urllib, which may still get through.  # Step: signal fallback.
        return None  # The urllib path raises a proper YouCamError if it also fails.
    # Split the status trailer off the end of stdout.  # Step: split trailer.
    stdout_text = result.stdout.decode("utf-8", errors="replace")  # API bodies are JSON text; the PUT body is empty.
    # Find the trailer marker from the end, because the body itself could contain similar text.  # Step: find marker.
    marker_at = stdout_text.rfind("\n__HTTP_STATUS__:")  # The last occurrence is curl's trailer.
    # Without a trailer the response is unusable; treat it as a transport failure and let urllib arbitrate.  # Branch: no trailer.
    if marker_at < 0:  # curl died mid-stream (for example the proxy closed the connection).
        # Signal the caller to use urllib.  # Step: signal fallback.
        return None  # One more chance via the other transport.
    # Read the numeric status from the trailer.  # Step: read status.
    status = int(stdout_text[marker_at + len("\n__HTTP_STATUS__:"):].strip() or "0")  # Zero when the trailer is malformed.
    # Everything before the marker is the real response body.  # Step: body text.
    response_text = stdout_text[:marker_at]  # Returned to the caller untouched.
    # A connection-level curl failure (DNS, refused, proxy reset) exits non-zero with no HTTP status; urllib gets the final say.  # Branch: transport failure.
    if result.returncode != 0 and status == 0:  # curl reported no HTTP exchange at all.
        # Signal the caller to use urllib.  # Step: signal fallback.
        return None  # Distinguishes "network said nothing" from "API said no".
    # HTTP errors are real API verdicts and must surface with the API's own error body, never be retried blindly.  # Branch: HTTP error.
    if status >= 400:  # 4xx and 5xx are answers, not transport problems.
        # Raise the same translated error the urllib path raises.  # Step: raise HTTP error.
        raise YouCamError("YouCam API HTTP " + str(status) + ": " + response_text[:400])  # Body carries the documented error_code.
    # Success: hand the raw body text (or the raw-bytes marker for the PUT) to the caller.  # Step: return body.
    return response_text  # api_request parses this as JSON; put_presigned ignores the content.
# Start the helper that uploads raw image bytes to a pre-signed URL from the File API.  # Function: put_presigned.
def put_presigned(url, headers, image_bytes):  # Define put_presigned with the signed URL, its required headers, and the image bytes.
    # Try the curl transport first, with exactly the signed headers and NO bearer header (the signature forbids extras beyond the signed set plus our user agent).  # Step: curl PUT.
    if _curl_request("PUT", url, body=image_bytes, extra_headers=headers) is not None:  # A non-None return means curl carried the upload successfully.
        # Curl delivered the bytes; the step is done.  # Step: PUT complete.
        return  # S3 answered 2xx with an empty body, which the helper already validated.
    # Build a PUT request carrying the image bytes as the body.  # Step: build PUT request.
    request = urllib.request.Request(url, data=image_bytes, method="PUT")  # The docs' step 4 is a plain PUT of the file.
    # Copy every header the File API told us to send (Content-Type and Content-Length).  # Step: copy signed headers.
    for header_name, header_value in headers.items():  # The signed URL is only valid with these exact headers.
        # Attach one required header to the request.  # Step: attach header.
        request.add_header(header_name, str(header_value))  # Values arrive as strings in the documented example.
    # Attach the user agent for the same network reason as the API calls.  # Step: user agent.
    request.add_header("User-Agent", USER_AGENT)  # The upload goes to S3; the header is harmless there.
    # Guard the upload so failures become YouCamError.  # Step: guarded upload.
    try:  # Begin the guarded upload block.
        # Perform the PUT; a 2xx response with an empty body means success.  # Step: perform PUT.
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # S3 answers 200 with no JSON body.
            # Drain the body so the connection closes cleanly.  # Step: drain body.
            response.read()  # Nothing to parse; success is the status code.
    # Catch HTTP failures during the upload.  # Handler: upload HTTP error.
    except urllib.error.HTTPError as error:  # A bad signature or wrong header lands here.
        # Raise a readable upload error.  # Step: raise upload error.
        raise YouCamError("Image upload failed with HTTP " + str(error.code))  # The signed URL or its headers were rejected.
    # Catch transport failures during the upload.  # Handler: upload transport error.
    except urllib.error.URLError as error:  # Connection problems land here.
        # Raise a readable transport error.  # Step: raise transport error.
        raise YouCamError("Image upload unreachable: " + str(error.reason))  # Explain the connection failure.
    # Catch bare socket timeouts and OS errors, which urllib lets escape unwrapped during reads.  # Handler: upload raw timeout.
    except (TimeoutError, OSError) as error:  # A stalled proxy read lands here (seen live 2026-10-23).
        # Raise a readable transport error instead of a traceback.  # Step: raise timeout error.
        raise YouCamError("Image upload transport failed: " + str(error))  # The agent turns this into the labeled SAMPLE fallback.
# Start step 1+2 of the documented flow: register the file, upload it, and return the file_id.  # Function: upload_image.
def upload_image(image_bytes, content_type, file_name):  # Define upload_image with the raw bytes, the MIME type, and a display file name.
    # Build the documented File API payload describing the file we are about to upload.  # Step: file payload.
    payload = {"files": [{"content_type": content_type, "file_name": file_name, "file_size": len(image_bytes)}]}  # Field names verified in the official usage guide's curl example.
    # Call the File API for this feature to obtain the upload instructions.  # Step: file API call.
    envelope = api_request("POST", "/s2s/v2.0/file/" + FEATURE, payload)  # The File API path uses v2.0 in the documented example.
    # Pull the first (and only) file entry out of the documented response shape.  # Step: read file entry.
    file_entry = envelope.get("data", {}).get("files", [{}])[0]  # Shape: data.files[0] holds file_id and requests.
    # Read the file_id that later steps use to reference this upload.  # Step: read file_id.
    file_id = file_entry.get("file_id", "")  # Without this the task cannot be created.
    # Read the list of signed upload requests for this file.  # Step: read requests.
    upload_requests = file_entry.get("requests", [])  # Shape: data.files[0].requests[0] holds method, url, headers.
    # Fail loudly if the response did not carry what the docs promise.  # Step: validate response.
    if not file_id or not upload_requests:  # A missing file_id or URL means the flow cannot continue.
        # Raise an error that names the unexpected shape.  # Step: raise shape error.
        raise YouCamError("File API response was missing file_id or the upload URL")  # Honest failure beats a silent wrong call later.
    # Take the first upload request (the docs describe exactly one for a single file).  # Step: pick request.
    upload_request = upload_requests[0]  # It carries the pre-signed URL and its required headers.
    # Upload the actual bytes to the pre-signed URL with the required headers.  # Step: PUT bytes.
    put_presigned(upload_request.get("url", ""), upload_request.get("headers", {}), image_bytes)  # Skipping this step makes later calls fail with 500/404, per the docs' warning.
    # Return the file_id so the task step can reference the uploaded photo.  # Step: return file_id.
    return file_id  # The caller passes this into create_task as src_file_id.
# Start step 3 of the documented flow: create the skin-analysis task.  # Function: create_task.
def create_task(file_id):  # Define create_task with the uploaded file's identifier.
    # Build the documented task payload: the source file, the SD concerns to score, mask options, and JSON output.  # Step: task payload.
    payload = {  # Open the task payload dictionary.
        "src_file_id": file_id,  # Field name verified in the official usage guide.
        "dst_actions": DST_ACTIONS,  # All SD actions; mixing in hd_* actions would be rejected as InvalidParameters.
        "miniserver_args": {"enable_mask_overlay": False},  # False keeps per-concern mask URLs separate, matching the documented default.
        "format": "json",  # "json" returns scores inline instead of a ZIP download, per the v1.7 release notes.
    }  # Close the task payload dictionary.
    # POST the task to the versioned task endpoint.  # Step: task API call.
    envelope = api_request("POST", "/s2s/" + API_VERSION + "/task/" + FEATURE, payload)  # Default path: /s2s/v2.0/task/skin-analysis.
    # Read the task_id out of the documented response shape.  # Step: read task_id.
    task_id = envelope.get("data", {}).get("task_id", "")  # Shape: data.task_id.
    # Fail loudly if no task_id came back.  # Step: validate task_id.
    if not task_id:  # Without a task_id there is nothing to poll.
        # Raise an error naming the problem.  # Step: raise task error.
        raise YouCamError("Task API response was missing task_id")  # The create call did not start a task.
    # Return the task_id for polling.  # Step: return task_id.
    return task_id  # The caller polls with this identifier.
# Start step 4 of the documented flow: poll one task until it succeeds, fails, or times out.  # Function: poll_task.
def poll_task(task_id):  # Define poll_task with the task identifier to watch.
    # Remember when polling started so the timeout can be enforced.  # Step: start clock.
    started_at = time.time()  # Seconds since the epoch.
    # Loop until the task resolves or the deadline passes.  # Loop: polling.
    while True:  # Each pass performs one status check.
        # GET the task status from the documented polling endpoint.  # Step: status call.
        envelope = api_request("GET", "/s2s/" + API_VERSION + "/task/" + FEATURE + "/" + task_id)  # Path: /task/skin-analysis/{task_id}.
        # Read the data member that carries the task state.  # Step: read data.
        data = envelope.get("data", {})  # Shape: data.task_status plus data.results on success.
        # Read the documented task_status field.  # Step: read status.
        task_status = data.get("task_status", "")  # Documented values: "running", "success", "error".
        # Return the full data member when the engine finished successfully.  # Branch: success.
        if task_status == "success":  # Scores are final and units were consumed only now, per the docs.
            # Hand the raw success payload to the normalizer.  # Step: return success.
            return data  # Contains data.results.output with per-concern scores.
        # Raise when the engine reported an error (no units are consumed in this case).  # Branch: error.
        if task_status == "error":  # The task failed on the API side.
            # Include any error detail the payload carried.  # Step: raise task failure.
            raise YouCamError("Skin analysis task failed: " + str(data.get("error", "unknown engine error")))  # Honest passthrough of the API's message.
        # Enforce the polling deadline while the task is still running.  # Step: check deadline.
        if time.time() - started_at > POLL_TIMEOUT_SECONDS:  # Results are retained 24h, but the UI should not wait forever.
            # Raise a timeout error the UI can show honestly.  # Step: raise timeout.
            raise YouCamError("Skin analysis task timed out after " + str(POLL_TIMEOUT_SECONDS) + " seconds")  # The task may still finish later; we simply stopped waiting.
        # Wait the documented-flexible interval before polling again.  # Step: sleep.
        time.sleep(POLL_INTERVAL_SECONDS)  # Gentle polling well inside the 5 QPS rate limit.
# Start the normalizer that converts a raw success payload into this app's stable shape.  # Function: normalize_results.
def normalize_results(data):  # Define normalize_results with the raw data member of a success response.
    # Read the results object that holds the per-concern output list.  # Step: read results.
    results = data.get("results", {})  # Shape: data.results.output is a list of per-concern entries.
    # Read the output list (empty when the shape surprises us).  # Step: read output list.
    output_entries = results.get("output", [])  # VERIFIED LIVE 2026-10-23: 11 entries for the 8 SD actions - the 8 concerns plus "all", "skin_age", and "resize_image".
    # Start the normalized concern list the agent and UI consume.  # Step: init concerns.
    concerns = []  # One entry per scored concern; the three auxiliary entries are extracted separately below, never ranked as concerns.
    # Start the overall and skin-age holders; the live payload carries them as their own output entries.  # Step: init overall fields.
    overall = None  # Filled from the "all" entry's "score" field when present.
    # Skin age gets the same treatment as the overall.  # Step: init skin age.
    skin_age = None  # Filled from the "skin_age" entry's "score" field when present.
    # Walk every raw output entry and sort it into the right bucket.  # Loop: raw entries.
    for entry in output_entries:  # Order from the API is not guaranteed, so the agent sorts later.
        # Read the entry's type once; every branch below keys off it.  # Step: read type.
        entry_type = entry.get("type", "unknown")  # Concern name ("moisture"), or "all" / "skin_age" / "resize_image" for the auxiliaries.
        # Keep only the requested SD concerns in the ranked concern list.  # Branch: real concern.
        if entry_type in DST_ACTIONS:  # Auxiliary entries must never reach rank_priorities (their missing scores sorted as zero and poisoned the ranking in the first live run).
            # Append the normalized concern with only the fields this app uses.  # Step: append concern.
            concerns.append({  # Open the normalized concern dictionary.
                "type": entry_type,  # The concern name, e.g. "moisture".
                "ui_score": entry.get("ui_score"),  # The user-friendly 1-100 score (higher is healthier).
                "raw_score": entry.get("raw_score"),  # The raw 1-100 score (higher is healthier).
                "mask_urls": entry.get("mask_urls", []),  # Detection mask image URLs for this concern (may be empty).
            })  # Close the normalized concern dictionary.
        # Extract the overall score from its own entry, where the live API puts it.  # Branch: overall entry.
        elif entry_type == "all":  # VERIFIED LIVE 2026-10-23: shape {"type": "all", "score": 74.0, "url": null} - the value lives in "score", NOT in ui_score/raw_score and NOT at results level.
            # Read the score field, falling back to ui_score for any future shape drift.  # Step: read overall.
            overall = entry.get("score", entry.get("ui_score"))  # A float like 74.0 in the verified payload.
            # Present a whole-number float as an int so the UI reads "74/100", not "74.0/100".  # Branch: whole float.
            if isinstance(overall, float) and overall.is_integer():  # The verified payload's 74.0 lands here.
                # Convert the whole float to an int for display.  # Step: int overall.
                overall = int(overall)  # Display hygiene only; the value is unchanged.
        # Extract the skin age from its own entry the same way.  # Branch: skin-age entry.
        elif entry_type == "skin_age":  # VERIFIED LIVE 2026-10-23: shape {"type": "skin_age", "score": 31, "url": null}.
            # Read the score field, falling back to ui_score for any future shape drift.  # Step: read skin age.
            skin_age = entry.get("score", entry.get("ui_score"))  # An int age estimate in the verified payload.
        # Every other entry type (today: "resize_image", the engine's resized copy of the input photo) is deliberately ignored.  # Branch: auxiliary entry.
        else:  # Not a concern, not a headline number - the app has no use for it.
            # Skip the entry without failing; new auxiliary types must never break normalization.  # Step: skip auxiliary.
            continue  # The loop moves on to the next entry.
    # Build the normalized analysis object.  # Step: build analysis.
    analysis = {  # Open the analysis dictionary.
        "source": "youcam-live",  # Marks these numbers as a real API result, never a sample.
        "concerns": concerns,  # Exactly the requested SD concerns, in API order.
        "overall": overall,  # The "all" entry's score (verified live), or None when the API omits it.
        "skin_age": skin_age,  # The "skin_age" entry's score (verified live), or None when the API omits it.
    }  # Close the analysis dictionary.
    # Return the normalized analysis.  # Step: return analysis.
    return analysis  # The agent layer consumes exactly this shape (and the identical mock shape).
# Start the convenience wrapper that runs the whole documented flow end to end.  # Function: analyze_photo.
def analyze_photo(image_bytes, content_type, file_name):  # Define analyze_photo with the photo bytes, its MIME type, and a file name.
    # Step 1+2: upload the photo and get its file_id.  # Step: upload.
    file_id = upload_image(image_bytes, content_type, file_name)  # Registers metadata, then PUTs the bytes to the signed URL.
    # Step 3: create the skin-analysis task for that file.  # Step: create task.
    task_id = create_task(file_id)  # Returns the identifier to poll.
    # Step 4: poll until success (or raise on error/timeout).  # Step: poll task.
    data = poll_task(task_id)  # Blocks with gentle polling inside the rate limits.
    # Normalize the raw payload into the app's stable analysis shape.  # Step: normalize.
    return normalize_results(data)  # Same shape the mock generator produces, with source "youcam-live".
