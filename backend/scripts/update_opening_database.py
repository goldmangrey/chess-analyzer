"""Vendor a pinned CC0 snapshot of lichess-org/chess-openings.

This maintenance script is not used at application runtime. It combines the
five source TSV files into one deterministic local asset.
"""

from pathlib import Path
from urllib.request import urlopen


REVISION = "4b8622759e7ae6f93f011cc6c83a3823401ab45e"
SOURCE = "https://raw.githubusercontent.com/lichess-org/chess-openings/{revision}/{volume}.tsv"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "openings.tsv"


def main() -> None:
    rows: list[str] = []
    for volume in "abcde":
        with urlopen(SOURCE.format(revision=REVISION, volume=volume), timeout=30) as response:
            lines = response.read().decode("utf-8").splitlines()
        if not lines or lines[0] != "eco\tname\tpgn":
            raise RuntimeError(f"Unexpected opening database format in {volume}.tsv")
        rows.extend(lines[1:])
    OUTPUT.write_text("eco\tname\tpgn\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} openings to {OUTPUT}")


if __name__ == "__main__":
    main()
