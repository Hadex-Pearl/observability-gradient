"""Assembles the six L2 third-person prompts exactly as they'll be sent -- system
prompt plus the l2_third template resolved with each item's third-person option
nouns (option_a_third/option_b_third) -- and writes them to report/l2_third_prompts.txt.

Run with:
    python scripts/assemble_l2_third.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import ROOT_DIR  # noqa: E402
from scripts.derive_third_person import derive_l2_third, load_prompts  # noqa: E402

OUTPUT_PATH = ROOT_DIR / "report" / "l2_third_prompts.txt"


def assemble(data, item):
    system = data["shared"]["system_prompts"]["l2"]
    user = derive_l2_third(data, item)
    return f"=== {item['id']} ===\n[system]\n{system}\n[user]\n{user}"


def main():
    data = load_prompts()
    blocks = [assemble(data, item) for item in data["items"]]
    text = "\n".join(blocks)

    OUTPUT_PATH.write_text(text)
    print(text)
    print(f"\nwrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
