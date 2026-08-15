"""Loads items/items.yaml with pyyaml and validates it against the item schema. Run with:
    python tests/test_items.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import CONFIG  # noqa: E402

SCHEMA_FIELDS = [
    "id",
    "dimension",
    "option_a",
    "option_b",
    "source_item",
    "source_citations",
    "what_changed",
    "l0_affordance",
    "excluded_because",
]


def load_items():
    with open(CONFIG["paths"]["items_file"]) as fh:
        return yaml.safe_load(fh)


def main():
    data = load_items()
    assert isinstance(data, dict), "items.yaml must load as a mapping"
    assert "items" in data, "items.yaml must have a top-level 'items' key"
    assert "rejected" in data, "items.yaml must have a top-level 'rejected' key"

    active = data["items"]
    rejected = data["rejected"]
    assert active, "no active items found"

    print(f"loaded {len(active)} active item(s) and {len(rejected)} rejected item(s)")

    ids_seen = set()
    for item in active:
        missing = [f for f in SCHEMA_FIELDS if f not in item]
        assert not missing, f"item {item.get('id')!r} missing fields: {missing}"

        for field in SCHEMA_FIELDS:
            if field == "excluded_because":
                assert item[field] is None, f"active item {item['id']!r} must have excluded_because=null, got {item[field]!r}"
            elif field == "source_citations":
                assert isinstance(item[field], list) and len(item[field]) >= 1, (
                    f"item {item['id']!r} source_citations must be a non-empty list"
                )
            else:
                assert item[field] not in (None, ""), f"item {item['id']!r} field {field!r} must be non-null"

        assert item["id"] not in ids_seen, f"duplicate item id: {item['id']!r}"
        ids_seen.add(item["id"])

    print(f"PASS: all {len(active)} active items have every field populated except excluded_because")

    for item in rejected:
        missing = [f for f in SCHEMA_FIELDS if f not in item]
        assert not missing, f"rejected item {item.get('id')!r} missing fields: {missing}"
        assert item["excluded_because"], f"rejected item {item['id']!r} must have excluded_because populated"
        assert item["source_item"], f"rejected item {item['id']!r} must have source_item populated"
        assert item["source_citations"], f"rejected item {item['id']!r} must have source_citations populated"

    print(f"PASS: all {len(rejected)} rejected item(s) have excluded_because populated")
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
