#!/usr/bin/env python3
"""The catalogue's published format contract.

    python3.14 pipeline/contract.py            # write contract/format.json
    python3.14 pipeline/contract.py --check    # exit 1 if it is out of date

The contract states the shape of a catalogue release: its format version,
the record fields and which are required, and the closed vocabularies a
record may use. It is built from the pipeline's own definitions, so it can
never disagree with what the merge writes; CI checks the committed copy is
current. The app keeps a copy of the contract it reads, and its tests fail a
release whose contract it cannot read.

`contract/countries.json` sits beside it: the country names the merge writes
and the codes the app resolves them to (see places.known_country_names).
"""

import argparse
import json
import os
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, *(os.path.join(os.path.dirname(_HERE), _d) for _d in ("pipeline", "research", "curated"))):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence  # noqa: E402
import site_catalogue_format as fmt  # noqa: E402

CONTRACT_DIR = Path(_HERE).parent / "contract"
CONTRACT_FILE = "format.json"

# Every field a catalogue record may carry, in the order the app's parser
# lists them. A record without one of the required fields fails validation.
RECORD_FIELDS = (
    "id", "name", "lat", "lon", "country_code", "country", "region",
    "locality", "island", "body_of_water", "water_type", "max_depth_m",
    "min_depth_m", "types", "entry", "difficulty", "features", "hazards",
    "description", "website", "kind", "source", "source_ref", "trust",
    "position_from",
)
REQUIRED_FIELDS = frozenset({"id", "name", "source", "trust"})


def build_contract() -> dict:
    """The contract, from the pipeline's definitions."""
    return {
        "format": fmt.FORMAT,
        "fields": {
            name: {"required": name in REQUIRED_FIELDS} for name in RECORD_FIELDS
        },
        "site_types": list(fmt.SITE_TYPE_IDS),
        "entry_methods": list(fmt.ENTRY_METHODS),
        "trust_levels": list(fmt.TRUST_LEVELS),
        "position_from": ["map"],
        "withdrawal_reasons": list(fmt.WITHDRAWAL_REASONS),
        "hazard_codes": sorted(evidence.HAZARD_SENTENCES),
        "kinds": list(fmt.KINDS),
    }


def _text(contract: dict) -> str:
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_contract(directory: Path) -> None:
    """Writes `format.json` into [directory]."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / CONTRACT_FILE).write_text(_text(build_contract()), encoding="utf-8")


def check(directory: Path = CONTRACT_DIR) -> int:
    """0 when [directory]'s `format.json` is the current contract, else 1."""
    path = directory / CONTRACT_FILE
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != _text(build_contract()):
        print(f"{path} is out of date: run python3.14 pipeline/contract.py")
        return 1
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.check:
        return check()
    write_contract(CONTRACT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
