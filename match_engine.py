from copy import deepcopy

import networkx as nx

from music_profile import normalize_items, weighted_overlap


SIGNAL_WEIGHTS = {"current": 0.35, "rewind": 0.40, "identity": 0.25}


def artist_stack(profile):
    return normalize_items(
        profile.get("forever_artists", [])
        + profile.get("current_artists", [])
        + profile.get("wildcard_artists", []),
        limit=8,
    )


def shared_items(left, right):
    right_keys = {item.casefold() for item in right}
    return [item for item in left if item.casefold() in right_keys]


def score_breakdown(left_profile, right_profile):
    left_artists = artist_stack(left_profile)
    right_artists = artist_stack(right_profile)
    current = weighted_overlap(
        left_profile.get("current_items", []), right_profile.get("current_items", [])
    )
    rewind = weighted_overlap(
        left_profile.get("rewind_items", []), right_profile.get("rewind_items", [])
    )
    identity = weighted_overlap(left_artists, right_artists)
    total = round(
        SIGNAL_WEIGHTS["current"] * current
        + SIGNAL_WEIGHTS["rewind"] * rewind
        + SIGNAL_WEIGHTS["identity"] * identity,
        4,
    )
    return {
        "total": total,
        "current": current,
        "rewind": rewind,
        "identity": identity,
        "shared_current": shared_items(
            left_profile.get("current_items", []), right_profile.get("current_items", [])
        ),
        "shared_rewind": shared_items(
            left_profile.get("rewind_items", []), right_profile.get("rewind_items", [])
        ),
        "shared_artists": shared_items(left_artists, right_artists),
    }


def mutual_relationship(left, right):
    left_looking = set(left.get("looking_for", []))
    right_looking = set(right.get("looking_for", []))
    if "Friend" in left_looking and "Friend" in right_looking:
        return "Friend"
    if "Partner" not in left_looking or "Partner" not in right_looking:
        return None
    if right.get("gender") not in left.get("attracted_to", []):
        return None
    if left.get("gender") not in right.get("attracted_to", []):
        return None
    return "Partner"


def maximum_weight_pairs(people, respect_constraints=True, minimum_score=0.01):
    people = deepcopy(people)
    by_id = {person["id"]: person for person in people}
    graph = nx.Graph()
    graph.add_nodes_from(by_id)
    candidates = []

    for left_index, left in enumerate(people):
        for right in people[left_index + 1 :]:
            relationship = mutual_relationship(left, right)
            if respect_constraints and relationship is None:
                continue
            breakdown = score_breakdown(left["profile"], right["profile"])
            candidate = {
                "left_id": left["id"],
                "right_id": right["id"],
                "relationship": relationship or "Unfiltered",
                "score": breakdown["total"],
                "breakdown": breakdown,
            }
            candidates.append(candidate)
            if breakdown["total"] >= minimum_score:
                graph.add_edge(
                    left["id"],
                    right["id"],
                    weight=breakdown["total"],
                    candidate=candidate,
                )

    matched_edges = nx.algorithms.matching.max_weight_matching(
        graph, maxcardinality=True, weight="weight"
    )
    pairs = []
    matched_ids = set()
    for left_id, right_id in matched_edges:
        edge = graph.get_edge_data(left_id, right_id)
        candidate = deepcopy(edge["candidate"])
        left = by_id[left_id]
        right = by_id[right_id]
        candidate.update(
            {
                "left": left,
                "right": right,
                "expected": left.get("expected_match") == right_id
                and right.get("expected_match") == left_id,
            }
        )
        pairs.append(candidate)
        matched_ids.update((left_id, right_id))

    pairs.sort(key=lambda pair: pair["score"], reverse=True)
    unmatched = [person for person in people if person["id"] not in matched_ids]
    return {"pairs": pairs, "unmatched": unmatched, "candidates": candidates}
