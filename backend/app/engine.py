"""Pure recommendation logic: no database, providers, or learned feasibility."""

from itertools import product
import numpy as np

FEATURE_NAMES = ["formality", "warmth", "color harmony", "pattern simplicity"]
NEUTRALS = {"black", "white", "navy", "gray", "beige", "brown"}


def features(items):
    colors = [x["primary_color"] for x in items]
    color = sum(
        a == b or a in NEUTRALS or b in NEUTRALS
        for i, a in enumerate(colors)
        for b in colors[i + 1 :]
    ) / max(1, len(colors) * (len(colors) - 1) / 2)
    return np.array(
        [
            np.mean([x["formality"] / 4 for x in items]),
            np.mean([x["warmth"] / 4 for x in items]),
            color,
            np.mean([x["pattern"] == "solid" for x in items]),
        ],
        dtype=float,
    )


def weather_bounds(c):
    # Total warmth of body clothing (shoes/accessories excluded).
    effective = c.temperature - min(c.wind / 10, 5)
    return (
        (7, 16)
        if effective < 5
        else (4, 12)
        if effective < 15
        else (2, 8)
        if effective < 23
        else (0, 4)
    )


def eligible(g, c, owner):
    return (
        g["owner_id"] == owner
        and not g.get("archived", False)
        and g["laundry"] == "clean"
        and g["id"] not in c.excluded
        and c.min_formality <= g["formality"] <= c.max_formality
    )


def conflicts(items, c, owner):
    issues = []
    ids = [g["id"] for g in items]
    slots = [g["slot"] for g in items]
    if len(set(ids)) != len(ids):
        issues.append("Duplicate garment")
    if len(set(slots)) != len(slots):
        issues.append("Only one garment per slot")
    body = set(slots) - {"outerwear", "accessory"}
    if body not in ({"top", "bottom", "shoes"}, {"onepiece", "shoes"}):
        issues.append("Use top + bottom + shoes, or one-piece + shoes")
    if not set(c.required) <= set(ids):
        issues.append("Required garments missing")
    if c.outerwear and "outerwear" not in slots:
        issues.append("Outerwear requested")
    if c.accessory and "accessory" not in slots:
        issues.append("Accessory requested")
    if not all(eligible(g, c, owner) for g in items):
        issues.append("Ownership, availability, exclusion or dress-code conflict")
    warmth = sum(g["warmth"] for g in items if g["slot"] not in ("shoes", "accessory"))
    lo, hi = weather_bounds(c)
    if not lo <= warmth <= hi:
        issues.append(f"Body warmth {warmth} must be within {lo}–{hi}")
    if c.precipitation == "rain" and any(
        "rain" not in g["weather"] for g in items if g["slot"] in ("shoes", "outerwear")
    ):
        issues.append("Rain requires rain-suitable shoes and outerwear")
    if c.wind >= 25 and not any(
        g["slot"] == "outerwear" and "wind" in g["weather"] for g in items
    ):
        issues.append("Strong wind requires wind-suitable outerwear")
    return issues


def preflight(wardrobe, c, owner):
    byid = {g["id"]: g for g in wardrobe}
    for id in c.required:
        if id not in byid or not eligible(byid[id], c, owner):
            return (
                "REQUIRED_ITEM_UNAVAILABLE",
                "A required item is missing, archived, dirty, excluded, outside dress bounds, or belongs to another user. Correct it or remove the requirement.",
            )
    slots = [byid[i]["slot"] for i in c.required]
    if len(slots) != len(set(slots)) or (
        "onepiece" in slots and ("top" in slots or "bottom" in slots)
    ):
        return (
            "INCOMPATIBLE_REQUIRED_ITEMS",
            "Required items occupy the same slot or mix a one-piece with separates. Choose one template.",
        )
    return None


def score(items, c, vector=None, recent=None, history=None, ablation=None):
    f = features(items)
    lo, hi = weather_bounds(c)
    warmth = sum(g["warmth"] for g in items if g["slot"] not in ("shoes", "accessory"))
    ids = frozenset(g["id"] for g in items)
    comp = {
        "color": float(f[2]),
        "coherence": 1
        - (max(g["formality"] for g in items) - min(g["formality"] for g in items)) / 4,
        "comfort": max(0, 1 - abs(warmth - (lo + hi) / 2) / max(1, (hi - lo) / 2)),
        "personal": float(np.dot(vector if vector is not None else np.zeros(4), f)),
        "novelty": 0.0 if ids in (history or []) else 1.0,
        "rotation": 1 - float(np.mean([(recent or {}).get(g["id"], 0) for g in items])),
    }
    weights = {
        "color": 0.22,
        "coherence": 0.22,
        "comfort": 0.18,
        "personal": 0.35,
        "novelty": 0.10,
        "rotation": 0.10,
    }
    if ablation == "no_color":
        weights["color"] = 0
    if ablation == "no_recency":
        weights["rotation"] = 0
    if ablation == "no_personalization":
        weights["personal"] = 0
    comp["total"] = sum(comp[k] * weights[k] for k in weights)
    return {k: round(v, 5) for k, v in comp.items()}


def templates(c):
    extra = (["outerwear"] if c.outerwear else []) + (
        ["accessory"] if c.accessory else []
    )
    # Required optional slots must participate even when the toggle is off.
    return [["top", "bottom", "shoes"] + extra, ["onepiece", "shoes"] + extra]


def candidates(
    wardrobe,
    c,
    owner,
    vector=None,
    recent=None,
    history=None,
    beam=160,
    cap=24,
    exhaustive=False,
):
    error = preflight(wardrobe, c, owner)
    if error:
        return [], error
    pools = {
        slot: [
            g
            for g in wardrobe
            if g["slot"] == slot
            and eligible(g, c, owner)
            and not (
                c.precipitation == "rain"
                and slot in ("shoes", "outerwear")
                and "rain" not in g["weather"]
            )
            and not (
                c.wind >= 25 and slot == "outerwear" and "wind" not in g["weather"]
            )
        ]
        for slot in ("top", "bottom", "shoes", "onepiece", "outerwear", "accessory")
    }
    required = {g["slot"]: g for g in wardrobe if g["id"] in c.required}
    results = []
    for original_slots in templates(c):
        slots = original_slots + [
            s
            for s in required
            if s not in original_slots and s in ("outerwear", "accessory")
        ]
        if not set(required) <= set(slots):
            continue
        lists = []
        for s in slots:
            pool = [required[s]] if s in required else pools[s]
            pool = sorted(
                pool,
                key=lambda g: (
                    -0.35
                    * float(
                        np.dot(
                            vector if vector is not None else np.zeros(4), features([g])
                        )
                    ),
                    -g["formality"],
                    g["id"],
                ),
            )
            lists.append(pool if exhaustive else pool[:cap])
        if any(not p for p in lists):
            continue
        if exhaustive:
            states = product(*lists)
        else:
            states = [[]]
            for pool in lists:
                expanded = [state + [g] for state in states for g in pool]
                # Partial scoring uses same soft features; hard checks occur on complete boards.
                states = sorted(
                    expanded,
                    key=lambda x: score(x, c, vector, recent, history)["total"],
                    reverse=True,
                )[:beam]
        for state in states:
            state = list(state)
            if not conflicts(state, c, owner):
                results.append((state, score(state, c, vector, recent, history)))
    if not results:
        missing = [s for s in ("shoes",) if not pools[s]]
        message = (
            ("No eligible " + ", ".join(missing) + ". " if missing else "")
            + "No feasible board found within the candidate budget. Check clean status, dress bounds, warmth, rain protection and required items; constraints were not relaxed."
        )
        return [], ("NO_FEASIBLE_OUTFIT", message)
    return sorted(results, key=lambda p: p[1]["total"], reverse=True), None


def diverse(ranked, n=3):
    selected = []
    remaining = list(ranked)
    while remaining and len(selected) < n:

        def utility(p):
            ids = {x["id"] for x in p[0]}
            similarity = max(
                (
                    len(ids & {x["id"] for x in q[0]})
                    / len(ids | {x["id"] for x in q[0]})
                    for q in selected
                ),
                default=0,
            )
            return p[1]["total"] - 0.25 * similarity

        best = max(remaining, key=utility)
        remaining.remove(best)
        if not any(
            {g["id"] for g in best[0]} == {g["id"] for g in q[0]} for q in selected
        ):
            selected.append(best)
    return selected


def adjust(items, wardrobe, c, owner, direction, vector=None):
    attribute = "warmth" if direction in ("warmer", "cooler") else "formality"
    sign = 1 if direction in ("warmer", "formal") else -1
    alternatives = []
    for i, old in enumerate(items):
        if old["id"] in c.required:
            continue
        for new in wardrobe:
            if (
                new["slot"] != old["slot"]
                or new["id"] == old["id"]
                or sign * (new[attribute] - old[attribute]) <= 0
            ):
                continue
            updated = items[:i] + [new] + items[i + 1 :]
            if conflicts(updated, c, owner):
                continue
            penalty = (
                0.08 * (new["primary_color"] != old["primary_color"])
                + 0.06 * (new["pattern"] != old["pattern"])
                + 0.04
                * abs(
                    new["formality" if attribute == "warmth" else "warmth"]
                    - old["formality" if attribute == "warmth" else "warmth"]
                )
            )
            alternatives.append(
                (score(updated, c, vector)["total"] - penalty, updated, old, new)
            )
    if not alternatives:
        return None
    _, updated, old, new = max(alternatives, key=lambda x: x[0])
    return (
        updated,
        old,
        new,
        f"Replaced {old['name']} with {new['name']}: {attribute} {old[attribute]} → {new[attribute]}. All other garment IDs and hard constraints are preserved.",
    )


def update_preferences(vector, count, items, event, reason=None):
    # Signed, centered content evidence with a five-event prior; skips add no label.
    if event == "skipped":
        return list(vector), count
    x = features(items) - 0.5
    label = {"liked": 1.0, "disliked": -1.0, "wore": 0.6}[event]
    evidence = label * x
    reason_signal = {
        "too formal": (0, -1),
        "too casual": (0, 1),
        "too cold": (1, 1),
        "too warm": (1, -1),
        "don’t like the colors": (2, 1),
    }
    if reason in reason_signal:
        i, d = reason_signal[reason]
        evidence[i] = d * 0.75
    updated = (np.array(vector) * (count + 5) + evidence) / (count + 6)
    return np.clip(updated, -1, 1).tolist(), count + 1
