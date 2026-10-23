# mock_data.py - the SAMPLE analysis generator used whenever no real YouCam result exists.  # Module header: what this file is.
# HONESTY RULE: everything produced here is illustrative sample data, never a measurement.  # Design rule: samples must never impersonate the API.
# The API layer and the UI both label this data "SAMPLE" (source field plus an on-screen banner), and the README repeats the warning.  # Labeling: source field here, banner in the UI.
# The generator is deterministic: the same concern text always yields the same sample, so demos and tests are repeatable.  # Design choice: no randomness, ever.
# It is also keyword-aware, so the sample roughly reflects what the user typed (mentioning dryness lowers the sample moisture score).  # Behavior: text nudges the relevant concern scores.
# Import the hashlib module so the concern text can be turned into a stable numeric seed.  # Library: hashlib.
import hashlib  # Deterministic hashing for repeatable samples.
# Define the eight concerns in the same order and with the same names the real API returns.  # Constant: concern order.
CONCERN_TYPES = ["moisture", "oiliness", "redness", "acne", "pore", "texture", "wrinkle", "radiance"]  # Matches youcam.DST_ACTIONS exactly.
# Define a healthy baseline sample score per concern, before keyword nudges.  # Constant: baselines.
BASELINE_SCORES = {"moisture": 74, "oiliness": 71, "redness": 76, "acne": 79, "pore": 72, "texture": 73, "wrinkle": 77, "radiance": 75}  # Mid-70s reads as "pretty good skin" in a demo.
# Define keyword groups that lower the matching concern's sample score when the user mentions them.  # Constant: keyword map.
KEYWORD_NUDGES = {  # Open the keyword-to-concern map.
    "moisture": ["dry", "dehydrat", "flaky", "tight", "thirsty"],  # Dryness words pull the moisture score down.
    "oiliness": ["oily", "shine", "shiny", "greasy", "t-zone", "tzone"],  # Shine words pull the oiliness score down.
    "redness": ["red", "redness", "rosacea", "sensitive", "irritat", "flush"],  # Irritation words pull the redness score down.
    "acne": ["acne", "breakout", "pimple", "blemish", "zit", "blackhead"],  # Breakout words pull the acne score down.
    "pore": ["pore", "large pores", "visible pores"],  # Pore words pull the pore score down.
    "texture": ["rough", "bumpy", "uneven", "texture", "patchy"],  # Texture words pull the texture score down.
    "wrinkle": ["wrinkle", "fine line", "aging", "ageing", "crow"],  # Aging words pull the wrinkle score down.
    "radiance": ["dull", "tired", "glow", "radiance", "dark spot", "spot", "uneven tone"],  # Dullness words pull the radiance score down.
}  # Close the keyword-to-concern map.
# Define how many points one matched keyword group removes from its concern's sample score.  # Constant: nudge size.
NUDGE_POINTS = 26  # Big enough that the user's top concern visibly ranks last in the sample.
# Start the helper that derives a small stable per-concern offset from the input text.  # Function: seed_offset.
def seed_offset(seed_text, concern):  # Define seed_offset with the full input text and one concern name.
    # Hash the text plus the concern name so each concern gets its own stable offset.  # Step: hash.
    digest = hashlib.sha256((seed_text + "|" + concern).encode("utf-8")).hexdigest()  # SHA-256 of the combined string.
    # Convert the first four hex digits into an integer.  # Step: to integer.
    value = int(digest[:4], 16)  # Range 0-65535, fully deterministic.
    # Map the integer into a -6..+6 point offset so samples vary a little without looking random.  # Step: small offset.
    return (value % 13) - 6  # Keeps every sample plausible and repeatable.
# Start the main entry point: build a SAMPLE analysis in exactly the real client's shape.  # Function: sample_analysis.
def sample_analysis(concern_text):  # Define sample_analysis with the user's free-text skin concern.
    # Normalize the text once for keyword matching and seeding.  # Step: normalize text.
    lowered = (concern_text or "").lower()  # Empty text is allowed and yields the plain baseline sample.
    # Start the normalized concern list in the documented API order.  # Step: init concerns.
    concerns = []  # One entry per concern, same shape as youcam.normalize_results.
    # Walk the eight concerns and compute each sample score.  # Loop: concerns.
    for concern in CONCERN_TYPES:  # Order matches the real dst_actions list.
        # Start from this concern's healthy baseline.  # Step: baseline.
        score = BASELINE_SCORES[concern]  # Mid-70s starting point.
        # Add the small deterministic per-concern offset.  # Step: offset.
        score += seed_offset(lowered, concern)  # Repeatable variety.
        # Check whether the user mentioned this concern in their own words.  # Step: keyword check.
        keywords = KEYWORD_NUDGES.get(concern, [])  # The words that signal this concern.
        # Lower the score when any keyword for this concern appears in the text.  # Branch: mentioned.
        if any(keyword in lowered for keyword in keywords):  # Substring match keeps it simple and predictable.
            # Apply the nudge so the mentioned concern ranks as the user's weakest sample area.  # Step: apply nudge.
            score -= NUDGE_POINTS  # The agent will then target this concern first.
        # Clamp the score into the documented 1-100 range.  # Step: clamp.
        score = max(5, min(97, score))  # Samples stay plausible, never 0 or 100.
        # Append the concern in the exact shape the real client returns.  # Step: append concern.
        concerns.append({  # Open the sample concern dictionary.
            "type": concern,  # The concern name, identical vocabulary to the API.
            "ui_score": score,  # Sample UI score (1-100, higher is healthier).
            "raw_score": round(score - 4.5, 2),  # Sample raw score, slightly lower like the real calibration gap.
            "mask_urls": [],  # Samples have no detection masks; the UI hides the mask row for samples.
        })  # Close the sample concern dictionary.
    # Compute a sample overall score as the rounded mean of the eight concerns.  # Step: overall.
    overall = round(sum(item["ui_score"] for item in concerns) / len(concerns))  # Mirrors the documented "all" overall score's role.
    # Build the sample analysis in the client's exact shape, clearly sourced as a sample.  # Step: build analysis.
    analysis = {  # Open the sample analysis dictionary.
        "source": "sample",  # The honesty label: the UI shows a SAMPLE banner whenever source is not "youcam-live".
        "concerns": concerns,  # The eight sample concern scores.
        "overall": overall,  # Sample overall score.
        "skin_age": None,  # Samples do not invent a skin age; the UI simply omits it.
    }  # Close the sample analysis dictionary.
    # Return the sample analysis to the agent layer.  # Step: return sample.
    return analysis  # Same shape as a live result, honestly labeled.
