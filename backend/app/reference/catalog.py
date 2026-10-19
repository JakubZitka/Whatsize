"""Dimension tables: garment categories, measurement points, size systems, fit types."""

from __future__ import annotations

# Measurement keys used across the chart table, the engine and the API.
DIMENSIONS = [
    "bust_chest_cm",
    "underbust_cm",
    "waist_cm",
    "hip_cm",
    "neck_cm",
    "stature_cm",
    "foot_length_mm",
]

# --------------------------------------------------------------------------
# dim_garment_category — the primary dimension is a function of
# (category, gender), never a constant (PRD §8.1 principle 5, EN 13402-2).
# --------------------------------------------------------------------------
GARMENT_CATEGORIES: list[dict] = [
    # code, gender, name_en, name_cs, kind, primary, secondary, zone
    ("W_TOPS", "W", "Tops & T-shirts", "Trička a topy", "w_upper",
     "bust_chest_cm", "waist_cm|hip_cm|stature_cm", "torso"),
    ("W_DRESSES", "W", "Dresses", "Šaty", "w_upper",
     "bust_chest_cm", "waist_cm|hip_cm|stature_cm", "full"),
    ("W_TROUSERS", "W", "Trousers", "Kalhoty", "w_lower",
     "waist_cm", "hip_cm|stature_cm", "legs"),
    ("W_JEANS", "W", "Jeans", "Džíny", "w_jeans",
     "waist_cm", "hip_cm|stature_cm", "legs"),
    ("W_SKIRTS", "W", "Skirts", "Sukně", "w_lower",
     "waist_cm", "hip_cm", "legs"),
    ("W_JACKETS", "W", "Jackets", "Bundy a saka", "w_upper",
     "bust_chest_cm", "waist_cm|hip_cm|stature_cm", "torso"),
    ("W_COATS", "W", "Coats", "Kabáty", "w_upper",
     "bust_chest_cm", "waist_cm|hip_cm|stature_cm", "full"),
    ("W_BRA", "W", "Bras", "Podprsenky", "bra",
     "underbust_cm+bust_chest_cm", "", "torso"),
    ("W_FOOTWEAR", "W", "Footwear", "Obuv", "foot",
     "foot_length_mm", "", "feet"),
    ("M_TOPS", "M", "Tops & T-shirts", "Trička a mikiny", "m_upper",
     "bust_chest_cm", "waist_cm|stature_cm", "torso"),
    ("M_SHIRTS", "M", "Shirts", "Košile", "m_shirt",
     "neck_cm", "bust_chest_cm|stature_cm", "torso"),
    ("M_TROUSERS", "M", "Trousers", "Kalhoty", "m_lower",
     "waist_cm", "hip_cm|stature_cm", "legs"),
    ("M_JEANS", "M", "Jeans", "Džíny", "m_jeans",
     "waist_cm", "hip_cm|stature_cm", "legs"),
    ("M_JACKETS", "M", "Jackets & suits", "Bundy a saka", "m_upper",
     "bust_chest_cm", "waist_cm|stature_cm", "torso"),
    ("M_COATS", "M", "Coats", "Kabáty", "m_upper",
     "bust_chest_cm", "waist_cm|stature_cm", "full"),
    ("M_FOOTWEAR", "M", "Footwear", "Obuv", "foot",
     "foot_length_mm", "", "feet"),
    ("K_ALL", "K", "Children's clothing", "Dětské oblečení", "kids",
     "stature_cm", "", "full"),
]
GARMENT_CATEGORIES = [
    dict(zip(["category_code", "gender", "name_en", "name_cs", "kind", "primary_dimension",
              "secondary_dimensions", "silhouette_zone"], row, strict=True))
    for row in GARMENT_CATEGORIES
]
CATEGORY_BY_CODE = {c["category_code"]: c for c in GARMENT_CATEGORIES}

# --------------------------------------------------------------------------
# dim_measurement_point — ISO 8559-1 aligned vocabulary. Clause numbers are
# deliberately not stated until checked against the standard text.
# --------------------------------------------------------------------------
_MP = [
    # code, name_en, name_cs, group, unit, self_measurable, maps_to, how_to / tension
    ("stature", "Stature", "Tělesná výška", "height", "cm", True, "stature_cm",
     "Barefoot, back against a wall, from floor to top of head."),
    ("bust_girth", "Bust girth", "Obvod přes prsa", "girth", "cm", True, "bust_chest_cm",
     "Over the fullest part of the bust. Tape LOOSE — resting, not compressing."),
    ("chest_girth", "Chest girth", "Obvod hrudníku", "girth", "cm", True, "bust_chest_cm",
     "Under the armpits over the fullest part of the chest, tape horizontal."),
    ("underbust_girth", "Underbust girth", "Obvod pod prsy", "girth", "cm", True,
     "underbust_cm", "Directly under the bust. Tape SNUG — firm, exhale normally."),
    ("waist_girth", "Waist girth", "Obvod pasu", "girth", "cm", True, "waist_cm",
     "At the natural waist (narrowest point), relaxed, tape horizontal."),
    ("hip_girth", "Hip girth", "Obvod boků", "girth", "cm", True, "hip_cm",
     "Over the fullest part of the seat, feet together."),
    ("high_hip_girth", "High hip girth", "Obvod horních boků", "girth", "cm", True, "",
     "About 10 cm below the waist, over the hip bones."),
    ("neck_girth", "Neck girth", "Obvod krku", "girth", "cm", True, "neck_cm",
     "Around the neck at the Adam's apple level, one finger under the tape."),
    ("neck_base_girth", "Neck base girth", "Obvod u kořene krku", "girth", "cm", False, "",
     "Around the base of the neck through the neck points."),
    ("upper_arm_girth", "Upper arm girth", "Obvod paže", "girth", "cm", True, "",
     "Fullest part of the upper arm, arm relaxed."),
    ("wrist_girth", "Wrist girth", "Obvod zápěstí", "girth", "cm", True, "",
     "Over the wrist bone."),
    ("thigh_girth", "Thigh girth", "Obvod stehna", "girth", "cm", True, "",
     "Fullest part of the thigh, just below the crotch."),
    ("knee_girth", "Knee girth", "Obvod kolena", "girth", "cm", True, "",
     "Around the middle of the knee cap, leg straight."),
    ("calf_girth", "Calf girth", "Obvod lýtka", "girth", "cm", True, "",
     "Fullest part of the calf."),
    ("head_girth", "Head girth", "Obvod hlavy", "girth", "cm", True, "",
     "Above the eyebrows and ears."),
    ("inside_leg_length", "Inside leg length", "Vnitřní délka nohy", "length", "cm", True, "",
     "Crotch to floor, barefoot. Easier with a book pressed up as a marker."),
    ("outside_leg_length", "Outside leg length", "Vnější délka nohy", "length", "cm", False, "",
     "Side waist to floor."),
    ("arm_length", "Arm length", "Délka paže", "length", "cm", False, "",
     "Shoulder point over the bent elbow to the wrist — needs a second person."),
    ("shoulder_width", "Shoulder width", "Šířka ramen", "width", "cm", False, "",
     "Across the back between the shoulder points."),
    ("back_width", "Back width", "Šířka zad", "width", "cm", False, "",
     "Across the back between the armpit creases."),
    ("back_waist_length", "Back waist length", "Délka zad do pasu", "length", "cm", False, "",
     "Cervical vertebra (C7) to waist."),
    ("total_crotch_length", "Total crotch length", "Délka sedu", "length", "cm", False, "",
     "Front waist through the crotch to back waist."),
    ("foot_length", "Foot length", "Délka chodidla", "foot", "mm", True, "foot_length_mm",
     "Standing, heel against a wall, to the tip of the longest toe. Measure both feet."),
    ("foot_width", "Foot width", "Šířka chodidla", "foot", "mm", True, "",
     "Widest part of the foot while standing."),
    ("body_mass", "Body mass", "Tělesná hmotnost", "mass", "kg", True, "",
     "Optional. Used only as a plausibility signal (PRD §10)."),
]
MEASUREMENT_POINTS = [
    dict(zip(["code", "name_en", "name_cs", "iso_8559_1_group", "unit", "self_measurable",
              "maps_to_dimension", "how_to_measure"], row, strict=True))
    for row in _MP
]

# --------------------------------------------------------------------------
# dim_size_system — every labelling system with its rule and its traps.
# --------------------------------------------------------------------------
_SS = [
    ("EU_DE", "Germany / Central Europe", "women & men apparel", "scalar",
     "Women: bust/2 - 6. Men: chest/2.",
     "Shops label it just 'EU' — the same body is EU_FR two sizes up."),
    ("EU_FR", "France / Spain / Belgium", "women apparel", "scalar",
     "Women: bust/2 - 4 (= EU_DE + 2).", "Inditex and Mango label in this scale as 'EU'."),
    ("IT", "Italy", "women & men apparel", "scalar",
     "Women: EU_DE + 6. Men: = EU_DE.",
     "Some Italian menswear brands label EU + 2 — verify per brand."),
    ("UK", "United Kingdom", "women & men apparel", "scalar",
     "Women: EU_DE - 26. Men jackets: chest in inches (= EU - 10).",
     "Women's UK and US differ by 4, not 2."),
    ("US", "United States", "women & men apparel", "scalar",
     "Women: EU_DE - 30. Men jackets: chest in inches.",
     "No mandatory US standard since 1983; brand drift is large."),
    ("AU", "Australia", "women apparel", "scalar", "Women: = UK.", ""),
    ("ALPHA", "Letter sizes (EN 13402-3)", "apparel", "range",
     "Stored band per letter, see ref tables.",
     "Bands widen irregularly above L/XL — cannot be generated by a rule."),
    ("WL", "Waist / length (inches)", "jeans & trousers", "tuple",
     "W = body waist in inches, L = inside leg in inches.",
     "Brands run large on W (vanity sizing) — per-brand offset."),
    ("JP_JIS", "Japan JIS L 4005", "women apparel", "tuple",
     "Number (bust, 3 cm steps) + body type A/Y/AB/B + height P/R/T, e.g. 9AR.",
     "A tuple, not a scalar — storing '9' loses information."),
    ("CN_GBT", "China GB/T 1335", "apparel", "tuple",
     "Stature/girth + drop code, e.g. 160/84A.", "Drop code A/Y/B/C encodes build."),
    ("NECK_CM", "Shirt neck (cm)", "men shirts", "scalar",
     "Neck girth in cm.", "Primary dimension for formal shirts is neck, not chest."),
    ("NECK_IN", "Shirt neck (inches)", "men shirts", "scalar",
     "Neck girth in inches, half sizes.", ""),
    ("KIDS_HEIGHT", "Children by height", "children", "scalar",
     "Label = stature in cm (6 cm steps).", "Age labels are proxies — height is the key."),
    ("BRA_EU", "Bra EU (EN 13402)", "bras", "tuple",
     "Band = underbust rounded to 5 cm; cup = bust - underbust in 2 cm steps.",
     "Cup letters diverge from UK/US above D."),
    ("BRA_FR", "Bra France / Spain", "bras", "tuple", "Band = EU + 15; cup = EU.", ""),
    ("BRA_IT", "Bra Italy", "bras", "tuple", "Band index 0 = EU 60; cup = EU.", ""),
    ("BRA_UK", "Bra UK", "bras", "tuple",
     "Band in inches; cups A B C D DD E F FF G GG H (2.54 cm steps).",
     "UK E = EU F. Use retail equivalences, not arithmetic."),
    ("BRA_US", "Bra US", "bras", "tuple", "Band in inches; cups … D DD DDD G H.",
     "US DDD = UK E = EU F."),
    ("BRA_AU", "Bra Australia", "bras", "tuple", "Band = UK - 22; cups = UK.", ""),
    ("BRA_JP", "Bra Japan", "bras", "tuple", "Band = EU; cup steps 2.5 cm.",
     "JP letter is about one cup above the EU letter."),
    ("SHOE_EU", "Shoes EU (Paris point)", "footwear", "scalar",
     "EU = 1.5 x (foot cm + 1.5). Step 6.67 mm.", "Some brands grid in 1/2 or 1/3 sizes."),
    ("SHOE_UK", "Shoes UK (barleycorn)", "footwear", "scalar",
     "UK = 3 x foot inches - 23. Step 8.47 mm.", ""),
    ("SHOE_US_M", "Shoes US men", "footwear", "scalar",
     "US M = UK + offset (usually 1, some brands 0.5).",
     "US-to-UK offset is not constant across manufacturers — per brand."),
    ("SHOE_US_W", "Shoes US women", "footwear", "scalar",
     "US W = US M + 1.5 (or + 1, or + 2 on unisex grids).",
     "Per-brand attribute, never a global constant."),
    ("SHOE_MONDO", "Mondopoint (ISO 9407) / JP", "footwear", "scalar",
     "Foot length in mm (JP shows cm).", "Canonical key of the schema."),
]
SIZE_SYSTEMS = [
    dict(zip(["code", "name", "applies_to", "value_type", "conversion_rule", "traps"], row,
             strict=True))
    for row in _SS
]

# --------------------------------------------------------------------------
# dim_fit_type — fit is orthogonal to size, never part of the label (FR-2.2).
# size_shift_cm moves the user's effective girth when scoring: less ease
# (slim) sizes up at the margin, more ease (relaxed) sizes down.
# --------------------------------------------------------------------------
_FT = [
    # code, name_cs, kind, ease_min, ease_max, length_delta, size_shift, rule
    ("skinny", "Skinny", "ease", -2, 2, 0, 1.0, "Stretch fabric, negative ease possible."),
    ("slim", "Slim", "ease", 4, 8, 0, 1.0, ""),
    ("regular", "Regular", "ease", 8, 14, 0, 0.0, "Default fit."),
    ("relaxed", "Relaxed", "ease", 14, 20, 0, -1.0, ""),
    ("oversized", "Oversized", "ease", 20, 35, 0, -2.0, ""),
    ("petite", "Petite", "proportional", None, None, -5, 0.0,
     "Stature below the block assumption (W <= 160 cm, M <= 170 cm)."),
    ("tall", "Tall", "proportional", None, None, 5, 0.0,
     "Stature above the block assumption (W >= 176 cm, M >= 188 cm)."),
    ("curvy", "Curvy", "proportional", None, None, 0, 0.0,
     "Large hip-waist differential (W: hip - waist >= 30 cm); hip ranges +5 cm."),
    ("athletic", "Athletic", "proportional", None, None, 0, 0.0,
     "Large chest-waist drop (M: chest - waist >= 18 cm); waist -6 / hip +4 cm."),
    ("plus", "Plus", "proportional", None, None, 0, 0.0, "Extended size run (W bust >= 107)."),
    ("maternity", "Těhotenské", "proportional", None, None, 0, 0.0,
     "User-selected only — never inferred (PRD §10)."),
]
FIT_TYPES = [
    dict(zip(["fit_code", "name_cs", "kind", "girth_ease_min_cm", "girth_ease_max_cm",
              "length_delta_cm", "size_shift_cm", "rule"], row, strict=True))
    for row in _FT
]
FIT_BY_CODE = {f["fit_code"]: f for f in FIT_TYPES}
