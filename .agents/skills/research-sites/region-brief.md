# Region brief (filled in by the research-sites skill)

You are researching ONE region for the Submersion site catalogue, an
ODbL-licensed open database shipped inside a dive log app. Each site you
find becomes an evidence entry: facts plus the pages behind each fact.

- Region: {{REGION}} (centre {{LAT}}, {{LON}}; radius {{RADIUS_KM}} km)
- Country code: {{COUNTRY_CODE}}
- Write only in: {{RUN_FOLDER}}/{{REGION_SLUG}}/
- Already in the catalogue within the radius (leave these out, and
  anything within 150 m of them): {{EXISTING}}
- Aim for 6 to 15 passing sites. Quality over quantity.

Read first, in this repository: `research/README.md` (the rules and the
entry format; it is authoritative), `research/domains.json` (which domains
count, which are cite-only, which are never used), and `AGENTS.md`.

## Leads

To find candidate sites, read directories and aggregators freely:
agency directories, Scuba Spot Advisor, waypoints.ph, Dive Vibe's community
data, search results. Hold leads in memory only: a site name, the region,
and the address where you saw it. Never write a lead list to disk, never
record a position or any other figure from a lead source, and never cite a
lead source as a counting page. A lead says where to look, not where a site
is.

## Pages that count

Official pages (marine parks and reserves, government notices, harbour or
heritage bodies, survey data under an open licence) and first-hand pages
(operators, resorts, liveaboards and charters that run the dive; dive press;
club write-ups by people who dived it). Prefer park and reserve authorities
that publish mooring or site positions, and operators' own interactive
maps: they are where written positions are.

Before relying on a domain that is on no list, read its terms of use. Terms
that forbid copying or reuse make it `never`; a bare copyright line, an
"All rights reserved" footer with no reuse clause, or no terms is fine.
Propose each new domain in your `domains.json` with its list, its kind
(`official`, `operator`, `press`, `club`, `other`) and a one-line reason in
your own words. The maintainer rules on it; entries citing it wait until
then.

## Each site

1. **Existence:** two counting pages on different registrable domains name
   the site in the same bay, island or reef system (`named`). Set
   `named.place` in your own words.
2. **Position:** a stated figure on a counting page (as written), a pin on
   the publisher's own interactive map (stated; for Google My Maps the KML
   is `https://www.google.com/maps/d/kml?mid=<MID>&forcekml=1`), or a point
   read off a counting page's map image matched to two or more
   OpenStreetMap landmarks (`"method": "map"`; say which landmarks in the
   note, with their coordinates and the pixel scale). Never from words
   alone.
3. **Facts:** depth, entry, type and hazards only as counting pages state
   them, in the closed vocabularies of the README.
4. **Checks you can make yourself:** the point is in water (or at the
   shore for a shore entry), in the named place, and not a hotel's,
   village's or shop's map point copied as the site's. Drop or explain any
   figure that fails.
5. **No page text:** facts and addresses only; `note` in your own words.

Any request a script makes sends `User-Agent: dive-site-harvester/1.0` and
nothing naming a person or the project.

## Checker

Write `{{RUN_FOLDER}}/{{REGION_SLUG}}/sites.json` as
`{"sites": [...], "withdrawn_curated": []}` and a `domains.json` that is the
repository's plus your proposals, then run:

    python3.14 research/check.py --file {{RUN_FOLDER}}/{{REGION_SLUG}}/sites.json --domains {{RUN_FOLDER}}/{{REGION_SLUG}}/domains.json

Fix or drop failing entries; never force one. Every entry you hand back
passes. Leave `review` as `{"state": "pending"}`.

## What to hand back

Return your report as text (you cannot write report files):

- every domain you used or rejected: list, kind, terms address, terms in
  one line;
- per passing site: how it was placed, and anything a reviewer should look
  at;
- per candidate that did not pass: why, in one line;
- your doubts for the maintainer;
- your token usage.
