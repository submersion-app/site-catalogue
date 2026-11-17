#!/usr/bin/env python3
"""Tests for snapshot sets: packing a cache with each source's terms, and
restoring a published set.

Run: python3.14 pipeline/snapshot_sets_test.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))]

import merge  # noqa: E402
import snapshot_sets  # noqa: E402
import snapshots  # noqa: E402


def _fill(cache: Path) -> None:
    for key in ("osm_sites", "ukho", "njdep", "nc_dmf", "noaa_reefs"):
        snapshots.write_snapshot(key, "https://example.org", [{"id": 1}], cache)
    (cache / merge.NJDEP_METADATA_FILE).write_text("<metadata>NJ</metadata>", encoding="utf-8")
    (cache / merge.MD_DNR_METADATA_FILE).write_text("<metadata>MD</metadata>", encoding="utf-8")
    (cache / "naturalearth").mkdir()
    (cache / "naturalearth" / "ne_10m_lakes.geojson").write_text('{"features": []}', encoding="utf-8")


class PackTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name) / "cache"
        self.out = Path(self._tmp.name) / "out"
        _fill(self.cache)

    def test_every_snapshot_gets_a_terms_note(self):
        paths = snapshot_sets.pack(self.cache, self.out)
        for key in ("osm_sites", "ukho", "njdep", "nc_dmf", "noaa_reefs"):
            self.assertIn(self.out / f"{key}.json", paths)
            self.assertIn(self.out / f"{key}.TERMS.txt", paths)

    def test_own_terms_notes_stand_apart_from_odbl(self):
        self.assertIn("Not part of the ODbL database", snapshot_sets.terms_note("nc_dmf"))
        self.assertIn("not for commercial use", snapshot_sets.terms_note("nc_dmf"))
        self.assertIn("NJDEP's metadata", snapshot_sets.terms_note("njdep"))
        federal = snapshot_sets.terms_note("noaa_reefs")
        self.assertIn("Information courtesy Texas Parks and Wildlife Department", federal)
        self.assertIn("Hawaii", federal)
        self.assertNotIn("Not part of the ODbL database", snapshot_sets.terms_note("ukho"))
        self.assertIn("OGL-UK-3.0", snapshot_sets.terms_note("ukho"))

    def test_new_jersey_ships_with_its_metadata(self):
        snapshot_sets.pack(self.cache, self.out)
        self.assertTrue((self.out / merge.NJDEP_METADATA_FILE).exists())

    def test_the_manifest_lists_every_asset(self):
        paths = snapshot_sets.pack(self.cache, self.out)
        manifest = json.loads((self.out / snapshot_sets.MANIFEST).read_text("utf-8"))
        self.assertEqual(manifest["files"]["naturalearth.ne_10m_lakes.geojson"],
                         "naturalearth/ne_10m_lakes.geojson")
        self.assertEqual(manifest["keys"], ["nc_dmf", "njdep", "noaa_reefs", "osm_sites", "ukho"])
        self.assertIn(self.out / snapshot_sets.MANIFEST, paths)
        self.assertEqual(paths, sorted(paths))

    def test_a_metadata_file_that_is_not_xml_is_refused(self):
        # A Maryland "metadata" file once turned up as a zipped GeoPackage.
        (self.cache / merge.MD_DNR_METADATA_FILE).write_bytes(b"PK\x03\x04 not xml")
        with self.assertRaises(ValueError) as caught:
            snapshot_sets.pack(self.cache, self.out)
        self.assertIn(merge.MD_DNR_METADATA_FILE, str(caught.exception))
        self.assertFalse(self.out.exists() and any(self.out.iterdir()))

    def test_a_restored_set_is_the_cache_it_was_packed_from(self):
        snapshot_sets.pack(self.cache, self.out)
        restored = Path(self._tmp.name) / "restored"

        def fetch(tag, dest):
            shutil.copytree(self.out, dest, dirs_exist_ok=True)

        snapshot_sets.restore("snapshots-2026-11-17", restored, fetch=fetch)
        for path in self.cache.rglob("*"):
            if path.is_file():
                twin = restored / path.relative_to(self.cache)
                self.assertEqual(twin.read_bytes(), path.read_bytes(), str(twin))

    def test_a_missing_set_stops_and_writes_nothing(self):  # Review Focus 4
        cache = Path(self._tmp.name) / "empty"

        def absent(tag, dest):
            raise snapshot_sets.MissingSnapshotSet(tag)

        with self.assertRaises(snapshot_sets.MissingSnapshotSet):
            snapshot_sets.restore("snapshots-1999-01-01", cache, fetch=absent)
        self.assertFalse(cache.exists() and any(cache.iterdir()))


if __name__ == "__main__":
    unittest.main()
