import random
from copy import deepcopy

from match_engine import maximum_weight_pairs, mutual_relationship, score_breakdown


def profile(current, rewind, forever, current_artists=(), wildcards=()):
    return {
        "current_items": list(current),
        "rewind_items": list(rewind),
        "forever_artists": list(forever),
        "current_artists": list(current_artists),
        "wildcard_artists": list(wildcards),
    }


SAMPLE_COHORT = [
    {
        "id": "avery", "name": "Avery", "gender": "Woman", "looking_for": ["Friend"],
        "attracted_to": [], "expected_match": "blair", "color": "coral",
        "profile": profile(
            ["Saturn — SZA", "Snooze — SZA", "Pink + White — Frank Ocean"],
            ["Nights — Frank Ocean", "Supermodel — SZA", "Japanese Denim — Daniel Caesar"],
            ["SZA", "Frank Ocean", "Daniel Caesar"], ["Tems", "Ravyn Lenae"], ["Solange"],
        ),
    },
    {
        "id": "blair", "name": "Blair", "gender": "Nonbinary", "looking_for": ["Friend"],
        "attracted_to": [], "expected_match": "avery", "color": "coral",
        "profile": profile(
            ["Saturn — SZA", "Pink + White — Frank Ocean", "Love Me JeJe — Tems"],
            ["Nights — Frank Ocean", "Supermodel — SZA", "Get You — Daniel Caesar"],
            ["Frank Ocean", "SZA", "Daniel Caesar"], ["Tems", "Blood Orange"], ["Solange"],
        ),
    },
    {
        "id": "casey", "name": "Casey", "gender": "Man", "looking_for": ["Friend"],
        "attracted_to": [], "expected_match": "drew", "color": "mint",
        "profile": profile(
            ["Starburster — Fontaines D.C.", "Alesis — Mk.gee", "Not Strong Enough — boygenius"],
            ["Someday — The Strokes", "Ribs — Lorde", "Myth — Beach House"],
            ["The Strokes", "Lorde", "Beach House"], ["Mk.gee", "Fontaines D.C."], ["Big Thief"],
        ),
    },
    {
        "id": "drew", "name": "Drew", "gender": "Woman", "looking_for": ["Friend"],
        "attracted_to": [], "expected_match": "casey", "color": "mint",
        "profile": profile(
            ["Starburster — Fontaines D.C.", "Alesis — Mk.gee", "Simulation Swarm — Big Thief"],
            ["Someday — The Strokes", "Ribs — Lorde", "Myth — Beach House"],
            ["Lorde", "The Strokes", "Beach House"], ["Mk.gee", "Big Thief"], ["Wednesday"],
        ),
    },
    {
        "id": "emery", "name": "Emery", "gender": "Nonbinary", "looking_for": ["Friend"],
        "attracted_to": [], "expected_match": "finley", "color": "violet",
        "profile": profile(
            ["Xtal — Aphex Twin", "Archangel — Burial", "Glue — Bicep"],
            ["Roygbiv — Boards of Canada", "Two Thousand and Seventeen — Four Tet", "Windowlicker — Aphex Twin"],
            ["Aphex Twin", "Boards of Canada", "Burial"], ["Bicep", "Four Tet"], ["SOPHIE"],
        ),
    },
    {
        "id": "finley", "name": "Finley", "gender": "Man", "looking_for": ["Friend"],
        "attracted_to": [], "expected_match": "emery", "color": "violet",
        "profile": profile(
            ["Xtal — Aphex Twin", "Archangel — Burial", "Apricots — Bicep"],
            ["Roygbiv — Boards of Canada", "Two Thousand and Seventeen — Four Tet", "Windowlicker — Aphex Twin"],
            ["Boards of Canada", "Aphex Twin", "Burial"], ["Four Tet", "Bicep"], ["Autechre"],
        ),
    },
    {
        "id": "gray", "name": "Gray", "gender": "Man", "looking_for": ["Partner"],
        "attracted_to": ["Woman"], "expected_match": "hayden", "color": "gold",
        "profile": profile(
            ["Good Luck, Babe! — Chappell Roan", "360 — Charli xcx", "Espresso — Sabrina Carpenter"],
            ["Supercut — Lorde", "Style — Taylor Swift", "Dancing On My Own — Robyn"],
            ["Lorde", "Charli xcx", "Robyn"], ["Chappell Roan", "Caroline Polachek"], ["Carly Rae Jepsen"],
        ),
    },
    {
        "id": "hayden", "name": "Hayden", "gender": "Woman", "looking_for": ["Partner"],
        "attracted_to": ["Man"], "expected_match": "gray", "color": "gold",
        "profile": profile(
            ["Good Luck, Babe! — Chappell Roan", "360 — Charli xcx", "Von dutch — Charli xcx"],
            ["Supercut — Lorde", "Style — Taylor Swift", "Dancing On My Own — Robyn"],
            ["Charli xcx", "Lorde", "Robyn"], ["Chappell Roan", "Caroline Polachek"], ["Carly Rae Jepsen"],
        ),
    },
]


def apply_noise(people, noise_percent, seed=7):
    noisy = deepcopy(people)
    rate = max(0, min(int(noise_percent), 50)) / 100
    if rate == 0:
        return noisy
    for person in noisy:
        for key in ("current_items", "rewind_items", "forever_artists", "current_artists", "wildcard_artists"):
            values = person["profile"].get(key, [])
            rng = random.Random(f"{seed}:{person['id']}:{key}")
            kept = [value for value in values if rng.random() >= rate]
            if values and not kept:
                kept = [values[rng.randrange(len(values))]]
            rng.shuffle(kept)
            person["profile"][key] = kept
    return noisy


def matrix_for(people, respect_constraints):
    matrix = []
    for left in people:
        row = []
        for right in people:
            if left["id"] == right["id"]:
                row.append(None)
                continue
            relationship = mutual_relationship(left, right)
            row.append(
                {
                    "score": score_breakdown(left["profile"], right["profile"])["total"],
                    "eligible": not respect_constraints or relationship is not None,
                }
            )
        matrix.append(row)
    return matrix


def build_match_lab(noise_percent=0, respect_constraints=True):
    people = apply_noise(SAMPLE_COHORT, noise_percent)
    outcome = maximum_weight_pairs(people, respect_constraints=respect_constraints)
    expected_total = len(people) // 2
    recovered = sum(1 for pair in outcome["pairs"] if pair["expected"])
    eligible_edges = len(outcome["candidates"])
    average_score = (
        round(sum(pair["score"] for pair in outcome["pairs"]) / len(outcome["pairs"]), 3)
        if outcome["pairs"] else 0
    )
    return {
        "people": people,
        "pairs": outcome["pairs"],
        "unmatched": outcome["unmatched"],
        "matrix": matrix_for(people, respect_constraints),
        "noise_percent": int(noise_percent),
        "respect_constraints": respect_constraints,
        "metrics": {
            "expected_recovered": recovered,
            "expected_total": expected_total,
            "eligible_edges": eligible_edges,
            "average_score": average_score,
        },
    }
