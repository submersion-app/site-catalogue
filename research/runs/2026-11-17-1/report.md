# Research run 2026-11-17-1

Scope: one region, chosen by the maintainer (the pipeline's first end to end
run). Token ceiling: 500k, confirmed by the maintainer on 2026-11-17.

## Region: Honduras: Roatan

Centre 16.33, -86.53, radius 50 km. Left out (already in the catalogue, and
anything within 150 m): Bear's Den, Blue Channel, Butcher's Bank, El Aguila,
Half Moon Bay Wall, Mandy's Eel Garden, Spooky Channel, West End Wall
(curated) and the Hawthorn Trader (UKHO).

Result: 15 entries, all passing `check.py`: 2 placed by `confirmed`, 12 by
`stated`, 1 by `map`. Region agent: 244,559 tokens, 75 tool calls.

### Main source

The Roatan Marine Park's resources page links its dive site map, a Google My
Maps layer whose KML holds 435 mooring pins. Each pin's record gives north and
west in decimal degrees (equal to the pin geometry), area, use, mooring depth
in feet and service dates. Every entry cites the resources page as `url` and
the KML as `map`. Mooring depth is not used as a site depth, and nothing was
recorded from the pins' donor names.

### Domains proposed (all counting)

| Domain | Kind | Terms address | Terms |
|---|---|---|---|
| roatanmarinepark.org | official | /terms-conditions | Cover only the park's patrol app; no copying or reuse clause; bare copyright line |
| reefbuilders.com | press | none (/terms-of-use and /terms are 404) | Bare copyright line |
| cocoviewresort.com | operator | none found | Bare copyright line |
| anthonyskey.com | operator | /privacy-policy/ only | All rights reserved footer, no reuse clause |
| sundiversroatan.com | operator | /privacy-policy/ only | All rights reserved footer, no reuse clause |
| kotosadventures.com | operator | none found | All rights reserved footer; several of its site texts copy Splash Inn's, so cited for Mary's Place only |
| roatansplashinn.com | operator | /en/privacy only | Bare copyright line |
| scuba.shop | operator | none found | No terms; the Squarespace page's canonical address |

Read and not used: roatan-diving.com (a directory that embeds the park map),
a Squarespace mirror of Coconut Tree Divers (its own domain no longer
resolves), scubadiving.com (403, terms unreadable), steemit.com (user
content). Agency directories, diveplannerpro and zentacle were leads only.

### Passing sites

1. **Hole in the Wall** (confirmed): park pin and Reef Builders figure 13 m
   apart. Depth from Reef Builders and Sun Divers; Splash Inn's range left
   out as it describes the chute. A diver logbook lead says the park's pin
   here may be the Mangrove Bight buoy.
2. **Lighthouse** (confirmed, 5 m apart). 525 m from Half Moon Bay Wall.
3. **Overheat** (map route): Reef Builders' figure is about 263 m from the
   park mooring, so the shipped point is their mean. Dropping the Reef
   Builders figure would ship the mooring alone, by the stated route.
4. **Fish Den** (stated, park). Reef Builders' figure for it is malformed
   (14 km off read as decimal) and was not recorded.
5. **Odyssey Wreck** (stated): the main wreck pin; the park's separate
   stern pin is about 60 m away.
6. **Mary's Place** (stated).
7. **Calvin's Crack** (stated): the plain pin; a second mooring lies 55 m
   west.
8. **Mr. Bud Wreck** (stated).
9. **Newman's Wall** (stated): the agent's own water check failed; the
   nearest OSM coastline is about 330 m north and the agent suspects its
   orientation.
10. **Gold Chain Reef** (stated): minimum depth only.
11. **Carib Point** (stated): the south-east Half Moon Bay, not West End's.
12. **Cara a Cara** (stated).
13. **Insidious Wall** (stated): minimum depth only.
14. **Sea Quest Shallow** (stated): Reef Builders' figure has an invalid
    minutes value and was not recorded.
15. **Cemetery Wall** (stated): 340 m from Mary's Place.

### Candidates that did not pass

- Pillar Coral: no second counting domain names it.
- Prince Albert wreck: named by CoCo View only, and not in the park layer.
- Turtle Crossing / Deep Turtle Crossing: the park pin is a snorkel mooring,
  ambiguous.
- Seaquest Deep, Gibson Bight, Canyon Reef, Valley of the Kings and other
  West End sites: already in the catalogue, no second naming domain, or
  left out to stay within 15.

### Doubts raised by the region agent

- Reef Builders' figures fall within 4 to 13 m of park moorings for three of
  four sites: probably taken at the same buoys or from the park's list. Both
  confirmed routes rest on them.
- Reef Builders writes figures like `16.18.824 N`; the agent recorded them
  as `16 18.824 N` (first dot replaced, digits kept) and said so in each
  note.
- Park pins are mooring buoys, not the feature itself, on long or deep
  sites.
- KOTOS copies Splash Inn's site texts, so the two were treated as one
  source.

### Machine checks

`named.osm` is `relation/5989963` (Roatan, place=island) for every entry.
14 of 15 pass all three checks. **Newman's Wall fails `in_water`**, and the
failure is the check's, not the point's: the nearest coastline point is the
southern vertex of Fantasy Island, a closed, correctly oriented islet ring
334 m north. The two segments meeting at that vertex are equally near and
give opposite sides; `_nearest_segment` keeps the first, which says land.
The failed result stays recorded, so the entry goes to the maintainer.

### Second pass

One independent agent, given only the entries' facts and cited addresses.
14 agree. **Carib Point disagrees** on `named.place`: the park's own layer
puts its Half Moon Bay pins just west of its Jonesville pins, so "east of
Jonesville" is wrong; "Half Moon Bay, just west of Jonesville" fits. Its
position agrees exactly. Left as recorded (editing the place would void the
pass); the entry goes to the maintainer. The pass also suggested Overheat's
place read "south-west of the El Aguila wreck" rather than "south of"; it
agreed with the entry as written.

### Tiers

With the committed `domains.json`, all 15 wait on the eight unruled domains
(`domains-queue.md`). With the rulings as proposed:

- Auto tier (10): Hole in the Wall, Lighthouse, Fish Den, Odyssey Wreck,
  Calvin's Crack, Mr. Bud Wreck, Gold Chain Reef, Cara a Cara, Insidious
  Wall, Sea Quest Shallow.
- Maintainer queue (5): Overheat (map route), Mary's Place and Cemetery
  Wall (340 m apart, each within 500 m of the other), Newman's Wall (failed
  `in_water`, see above), Carib Point (second pass disagreed).
- Audit sample (5 of 10, the minimum): Cara a Cara, Gold Chain Reef,
  Lighthouse, Mr. Bud Wreck, Sea Quest Shallow.

### Cost

| Step | Tokens |
|---|---|
| Region agent (Roatan) | 244,559 |
| Second pass (15 entries) | 131,337 |
| Total, agents | 375,896 of the 500,000 ceiling |
| Per passing site (15) | 25,060 |
| Per auto tier site (10, if ruled as proposed) | 37,590 |

The orchestrating session's own tokens (machine checks, tiering, this
report) are not counted.

### Maintainer decisions

- 2026-11-17: token ceiling 500k.
- 2026-11-17: all eight domains in `domains-queue.md` ruled as proposed
  (counting, with the kinds proposed), added to `research/domains.json`.
  Re-split with the committed lists: 10 auto, 5 queue, none waiting; the
  same audit sample.
