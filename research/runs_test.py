#!/usr/bin/env python3
"""Tests for research run tooling: picking thin regions, tiering entries,
the sample audit and its pause rule.

Run: python3.14 research/runs_test.py
"""

import copy
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))]

import runs  # noqa: E402
from auto_tier_test import DOMAINS, _auto_entry  # noqa: E402
from check_test import _entry  # noqa: E402

TODAY = date(2026, 11, 17)


class ThinRegionsTest(unittest.TestCase):
    _REGIONS = [
        {"name": "Busy", "lat": 0.0, "lon": 0.0, "radius_km": 50},
        {"name": "Thin", "lat": 10.0, "lon": 10.0, "radius_km": 50},
        {"name": "Empty", "lat": -20.0, "lon": 40.0, "radius_km": 50},
    ]
    _CATALOGUE = {"sites": [
        {"id": "a", "lat": 0.1, "lon": 0.1},
        {"id": "b", "lat": 0.2, "lon": 0.1},
        {"id": "c", "lat": 10.1, "lon": 10.0},
        {"id": "w", "lat": -20.0, "lon": 40.0, "kind": "register"},
    ]}

    def test_regions_rank_by_dive_sites_fewest_first(self):
        ranked = runs.thin_regions(self._CATALOGUE, self._REGIONS, set(), limit=3)
        self.assertEqual([r["name"] for r in ranked], ["Empty", "Thin", "Busy"])
        self.assertEqual(ranked[0]["dive_sites"], 0)

    def test_researched_regions_are_skipped_and_the_limit_holds(self):
        ranked = runs.thin_regions(self._CATALOGUE, self._REGIONS, {"Empty"}, limit=1)
        self.assertEqual([r["name"] for r in ranked], ["Thin"])

    def test_researched_regions_are_read_from_run_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder) / "2026-11-17-1"
            run.mkdir()
            (run / "report.md").write_text(
                "# Research run\n\n## Region: Thin\n\ntext\n\n## Region: Busy\n", encoding="utf-8"
            )
            self.assertEqual(runs.researched_regions(Path(folder)), {"Thin", "Busy"})

    def test_the_committed_regions_load(self):
        regions = runs.load_regions()
        self.assertGreater(len(regions), 90)
        tulamben = next(r for r in regions if "Tulamben" in r["name"])
        self.assertLess(tulamben["lat"], 0)


class TierTest(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(runs.tier_of(_auto_entry(), DOMAINS, today=TODAY), "auto")
        unruled = _auto_entry()
        unruled["named"]["sources"].append({"url": "https://new.example/x", "read": "2026-11-16"})
        self.assertEqual(runs.tier_of(unruled, DOMAINS, today=TODAY), "waiting")
        press_only = _entry(review={"state": "pending"})
        self.assertEqual(runs.tier_of(press_only, DOMAINS, today=TODAY), "maintainer")

    def test_split_run(self):
        auto = _auto_entry()
        maintainer = _entry(id="research_id_other", name="Other",
                            review={"state": "pending"})
        maintainer["position"] = copy.deepcopy(maintainer["position"])
        for source in maintainer["position"]["sources"]:
            if isinstance(source.get("lat"), float):
                source["lat"] -= 0.1
        maintainer["position"]["sources"] = maintainer["position"]["sources"][:1]
        maintainer["position"]["lat"] = maintainer["position"]["sources"][0]["lat"]
        maintainer["position"]["lon"] = maintainer["position"]["sources"][0]["lon"]
        split = runs.split_run([auto, maintainer], DOMAINS, today=TODAY)
        self.assertEqual([e["id"] for e in split.auto], ["research_id_usat_liberty"])
        self.assertEqual([e["id"] for e in split.queue], ["research_id_other"])
        self.assertEqual(split.waiting, [])


class AuditTest(unittest.TestCase):
    def test_audit_sample_bounds(self):
        self.assertEqual(len(runs.audit_sample([f"e{i}" for i in range(3)], "r")), 3)
        self.assertEqual(len(runs.audit_sample([f"e{i}" for i in range(40)], "r")), 5)
        self.assertEqual(len(runs.audit_sample([f"e{i}" for i in range(200)], "r")), 20)
        self.assertEqual(len(runs.audit_sample([f"e{i}" for i in range(900)], "r")), 30)
        self.assertEqual(runs.audit_sample([], "r"), [])

    def test_the_sample_is_reproducible_from_the_run(self):
        ids = [f"e{i}" for i in range(100)]
        self.assertEqual(runs.audit_sample(ids, "2026-11-17-1"), runs.audit_sample(list(reversed(ids)), "2026-11-17-1"))
        self.assertNotEqual(runs.audit_sample(ids, "2026-11-17-1"), runs.audit_sample(ids, "2026-11-17-2"))

    def test_pause_rule(self):
        self.assertFalse(runs.pause_tripped(1, 20))
        self.assertTrue(runs.pause_tripped(2, 20))
        self.assertTrue(runs.pause_tripped(1, 5))
        self.assertFalse(runs.pause_tripped(0, 0))


if __name__ == "__main__":
    unittest.main()
