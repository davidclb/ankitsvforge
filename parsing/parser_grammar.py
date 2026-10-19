import csv
from pathlib import Path

from models.models import Grammar


def parse_grammar(filepath: str | Path) -> list[Grammar]:
    try:
        with open(filepath, newline="") as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter="\t")
            grammars = []
            for row in reader:
                # skip date separator lines (only 'rule' filled, rest empty)
                if all(not v for k, v in row.items() if k != "rule"):
                    continue
                grammars.append(
                    Grammar(
                        row["rule"],
                        row["explanation"],
                        row["example"],
                        row["arabic"],
                        row["source"],
                    )
                )
        return grammars
    except FileNotFoundError:
        raise
