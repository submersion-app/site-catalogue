#!/usr/bin/env python3
"""Tooling for a research run: where to research, and how its entries are
tiered and audited.

    python3.14 research/runs.py regions [--limit N]

A run researches the thinnest regions first: the well-known diving areas
(regions.json) with the fewest dive site records within their radius in the
committed catalogue, skipping those an earlier run's report already covers.
Its passing entries are split three ways: the auto tier (auto_tier.py),
which ships after the maintainer checks a sample of it; the maintainer's
queue, decided entry by entry; and entries waiting on a domain nobody has
ruled yet, which join a later queue.
"""

import argparse
import copy
import json
import math
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import check  # noqa: E402

REGIONS_FILE = Path(_HERE) / "regions.json"
RUNS_DIR = Path(_HERE) / "runs"
CATALOGUE_FILE = Path(_HERE).parent / "catalogue" / "site_catalogue.json"

AUDIT_SHARE = 0.10
AUDIT_MIN = 5
AUDIT_MAX = 30
PAUSE_RATE = 0.05
_REGION_HEADING = re.compile(r"^## Region: (.+?)\s*$", re.MULTILINE)


@dataclass
class RunSplit:
    auto: list = field(default_factory=list)
    queue: list = field(default_factory=list)
    waiting: list = field(default_factory=list)


def load_regions(path: Path = REGIONS_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["regions"]


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def researched_regions(runs_dir: Path = RUNS_DIR) -> set[str]:
    """The regions earlier runs' reports cover (`## Region: <name>`)."""
    names: set[str] = set()
    for report in sorted(runs_dir.glob("*/report.md")):
        names.update(_REGION_HEADING.findall(report.read_text(encoding="utf-8")))
    return names


def thin_regions(catalogue: dict, regions: list[dict], researched: set[str], limit: int) -> list[dict]:
    """Up to [limit] regions not in [researched], fewest dive site records
    within their radius first, each with its count as `dive_sites`."""
    sites = [
        s for s in catalogue.get("sites") or []
        if s.get("kind", "site") != "register" and s.get("lat") is not None
    ]
    ranked = []
    for region in regions:
        if region["name"] in researched:
            continue
        count = sum(
            1 for s in sites
            if abs(s["lat"] - region["lat"]) <= 1.0
            and _km(region["lat"], region["lon"], s["lat"], s["lon"]) <= region["radius_km"]
        )
        ranked.append({**region, "dive_sites": count})
    ranked.sort(key=lambda r: (r["dive_sites"], r["name"]))
    return ranked[:limit]


def _as_auto(entry: dict) -> dict:
    candidate = copy.deepcopy(entry)
    candidate["review"] = {"state": "approved", "date": "2000-01-01", "by": "auto"}
    return candidate


def _cites_unruled(entry: dict, domains) -> bool:
    return any(domains.kind_of(str(s.get("url"))) is None for s in check._all_sources(entry))


def split_run(entries: list[dict], domains, *, today: date, existing: list[dict] = ()) -> RunSplit:
    """[entries] (each passing the checker) split into the auto tier, the
    maintainer's queue, and those waiting on a domain ruling. [existing]
    entries count as neighbours."""
    split = RunSplit()
    ruled = [e for e in entries if not _cites_unruled(e, domains)]
    split.waiting = [e for e in entries if _cites_unruled(e, domains)]
    candidates = [_as_auto(e) for e in ruled]
    results = check.check_entries(candidates + list(existing), domains, today=today)
    for entry, checked in zip(ruled, results):
        if checked.ok:
            split.auto.append(entry)
        else:
            split.queue.append(entry)
    return split


def tier_of(entry: dict, domains, *, today: date) -> str:
    """`auto`, `maintainer` or `waiting`, for one entry on its own."""
    split = split_run([entry], domains, today=today)
    return "auto" if split.auto else "waiting" if split.waiting else "maintainer"


def audit_sample(auto_ids: list[str], seed: str) -> list[str]:
    """The auto-tier entries the maintainer checks: 10 percent, at least 5
    (or all, when fewer), at most 30, drawn reproducibly from [seed] (the
    run's folder name) whatever order the ids come in."""
    ids = sorted(auto_ids)
    size = min(len(ids), max(AUDIT_MIN, min(AUDIT_MAX, round(AUDIT_SHARE * len(ids)))))
    return sorted(random.Random(seed).sample(ids, size))


def pause_tripped(wrong: int, sampled: int) -> bool:
    """Whether the sample's error rate pauses the auto tier."""
    return sampled > 0 and wrong / sampled > PAUSE_RATE


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    regions_command = commands.add_parser("regions")
    regions_command.add_argument("--limit", type=int, default=10)
    arguments = parser.parse_args(argv)
    catalogue = json.loads(CATALOGUE_FILE.read_text(encoding="utf-8"))
    for region in thin_regions(catalogue, load_regions(), researched_regions(), arguments.limit):
        print(f"{region['dive_sites']:4d}  {region['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
