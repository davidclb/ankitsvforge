import csv
from pathlib import Path

from models.models import Sentence


def parse_sentence(filepath: str | Path) -> list[Sentence]:
    try:
        with open(filepath, newline="") as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter="\t")
            sentences = []
            for row in reader:
                # skip date separator lines (only 'topic' filled; rest empty or missing)
                if all(not v for k, v in row.items() if k != "topic"):
                    continue
                sentences.append(
                    Sentence(
                        row["topic"],
                        row["order"],
                        row["type"],
                        row["transliteration"],
                        row["meaning"],
                        row["arabic"],
                        row["source"],
                    )
                )
        return sentences
    except FileNotFoundError:
        raise
