#!/usr/bin/env python3
"""Tests for the auto tier: which researched entries may be approved
without the maintainer reading each one, enforced by the checker.

Run: python3.14 research/auto_tier_test.py
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

import auto_tier  # noqa: E402
import check  # noqa: E402
import evidence  # noqa: E402
from check_test import _A, _entry, _rules  # noqa: E402

TODAY = date(2026, 11, 17)

DOMAINS = evidence.DomainLists(
    counting={"opa.com": "operator", "pressb.org": "dive press", "park.gov": "official"},
    cite_only={},
    never={},
    kinds={"opa.com": "operator", "pressb.org": "press", "park.gov": "official"},
)

_NAMED = {"place": "Tulamben Bay", "sources": [
    {"url": "https://opa.com/sites", "read": "2026-11-16"},
    {"url": "https://park.gov/sites", "read": "2026-11-16"},
]}


def _checks(passed=True):
    return [
        {"name": name, "passed": passed, "date": "2026-11-17", "osm": ["way/1"]}
        for name in auto_tier.CHECK_NAMES
    ]


def _auto_entry(**overrides):
    """A confirmed, second-passed, checked entry approved by the auto tier."""
    entry = _entry(named=copy.deepcopy(_NAMED))
    entry.update(overrides)
    entry["checks"] = entry.get("checks", _checks())
    entry["review"] = {"state": "approved", "date": "2026-11-17", "by": "auto"}
    entry["second_pass"] = {
        "date": "2026-11-17", "agrees": True, "facts": auto_tier.facts_hash(entry),
    }
    return entry


def _stated_from(url, **overrides):
    """An auto entry placed by one stated figure on [url]."""
    source = dict(_A, url=url)
    entry = _entry(named=copy.deepcopy(_NAMED))
    entry["position"] = {"lat": source["lat"], "lon": source["lon"], "sources": [source]}
    entry.update(overrides)
    return _auto_entry(**{k: v for k, v in entry.items()})


def _one(entry, *more):
    return check.check_entries([entry, *more], DOMAINS, today=TODAY)[0]


class AutoTierTest(unittest.TestCase):
    def test_a_qualifying_entry_passes_as_auto(self):
        checked = _one(_auto_entry())
        self.assertEqual(checked.route, "confirmed")
        self.assertEqual(_rules(checked), set())

    def test_a_stated_operator_or_official_figure_qualifies(self):
        self.assertEqual(_rules(_one(_stated_from("https://opa.com/liberty"))), set())
        self.assertEqual(_rules(_one(_stated_from("https://park.gov/liberty"))), set())

    def test_auto_needs_an_official_or_operator_figure(self):
        checked = _one(_stated_from("https://pressb.org/liberty"))
        self.assertIn("auto_tier", _rules(checked))

    def test_auto_refuses_a_map_read_entry(self):  # acceptance 6
        source = dict(_A, method="map", map="https://opa.com/map.png")
        entry = _entry(named=copy.deepcopy(_NAMED))
        entry["position"] = {"lat": source["lat"], "lon": source["lon"], "sources": [source]}
        checked = _one(_auto_entry(**entry))
        self.assertEqual(checked.route, "map")
        self.assertIn("auto_tier", _rules(checked))

    def test_auto_refuses_missing_or_failed_checks(self):
        entry = _auto_entry()
        del entry["checks"]
        entry["second_pass"]["facts"] = auto_tier.facts_hash(entry)
        self.assertIn("auto_tier", _rules(_one(entry)))
        self.assertIn("auto_tier", _rules(_one(_auto_entry(checks=_checks(passed=False)))))

    def test_auto_refuses_a_missing_or_disagreeing_second_pass(self):
        entry = _auto_entry()
        del entry["second_pass"]
        self.assertIn("auto_tier", _rules(_one(entry)))
        entry = _auto_entry()
        entry["second_pass"]["agrees"] = False
        self.assertIn("auto_tier", _rules(_one(entry)))

    def test_auto_refuses_facts_edited_after_the_second_pass(self):  # Review Focus 1
        entry = _auto_entry()
        entry["position"]["sources"][0]["lat"] = -8.27371
        self.assertIn("auto_tier", _rules(_one(entry)))

    def test_a_note_or_review_edit_does_not_void_the_second_pass(self):
        entry = _auto_entry()
        entry["note"] = "Re-read on the operator's new page."
        entry["review"]["date"] = "2026-11-18"
        self.assertEqual(_rules(_one(entry)), set())

    def test_auto_refuses_an_entry_with_a_neighbour_within_500_m(self):
        near = _auto_entry(id="research_id_near", name="Near",
                           distinct_from=["research_id_usat_liberty"])
        near["position"] = {"lat": -8.2770, "lon": 115.5929,
                            "sources": [dict(_A, lat=-8.2770)]}
        near["second_pass"]["facts"] = auto_tier.facts_hash(near)
        checked = _one(_auto_entry(), near)
        self.assertIn("auto_tier", _rules(checked))

    def test_a_maintainer_approval_needs_none_of_this(self):
        entry = _entry(review={"state": "approved", "date": "2026-11-17", "by": "maintainer"})
        self.assertEqual(_rules(_one(entry)), set())
        entry = _entry(review={"state": "approved", "date": "2026-11-17"})
        self.assertEqual(_rules(_one(entry)), set())

    def test_review_by_is_auto_or_maintainer(self):
        entry = _entry(review={"state": "approved", "date": "2026-11-17", "by": "robot"})
        self.assertIn("shape", _rules(_one(entry)))


class DomainKindTest(unittest.TestCase):
    def _load(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "domains.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return evidence.load_domains(path)

    def test_counting_domains_carry_a_kind(self):
        domains = self._load({"counting": {"www.Opa.com": {"kind": "operator", "reason": "r"}}})
        self.assertEqual(domains.kind_for("https://dive.opa.com/x"), "operator")
        self.assertEqual(domains.counting["opa.com"], "r")
        self.assertIsNone(domains.kind_for("https://other.org/x"))

    def test_counting_domain_needs_a_kind(self):
        with self.assertRaises(ValueError):
            self._load({"counting": {"x.com": {"reason": "r"}}})
        with self.assertRaises(ValueError):
            self._load({"counting": {"x.com": {"kind": "blog", "reason": "r"}}})

    def test_the_committed_lists_load(self):
        domains = evidence.load_domains(check.DOMAINS_FILE)
        self.assertEqual(domains.kind_for("https://jncc.gov.uk/x"), "official")
        self.assertEqual(domains.kind_for("https://www.lembehresort.com/x"), "operator")
        self.assertEqual(domains.kind_for("https://juergenfreund.com/x"), "press")


if __name__ == "__main__":
    unittest.main()
