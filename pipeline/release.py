#!/usr/bin/env python3
"""Catalogue releases.

    python3.14 pipeline/release.py --out build/release

Builds the files a release publishes, from the snapshot set the committed
catalogue names (catalogue/SNAPSHOTS), restored into the snapshot cache
first. The rebuilt catalogue must equal the committed one byte for byte, or
nothing is written: a release publishes only what its snapshot set
reproduces. The release then adds the open-only build (the ODbL database
without the own-terms sources) and the format contract and country table
the catalogue was built against. The workflow publishes the folder as a
GitHub release tagged by date (next_tag).
"""

import argparse
import contextlib
import io
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import contract  # noqa: E402
import merge  # noqa: E402
from snapshots import CACHE_DIR  # noqa: E402

RELEASE_FILES = (
    "site_catalogue.json",
    "site_catalogue.version",
    merge.NJDEP_METADATA_SHIPPED,
    merge.MD_DNR_METADATA_SHIPPED,
    "site_catalogue_open.json",
    "format.json",
    "countries.json",
)
# The files the merge writes, compared with the committed catalogue.
_BUILT = RELEASE_FILES[:4]


class NotReproducible(RuntimeError):
    """The snapshot set does not rebuild the committed catalogue."""


def _merge(argv: list[str], inputs: dict) -> str:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = merge.main(argv, **inputs)
    if code != 0:
        raise RuntimeError(f"the merge stopped:\n{output.getvalue()}")
    return output.getvalue()


def build_release(
    cache: Path, out: Path, committed: Path = merge.DEFAULT_OUT, *,
    report: list | None = None, **inputs
) -> list[Path]:
    """Writes the release files into [out] and returns them in
    RELEASE_FILES order; the merge's report is appended to [report].
    [inputs] (places, curated, research) stand in for the merge's own in
    tests. Raises NotReproducible, writing nothing, when the rebuild differs
    from [committed]."""
    with tempfile.TemporaryDirectory() as folder:
        rebuilt, open_only = Path(folder) / "full", Path(folder) / "open"
        output = _merge(["--cache", str(cache), "--out", str(rebuilt)], inputs)
        if report is not None:
            report.append(output)
        differing = [
            name for name in _BUILT
            if (committed / name).exists() != (rebuilt / name).exists()
            or ((rebuilt / name).exists()
                and (rebuilt / name).read_bytes() != (committed / name).read_bytes())
        ]
        if differing:
            raise NotReproducible(
                "the snapshot set does not rebuild the committed "
                + ", ".join(differing)
            )
        _merge(["--cache", str(cache), "--out", str(open_only), "--open-only"], inputs)
        out.mkdir(parents=True, exist_ok=True)
        for name in _BUILT:
            if (rebuilt / name).exists():
                shutil.copyfile(rebuilt / name, out / name)
        shutil.copyfile(open_only / "site_catalogue.json", out / "site_catalogue_open.json")
    contract.write_contract(out)
    shutil.copyfile(contract.CONTRACT_DIR / "countries.json", out / "countries.json")
    return [out / name for name in RELEASE_FILES if (out / name).exists()]


def release_notes(merge_output: str, snapshot_tag: str) -> str:
    """A release's notes: the snapshot set it was built from, then the
    merge's report."""
    return (
        f"Built from {snapshot_tag}.\n\n"
        "`site_catalogue_open.json` is the ODbL database alone; the full "
        "catalogue also holds the own-terms sources (see LICENSE-DATA.md).\n\n"
        f"```\n{merge_output.rstrip()}\n```\n"
    )


def next_tag(existing: list[str], today: date) -> str:
    """The next free date tag: YYYY.MM.DD, then .2, .3 on the same day."""
    base = today.strftime("%Y.%m.%d")
    if base not in existing:
        return base
    n = 2
    while f"{base}.{n}" in existing:
        n += 1
    return f"{base}.{n}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--notes", type=Path, default=None)
    arguments = parser.parse_args(argv)
    snapshot_tag = (merge.DEFAULT_OUT / "SNAPSHOTS").read_text("utf-8").strip()
    report: list = []
    try:
        files = build_release(CACHE_DIR, arguments.out, report=report)
    except NotReproducible as error:
        print(error)
        return 2
    for path in files:
        print(path)
    if arguments.notes:
        arguments.notes.write_text(release_notes(report[0], snapshot_tag), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
