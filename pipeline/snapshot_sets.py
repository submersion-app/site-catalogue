#!/usr/bin/env python3
"""Snapshot sets: every source's raw download, published as a release.

    python3.14 pipeline/snapshot_sets.py pack --out DIR
    python3.14 pipeline/snapshot_sets.py restore snapshots-YYYY-MM-DD

A snapshot set is what one catalogue release was built from, so any release
can be rebuilt byte for byte. `pack` copies the snapshot cache into a flat
folder ready to attach to a GitHub release tagged `snapshots-YYYY-MM-DD`:
each source's snapshot beside a `<key>.TERMS.txt` stating its licence and
credit, New Jersey's and Maryland's metadata, the Natural Earth boundaries
the merge places countries with, and `SET.json`, which says where each file
goes back in the cache. `restore` downloads a set and puts it back.

Every source's terms allow its raw download to be published on conditions.
New Jersey's travel with its metadata; North Carolina's, and the Texas and
Hawaii rows inside the federal reef file, are not part of the ODbL database
and are not for commercial use. Each terms note says so.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import merge  # noqa: E402
import site_catalogue_format as fmt  # noqa: E402
from snapshots import CACHE_DIR  # noqa: E402

MANIFEST = "SET.json"
BOUNDARIES = "naturalearth"

# The catalogue source each snapshot belongs to.
_SOURCE_OF = {
    "osm_sites": "osm",
    "osm_wrecks": "osm",
    "wikidata_sites": "wikidata",
    "wikidata_wrecks": "wikidata",
}

_OWN_TERMS = "Not part of the ODbL database; not for commercial use."


class MissingSnapshotSet(RuntimeError):
    """The named snapshot set has not been published."""

    def __init__(self, tag: str):
        super().__init__(f"no snapshot set {tag}")
        self.tag = tag


def _source_lines(key: str) -> list[str]:
    source = fmt.SOURCES[key]
    return [
        f"{source['name']}",
        f"Licence: {source['licence']} ({source['licence_url']})",
        f"Credit: {source['credit']}",
    ]


def terms_note(key: str) -> str:
    """The terms of snapshot [key], in plain text."""
    if key == BOUNDARIES:
        return (
            "Natural Earth boundaries (admin 0 subunits, admin 1 states and\n"
            "provinces, lakes), public domain:\n"
            "https://www.naturalearthdata.com/about/terms-of-use/\n"
        )
    source_key = _SOURCE_OF.get(key, key)
    lines = [f"Snapshot: {key}", ""] + _source_lines(source_key)
    if key == "njdep":
        lines += [
            "",
            "Redistributed with NJDEP's metadata, credit and disclaimer, "
            f"coordinates as received ({merge.NJDEP_METADATA_FILE} in this set).",
            "Not part of the ODbL database.",
        ]
    elif source_key in fmt.OWN_TERMS_SOURCES:
        lines += ["", _OWN_TERMS]
    if key == "noaa_reefs":
        lines += [
            "",
            "This file also holds the Texas and Hawaii rows, on their states' terms:",
            "",
            *_source_lines("tpwd"),
            _OWN_TERMS,
            "",
            *_source_lines("hi_dar"),
            _OWN_TERMS,
            "",
            f"Maryland's rows travel with Maryland's metadata ({merge.MD_DNR_METADATA_FILE}).",
        ]
    return "\n".join(lines) + "\n"


def pack(cache: Path, out: Path) -> list[Path]:
    """Copies the snapshot set in [cache] into the flat folder [out], with a
    terms note per snapshot and the manifest. Returns the written paths."""
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    keys = sorted(path.stem for path in cache.glob("*.json"))
    fetched_at = {}
    for key in keys:
        files[f"{key}.json"] = f"{key}.json"
        fetched_at[key] = json.loads((cache / f"{key}.json").read_text("utf-8")).get("fetched_at")
        (out / f"{key}.TERMS.txt").write_text(terms_note(key), encoding="utf-8")
    for name in (merge.NJDEP_METADATA_FILE, merge.MD_DNR_METADATA_FILE):
        if (cache / name).exists():
            files[name] = name
    boundaries = cache / BOUNDARIES
    if boundaries.is_dir():
        for path in sorted(boundaries.iterdir()):
            files[f"{BOUNDARIES}.{path.name}"] = f"{BOUNDARIES}/{path.name}"
        (out / f"{BOUNDARIES}.TERMS.txt").write_text(terms_note(BOUNDARIES), encoding="utf-8")
    for asset, relative in files.items():
        shutil.copyfile(cache / relative, out / asset)
    manifest = {"keys": keys, "fetched_at": fetched_at, "files": files}
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sorted(path for path in out.iterdir() if path.is_file())


def gh_release_download(tag: str, dest: Path) -> None:
    """Downloads every asset of release [tag] into [dest] with `gh`."""
    result = subprocess.run(
        ["gh", "release", "download", tag, "--dir", str(dest)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "not found" in result.stderr.lower():
            raise MissingSnapshotSet(tag)
        raise RuntimeError(f"gh release download {tag}: {result.stderr.strip()}")


def restore(tag: str, cache: Path = CACHE_DIR, *, fetch=gh_release_download) -> None:
    """Puts snapshot set [tag] back into [cache]. Raises MissingSnapshotSet,
    writing nothing, when the set was never published."""
    with tempfile.TemporaryDirectory() as folder:
        downloaded = Path(folder)
        fetch(tag, downloaded)
        manifest = json.loads((downloaded / MANIFEST).read_text("utf-8"))
        missing = [asset for asset in manifest["files"] if not (downloaded / asset).exists()]
        if missing:
            raise RuntimeError(f"{tag} is missing {', '.join(sorted(missing))}")
        for asset, relative in manifest["files"].items():
            target = cache / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(downloaded / asset, target)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    pack_command = commands.add_parser("pack")
    pack_command.add_argument("--out", type=Path, required=True)
    pack_command.add_argument("--cache", type=Path, default=CACHE_DIR)
    restore_command = commands.add_parser("restore")
    restore_command.add_argument("tag")
    restore_command.add_argument("--cache", type=Path, default=CACHE_DIR)
    arguments = parser.parse_args(argv)
    if arguments.command == "pack":
        for path in pack(arguments.cache, arguments.out):
            print(path)
        return 0
    try:
        restore(arguments.tag, arguments.cache)
    except MissingSnapshotSet as error:
        print(error)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
