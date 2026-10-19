import csv
from pathlib import Path

from models.models import Vocab


def parse_vocab(filepath: str | Path) -> list[Vocab]:
    try:
        with open(filepath, newline="") as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter="\t")
            vocabs = []
            for row in reader:
                # Skip if the the line contains a time
                if all(not v for k, v in row.items() if k != "transliteration"):
                    continue
                vocabs.append(
                    Vocab(
                        row["transliteration"],
                        row["meaning"],
                        row["arabic"],
                        row["dual"],
                        row["feminine"],
                        row["plural"],
                        row["source"],
                    )
                )
        return vocabs
    except FileNotFoundError:
        raise
