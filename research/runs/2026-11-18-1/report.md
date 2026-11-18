# Research run 2026-11-18-1

Scope: one region, chosen by the maintainer (Bonaire). Token ceiling:
500k, confirmed by the maintainer on 2026-11-18.

## Region: Bonaire

Centre 12.15, -68.27, radius 50 km. The catalogue already holds 65
OpenStreetMap dive site records within the radius, covering most of the
main island's leeward coast and the Washington Slagbaai park; there was
nothing on Klein Bonaire. Those records, and anything within 150 m of
them, were left out.

Result: 11 entries, all passing `check.py`, **all placed by the `map`
route**: 8 on Klein Bonaire and 3 on the main island's north-west coast.
Region agent: 299,615 tokens, 138 tool calls.

### Why every position is a map reading

No counting page states a written position for any Bonaire site. The
region agent searched park, operator, press and club pages, and a later
independent search found none either. STINAPA reports about 100 public
moorings but publishes no list of their positions. The pages that do
carry coordinates are directories, compilations or a commercial chart.
None of them counts, so none of their figures was recorded.

### Main source

STINAPA's Bonaire National Marine Park page links its 2025 park folder.
Page 2 of the folder is a dive site map numbering the main island's
moorings 1 to 61 and Klein Bonaire's A to Z, with a table of access (boat,
land, snorkel). Every entry cites the park page as `url` and that image as
`map`. Beyond the Corals' dive sites page names the same sites with the
same numbers and letters, so it is the second naming domain. Entry (boat
or shore) comes from the folder's table. No counting page states depths or
hazards reliably, so none are recorded.

The folder map is schematic: markers sit at even spacing along a drawn
coast that is not to scale.

- **Klein Bonaire (8):** the drawn island was fitted to the OpenStreetMap
  coastline (ways 12195427 and 317792829) by a least squares affine
  transform at its four extreme points, about 18 by 17 m per pixel, with
  residuals of 43 to 84 m. The west lobe pond (51 m off) and Tanki Kalbas
  (97 m off) check it. The drawn lighthouse is about 840 m off and was not
  used. The points lie 73 to 323 m off the coast, probably further out than
  the real moorings.
- **Main island (3):** the drawn coast is too schematic to fit. Each point
  is placed on the straight line between the OpenStreetMap dive site nodes
  of the two numbered neighbours either side of it, at the fraction its
  marker lies along the drawn marker path. This is the weaker reading. It
  anchors on catalogue dive site nodes, not on coastline or named
  landmarks, and the maintainer chose to keep these three entries
  (2026-11-18).

### Domains (ruled by the maintainer, 2026-11-18, as proposed)

| Domain | List | Kind | Terms address | Terms |
|---|---|---|---|---|
| stinapabonaire.org | counting | official | /terms-conditions/ | Empty page; bare copyright line |
| beyondthecorals.com | counting | operator | /wp-content/uploads/2024/06/General-Terms-and-Conditions.pdf | Bookings and media only; no reuse clause; bare copyright line |
| harpsguidetobonaire.com | cite_only | | none found | A family's compiled guide whose coordinate table mixes formats and holds plainly wrong figures |
| duikersgids.nl | cite_only | | not read | Subscription directory with user logbooks |
| infobonaire.com | cite_only | | not read | Tourism directory |
| bonaireisland.com | never | | /terms-of-use/ | Personal use only; commercial copying and redistribution forbidden |
| frankosmaps.com | never | | not read | Commercial chart; a set of positions protected as a database |

Read and not used:

- buddydive.com: its map is Franko's, reprinted with permission.
- sunwisebonaire.com: a rental agency; its embedded map layer returns 404.
- wannadive.com (Wannadive Bonaire, an operator, not the never-listed
  directory): no site content.
- divefriendsbonaire.com: its site PDF returned 403.
- NOAA CARICOMP Barcadera: the station is about 400 m from the dive
  mooring.

### Passing sites

1. **Rappel** (11): 446 m from La Dania's Leap, 763 m from Boka di Tolo,
   59 m seaward. Boat.
2. **Kalli's Reef** (19): about 400 m from Jeff Davis Memorial and from
   Oil Slick Leap, 27 m off the coast. Boat and shore.
3. **Barkadera** (21): between Oil Slick Leap and Andrea II, 143 m
   seaward. Boat.
4. **Ebo's Reef** (B): 323 m off the north-east shore. Boat.
5. **Nearest Point** (E): 143 m off the south-east shore. Boat.
6. **Monte's Divi Tree** (H): 73 m off the south shore. Boat.
7. **Captain Don's Reef** (K): 234 m off the south shore. Boat.
8. **Forest** (N): 132 m off the south-west shore. Boat.
9. **Southwest Corner** (O): 250 m off the south-west tip, 365 m from
   Forest. Boat.
10. **Munk's Haven** (P): 298 m off the west shore, 323 m from Southwest
    Corner. Boat.
11. **Sampler** (Z): 297 m off the north shore. Boat.

### Candidates that did not pass

- Bloodlet, Country Garden, Bon Bini na Kas, Chez Hines: the straight line
  reading fell on land where the coast curves; dropped rather than given an
  offshore offset no page states.
- No Name (A): the reading is about 500 m from the OpenStreetMap No Name
  beach, larger than the map's error elsewhere.
- Other Klein Bonaire letters: left out to keep the spacing above the
  map's error and the run at or under 15.
- Petrie's Pillar, Small Wall: not attempted, crowded between catalogue
  records.
- Ol' Blue: the same mooring as the catalogue's Boka di Tolo.
- Town Pier: STINAPA lists it as closed.

### Doubts raised by the region agent

- Beyond the Corals numbers its sites as the Franko chart and Buddy Dive's
  brochure do, so its list may share a source with STINAPA's. It is used
  for naming only.
- A published STINAPA mooring list would replace every position here with
  a stated one and settle most of the region; asking STINAPA for it is the
  way to a better Bonaire.

### Machine checks

`named.osm` is `relation/4266671` (Bonaire, place=island) for the three
main island entries and `relation/5176051` (Klein Bonaire, place=island)
for the eight others. All 11 pass all three checks. Kalli's Reef passes
`in_water` as a shore entry, 27 m from the coastline. Overpass returned
intermittent 502s; each entry was retried until its checks completed.

### Second pass

One independent agent, given only the entries' facts and cited addresses.
It found that STINAPA's page names no site in its own text: the names are
on the linked folder map, which it read as part of the page. It agreed
with every fact of all 11 entries. For the map readings, it checked each
point against the marker's place on the drawn coast and its order among
its neighbours.

### Tiers

With the rulings in `research/domains.json`: auto tier 0, maintainer queue
11, waiting 0. A map reading never reaches the auto tier, so there is no
audit sample and no auto PR for this run.

### Cost

| Step | Tokens |
|---|---|
| Region agent (Bonaire) | 299,615 |
| Second pass (11 entries) | 123,993 |
| Total, agents | 423,608 of the 500,000 ceiling |
| Per passing site (11) | 38,510 |

The orchestrating session's own tokens (machine checks, tiering, this
report) are not counted.

### Maintainer decisions

- 2026-11-18: token ceiling 500k.
- 2026-11-18: all 11 entries go to the queue, the three main island
  interpolations included.
- 2026-11-18: all seven domains in `domains-queue.md` ruled as proposed.
- 2026-11-18: all 11 entries approved by the maintainer after the review
  page; catalogue rebuilt from snapshots-2026-11-16 (11 new, 0 gone,
  21,010).
