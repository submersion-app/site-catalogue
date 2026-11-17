# Submersion site catalogue

The built-in dive site catalogue of [Submersion](https://github.com/submersion-app/submersion),
a dive log app: about 21,000 dive sites, wrecks and artificial reefs, compiled
from OpenStreetMap, open wreck and reef registers, Wikidata, and sites
researched for Submersion from published sources.

This repository holds everything that builds it: the fetchers for each source,
the merge, the researched sites' evidence and the checker that enforces their
rules, and the format contract the app reads. Its releases are what the app
ships.

## Licences

- **The catalogue** is a database under the
  [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/),
  because it includes OpenStreetMap data. Four sources allow reuse only on
  their own terms and are not part of the ODbL database: New Jersey, North
  Carolina, Texas and Hawaii reefs. See [LICENSE-DATA.md](LICENSE-DATA.md).
- **The code** is under the GNU General Public License v3.0, as the app is.
  See [LICENSE](LICENSE).

## Using a release

Each release (tagged `YYYY.MM.DD`) carries:

| File | What it is |
|---|---|
| `site_catalogue.json` | The catalogue the app ships |
| `site_catalogue.version` | Its hash; the app re-imports the catalogue when it changes |
| `site_catalogue_open.json` | The ODbL database alone, without the own-terms sources |
| `site_catalogue_njdep_metadata.xml`, `site_catalogue_md_dnr_metadata.xml` | Metadata New Jersey's and Maryland's terms require beside their records |
| `format.json`, `countries.json` | The format contract and country table the release was built against |

Anyone redistributing the data commercially should use `site_catalogue_open.json`.

Each release's notes name the snapshot set it was built from. Snapshot sets
are releases tagged `snapshots-YYYY-MM-DD`: every source's raw download, each
beside a `TERMS.txt` stating its licence and credit.

## Building

Python 3.14, standard library only.

1. Fetch every source into `.cache/snapshots/` (each fetcher can be run on its
   own, as `python3.14 pipeline/src_ukho.py` and its siblings, and
   `python3.14 pipeline/places.py` for the boundaries), or restore a published
   snapshot set.
2. Build: `python3.14 pipeline/merge.py`, which rewrites `catalogue/`.

`catalogue/` is committed: it is the catalogue the next release publishes,
and `catalogue/SNAPSHOTS` names the snapshot set it was built from. To
rebuild it exactly, restore that set
(`python3.14 pipeline/snapshot_sets.py restore <tag>`) and run the merge.
The merge compares against the committed catalogue and stops when a
researched or curated record would leave it without a withdrawal.

The open-only build: `python3.14 pipeline/merge.py --open-only --out build/open`.

Run the tests with `python3.14 pipeline/run_tests.py`, and the researched
sites' checker with `python3.14 research/check.py`.

## Design records

The designs behind the catalogue (the `docs/design/specs/...` files the code
comments cite) live in the app repository,
[submersion-app/submersion](https://github.com/submersion-app/submersion/tree/main/docs/design/specs).

## Researched sites

Sites the registers do not list (reefs, walls, shore dives) are researched
from published pages under the rules in [research/README.md](research/README.md).
Every fact cites the pages behind it; no page text is kept. A researched site
ships marked "Not verified" in the app and is never picked for a diver by GPS.
