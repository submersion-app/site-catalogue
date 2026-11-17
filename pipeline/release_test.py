#!/usr/bin/env python3
"""Tests for catalogue releases: a release rebuilds the committed catalogue
from its snapshot set, byte for byte, before anything is published.

Run: python3.14 pipeline/release_test.py
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))]

import contract  # noqa: E402
import merge  # noqa: E402
import release  # noqa: E402
import site_catalogue_format as fmt  # noqa: E402
import snapshots  # noqa: E402
from merge_test import _CURATED, _NO_RESEARCH, _Places, _snapshots  # noqa: E402


class BuildReleaseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.cache = root / "cache"
        for key, rows in _snapshots().items():
            snapshots.write_snapshot(key, "https://example.org", rows, self.cache)
        (self.cache / merge.NJDEP_METADATA_FILE).write_text("<metadata>NJ</metadata>", encoding="utf-8")
        (self.cache / merge.MD_DNR_METADATA_FILE).write_text("<metadata>MD</metadata>", encoding="utf-8")
        self.inputs = dict(places=_Places(), curated=_CURATED, research=_NO_RESEARCH)
        # The committed catalogue, as the merge last wrote it.
        self.committed = root / "committed"
        with redirect_stdout(io.StringIO()):
            code = merge.main(["--cache", str(self.cache), "--out", str(self.committed)], **self.inputs)
        self.assertEqual(code, 0)
        self.out = root / "release"

    def _build(self, out=None):
        return release.build_release(self.cache, out or self.out, self.committed, **self.inputs)

    def test_a_release_holds_every_file(self):
        names = [path.name for path in self._build()]
        self.assertEqual(names, list(release.RELEASE_FILES))

    def test_the_same_set_builds_the_same_bytes(self):  # acceptance 2
        a = self._build(Path(self._tmp.name) / "a")
        b = self._build(Path(self._tmp.name) / "b")
        for x, y in zip(a, b):
            self.assertEqual(x.read_bytes(), y.read_bytes(), x.name)

    def test_the_catalogue_is_the_committed_one(self):
        self._build()
        self.assertEqual(
            (self.out / "site_catalogue.json").read_bytes(),
            (self.committed / "site_catalogue.json").read_bytes(),
        )

    def test_a_catalogue_that_does_not_rebuild_stops_the_release(self):
        path = self.committed / "site_catalogue.json"
        path.write_bytes(path.read_bytes().replace(b"Pocopson", b"Pocopsom"))
        with self.assertRaises(release.NotReproducible):
            self._build()
        self.assertFalse((self.out / "format.json").exists())

    def test_the_open_build_leaves_out_the_own_terms_sources(self):
        self._build()
        doc = json.loads((self.out / "site_catalogue_open.json").read_text("utf-8"))
        self.assertTrue(doc["sites"])
        self.assertFalse({s["source"] for s in doc["sites"]} & set(fmt.OWN_TERMS_SOURCES))

    def test_every_record_field_is_in_the_contract(self):
        self._build()
        doc = json.loads((self.out / "site_catalogue.json").read_text("utf-8"))
        listed = set(contract.build_contract()["fields"])
        for site in doc["sites"]:
            self.assertTrue(set(site) <= listed, (site["id"], set(site) - listed))

    def test_every_curated_site_is_carried(self):
        self._build()
        ids = {s["id"] for s in json.loads((self.out / "site_catalogue.json").read_text("utf-8"))["sites"]}
        for entry in _CURATED:
            self.assertIn(entry["id"], ids)

    def test_the_contract_files_travel(self):
        self._build()
        self.assertEqual(json.loads((self.out / "format.json").read_text("utf-8")), contract.build_contract())
        self.assertTrue((self.out / "countries.json").exists())


class TagAndNotesTest(unittest.TestCase):
    def test_tags(self):
        self.assertEqual(release.next_tag([], date(2026, 12, 1)), "2026.12.01")
        self.assertEqual(release.next_tag(["2026.12.01"], date(2026, 12, 1)), "2026.12.01.2")
        self.assertEqual(
            release.next_tag(["2026.12.01", "2026.12.01.2", "snapshots-2026-12-01"], date(2026, 12, 1)),
            "2026.12.01.3",
        )

    def test_notes_name_the_snapshot_set(self):
        notes = release.release_notes("report", "snapshots-2026-11-16")
        self.assertTrue(notes.startswith("Built from snapshots-2026-11-16"))


if __name__ == "__main__":
    unittest.main()
