#!/usr/bin/env python3
"""The auto tier: which researched entries ship without the maintainer
reading each one.

An entry may carry `"review": {"state": "approved", "by": "auto"}` only
when all of these hold (the own repository design, section 6):

- its position is confirmed by two stated figures, or stated by one fine
  figure on an official or operator page;
- a second, independent pass re-read every page it cites and agreed with
  every fact, and no fact changed since (`second_pass.facts` is the hash of
  the facts it checked);
- the machine checks (in water, in the named place, not a copied point of
  a hotel or village) ran and passed (`checks`);
- no other standing entry lies within 500 m.

The checker enforces this, so CI refuses an auto approval the tier does not
allow, whatever wrote it. Everything else that passes the checker comes to
the maintainer entry by entry.
"""

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence  # noqa: E402

CHECK_NAMES = ("in_water", "in_place", "copied_point")
AUTO_KINDS = ("official", "operator")
# Fields that may change after the second pass without voiding it: the
# decision, the pass itself, the checks and the researcher's own note.
_NOT_FACTS = ("review", "second_pass", "checks", "note")


def facts_hash(entry: dict) -> str:
    """The hash of an entry's facts, as the second pass checked them."""
    facts = {key: value for key, value in entry.items() if key not in _NOT_FACTS}
    text = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fine_stated_sources(entry: dict, domains) -> list[dict]:
    """The counting, stated position figures fine enough to place a site."""
    import check  # here, not at the top: check imports this module

    fine = []
    for source in (entry.get("position") or {}).get("sources") or []:
        if not isinstance(source, dict) or source.get("method", "stated") != "stated":
            continue
        if domains.kind_of(str(source.get("url"))) != "counting":
            continue
        try:
            _, lat_step = evidence.parse_coordinate(source.get("lat"), "lat")
            _, lon_step = evidence.parse_coordinate(source.get("lon"), "lon")
        except (TypeError, ValueError):
            continue
        if lat_step <= check.COARSEST_DEG and lon_step <= check.COARSEST_DEG:
            fine.append(source)
    return fine


def auto_tier_problems(checked, domains, *, near: list[str]) -> list[str]:
    """Why [checked] may not be approved by the auto tier; empty when it
    may. [near] names the standing entries within 500 m of it."""
    entry = checked.entry
    problems = []
    if checked.route == "confirmed":
        pass
    elif checked.route == "stated":
        kinds = {domains.kind_for(str(s.get("url"))) for s in _fine_stated_sources(entry, domains)}
        if not kinds & set(AUTO_KINDS):
            problems.append("its stated position is not on an official or operator page")
    else:
        problems.append(f"its position is {checked.route or 'missing'}, not stated")

    second_pass = entry.get("second_pass")
    if not isinstance(second_pass, dict):
        problems.append("no second pass")
    elif second_pass.get("agrees") is not True:
        problems.append("the second pass did not agree with every fact")
    elif second_pass.get("facts") != facts_hash(entry):
        problems.append("its facts changed after the second pass")

    results = {c.get("name"): c.get("passed") for c in entry.get("checks") or [] if isinstance(c, dict)}
    for name in CHECK_NAMES:
        if name not in results:
            problems.append(f"no {name} check")
        elif results[name] is not True:
            problems.append(f"the {name} check failed")

    if near:
        problems.append("another entry lies within 500 m: " + ", ".join(sorted(near)))
    return problems
