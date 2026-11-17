#!/usr/bin/env python3
"""Machine checks for a researched entry, run before the auto tier.

    python3.14 research/machine_checks.py ENTRY_ID [--file research/sites.json]

Three checks against OpenStreetMap, asked live through Overpass:

- in_water: the point is in water. Within 2 km of a coastline, the side of
  the nearest coastline segment decides (OpenStreetMap draws coastlines
  with land on their left); further out, the offline land polygons the
  merge places countries with decide. A shore entry passes within 100 m
  of the coastline on either side: a shore dive starts at the water.
- in_place: the point lies within the bounds of the feature `named.osm`
  names (the island, bay or reef the pages put the site in), grown by 2 km.
- copied_point: no shop, hotel, amenity or place node lies within 15 m of
  the point. Some operators publish their resort's map point as a dive
  site's; such a figure says where the resort is, not the site.

Each result is recorded in the entry's `checks` with the OpenStreetMap ids
it used, so anyone can re-run it. CI does not recompute them (it has no
network); the checker requires them for the auto tier, and the sample
audit measures whether they hold.
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence  # noqa: E402

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "dive-site-harvester/1.0"
COAST_REACH_M = 2000.0
SHORE_M = 100.0
PLACE_MARGIN_M = 2000.0
COPIED_M = 15.0
BUSY_PAUSE_S = 30.0
_last_query = [0.0]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    osm: list = field(default_factory=list)
    detail: str = ""


def as_fact(result: CheckResult, today: date) -> dict:
    """[result] in the shape an entry's `checks` holds."""
    return {"name": result.name, "passed": result.passed,
            "date": today.isoformat(), "osm": list(result.osm)}


def query(ql: str) -> dict:
    """Asks Overpass [ql], at most once a second, as the harvester."""
    wait = 1.0 - (time.monotonic() - _last_query[0])
    if wait > 0:
        time.sleep(wait)
    data = urllib.parse.urlencode({"data": ql}).encode("ascii")
    request = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": USER_AGENT})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as error:
            # A busy server is asked once more after a pause, as the
            # pipeline's OpenStreetMap fetch does.
            if attempt or error.code not in (429, 502, 503, 504):
                raise
            time.sleep(BUSY_PAUSE_S)
    _last_query[0] = time.monotonic()
    return json.loads(body)


def _local_xy(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    """Metres east and north of (lat0, lon0), flat over a few kilometres."""
    y = (lat - lat0) * 111_320.0
    x = (lon - lon0) * 111_320.0 * math.cos(math.radians(lat0))
    return x, y


def _nearest_segment(lat: float, lon: float, ways: list[dict]):
    """(distance in metres, cross product sign, way id) of the coastline
    segment nearest the point."""
    best = None
    for way in ways:
        points = [_local_xy(lat, lon, p["lat"], p["lon"]) for p in way.get("geometry") or []]
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            t = 0.0 if length2 == 0 else max(0.0, min(1.0, (-ax * dx - ay * dy) / length2))
            px, py = ax + t * dx, ay + t * dy
            distance = math.hypot(px, py)
            # Left of a->b (cross > 0) is land on an OpenStreetMap coastline.
            cross = dx * (0 - ay) - dy * (0 - ax)
            if best is None or distance < best[0]:
                best = (distance, cross, way["id"])
    return best


def _default_on_land():
    import places
    from snapshots import CACHE_DIR

    lookup = places.load_places(CACHE_DIR)
    return lambda lat, lon: (
        lookup._units.containing(lat, lon) is not None
        and lookup._lakes.containing(lat, lon) is None
    )


def in_water(lat: float, lon: float, *, shore: bool, overpass=query, on_land=None) -> CheckResult:
    """Whether (lat, lon) is in water, or at the water's edge for a shore
    entry."""
    answer = overpass(
        f"[out:json][timeout:60];way(around:{COAST_REACH_M:.0f},{lat},{lon})[natural=coastline];out geom;"
    )
    ways = [e for e in answer.get("elements") or [] if e.get("type") == "way"]
    nearest = _nearest_segment(lat, lon, ways)
    if nearest is not None:
        distance, cross, way_id = nearest
        land = cross > 0
        osm = [f"way/{way_id}"]
        if shore and distance <= SHORE_M:
            return CheckResult("in_water", True, osm, f"{distance:.0f} m from the coastline")
        side = "landward" if land else "seaward"
        return CheckResult("in_water", not land, osm, f"{side} of the coastline, {distance:.0f} m from it")
    on_land = on_land or _default_on_land()
    land = on_land(lat, lon)
    return CheckResult(
        "in_water", not land, [],
        "inside the land polygons, no coastline within 2 km" if land
        else "outside the land polygons, no coastline within 2 km",
    )


def in_place(lat: float, lon: float, osm_ref: str, *, overpass=query) -> CheckResult:
    """Whether (lat, lon) lies within [osm_ref]'s bounds grown by 2 km."""
    kind, _, number = osm_ref.partition("/")
    answer = overpass(f"[out:json][timeout:60];{kind}({number});out bb;")
    elements = answer.get("elements") or []
    if not elements:
        return CheckResult("in_place", False, [osm_ref], "the feature was not found")
    element = elements[0]
    if "bounds" in element:
        b = element["bounds"]
        south, west, north, east = b["minlat"], b["minlon"], b["maxlat"], b["maxlon"]
    else:
        south = north = element["lat"]
        west = east = element["lon"]
    grow_lat = PLACE_MARGIN_M / 111_320.0
    grow_lon = PLACE_MARGIN_M / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))
    inside = (south - grow_lat <= lat <= north + grow_lat) and (west - grow_lon <= lon <= east + grow_lon)
    return CheckResult("in_place", inside, [osm_ref],
                       "within 2 km of the feature" if inside else "more than 2 km from the feature")


def _point_of(element: dict) -> tuple[float, float] | None:
    if "lat" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    return (center["lat"], center["lon"]) if center else None


def copied_point(lat: float, lon: float, *, overpass=query) -> CheckResult:
    """Fails when a shop, hotel, amenity or place sits on the point: a node
    within 15 m, or an outline whose centre (the point maps show) is."""
    around = f"around:{COPIED_M:.0f},{lat},{lon}"
    answer = overpass(
        f"[out:json][timeout:60];"
        f"(nwr({around})[tourism];nwr({around})[amenity];"
        f"nwr({around})[shop];nwr({around})[place];);out center tags;"
    )
    found = []
    for element in answer.get("elements") or []:
        point = _point_of(element)
        if point and evidence.metres_between(lat, lon, *point) <= COPIED_M:
            found.append(element)
    if not found:
        return CheckResult("copied_point", True, [], "nothing within 15 m")
    names = ", ".join(str((e.get("tags") or {}).get("name") or e["id"]) for e in found)
    return CheckResult("copied_point", False, [f"{e['type']}/{e['id']}" for e in found],
                       f"the figure is on {names}")


def run_checks(entry: dict, *, overpass=query, on_land=None) -> list[CheckResult]:
    """The three checks for [entry] at its shipped point."""
    position = entry.get("position") or {}
    lat, lon = position["lat"], position["lon"]
    shore = "shore" in ((entry.get("entry") or {}).get("value") or [])
    results = [in_water(lat, lon, shore=shore, overpass=overpass, on_land=on_land)]
    osm_ref = (entry.get("named") or {}).get("osm")
    results.append(
        in_place(lat, lon, osm_ref, overpass=overpass) if osm_ref
        else CheckResult("in_place", False, [], "named.osm is not set")
    )
    results.append(copied_point(lat, lon, overpass=overpass))
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("entry_id")
    parser.add_argument("--file", type=Path, default=Path(_HERE) / "sites.json")
    arguments = parser.parse_args(argv)
    sites = json.loads(arguments.file.read_text("utf-8"))["sites"]
    entry = next((s for s in sites if s.get("id") == arguments.entry_id), None)
    if entry is None:
        print(f"no entry {arguments.entry_id}")
        return 2
    for result in run_checks(entry):
        print(f"{result.name}: {'pass' if result.passed else 'FAIL'} {result.osm} {result.detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
