#!/usr/bin/env python3
"""Tests for the monthly refresh: a failing or collapsed source is reused
from the previous snapshot set and named; nothing is dropped silently.

Run: python3.14 pipeline/refresh_test.py
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))]

import refresh  # noqa: E402
import snapshots  # noqa: E402


def _rows(n):
    return [{"id": i} for i in range(n)]


class RefreshTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name) / "cache"
        self.previous = Path(self._tmp.name) / "previous"
        for key in ("ukho", "awois", "osm_sites"):
            snapshots.write_snapshot(key, "https://old.example", _rows(100), self.previous)

    def _restore(self, tag, cache):
        shutil.copytree(self.previous, cache, dirs_exist_ok=True)

    def _fetch(self, key, n=100):
        return refresh.Fetch(
            run=lambda cache: snapshots.write_snapshot(key, "https://new.example", _rows(n), cache),
            keys=(key,),
        )

    def _raises(self, key):
        def run(cache):
            raise RuntimeError("HTTP 500 from the register\nmore detail")
        return refresh.Fetch(run=run, keys=(key,))

    def test_a_failing_source_is_reused_and_named(self):
        result = refresh.refresh(
            "snapshots-2026-11-16", self.cache,
            fetches={"ukho": self._raises("ukho"), "awois": self._fetch("awois")},
            pause=0, restore=self._restore,
        )
        self.assertEqual(result.fetched, ["awois"])
        self.assertEqual(result.reused, {"ukho": "HTTP 500 from the register"})
        self.assertEqual(snapshots.read_snapshot("ukho", self.cache)["url"], "https://old.example")
        self.assertEqual(snapshots.read_snapshot("awois", self.cache)["url"], "https://new.example")

    def test_a_failure_is_retried_once_before_reuse(self):
        calls = []

        def flaky(cache):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("timeout")
            snapshots.write_snapshot("ukho", "https://new.example", _rows(100), cache)

        result = refresh.refresh(
            "snapshots-2026-11-16", self.cache,
            fetches={"ukho": refresh.Fetch(run=flaky, keys=("ukho",))},
            pause=0, restore=self._restore,
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.fetched, ["ukho"])

    def test_a_collapsed_snapshot_counts_as_failed(self):  # Review Focus 2
        result = refresh.refresh(
            "snapshots-2026-11-16", self.cache,
            fetches={"osm_sites": self._fetch("osm_sites", n=10)},
            pause=0, restore=self._restore,
        )
        self.assertIn("osm_sites", result.reused)
        self.assertIn("10 rows", result.reused["osm_sites"])
        self.assertEqual(len(snapshots.read_snapshot("osm_sites", self.cache)["rows"]), 100)

    def test_a_failure_with_no_previous_set_is_reported(self):
        result = refresh.refresh(
            None, self.cache, fetches={"ukho": self._raises("ukho")},
            pause=0, restore=self._restore,
        )
        self.assertEqual(result.failed_without_fallback, ["ukho"])

    def test_the_pr_body_names_what_was_reused(self):
        body = refresh.pr_body(
            refresh.RefreshResult(["awois"], {"ukho": "HTTP 500"}, []), "the merge report"
        )
        self.assertIn("the merge report", body)
        self.assertIn("ukho: HTTP 500", body)
        self.assertIn("Refs #4514", body)
        self.assertIn("ran the tests and the checker", body)


if __name__ == "__main__":
    unittest.main()
