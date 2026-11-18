#!/usr/bin/env python3
"""Tests for the machine checks a researched entry runs before the auto
tier: in water, in the named place, not a copied point.

The Overpass answers are small hand-built geometries, so each rule is
pinned exactly; the module's live query is not called.

Run: python3.14 research/machine_checks_test.py
"""

import os
import sys
import unittest
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))]

import machine_checks as mc  # noqa: E402

# A straight coastline along latitude 0, drawn west to east, so land (on
# its left) lies to the north.
_COAST = {"elements": [{
    "type": "way", "id": 11, "tags": {"natural": "coastline"},
    "geometry": [{"lat": 0.0, "lon": 0.0}, {"lat": 0.0, "lon": 0.02}],
}]}
_NO_COAST = {"elements": []}


def _overpass(answers):
    """A stand-in for the live query: the answer for the first key found
    in the query text."""
    def query(ql):
        for key, answer in answers.items():
            if key in ql:
                return answer
        raise AssertionError(f"unexpected query: {ql}")
    return query


class InWaterTest(unittest.TestCase):
    def test_a_point_seaward_of_the_coastline_is_in_water(self):
        result = mc.in_water(-0.005, 0.01, shore=False, overpass=_overpass({"coastline": _COAST}))
        self.assertTrue(result.passed)
        self.assertEqual(result.osm, ["way/11"])

    def test_a_point_landward_of_the_coastline_is_not(self):
        result = mc.in_water(0.005, 0.01, shore=False, overpass=_overpass({"coastline": _COAST}))
        self.assertFalse(result.passed)

    def test_a_shore_entry_on_the_beach_passes(self):
        # About 55 m inland: on land, but a shore dive starts at the water.
        result = mc.in_water(0.0005, 0.01, shore=True, overpass=_overpass({"coastline": _COAST}))
        self.assertTrue(result.passed)
        far = mc.in_water(0.005, 0.01, shore=True, overpass=_overpass({"coastline": _COAST}))
        self.assertFalse(far.passed)

    def test_far_from_any_coastline_the_land_polygons_decide(self):
        sea = mc.in_water(5.0, 5.0, shore=False, overpass=_overpass({"coastline": _NO_COAST}),
                          on_land=lambda lat, lon: False)
        self.assertTrue(sea.passed)
        inland = mc.in_water(5.0, 5.0, shore=False, overpass=_overpass({"coastline": _NO_COAST}),
                             on_land=lambda lat, lon: True)
        self.assertFalse(inland.passed)


def _ring_answer(nodes, *, start, splits=()):
    """An Overpass answer holding the closed ring through [nodes] (lat,
    lon pairs in drawing order), drawn from node [start] and cut into one
    way per run between the [splits] node indexes, each way sharing its end
    node with the next as OpenStreetMap coastlines do."""
    order = [nodes[(start + i) % len(nodes)] for i in range(len(nodes) + 1)]
    cuts = [0, *sorted(splits), len(nodes)]
    return {"elements": [{
        "type": "way", "id": 100 + n, "tags": {"natural": "coastline"},
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in order[a:b + 1]],
    } for n, (a, b) in enumerate(zip(cuts, cuts[1:]))]}


# A small diamond islet near (0, 0) with a sharp spike to the south, drawn
# counter-clockwise (land on its left): south spike, east, north, west.
_ISLET = [(-0.002, 0.0), (0.0, 0.001), (0.002, 0.0), (0.0, -0.001)]
# About 315 m south east of the spike, in open water. The spike is the
# nearest coastline point, so the segments into and out of it are equally
# near; the point is left of the incoming one's line and right of the
# outgoing one's.
_OFF_SPIKE = (-0.004, 0.002)


class InWaterVertexTest(unittest.TestCase):
    def test_water_off_a_spike_is_water_whichever_node_the_ring_starts_at(self):
        for start in range(len(_ISLET)):
            with self.subTest(start=start):
                answer = _ring_answer(_ISLET, start=start)
                result = mc.in_water(*_OFF_SPIKE, shore=False, overpass=_overpass({"coastline": answer}))
                self.assertTrue(result.passed, result.detail)
                self.assertIn("seaward", result.detail)

    def test_land_off_a_reflex_vertex_is_land_whichever_node_the_ring_starts_at(self):
        # The same diamond drawn clockwise is a pond: land lies outside it,
        # and the spike is a reflex corner of the land.
        pond = list(reversed(_ISLET))
        for start in range(len(pond)):
            with self.subTest(start=start):
                answer = _ring_answer(pond, start=start)
                result = mc.in_water(*_OFF_SPIKE, shore=False, overpass=_overpass({"coastline": answer}))
                self.assertFalse(result.passed, result.detail)
                self.assertIn("landward", result.detail)

    def test_a_spike_where_two_ways_meet_records_both(self):
        # Drawn from the west node, the spike is node 1: one way ends there
        # and the next begins there.
        answer = _ring_answer(_ISLET, start=3, splits=(1,))
        result = mc.in_water(*_OFF_SPIKE, shore=False, overpass=_overpass({"coastline": answer}))
        self.assertTrue(result.passed, result.detail)
        self.assertEqual(result.osm, ["way/100", "way/101"])

    def test_a_point_off_a_segment_still_takes_that_segment_side(self):
        # Due east of the islet's east node's south face: the nearest
        # point is inside one segment, so no vertex rule applies.
        answer = _ring_answer(_ISLET, start=0)
        sea = mc.in_water(-0.0015, 0.0025, shore=False, overpass=_overpass({"coastline": answer}))
        self.assertTrue(sea.passed, sea.detail)
        self.assertEqual(sea.osm, ["way/100"])
        land = mc.in_water(-0.0005, 0.0003, shore=False, overpass=_overpass({"coastline": answer}))
        self.assertFalse(land.passed, land.detail)


class InPlaceTest(unittest.TestCase):
    _ISLAND = {"elements": [{
        "type": "way", "id": 96698692,
        "bounds": {"minlat": 4.112, "minlon": 118.627, "maxlat": 4.1176, "maxlon": 118.6307},
    }]}

    def test_a_point_within_two_km_of_the_place_passes(self):
        result = mc.in_place(4.1236, 118.6286, "way/96698692", overpass=_overpass({"way(96698692)": self._ISLAND}))
        self.assertTrue(result.passed)
        self.assertEqual(result.osm, ["way/96698692"])

    def test_a_point_far_from_the_place_fails(self):
        result = mc.in_place(1.45, 125.23, "way/96698692", overpass=_overpass({"way(96698692)": self._ISLAND}))
        self.assertFalse(result.passed)

    def test_a_node_place_is_a_point_with_the_margin(self):
        node = {"elements": [{"type": "node", "id": 5, "lat": 1.0, "lon": 1.0}]}
        self.assertTrue(mc.in_place(1.01, 1.0, "node/5", overpass=_overpass({"node(5)": node})).passed)
        self.assertFalse(mc.in_place(1.05, 1.0, "node/5", overpass=_overpass({"node(5)": node})).passed)

    def test_a_missing_feature_fails(self):
        result = mc.in_place(1.0, 1.0, "relation/9", overpass=_overpass({"relation(9)": {"elements": []}}))
        self.assertFalse(result.passed)


class CopiedPointTest(unittest.TestCase):
    def test_a_figure_on_a_resort_node_is_flagged(self):
        resort = {"elements": [{
            "type": "node", "id": 777, "lat": -8.23685, "lon": 115.5624,
            "tags": {"tourism": "hotel", "name": "Alam Batu"},
        }]}
        result = mc.copied_point(-8.23685, 115.5624, overpass=_overpass({"around:150": resort}))
        self.assertFalse(result.passed)
        self.assertEqual(result.osm, ["node/777"])
        self.assertIn("Alam Batu", result.detail)

    def test_a_figure_on_a_resort_outline_is_flagged(self):
        # Alam Batu's resort is mapped as a building outline: its centre is
        # about 10 m from the published figure.
        resort = {"elements": [{
            "type": "way", "id": 60550309, "center": {"lat": -8.2367536, "lon": 115.5623839},
            "tags": {"tourism": "hotel", "name": "Alam Batu Beach Bungalow Resort"},
        }]}
        result = mc.copied_point(-8.23685, 115.5624, overpass=_overpass({"around:150": resort}))
        self.assertFalse(result.passed)
        self.assertEqual(result.osm, ["way/60550309"])

    def test_a_place_further_than_15_m_is_not_the_figure(self):
        cafe = {"elements": [{
            "type": "node", "id": 9, "lat": -8.2372, "lon": 115.5624,
            "tags": {"amenity": "cafe"},
        }]}
        result = mc.copied_point(-8.23685, 115.5624, overpass=_overpass({"around:150": cafe}))
        self.assertTrue(result.passed)

    def test_a_figure_with_nothing_beneath_it_passes(self):
        result = mc.copied_point(4.1236, 118.6286, overpass=_overpass({"around:150": {"elements": []}}))
        self.assertTrue(result.passed)


class FactTest(unittest.TestCase):
    def test_a_result_is_recorded_in_the_checks_shape(self):
        result = mc.CheckResult("in_water", True, ["way/11"], "seaward of the coastline")
        self.assertEqual(
            mc.as_fact(result, date(2026, 11, 17)),
            {"name": "in_water", "passed": True, "date": "2026-11-17", "osm": ["way/11"]},
        )


if __name__ == "__main__":
    unittest.main()
