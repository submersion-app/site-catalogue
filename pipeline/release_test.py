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
from unittest import mock

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

    def _build(self, out=None, **options):
        return release.build_release(self.cache, out or self.out, self.committed, **options, **self.inputs)

    def _previous(self, *, drop=0, extra=()):
        """A previous release's catalogue: the committed one without its
        first [drop] sites, and with [extra] ids it no longer ships."""
        doc = json.loads((self.committed / "site_catalogue.json").read_text("utf-8"))
        path = Path(self._tmp.name) / "previous.json"
        path.write_text(
            json.dumps({**doc, "sites": doc["sites"][drop:] + [{"id": i} for i in extra]}),
            encoding="utf-8",
        )
        return path, [site["id"] for site in doc["sites"][:drop]]

    def test_the_notes_compare_with_the_previous_release(self):
        previous, added = self._previous(drop=1, extra=("osm_gone",))
        report: list = []
        self._build(previous=previous, report=report)
        self.assertIn("Ids new: 1", report[0])
        self.assertIn(added[0], report[0])
        self.assertIn("Ids gone: 1", report[0])
        self.assertIn("osm_gone", report[0])
        self.assertNotIn("every id is new", report[0])

    def test_the_first_release_has_nothing_to_compare_with(self):
        report: list = []
        self._build(report=report)
        self.assertIn("every id is new", report[0])

    def test_a_curated_site_gone_since_the_previous_release_stops_it(self):
        # The departure guard runs against what the app last received.
        previous, _ = self._previous(extra=("curated_gone",))
        with self.assertRaises(RuntimeError) as caught:
            self._build(previous=previous)
        self.assertIn("curated_gone", str(caught.exception))
        self.assertFalse((self.out / "format.json").exists())

    def test_main_passes_the_previous_release_on(self):
        previous = Path(self._tmp.name) / "previous.json"
        notes = Path(self._tmp.name) / "notes.md"

        def build(cache, out, *, report, previous):
            report.append("Ids new: 1")
            return []

        (self.committed / "SNAPSHOTS").write_text("snapshots-2026-11-16\n", encoding="utf-8")
        with mock.patch.object(merge, "DEFAULT_OUT", self.committed), \
                mock.patch.object(release, "build_release", side_effect=build) as built, \
                redirect_stdout(io.StringIO()):
            code = release.main(["--out", str(self.out), "--notes", str(notes),
                                 "--previous", str(previous)])
        self.assertEqual(code, 0)
        self.assertEqual(built.call_args.kwargs["previous"], previous)
        self.assertIn("Ids new: 1", notes.read_text("utf-8"))

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
