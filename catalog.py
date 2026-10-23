# catalog.py - the built-in demo product catalog SkinSense Agent recommends from.  # Module header: what this file is.
# These are illustrative demo products with invented brand names, so the prototype can be judged end to end before any retail partner data exists.  # Honesty note: no real brands, no affiliate links.
# Swapping this list for a retailer's real feed later requires no agent changes: the agent only reads the fields defined here.  # Design choice: catalog is data, not code.
# Prices are realistic shelf prices in USD and exist so the refine loop can honor budget feedback honestly.  # Behavior: budget swaps need real numbers to compare.
# Define the demo catalog as a list of product dictionaries.  # Constant: product catalog.
PRODUCTS = [  # Open the catalog list.
    {  # Open product 1: a gentle everyday cleanser.
        "id": "cleanser-gentle-foam",  # Stable identifier used by routines and feedback swaps.
        "name": "Cloud Foam Gentle Cleanser",  # Display name shown on the product card.
        "brand": "Aurelle (demo brand)",  # Invented brand, labeled demo so nobody mistakes it for a real product.
        "step": "cleanse",  # Routine step this product fills.
        "targets": ["redness", "texture", "moisture"],  # Concerns this product helps, matched against analysis scores.
        "price": 14.0,  # Demo shelf price in USD.
        "fragrance_free": True,  # Safe for sensitive-skin feedback.
        "vto": False,  # Cleansers have nothing to try on virtually.
        "blurb": "A low-pH foam that cleans without stripping, so tight, red skin calms down instead of flaring up.",  # One-line value pitch shown on the card.
    },  # Close product 1.
    {  # Open product 2: a budget hydrating cleanser.
        "id": "cleanser-cream-milk",  # Stable identifier.
        "name": "Oat Milk Cream Cleanser",  # Display name.
        "brand": "Aurelle (demo brand)",  # Invented demo brand.
        "step": "cleanse",  # Routine step.
        "targets": ["moisture", "redness"],  # Concerns helped.
        "price": 11.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # No try-on for cleansers.
        "blurb": "A non-foaming milk for dry, reactive skin that would rather skip washing than feel squeaky.",  # Value pitch.
    },  # Close product 2.
    {  # Open product 3: a hydration serum.
        "id": "serum-hydra-boost",  # Stable identifier.
        "name": "Hydra Boost Hyaluronic Serum",  # Display name.
        "brand": "Northlight Skin (demo brand)",  # Invented demo brand.
        "step": "treat",  # Routine step.
        "targets": ["moisture", "texture", "radiance"],  # Concerns helped.
        "price": 24.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # Serums are not try-on products.
        "blurb": "Layered hyaluronic acid that pulls water into the top layers so skin stops feeling tight by noon.",  # Value pitch.
    },  # Close product 3.
    {  # Open product 4: a calming redness serum.
        "id": "serum-calm-niacinamide",  # Stable identifier.
        "name": "Calm 10% Niacinamide Serum",  # Display name.
        "brand": "Northlight Skin (demo brand)",  # Invented demo brand.
        "step": "treat",  # Routine step.
        "targets": ["redness", "pore", "radiance", "oiliness"],  # Concerns helped.
        "price": 19.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # No try-on for serums.
        "blurb": "Niacinamide to even out blotchiness, visibly tighten pore appearance, and take the shine down a notch.",  # Value pitch.
    },  # Close product 4.
    {  # Open product 5: an acne treatment serum.
        "id": "serum-clear-bha",  # Stable identifier.
        "name": "Clear Pore 2% BHA Serum",  # Display name.
        "brand": "Northlight Skin (demo brand)",  # Invented demo brand.
        "step": "treat",  # Routine step.
        "targets": ["acne", "pore", "texture", "oiliness"],  # Concerns helped.
        "price": 21.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # No try-on for serums.
        "blurb": "Salicylic acid that works inside the pore, aimed at blackheads and the breakouts that start as clogged pores.",  # Value pitch.
    },  # Close product 5.
    {  # Open product 6: a radiance vitamin C serum.
        "id": "serum-glow-vitaminc",  # Stable identifier.
        "name": "Morning Glow Vitamin C Serum",  # Display name.
        "brand": "Solenne (demo brand)",  # Invented demo brand.
        "step": "treat",  # Routine step.
        "targets": ["radiance", "wrinkle", "texture"],  # Concerns helped.
        "price": 32.0,  # Demo price in USD.
        "fragrance_free": False,  # Contains a light citrus scent; the refine loop can swap it out.
        "vto": False,  # No try-on for serums.
        "blurb": "A morning antioxidant serum for dull, uneven tone that makes skin look awake before makeup does.",  # Value pitch.
    },  # Close product 6.
    {  # Open product 7: a wrinkle-focused night serum.
        "id": "serum-night-retinal",  # Stable identifier.
        "name": "Night Renew Retinal 0.1 Serum",  # Display name.
        "brand": "Solenne (demo brand)",  # Invented demo brand.
        "step": "treat",  # Routine step.
        "targets": ["wrinkle", "texture", "radiance"],  # Concerns helped.
        "price": 38.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # No try-on for serums.
        "blurb": "A beginner-strength retinal for fine lines and rough patches, used at night two or three times a week to start.",  # Value pitch.
    },  # Close product 7.
    {  # Open product 8: a rich moisturizer.
        "id": "moisturizer-barrier-cream",  # Stable identifier.
        "name": "Barrier Repair Ceramide Cream",  # Display name.
        "brand": "Aurelle (demo brand)",  # Invented demo brand.
        "step": "moisturize",  # Routine step.
        "targets": ["moisture", "redness", "texture"],  # Concerns helped.
        "price": 26.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # Creams are not try-on products.
        "blurb": "Ceramides and squalane in a cushiony cream that seals in the serums under it and stops overnight water loss.",  # Value pitch.
    },  # Close product 8.
    {  # Open product 9: a light gel moisturizer for oily skin.
        "id": "moisturizer-gel-cloud",  # Stable identifier.
        "name": "Cloud Gel Oil-Free Moisturizer",  # Display name.
        "brand": "Aurelle (demo brand)",  # Invented demo brand.
        "step": "moisturize",  # Routine step.
        "targets": ["oiliness", "acne", "moisture"],  # Concerns helped.
        "price": 18.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # No try-on for gels.
        "blurb": "A water-gel that hydrates without grease, so oily and breakout-prone skin stops skipping moisturizer.",  # Value pitch.
    },  # Close product 9.
    {  # Open product 10: a daily sunscreen.
        "id": "spf-invisible-shield",  # Stable identifier.
        "name": "Invisible Shield SPF 50",  # Display name.
        "brand": "Solenne (demo brand)",  # Invented demo brand.
        "step": "protect",  # Routine step.
        "targets": ["radiance", "wrinkle", "redness"],  # Concerns helped (prevention counts as treatment here).
        "price": 22.0,  # Demo price in USD.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # Clear SPF has nothing visible to try on.
        "blurb": "A clear-gel SPF 50 with no white cast; the single highest-leverage step for spots, lines, and redness.",  # Value pitch.
    },  # Close product 10.
    {  # Open product 11: a tinted moisturizer with virtual try-on.
        "id": "tint-skin-veil",  # Stable identifier.
        "name": "Skin Veil Tinted Moisturizer",  # Display name.
        "brand": "Solenne (demo brand)",  # Invented demo brand.
        "step": "tint",  # Routine step (the fun, shoppable finish).
        "targets": ["radiance", "redness", "moisture"],  # Concerns helped.
        "price": 29.0,  # Demo price in USD.
        "fragrance_free": False,  # Lightly scented; refine can swap to the fragrance-free routine.
        "vto": True,  # This is a makeup product, so the card offers a YouCam Makeup VTO try-on.
        "vto_effect": "foundation",  # The YouCam makeup-vto effect this card maps to in live mode.
        "blurb": "Sheer tinted coverage that evens redness today while the routine underneath fixes it over weeks. Try your shade on your own photo.",  # Value pitch that sells the try-on.
    },  # Close product 11.
    {  # Open product 12: a tinted lip and cheek balm with virtual try-on.
        "id": "tint-lip-cheek",  # Stable identifier.
        "name": "Petal Tint Lip & Cheek Balm",  # Display name.
        "brand": "Solenne (demo brand)",  # Invented demo brand.
        "step": "tint",  # Routine step.
        "targets": ["radiance"],  # Concerns helped.
        "price": 16.0,  # Demo price in USD.
        "fragrance_free": False,  # Lightly scented.
        "vto": True,  # Lip color is a classic YouCam Makeup VTO effect.
        "vto_effect": "lip_color",  # The YouCam makeup-vto effect this card maps to in live mode.
        "blurb": "A two-minute healthy-color finish for dull days; preview the shade on your photo before it goes in the bag.",  # Value pitch.
    },  # Close product 12.
    {  # Open product 13: a budget mineral sunscreen so a $20 cap can be honored in the protect step too.
        "id": "spf-mineral-budget",  # Stable identifier.
        "name": "Everyday Mineral SPF 30",  # Display name.
        "brand": "Aurelle (demo brand)",  # Invented demo brand.
        "step": "protect",  # Routine step.
        "targets": ["radiance", "wrinkle", "redness"],  # Concerns helped (prevention, like the premium SPF).
        "price": 15.0,  # Demo price in USD - deliberately the budget option for this step.
        "fragrance_free": True,  # Fragrance-free.
        "vto": False,  # Mineral SPF has nothing visible to try on.
        "blurb": "A mineral SPF 30 that keeps the daily-protection habit alive when the budget tightens.",  # Value pitch.
    },  # Close product 13.
]  # Close the catalog list.
# Start the helper that finds one product by its stable identifier.  # Function: by_id.
def by_id(product_id):  # Define by_id with the identifier to look up.
    # Walk the catalog until the identifier matches.  # Loop: catalog scan.
    for product in PRODUCTS:  # The catalog is tiny, so a linear scan is fine.
        # Return the product when its id matches.  # Branch: match.
        if product["id"] == product_id:  # Exact identifier match.
            # Hand the product dictionary back to the caller.  # Step: return product.
            return product  # The full product record.
    # Return None when nothing matched, so callers can fail honestly.  # Step: no match.
    return None  # Unknown identifiers are a caller bug, surfaced as None.
# Start the helper that lists every product for one routine step.  # Function: for_step.
def for_step(step):  # Define for_step with the routine step name.
    # Filter the catalog down to the requested step, preserving catalog order.  # Step: filter.
    return [product for product in PRODUCTS if product["step"] == step]  # Catalog order doubles as a quality ranking within a step.
