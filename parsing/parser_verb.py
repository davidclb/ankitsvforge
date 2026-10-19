import csv
from pathlib import Path
import sys
from models.models import Verb

PRONOUNS = ["ana", "enta", "ente", "houwe", "hiye", "nehna", "ento", "henne"]


def parse_verb(filepath: str | Path) -> list[Verb]:
    try:
        with open(filepath, newline="") as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter="\t")
            verbs = []
            for row in reader:
                # Skip if the the line contains a time
                if all(not v for k, v in row.items() if k != "verb"):
                    continue
                verbs.append(
                    Verb(
                        row["verb"],
                        row["meaning"],
                        row["tense"],
                        {p: row[p] for p in PRONOUNS if row[p]},
                        row["arabic"],
                        row["source"],
                    )
                )
        return verbs
    except FileNotFoundError:
        raise
