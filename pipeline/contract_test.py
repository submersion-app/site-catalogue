#!/usr/bin/env python3
"""Tests for the published format contract and the country table."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))]

import contract  # noqa: E402
import evidence  # noqa: E402
import places  # noqa: E402
import site_catalogue_format as fmt  # noqa: E402

CONTRACT = Path(_HERE).parent / "contract"


class ContractTest(unittest.TestCase):
    def test_contract_matches_the_python_definitions(self):
        on_disk = json.loads((CONTRACT / "format.json").read_text("utf-8"))
        self.assertEqual(on_disk, contract.build_contract())

    def test_vocabularies_are_the_formats_own(self):
        c = contract.build_contract()
        self.assertEqual(c["format"], fmt.FORMAT)
        self.assertEqual(c["site_types"], list(fmt.SITE_TYPE_IDS))
        self.assertEqual(c["entry_methods"], list(fmt.ENTRY_METHODS))
        self.assertEqual(c["trust_levels"], list(fmt.TRUST_LEVELS))
        self.assertEqual(c["withdrawal_reasons"], list(fmt.WITHDRAWAL_REASONS))
        self.assertEqual(c["kinds"], list(fmt.KINDS))
        self.assertEqual(c["hazard_codes"], sorted(evidence.HAZARD_SENTENCES))
        self.assertEqual(c["position_from"], ["map"])

    def test_fields_say_which_are_required(self):
        fields = contract.build_contract()["fields"]
        for name in ("id", "name", "source", "trust"):
            self.assertTrue(fields[name]["required"], name)
        for name in ("lat", "position_from", "max_depth_m", "website"):
            self.assertFalse(fields[name]["required"], name)

    def test_write_and_check(self):
        with tempfile.TemporaryDirectory() as folder:
            contract.write_contract(Path(folder))
            text = (Path(folder) / "format.json").read_text("utf-8")
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(json.loads(text), contract.build_contract())
            self.assertEqual(contract.check(Path(folder)), 0)
            (Path(folder) / "format.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(contract.check(Path(folder)), 1)


class CountryTableTest(unittest.TestCase):
    def test_country_table_resolves_as_the_app_did(self):
        known = places.known_country_names()
        self.assertEqual(known[places.fold_country("Bonaire")], "BQ")
        self.assertEqual(known[places.fold_country("United States")], "US")
        self.assertGreater(len(known), 400)

    def test_the_table_is_the_contracts_own_file(self):
        table = json.loads((CONTRACT / "countries.json").read_text("utf-8"))
        self.assertEqual(places.known_country_names(), table["names"])


if __name__ == "__main__":
    unittest.main()
