# live_run.py - the SkinSense LIVE verification run, executed by the demo operator (never by the web app).  # Module header: what this file is.
# Purpose: run ONE real YouCam skin-analysis task on the user's own front-facing selfie through the production youcam.py client, save the raw payload for the normalizer check, then prove the agent loop (priorities, routine, refine) on the LIVE scores without any further API calls.  # Scope: exactly one analysis task, plus local-only agent math.
# Credentials: YOUCAM_API_KEY is loaded from ~/workspace/arc-secrets/.env into this process's environment only; the value is never printed, logged, or saved.  # Secret hygiene: presence booleans only.
# Outputs: the raw success payload and a normalized summary are saved under ../demo-assets/ (OUTSIDE this git repo) because the payload's mask URLs depict the user's face and must never be committed or published.  # Privacy: face data stays out of git.
# Units discipline: uploads consume no units; exactly one analysis task is created here (plus at most one retry of the create call, and only when the first attempt 404s before any task exists).  # Budget: one task, per the run brief.
# Import the JSON module so the raw payload and the summary can be saved and printed.  # Library: json.
import json  # Make the json module available.
# Import the OS module so paths and environment variables can be handled.  # Library: os.
import os  # Make the os module available.
# Import the sys module so this script's own directory can be put on the import path.  # Library: sys.
import sys  # Make the sys module available.
# Define the directory this script lives in (the skinsense project root).  # Constant: base dir.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # youcam.py and agent.py sit next to this file.
# Make the sibling modules importable no matter where the operator runs the script from.  # Step: import path.
sys.path.insert(0, BASE_DIR)  # The project modules are imported by bare name below.
# Import the production YouCam client (the exact code the web app uses).  # Library: youcam (this project).
import youcam  # The documented REST client lives in youcam.py.
# Import the production agent loop so its math can be verified on the live scores locally.  # Library: agent (this project).
import agent  # The agentic loop lives in agent.py.
# Define the path of the shared ARC secrets file where the YouCam credentials live.  # Constant: secrets path.
SECRETS_PATH = os.path.expanduser("~/workspace/arc-secrets/.env")  # Mode-600 file; values are loaded, never echoed.
# Define the path of the user's front-facing selfie, sent by the user for exactly this run; SKINSENSE_PHOTO can point at a crop of the same selfie when the engine asks for a tighter frame.  # Constant: photo path.
PHOTO_PATH = os.environ.get("SKINSENSE_PHOTO", os.path.join(BASE_DIR, "..", "demo-assets", "scott-selfie.jpg"))  # Default: the 1206x1609 original; the 2026-10-23 retry used a center crop after error_src_face_too_small.
# Define the folder the run artifacts are saved into (outside the git repo, per the privacy note above).  # Constant: assets dir.
ASSETS_DIR = os.path.join(BASE_DIR, "..", "demo-assets")  # The selfie itself already lives there.
# Define the concern text used for the agent-side verification (the same sentence the demo UI pre-fills).  # Constant: concern text.
CONCERN_TEXT = "My skin feels dry and tight by midday, my cheeks flush red easily, and dull patches make makeup sit badly."  # Matches the UI's example so the demo story stays consistent.
# Start the helper that loads the API key from the secrets file into the process environment.  # Function: load_api_key.
def load_api_key():  # Define load_api_key, which returns True when the key was found (never the value).
    # Open the secrets file for reading.  # Step: open secrets.
    with open(SECRETS_PATH, "r", encoding="utf-8") as handle:  # The file is small; a plain read is fine.
        # Walk every line looking for the YouCam key assignment.  # Loop: secret lines.
        for line in handle:  # One assignment per line in this file.
            # Split on the FIRST equals sign only, because values may contain equals padding.  # Step: split once.
            name, separator, value = line.strip().partition("=")  # partition never raises on a missing separator.
            # Only the API key variable is loaded by this run; every other credential is ignored.  # Branch: wanted variable.
            if separator and name == "YOUCAM_API_KEY":  # The secret variable is not touched by this run at all.
                # Store the bare value (quotes removed) in the environment for this process only.  # Step: store value.
                os.environ["YOUCAM_API_KEY"] = value.strip().strip('"').strip("'")  # The API wants the bare key.
                # Report success as a boolean.  # Step: found.
                return True  # The caller prints this, never the value.
    # Report that no key line was found.  # Step: not found.
    return False  # The main sequence stops before any network call in this case.
# Start the main run sequence, executed only when this file is run directly.  # Block: main guard.
if __name__ == "__main__":  # Importing this file must never fire network calls.
    # Load the API key into the environment (value stays in memory only).  # Step: load key.
    key_found = load_api_key()  # Boolean only; safe to print.
    # Report key presence without the value.  # Step: report presence.
    print("api key loaded:", key_found)  # Example: True.
    # Stop before any network call when the key is missing.  # Branch: no key.
    if not key_found or not youcam.is_configured():  # Both checks must pass for a live run.
        # Raise a loud, precise failure.  # Step: fail loudly.
        raise SystemExit("YOUCAM_API_KEY not available; live run aborted before any API call")  # No units can be consumed without a task.
    # Read the selfie bytes exactly as the File API will register them.  # Step: read photo.
    with open(PHOTO_PATH, "rb") as handle:  # Binary read, as the client expects raw bytes.
        # Keep the bytes for the upload call.  # Step: keep bytes.
        photo_bytes = handle.read()  # The exact bytes of scott-selfie.jpg.
    # Report the photo size as a sanity check (never the image itself).  # Step: report photo.
    print("photo bytes:", len(photo_bytes))  # About 480 KB for the user's selfie.
    # Steps 1-2 of the documented flow: register the file and PUT the bytes (consumes no units).  # Step: upload.
    file_id = youcam.upload_image(photo_bytes, "image/jpeg", "scott-selfie.jpg")  # Returns the API-issued file_id on success.
    # Report the upload success with the API-issued identifier (not a credential).  # Step: report upload.
    print("upload OK, file_id =", file_id)  # Proves Bearer auth + the v2.0 file endpoint + the pre-signed PUT.
    # Step 3: create the analysis task, with the documented one-time version fallback.  # Step: create task.
    try:  # The default v2.0 task path is tried first, per the official usage guide.
        # Create the task under the configured API version (v2.0 unless the environment overrides it).  # Step: create v2.0.
        task_id = youcam.create_task(file_id)  # Returns the identifier to poll.
    # A 404 here means the task endpoint lives under the other documented version; nothing was created, so no units moved.  # Handler: version 404.
    except youcam.YouCamError as error:  # The client normalizes every failure into this type.
        # Only a 404 earns the single retry; any other error is a real verdict and stops the run.  # Branch: retryable.
        if "404" not in str(error):  # Auth, parameter, and server errors must not be retried blindly.
            # Re-raise the original error so the run fails honestly.  # Step: re-raise.
            raise  # The operator reads the API's own message from the traceback.
        # Report the fallback before taking it, so the log explains itself.  # Step: report fallback.
        print("task create 404 on", youcam.API_VERSION, "- retrying once under v2.1 with the same file_id")  # The upload is reused; no second upload.
        # Flip the client's version segment for the retry (the file path stays v2.0, as documented).  # Step: flip version.
        youcam.API_VERSION = "v2.1"  # create_task and poll_task both read this module global.
        # Create the task under v2.1 (the single allowed retry).  # Step: create v2.1.
        task_id = youcam.create_task(file_id)  # Same file_id; a fresh task identifier comes back.
    # Report the task identifier and the version that worked.  # Step: report task.
    print("task created, task_id =", task_id, "| api version =", youcam.API_VERSION)  # Scores land when polling returns success.
    # Step 4: poll until the engine reports success (units are consumed only on success, per the docs).  # Step: poll task.
    data = youcam.poll_task(task_id)  # Blocks with gentle polling inside the rate limits.
    # Save the raw success payload outside the repo for the normalizer shape check.  # Step: save raw.
    raw_record = {"task_id": task_id, "file_id": file_id, "api_version": youcam.API_VERSION, "data": data}  # Metadata plus the verbatim data member.
    # Write the raw record as JSON.  # Step: write raw.
    with open(os.path.join(ASSETS_DIR, "live-raw-response.json"), "w", encoding="utf-8") as handle:  # One file, overwritten per run.
        # Serialize with indentation so the operator can read the shape directly.  # Step: serialize raw.
        json.dump(raw_record, handle, indent=2)  # The record copy for the shape check.
    # Report the raw shape so the normalizer TODOs can be settled from facts.  # Step: report shape.
    results_obj = data.get("results", {})  # The results member the normalizer reads.
    # Print the key sets at both levels (names only, no values yet).  # Step: print keys.
    print("raw data keys:", sorted(data.keys()))  # Where do overall fields live: data or results?
    # Print the results-level keys the same way.  # Step: print results keys.
    print("raw results keys:", sorted(results_obj.keys()) if isinstance(results_obj, dict) else type(results_obj).__name__)  # "all" and "skin_age" are hunted here.
    # Print the per-entry keys of the first output entry, when the output is a list.  # Step: print entry keys.
    output_list = results_obj.get("output", []) if isinstance(results_obj, dict) else []  # The per-concern entries.
    # Guard the print for the unexpected-shape case.  # Branch: entries exist.
    if output_list:  # At least one concern entry came back.
        # Show the field names one entry carries.  # Step: entry keys.
        print("output entry keys:", sorted(output_list[0].keys()))  # ui_score / raw_score / mask_urls expected.
        # Show the concern types in API order.  # Step: entry types.
        print("output types:", [entry.get("type") for entry in output_list])  # Eight SD concerns expected.
    # Normalize the raw payload through the production normalizer.  # Step: normalize.
    analysis = youcam.normalize_results(data)  # The exact shape the agent and UI consume.
    # Print the normalized analysis in full (scores are the user's own results, not secrets).  # Step: print analysis.
    print("normalized analysis:", json.dumps(analysis, indent=2))  # overall and skin_age verdicts are visible here.
    # Save the normalized summary beside the raw record for the submission log.  # Step: save summary.
    summary = {"task_id": task_id, "file_id": file_id, "api_version": youcam.API_VERSION, "concern_text": CONCERN_TEXT, "analysis": analysis}  # Everything the verification log needs.
    # Write the summary as JSON.  # Step: write summary.
    with open(os.path.join(ASSETS_DIR, "live-analysis-summary.json"), "w", encoding="utf-8") as handle:  # Outside the repo, beside the raw record.
        # Serialize with indentation for readability.  # Step: serialize summary.
        json.dump(summary, handle, indent=2)  # The operator copies verdicts from here into SUBMISSION-DRAFT.md.
    # Verify the agent's priority ranking on the LIVE scores (local math, no API calls).  # Step: priorities.
    priorities = agent.rank_priorities(analysis)[:3]  # The three weakest live concerns.
    # Print the live priorities.  # Step: print priorities.
    print("live priorities:", [(item["type"], item.get("ui_score")) for item in priorities])  # Weakest first.
    # Verify the agent's plain-language explanation on the LIVE scores.  # Step: explanation.
    print("explanation:", agent.explain_analysis(analysis))  # Should name the weakest concerns and the overall, when present.
    # Verify the routine builder on the LIVE scores with no constraints.  # Step: routine.
    routine = agent.build_routine(analysis, {})  # AM, PM, and finish slots plus the basket total.
    # Print the routine compactly: slot, product, price.  # Step: print routine.
    print("routine:", [(slot["when"], slot["step"], slot["product"]["name"], slot["product"]["price"]) for slot in routine["slots"]], "| total:", routine["total_price"])  # Sensible picks aimed at the live priorities.
    # Verify one refine round on the LIVE scores (still local math only).  # Step: refine.
    refined = agent.refine("under $20 each and fragrance-free", {"analysis": analysis, "constraints": {}})  # The demo's signature pushback.
    # Print the refine verdict: mode, change count, and the new total.  # Step: print refine.
    print("refine mode:", refined["mode"], "| changes:", len(refined["changes"]), "| new total:", refined["routine"]["total_price"])  # Mode must read "live".
    # Print every refine change note so the operator can judge them for sense.  # Loop: change notes.
    for note in refined["changes"]:  # One note per line.
        # Print the note verbatim.  # Step: print note.
        print("  change:", note)  # Swaps and totals should reference the live routine's products.
    # Announce the end of the live run.  # Step: done.
    print("live run complete")  # The verification log entry is written by the operator from the lines above.
