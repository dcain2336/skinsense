# agent.py - the SkinSense agentic loop: analyze, prioritize, recommend, refine.  # Module header: what this file is.
# The loop mirrors the hackathon concept: a concern goes in, a YouCam Skin AI analysis comes back, the agent turns scores into a routine, and user feedback refines it.  # Concept: analyze -> recommend -> try-on -> refine.
# The agent is deliberately deterministic (rules over scores, no LLM), so the prototype runs offline with zero paid dependencies and behaves identically in tests.  # Design choice: rules, not a model.
# Honesty contract: an analysis is labeled "live" only when the real YouCam API produced it; every fallback is labeled "sample" with a plain-language notice.  # Honesty: mode labels are never faked.
# Import the sibling YouCam client for the live analysis path.  # Library: youcam (this project).
import youcam  # The documented REST client lives in youcam.py.
# Import the sibling SAMPLE generator for the no-key and no-photo paths.  # Library: mock_data (this project).
import mock_data  # The clearly-labeled sample generator lives in mock_data.py.
# Import the sibling demo catalog the routine builder recommends from.  # Library: catalog (this project).
import catalog  # The demo product list lives in catalog.py.
# Define friendly display names for each concern, used in explanations and the UI payload.  # Constant: concern labels.
CONCERN_LABELS = {"moisture": "Moisture", "oiliness": "Oil control", "redness": "Redness", "acne": "Breakouts", "pore": "Pores", "texture": "Texture", "wrinkle": "Fine lines", "radiance": "Radiance"}  # Short labels read better than raw API names.
# Define one plain-language sentence per concern explaining why a low score matters.  # Constant: concern explainers.
CONCERN_EXPLAINERS = {  # Open the explainer map.
    "moisture": "Low moisture means the skin barrier is losing water, which makes everything else feel worse.",  # Moisture explainer.
    "oiliness": "Low oil control means shine and clogged pores build up through the day.",  # Oiliness explainer.
    "redness": "A low redness score means visible irritation the routine should calm, not provoke.",  # Redness explainer.
    "acne": "A low breakout score means pores are clogging faster than they clear.",  # Acne explainer.
    "pore": "A low pore score means pores are stretched by oil and debris.",  # Pore explainer.
    "texture": "A low texture score means rough, uneven patches that products and makeup sit badly on.",  # Texture explainer.
    "wrinkle": "A low fine-lines score means early lines are setting in, mostly a night-time repair job.",  # Wrinkle explainer.
    "radiance": "A low radiance score means dull, tired-looking skin even when it is otherwise healthy.",  # Radiance explainer.
}  # Close the explainer map.
# Start the helper that ranks concerns from weakest to strongest.  # Function: rank_priorities.
def rank_priorities(analysis):  # Define rank_priorities with a normalized analysis dictionary.
    # Sort the concerns by UI score ascending so the weakest areas lead.  # Step: sort weakest first.
    ordered = sorted(analysis.get("concerns", []), key=lambda item: (item.get("ui_score") or 0))  # Missing scores sort as zero, surfacing data problems honestly.
    # Return the full ranked list; callers slice what they need.  # Step: return ranking.
    return ordered  # Weakest concern first.
# Start the helper that picks the best product for one step under the active constraints.  # Function: pick_product.
def pick_product(step, priority_types, constraints, exclude_ids=None):  # Define pick_product with the step, the ranked concern names, the constraints, and optional exclusions.
    # Start from every catalog product in this step, in catalog order.  # Step: candidates.
    candidates = catalog.for_step(step)  # Catalog order is the house quality ranking.
    # Apply the fragrance-free constraint when the user asked for it.  # Step: fragrance filter.
    if constraints.get("fragrance_free_only"):  # The refine loop sets this flag from feedback.
        # Keep only fragrance-free candidates when any exist.  # Step: filtered list.
        filtered = [item for item in candidates if item["fragrance_free"]]  # Scented products drop out.
        # Use the filtered list only when it is non-empty, so a step never goes unfilled silently.  # Branch: filter result.
        if filtered:  # At least one fragrance-free option exists for this step.
            # Replace the candidate list with the filtered one.  # Step: apply filter.
            candidates = filtered  # The swap will show up in the refine change list.
    # Apply the per-product budget cap when the user set one.  # Step: budget filter.
    max_price = constraints.get("max_price")  # None means no cap.
    # Filter by price only when a cap exists.  # Branch: cap present.
    if max_price:  # The user gave the agent a ceiling.
        # Keep only products at or under the cap when any exist.  # Step: price filter.
        affordable = [item for item in candidates if item["price"] <= max_price]  # Over-cap products drop out.
        # Use the affordable list only when it is non-empty.  # Branch: filter result.
        if affordable:  # Something in this step fits the budget.
            # Replace the candidate list with the affordable one.  # Step: apply cap.
            candidates = affordable  # Cheaper picks will show in the change list.
    # Drop explicitly excluded products (used so AM and PM treatments differ).  # Step: exclusions.
    exclude_ids = exclude_ids or []  # Default to no exclusions.
    # Build the usable list without the excluded identifiers.  # Step: usable list.
    usable = [item for item in candidates if item["id"] not in exclude_ids]  # Exclusions never empty the list silently (checked next).
    # Fall back to the unexcluded-ignoring list if exclusions removed everything.  # Branch: all excluded.
    if not usable:  # Every candidate was excluded (tiny catalog edge case).
        # Reuse the constrained candidates rather than returning nothing.  # Step: fallback list.
        usable = candidates  # A repeated product beats a missing routine step.
    # Score each candidate by how many priority concerns it targets, earliest priorities weighing most.  # Step: score candidates.
    def target_score(item):  # Define the scoring helper for one product.
        # Sum positional weights: the #1 concern is worth 3, #2 worth 2, #3 worth 1.  # Step: weighted overlap.
        weights = {name: 3 - index for index, name in enumerate(priority_types[:3])}  # Only the top three concerns drive picks.
        # Add the weight of every targeted concern this product covers.  # Step: sum weights.
        return sum(weights.get(target, 0) for target in item["targets"])  # Higher means a better match for this skin.
    # Sort by score descending, keeping catalog order as the tie-breaker.  # Step: rank candidates.
    ranked = sorted(usable, key=lambda item: -target_score(item))  # Python's sort is stable, so ties keep catalog order.
    # Return the winning product, or None when the step has no products at all.  # Step: return winner.
    return ranked[0] if ranked else None  # The catalog always fills every step today; None is the honest fallback.
# Start the routine builder that turns an analysis plus constraints into AM/PM/finish slots.  # Function: build_routine.
def build_routine(analysis, constraints):  # Define build_routine with the analysis and the active constraint dictionary.
    # Rank the concerns so the builder can aim at the weakest areas.  # Step: rank concerns.
    ranked = rank_priorities(analysis)  # Weakest first.
    # Extract just the concern names in ranked order for the picker.  # Step: priority names.
    priority_types = [item["type"] for item in ranked]  # The picker weights the first three.
    # Start the slot list the UI renders as the routine.  # Step: init slots.
    slots = []  # Each slot: when, step, product, why.
    # Define a small helper that appends one filled slot.  # Function: add_slot (inner).
    def add_slot(when, step, product, why):  # Define add_slot with the time label, step, chosen product, and the reason text.
        # Append the slot only when a product was actually found.  # Branch: product exists.
        if product:  # A missing product would render as a broken card.
            # Push the slot record the UI expects.  # Step: append slot.
            slots.append({"when": when, "step": step, "product": product, "why": why})  # The product dictionary rides along for the card.
    # Pick the cleanser once; morning and night share it.  # Step: cleanser pick.
    cleanser = pick_product("cleanse", priority_types, constraints)  # Best cleanser for the weakest concerns.
    # Add the AM cleanser slot with its reason.  # Step: AM cleanse slot.
    add_slot("AM", "cleanse", cleanser, "Start clean: removes overnight oil without stripping, which protects your " + CONCERN_LABELS.get(priority_types[0], "skin") + " goal.")  # Reason ties the step to the top concern.
    # Pick the AM treatment aimed at the single weakest concern.  # Step: AM treatment pick.
    am_treat = pick_product("treat", priority_types, constraints)  # The picker weights the #1 concern most.
    # Add the AM treatment slot.  # Step: AM treat slot.
    add_slot("AM", "treat", am_treat, "Your main treatment, aimed at " + CONCERN_LABELS.get(priority_types[0], "your top concern") + ", your weakest area.")  # Reason names the target.
    # Pick the shared moisturizer; the picker favors gel textures automatically when oil or breakouts rank high because those products target them.  # Step: moisturizer pick.
    moisturizer = pick_product("moisturize", priority_types, constraints)  # One moisturizer, used twice a day.
    # Add the AM moisturizer slot.  # Step: AM moisturize slot.
    add_slot("AM", "moisturize", moisturizer, "Locks the treatment in and keeps the barrier comfortable all day.")  # Reason explains the layer order.
    # Pick the sunscreen for the AM protect step.  # Step: SPF pick.
    spf = pick_product("protect", priority_types, constraints)  # The catalog has one SPF today; constraints still apply.
    # Add the AM protect slot.  # Step: AM protect slot.
    add_slot("AM", "protect", spf, "Daylight undoes routine progress; this is the step that defends spots, lines, and redness gains.")  # Reason sells prevention honestly.
    # Add the PM cleanser slot reusing the morning pick.  # Step: PM cleanse slot.
    add_slot("PM", "cleanse", cleanser, "Same gentle cleanser at night: the day comes off, the barrier stays calm.")  # Reason explains the reuse.
    # Pick the PM treatment aimed at the second concern, excluding the AM treatment when possible.  # Step: PM treatment pick.
    pm_priorities = priority_types[1:] + priority_types[:1]  # Rotate so the #2 concern leads this pick.
    # Run the picker with the rotated priorities and the AM pick excluded.  # Step: PM pick call.
    pm_treat = pick_product("treat", pm_priorities, constraints, exclude_ids=[am_treat["id"]] if am_treat else [])  # A different serum at night covers more ground.
    # Add the PM treatment slot unless the user asked for a minimal routine.  # Branch: minimal check.
    if not constraints.get("minimal"):  # Minimal routines keep a single daily treatment.
        # Append the PM treatment with its reason.  # Step: PM treat slot.
        add_slot("PM", "treat", pm_treat, "Night treatment aimed at " + CONCERN_LABELS.get(priority_types[1] if len(priority_types) > 1 else priority_types[0], "your next concern") + ", your second-weakest area.")  # Reason names the second target.
    # Add the PM moisturizer slot reusing the shared pick.  # Step: PM moisturize slot.
    add_slot("PM", "moisturize", moisturizer, "A slightly thicker layer at night is fine; this cream carries the barrier through sleep.")  # Reason closes the day.
    # Add the virtual try-on finish products unless the user opted out of makeup or asked for minimal.  # Branch: finish check.
    if not constraints.get("no_tint") and not constraints.get("minimal"):  # Try-on cards are the eCommerce VTO half of the concept.
        # Walk the tint products in catalog order.  # Loop: tint products.
        for tint in catalog.for_step("tint"):  # Two demo tint products exist today.
            # Respect the fragrance constraint for tints too.  # Branch: fragrance check.
            if constraints.get("fragrance_free_only") and not tint["fragrance_free"]:  # Scented tints drop out under the constraint.
                # Skip this tint under the active constraint.  # Step: skip tint.
                continue  # The change list will mention the removal.
            # Respect the budget cap for tints too.  # Branch: budget check.
            if constraints.get("max_price") and tint["price"] > constraints["max_price"]:  # Over-cap tints drop out.
                # Skip this tint under the budget.  # Step: skip tint.
                continue  # The routine stays honest about the cap.
            # Append the finish slot for this tint product.  # Step: finish slot.
            slots.append({"when": "Finish", "step": "tint", "product": tint, "why": "Optional finish: preview it on your own photo with virtual try-on before buying."})  # The why sells the VTO moment.
    # Compute the routine's total shelf price from the unique products used.  # Step: total price.
    unique_ids = []  # Track identifiers so shared AM/PM products count once.
    # Walk the slots collecting unique product identifiers.  # Loop: slots.
    for slot in slots:  # Each slot references one product.
        # Add the identifier when it is new.  # Branch: new product.
        if slot["product"]["id"] not in unique_ids:  # Shared cleanser/moisturizer count once.
            # Record the identifier.  # Step: record id.
            unique_ids.append(slot["product"]["id"])  # Unique shelf items only.
    # Sum the prices of the unique products.  # Step: sum prices.
    total_price = round(sum(catalog.by_id(product_id)["price"] for product_id in unique_ids), 2)  # The honest basket total.
    # Return the slots plus the total.  # Step: return routine.
    return {"slots": slots, "total_price": total_price, "item_count": len(unique_ids)}  # The UI renders exactly this.
# Start the helper that explains the analysis in one short paragraph.  # Function: explain_analysis.
def explain_analysis(analysis):  # Define explain_analysis with the normalized analysis.
    # Rank the concerns weakest first.  # Step: rank.
    ranked = rank_priorities(analysis)  # The explanation leads with the weakest areas.
    # Take the three weakest concerns for the summary.  # Step: top three.
    weakest = ranked[:3]  # Three is enough for a readable paragraph.
    # Build a readable fragment per weak concern, like "Moisture 48/100".  # Step: fragments.
    fragments = [CONCERN_LABELS.get(item["type"], item["type"]) + " " + str(item.get("ui_score")) + "/100" for item in weakest]  # Scores make the explanation concrete.
    # Join the fragments into a sentence.  # Step: join fragments.
    summary = "Your weakest areas are " + ", ".join(fragments) + ". "  # The opening sentence of the explanation.
    # Add the explainer sentence for the single weakest concern.  # Step: explainer.
    summary += CONCERN_EXPLAINERS.get(weakest[0]["type"], "") if weakest else ""  # One why-it-matters sentence, not three.
    # Add the overall score sentence when an overall exists.  # Branch: overall present.
    if analysis.get("overall") is not None:  # Live results and samples both provide an overall.
        # Append the overall framing.  # Step: overall sentence.
        summary += " Overall skin score: " + str(analysis["overall"]) + "/100."  # Higher is healthier, per the docs.
    # Return the finished explanation.  # Step: return summary.
    return summary  # The UI shows this above the score bars.
# Start the main analyze step of the loop: concern text plus optional photo in, full result out.  # Function: run_analysis.
def run_analysis(concern_text, photo):  # Define run_analysis with the user's text and an optional photo dict {bytes, content_type, file_name} or None.
    # Start with no notice; notices are added whenever a fallback happens.  # Step: init notice.
    notice = ""  # The UI displays this verbatim so fallbacks are never silent.
    # Decide the analysis path: live only when a key exists AND a photo was provided.  # Branch: live path.
    if youcam.is_configured() and photo:  # The API needs an image; text alone cannot be analyzed by it.
        # Guard the live call so an API failure degrades honestly instead of crashing.  # Step: guarded live call.
        try:  # Begin the guarded live block.
            # Run the documented upload -> task -> poll flow.  # Step: live analysis.
            analysis = youcam.analyze_photo(photo["bytes"], photo["content_type"], photo["file_name"])  # Real scores from Perfect Corp's engine.
            # Mark the mode as live for the UI badge.  # Step: live mode.
            mode = "live"  # The badge will read "Live YouCam analysis".
        # Catch any client failure and fall back to a labeled sample.  # Handler: live failure.
        except youcam.YouCamError as error:  # Upload, task, and polling failures all land here.
            # Build a sample so the demo still completes end to end.  # Step: fallback sample.
            analysis = mock_data.sample_analysis(concern_text)  # Keyword-aware sample, honestly labeled.
            # Mark the mode as sample.  # Step: sample mode.
            mode = "sample"  # The SAMPLE banner will show.
            # Tell the user exactly what happened, including the API's own error text.  # Step: fallback notice.
            notice = "The live YouCam analysis failed (" + str(error) + "), so this is SAMPLE data to keep the demo moving."  # No silent substitution, ever.
    # Handle the key-present-but-no-photo case: the API cannot run, so the sample carries the demo.  # Branch: key, no photo.
    elif youcam.is_configured() and not photo:  # A key alone is not enough for the image-based API.
        # Build the keyword-aware sample.  # Step: sample analysis.
        analysis = mock_data.sample_analysis(concern_text)  # Text-only path.
        # Mark the mode as sample.  # Step: sample mode.
        mode = "sample"  # SAMPLE banner shows.
        # Explain that a photo unlocks the real analysis.  # Step: notice.
        notice = "Add a front-facing photo to run the real YouCam Skin AI analysis; this preview uses SAMPLE data based on your description."  # Guides the user to the live path.
    # Handle the default no-key case: the whole analysis is a sample.  # Branch: no key.
    else:  # YOUCAM_API_KEY is unset in this environment.
        # Build the keyword-aware sample.  # Step: sample analysis.
        analysis = mock_data.sample_analysis(concern_text)  # Deterministic, repeatable sample.
        # Mark the mode as sample.  # Step: sample mode.
        mode = "sample"  # SAMPLE banner shows.
        # Explain the mock mode plainly.  # Step: notice.
        notice = "SAMPLE mode: no YouCam API key is configured, so these scores are illustrative sample data, not a real skin measurement."  # The honesty banner text.
    # Start from empty constraints for a fresh analysis.  # Step: fresh constraints.
    constraints = {}  # Refine rounds will add flags and caps here.
    # Build the first routine from the analysis.  # Step: build routine.
    routine = build_routine(analysis, constraints)  # AM, PM, and finish slots.
    # Assemble the full result the API returns and the client stores as session state.  # Step: build result.
    result = {  # Open the result dictionary.
        "mode": mode,  # "live" or "sample" - drives the UI badge and banner.
        "notice": notice,  # Empty on a clean live run; otherwise the fallback explanation.
        "analysis": analysis,  # The normalized scores (with their own source label inside).
        "priorities": rank_priorities(analysis)[:3],  # The three weakest concerns, for the UI highlights.
        "explanation": explain_analysis(analysis),  # The one-paragraph plain-language summary.
        "routine": routine,  # The AM/PM/finish slots plus the basket total.
        "state": {"analysis": analysis, "constraints": constraints},  # The client sends this back verbatim for refine rounds.
    }  # Close the result dictionary.
    # Return the full result.  # Step: return result.
    return result  # app.py serializes this as the /api/analyze response.
# Start the feedback parser that turns free-text feedback into routine constraints.  # Function: parse_feedback.
def parse_feedback(feedback_text, constraints):  # Define parse_feedback with the user's words and the current constraints (mutated copy returned).
    # Work on a copy so the caller's state is never mutated in place.  # Step: copy constraints.
    updated = dict(constraints)  # Shallow copy is enough for flat flags and numbers.
    # Normalize the feedback for keyword checks.  # Step: normalize.
    lowered = (feedback_text or "").lower()  # Case-insensitive matching.
    # Track human-readable descriptions of what the feedback changed.  # Step: init changes.
    changes = []  # The UI lists these so the refine feels transparent, not magic.
    # Detect fragrance sensitivity requests.  # Branch: fragrance.
    if "fragrance" in lowered or "scent" in lowered or "perfume" in lowered:  # Several phrasings mean the same constraint.
        # Set the fragrance-free flag when it is new.  # Branch: newly set.
        if not updated.get("fragrance_free_only"):  # Avoid duplicate change notes.
            # Apply the constraint.  # Step: apply fragrance.
            updated["fragrance_free_only"] = True  # Scented products will be swapped or dropped.
            # Record the change for the UI.  # Step: record change.
            changes.append("Switched the routine to fragrance-free products only.")  # Plain-language change note.
    # Detect sensitivity requests that imply the same gentle constraint.  # Branch: sensitive.
    if "sensitive" in lowered or "gentle" in lowered or "irritat" in lowered:  # Sensitive-skin feedback maps to the fragrance-free, calm-first picks.
        # Set the fragrance-free flag when it is new.  # Branch: newly set.
        if not updated.get("fragrance_free_only"):  # Same flag, different words.
            # Apply the constraint.  # Step: apply gentle.
            updated["fragrance_free_only"] = True  # The picker prefers the calm, unscented options.
            # Record the change.  # Step: record change.
            changes.append("Moved to gentler, fragrance-free picks for sensitive skin.")  # Plain-language change note.
    # Detect minimal-routine requests.  # Branch: minimal.
    if "simpler" in lowered or "simple" in lowered or "fewer" in lowered or "minimal" in lowered or "less steps" in lowered:  # Many ways to ask for less.
        # Set the minimal flag when it is new.  # Branch: newly set.
        if not updated.get("minimal"):  # Avoid duplicate notes.
            # Apply the constraint.  # Step: apply minimal.
            updated["minimal"] = True  # PM second treatment and try-on finish drop out.
            # Record the change.  # Step: record change.
            changes.append("Trimmed the routine to the essentials: cleanse, one treatment, moisturize, SPF.")  # Plain-language change note.
    # Detect makeup opt-outs.  # Branch: no tint.
    if "no makeup" in lowered or "skip makeup" in lowered or "no tint" in lowered or "without makeup" in lowered:  # Explicit opt-out phrases.
        # Set the no-tint flag when it is new.  # Branch: newly set.
        if not updated.get("no_tint"):  # Avoid duplicate notes.
            # Apply the constraint.  # Step: apply no tint.
            updated["no_tint"] = True  # Finish slots disappear.
            # Record the change.  # Step: record change.
            changes.append("Removed the tinted try-on products.")  # Plain-language change note.
    # Detect budget requests, including an explicit dollar ceiling like "under $20 each".  # Branch: budget.
    if "budget" in lowered or "cheaper" in lowered or "expensive" in lowered or "afford" in lowered or "under $" in lowered or "less than $" in lowered:  # Budget intent words.
        # Try to extract an explicit per-product ceiling from the text.  # Step: extract ceiling.
        ceiling = extract_dollar_amount(lowered)  # Returns None when no number was given.
        # Default to a sensible budget cap when no number was given.  # Branch: default cap.
        if ceiling is None:  # Words without numbers still deserve action.
            # Use twenty dollars as the demo budget ceiling per product.  # Step: default ceiling.
            ceiling = 20.0  # Most catalog steps have an option at or under this.
        # Apply the cap when it tightens the current one.  # Branch: cap tightens.
        if not updated.get("max_price") or ceiling < updated["max_price"]:  # A later, looser number never silently raises the cap.
            # Store the cap.  # Step: store cap.
            updated["max_price"] = ceiling  # The picker filters over-cap products.
            # Record the change with the number in it.  # Step: record change.
            changes.append("Set a $" + format(ceiling, ".0f") + " per-product budget and swapped in the best options that fit it.")  # Plain-language change note with the cap.
    # Return the updated constraints plus the change notes.  # Step: return parse.
    return updated, changes  # refine() compares routines before and after for product-level notes.
# Start the small helper that pulls the first dollar amount out of feedback text.  # Function: extract_dollar_amount.
def extract_dollar_amount(lowered_text):  # Define extract_dollar_amount with already-lowercased feedback text.
    # Scan character by character for a "$" followed by digits.  # Step: scan text.
    for index, char in enumerate(lowered_text):  # Positions matter for slicing the number out.
        # Check for the dollar sign that introduces an amount.  # Branch: dollar sign.
        if char == "$":  # A ceiling usually reads "under $20".
            # Collect the digits that follow the sign.  # Step: collect digits.
            digits = ""  # The numeric part being built.
            # Walk forward while characters are digits or a decimal point.  # Loop: digits.
            for next_char in lowered_text[index + 1:]:  # Slice from just after the sign.
                # Continue while the character belongs to a number.  # Branch: numeric char.
                if next_char.isdigit() or next_char == ".":  # Digits and one decimal point.
                    # Append the character to the number.  # Step: append digit.
                    digits += next_char  # Build the amount string.
                # Stop at the first non-numeric character.  # Branch: end of number.
                else:  # Anything else ends the amount.
                    # Leave the digit loop.  # Step: stop collecting.
                    break  # The amount is complete.
            # Convert and return the amount when digits were found.  # Branch: digits found.
            if digits:  # A bare "$" with no number is ignored.
                # Return the parsed float.  # Step: return amount.
                return float(digits)  # The per-product ceiling.
    # Return None when no dollar amount exists in the text.  # Step: no amount.
    return None  # The caller applies its default cap instead.
# Start the refine step of the loop: feedback plus stored state in, updated routine out.  # Function: refine.
def refine(feedback_text, state):  # Define refine with the user's feedback and the state returned by run_analysis.
    # Read the stored analysis (scores never change during refine; only the routine does).  # Step: read analysis.
    analysis = state.get("analysis", {})  # The same scores the routine was built from.
    # Read the constraints accumulated so far.  # Step: read constraints.
    old_constraints = state.get("constraints", {})  # Flags and caps from earlier rounds.
    # Build the current routine so product-level changes can be diffed.  # Step: old routine.
    old_routine = build_routine(analysis, old_constraints)  # Deterministic rebuild of what the user sees now.
    # Parse the new feedback into updated constraints plus notes.  # Step: parse feedback.
    new_constraints, changes = parse_feedback(feedback_text, old_constraints)  # Keyword rules, honestly mechanical.
    # Build the refined routine under the new constraints.  # Step: new routine.
    new_routine = build_routine(analysis, new_constraints)  # Same scores, smarter picks.
    # Index the old picks by slot key so swaps can be named.  # Step: index old picks.
    old_picks = {slot["when"] + ":" + slot["step"]: slot["product"]["id"] for slot in old_routine["slots"]}  # Slot key -> product id.
    # Walk the new slots and note every product swap in plain language.  # Loop: new slots.
    for slot in new_routine["slots"]:  # Each new slot may replace an old product.
        # Build the slot key the same way as the index.  # Step: slot key.
        slot_key = slot["when"] + ":" + slot["step"]  # Matches the old-picks index.
        # Compare the new pick with the old pick for this slot.  # Branch: swapped.
        if slot_key in old_picks and old_picks[slot_key] != slot["product"]["id"]:  # A different product now fills the slot.
            # Find the old product's name for the note.  # Step: old name.
            old_name = catalog.by_id(old_picks[slot_key])["name"]  # Human-readable old pick.
            # Record the swap in plain language.  # Step: record swap.
            changes.append("Swapped " + old_name + " for " + slot["product"]["name"] + " (" + slot["when"] + " " + slot["step"] + ").")  # The user sees exactly what changed.
    # Note when the basket total moved.  # Branch: total changed.
    if new_routine["total_price"] != old_routine["total_price"]:  # Price honesty is part of the refine story.
        # Record the before-and-after totals.  # Step: record total.
        changes.append("Basket total: $" + format(old_routine["total_price"], ".2f") + " -> $" + format(new_routine["total_price"], ".2f") + ".")  # Concrete numbers, not vibes.
    # Honesty check: name any product that still breaks the budget cap because its step has no in-cap option.  # Step: over-cap check.
    if new_constraints.get("max_price"):  # A cap is active for this routine.
        # Collect the names and prices of unique products still over the cap.  # Step: collect over-cap.
        over_cap = sorted({slot["product"]["name"] + " ($" + format(slot["product"]["price"], ".0f") + ")" for slot in new_routine["slots"] if slot["product"]["price"] > new_constraints["max_price"]})  # A set keeps shared AM/PM products from repeating.
        # Add the disclosure note when anything stayed over the cap.  # Branch: over-cap found.
        if over_cap:  # Some step could not be filled within the cap.
            # Record exactly which products broke the cap and why they stayed.  # Step: record over-cap.
            changes.append("Kept " + ", ".join(over_cap) + " - that step has no in-budget option in the catalog yet, and an empty step would be worse.")  # The cap story stays truthful.
    # Honesty check: name any scented product that survived the fragrance-free constraint for the same reason.  # Step: scented check.
    if new_constraints.get("fragrance_free_only"):  # The fragrance-free flag is active.
        # Collect the names of unique scented products still in the routine.  # Step: collect scented.
        scented_left = sorted({slot["product"]["name"] for slot in new_routine["slots"] if not slot["product"]["fragrance_free"]})  # Steps without a fragrance-free option keep their best product.
        # Add the disclosure note when anything scented survived.  # Branch: scented found.
        if scented_left:  # Some step has no fragrance-free option in the catalog.
            # Record exactly which products stayed and why.  # Step: record scented.
            changes.append("Kept " + ", ".join(scented_left) + " - that step has no fragrance-free option in the catalog yet.")  # The fragrance story stays truthful too.
    # Handle feedback the parser did not understand with an honest note instead of fake action.  # Branch: nothing parsed.
    if not changes:  # No keyword matched and nothing swapped.
        # Tell the user the routine is unchanged and what phrases work.  # Step: honest no-op.
        changes.append("I kept the routine the same - try 'fragrance-free', 'under $20 each', 'simpler', or 'no makeup' and I will adjust it.")  # Transparent about the rule-based parser.
    # Assemble the refine result with the refreshed state.  # Step: build result.
    result = {  # Open the refine result dictionary.
        "mode": analysis.get("source") == "youcam-live" and "live" or "sample",  # The mode still reflects where the scores came from.
        "routine": new_routine,  # The updated AM/PM/finish slots.
        "changes": changes,  # The plain-language list of what the feedback did.
        "state": {"analysis": analysis, "constraints": new_constraints},  # The client stores this for the next refine round.
    }  # Close the refine result dictionary.
    # Return the refine result.  # Step: return result.
    return result  # app.py serializes this as the /api/refine response.
