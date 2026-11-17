#!/usr/bin/env python3
"""The monthly register refresh.

    python3.14 pipeline/refresh.py --tag snapshots-YYYY-MM-DD
        [--previous snapshots-YYYY-MM-DD] [--body PATH]

Fetches every source into the snapshot cache, then builds the catalogue.
A source whose fetch fails, twice, or whose download holds fewer than half
the rows of the previous set's, is restored from the previous snapshot set
and named in the report: a refresh never drops a source silently. The merge
rebuilds the committed catalogue (catalogue/), so its guard compares
against every record the last catalogue shipped and stops the build when
one would leave without a withdrawal. catalogue/SNAPSHOTS then names the new
set (`--tag`), which the workflow publishes.

Exit codes: 0 rebuilt (the PR body is written to `--body`); 2 the merge
stopped (its output is written to `--body`, for an issue); 3 a source failed
with no previous set to fall back on.
"""

import argparse
import contextlib
import io
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import merge  # noqa: E402
import places  # noqa: E402
import snapshot_sets  # noqa: E402
import snapshots  # noqa: E402
import src_awois  # noqa: E402
import src_ireland  # noqa: E402
import src_osm  # noqa: E402
import src_reefs  # noqa: E402
import src_ukho  # noqa: E402
import src_wikidata  # noqa: E402

# A download holding fewer rows than this share of the previous set's is
# treated as a failed one (a truncated answer, a register gone half empty).
COLLAPSE_SHARE = 0.5


@dataclass(frozen=True)
class Fetch:
    """One download: what runs it, the snapshots it writes, and any other
    cache files it writes (metadata, boundary folders)."""

    run: Callable[[Path], object]
    keys: tuple = ()
    extra: tuple = ()


@dataclass
class RefreshResult:
    fetched: list = field(default_factory=list)
    reused: dict = field(default_factory=dict)
    failed_without_fallback: list = field(default_factory=list)


# The real downloads. Each writes into the default snapshot cache, so the
# refresh runs them with that cache.
FETCHES = {
    "boundaries": Fetch(lambda cache: places.fetch_boundaries(cache), extra=(snapshot_sets.BOUNDARIES,)),
    "ukho": Fetch(lambda cache: src_ukho.fetch(), keys=("ukho",)),
    "awois": Fetch(lambda cache: src_awois.fetch(), keys=("awois",)),
    "nms_ie": Fetch(lambda cache: src_ireland.fetch(), keys=("nms_ie",)),
    "fwc": Fetch(lambda cache: src_reefs.fetch_fwc(), keys=("fwc",)),
    "noaa_reefs": Fetch(lambda cache: src_reefs.fetch_federal(), keys=("noaa_reefs",),
                        extra=(merge.MD_DNR_METADATA_FILE,)),
    "njdep": Fetch(lambda cache: src_reefs.fetch_njdep(), keys=("njdep",),
                   extra=(merge.NJDEP_METADATA_FILE,)),
    "nc_dmf": Fetch(lambda cache: src_reefs.fetch_nc_dmf(), keys=("nc_dmf",)),
    "fknms": Fetch(lambda cache: src_reefs.fetch_fknms(), keys=("fknms",)),
    "osm_wrecks": Fetch(lambda cache: src_osm.fetch_wrecks(), keys=("osm_wrecks",)),
    "osm_sites": Fetch(lambda cache: src_osm.fetch_sites(), keys=("osm_sites",)),
    "wikidata": Fetch(lambda cache: src_wikidata.fetch(), keys=("wikidata_sites", "wikidata_wrecks")),
}


def _rows(key: str, cache: Path) -> int | None:
    try:
        return len(snapshots.read_snapshot(key, cache)["rows"])
    except (FileNotFoundError, KeyError, ValueError):
        return None


def _put_back(fetch: Fetch, previous: Path, cache: Path) -> None:
    for name in [f"{key}.json" for key in fetch.keys] + list(fetch.extra):
        source, target = previous / name, cache / name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        elif source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def _has(fetch: Fetch, previous: Path) -> bool:
    names = [f"{key}.json" for key in fetch.keys] + list(fetch.extra)
    return bool(names) and all((previous / name).exists() for name in names)


def refresh(
    previous_tag: str | None,
    cache: Path = snapshots.CACHE_DIR,
    *,
    fetches: dict = FETCHES,
    pause: float = 60,
    restore=snapshot_sets.restore,
) -> RefreshResult:
    """Runs every fetch into [cache], falling back to [previous_tag]'s set
    for any that fail or collapse."""
    result = RefreshResult()
    with tempfile.TemporaryDirectory() as folder:
        previous = Path(folder)
        if previous_tag:
            restore(previous_tag, previous)
        for name, fetch in fetches.items():
            reason = None
            for attempt in range(2):
                try:
                    fetch.run(cache)
                    reason = None
                    break
                except Exception as error:  # noqa: BLE001 - any failure falls back
                    reason = (str(error).strip().splitlines() or [type(error).__name__])[0]
                    if attempt == 0:
                        time.sleep(pause)
            if reason is None:
                for key in fetch.keys:
                    now, before = _rows(key, cache), _rows(key, previous)
                    if before and now is not None and now < COLLAPSE_SHARE * before:
                        reason = f"{key} came back with {now} rows, the previous set had {before}"
                        break
            if reason is None:
                result.fetched.append(name)
            elif _has(fetch, previous):
                _put_back(fetch, previous, cache)
                result.reused[name] = reason
            else:
                result.failed_without_fallback.append(name)
    return result


def pr_body(result: RefreshResult, merge_output: str) -> str:
    """The refresh PR's description."""
    lines = [
        "The monthly register refresh. The workflow that opened this PR "
        "ran the tests and the checker on it before opening it.",
        "",
        "## Merge report",
        "",
        "```",
        merge_output.rstrip(),
        "```",
    ]
    if result.reused:
        lines += ["", "## Reused from the previous set", ""]
        lines += [f"- {name}: {reason}" for name, reason in sorted(result.reused.items())]
    lines += ["", "Refs #4514", ""]
    return "\n".join(lines)


SNAPSHOTS_FILE = merge.DEFAULT_OUT / "SNAPSHOTS"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--previous", default=None, help="the previous snapshot set's tag")
    parser.add_argument("--tag", required=True, help="this refresh's snapshot set tag")
    parser.add_argument("--body", type=Path, default=Path("build/refresh-body.md"))
    arguments = parser.parse_args(argv)

    result = refresh(arguments.previous)
    if result.failed_without_fallback:
        print("Failed with no previous set: " + ", ".join(result.failed_without_fallback))
        return 3
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = merge.main([])
    print(output.getvalue())
    arguments.body.parent.mkdir(parents=True, exist_ok=True)
    if code != 0:
        arguments.body.write_text(output.getvalue(), encoding="utf-8")
        return 2
    SNAPSHOTS_FILE.write_text(arguments.tag + "\n", encoding="utf-8")
    arguments.body.write_text(pr_body(result, output.getvalue()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
