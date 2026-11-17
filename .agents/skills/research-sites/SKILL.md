---
name: research-sites
description: Run a research run that adds dive sites to the Submersion site catalogue from published pages. Use when asked to research dive sites, grow the catalogue, or research a named region. Picks the thinnest regions, researches them with one agent per region, runs the machine checks and an independent second pass, tiers each entry, and prepares the review page and the two PRs.
---

# Research sites

A research run adds researched dive sites to `research/sites.json` under the
rules in `research/README.md`, which are authoritative. Read it, and
`AGENTS.md`, before starting. Never write page text anywhere; never commit
a lead list; never force an entry that fails `research/check.py`.

## 1. Scope and budget

Ask the maintainer for:

- the scope: a number of regions, or region names;
- a token ceiling for the run.

Create the run folder `research/runs/<YYYY-MM-DD>-<n>/` (the next free n).

## 2. Regions

Run `python3.14 research/runs.py regions --limit <scope>`. It ranks the
well-known diving areas in `research/regions.json` by the dive site records
within 50 km in the committed catalogue, and skips regions an earlier
run's report already covers. Use the maintainer's names instead when given.

## 3. One agent per region

Dispatch one subagent per region with `region-brief.md` (beside this file),
filled in with the region's name, centre, the run folder, and the
catalogue records already within its radius (they are left out). Run
several at once. Before starting each new region, add up the token usage
the finished agents reported; stop starting regions once the ceiling is
passed, and say which regions were left.

Each agent gathers its leads in memory, researches, writes its entries to
`<run folder>/<region slug>/sites.json` and its domain proposals to
`<run folder>/<region slug>/domains.json`, runs the checker on them, and
returns its report as text (agents cannot write report files). Write each
report into the run's `report.md` under a heading `## Region: <name>`
(runs.py reads those headings to skip covered regions next time).

## 4. Machine checks

For each entry, set `named.osm` to the OpenStreetMap feature its
`named.place` names (find it with Nominatim or Overpass, the harvester
user agent, one request a second), then run the checks. From a short
script with `research/` on its import path: for each entry,
`[machine_checks.as_fact(r, today) for r in machine_checks.run_checks(entry)]`
becomes the entry's `checks`. To look at one entry by hand:
`python3.14 research/machine_checks.py <entry id> --file <its sites.json>`.
A failed check is recorded as failed, never dropped: it sends the entry to
the maintainer.

## 5. Second pass

Dispatch fresh subagents with `second-pass.md`, a batch of entries each.
Give each only the entries' cited addresses and recorded facts: never the
first agents' notes, reports or reasoning. For every entry it returns
agree or disagree with a reason per fact. Record
`"second_pass": {"date": <today>, "agrees": <bool>, "facts": auto_tier.facts_hash(entry)}`
after the last edit to the entry's facts. A disagreement goes in the
run's report beside the entry.

## 6. Tiers and domains

Merge the regions' entries and run `runs.split_run` with the committed
`domains.json` (and the committed entries as `existing`). Then:

- write `<run folder>/domains-queue.md`: each domain on no list, its terms
  address, the proposed list and kind, and the reason, in the agent's own
  words;
- the `waiting` entries stay in the run folder until their domains are
  ruled.

## 7. Review page and PRs

- Draw the sample: `runs.audit_sample([auto ids], <run folder name>)`.
- Write the review page with `review.render(checked, domains, audit=sample)`
  into the run folder, and hand it to the maintainer.
- With the maintainer's go-ahead, open two PRs against `main`:
  - **the auto PR**: the auto-tier entries, each with
    `"review": {"state": "approved", "date": <today>, "by": "auto"}`, and
    the rebuilt catalogue (restore `catalogue/SNAPSHOTS`'s set, run the
    merge);
  - **the queue PR**: the maintainer-tier entries, pending, and the domain
    rulings the queue asks for.
- Each PR body carries the run's cost report: tokens per region and per
  passing site, and `Refs #4514`.

## 8. After the audit

When the maintainer has marked the sample, count the wrong entries and run
`runs.pause_tripped(wrong, sampled)`. If it trips, move every auto entry of
the run into the queue PR (pending, no `by`), record the pause and its
cause in the run's `report.md`, and do not auto-approve in later runs until
the maintainer says the cause is fixed. Otherwise the auto PR may merge.
Record each queue decision in its entry's `review`, `"by": "maintainer"`.
