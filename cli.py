import argparse
from pathlib import Path
import logging
from anki.actions import (
    add_notes_grammar,
    add_notes_sentence,
    add_notes_verb,
    add_notes_vocab,
    check_note,
    create_deck,
    create_model_grammar,
    create_model_sentence,
    create_model_verb,
    create_model_vocab,
    toUpdate,
    updateNotefields,
)

from models.models import Grammar, Sentence, Verb, Vocab
from parsing.parser_grammar import parse_grammar
from parsing.parser_sentence import parse_sentence
from parsing.parser_verb import PRONOUNS, parse_verb
import sys

from parsing.parser_vocab import parse_vocab

DECK_NAME_VERB = "1 LebaneseConjugator"
MODEL_NAME_VERB = "LebaneseConjugator"
MODEL_NAME_VOCAB = "LebaneseVocab"
DECK_NAME_VOCAB = "13 LebaneseVocab"
DECK_NAME_SENTENCE = "12 LebaneseSentence"
MODEL_NAME_SENTENCE = "LebaneseSentence"
DECK_NAME_GRAMMAR = "LebaneseGrammar"
MODEL_NAME_GRAMMAR = "LebaneseGrammar"


def label_run_error(note: Verb | Vocab | Sentence | Grammar) -> str:
    if isinstance(note, Verb):
        return f"{note.verb} / {note.tense}"
    elif isinstance(note, Vocab):
        return note.transliteration
    elif isinstance(note, Sentence):
        return note.transliteration
    elif isinstance(note, Grammar):
        return note.rule


def label_dryrun(note: Verb | Vocab | Sentence | Grammar, operation: str) -> str:
    if operation == "create":
        if isinstance(note, Verb):
            return f"CREATE {note.verb} / {note.tense}"
        elif isinstance(note, Vocab):
            return f"CREATE {note.transliteration} / {note.meaning}"
        if isinstance(note, Grammar):
            return f"CREATE {note.rule}"
        elif isinstance(note, Sentence):
            return f"CREATE {note.transliteration} / {note.meaning}"
    if operation == "update":
        if isinstance(note, Verb):
            return f"UPDATE {note.verb} / {note.tense}"
        elif isinstance(note, Vocab):
            return f"UPDATE {note.transliteration} / {note.meaning}"
        if isinstance(note, Grammar):
            return f"CREATE {note.rule}"
        elif isinstance(note, Sentence):
            return f"CREATE {note.transliteration} / {note.meaning}"


def run_import(notes: Verb | Vocab | Sentence | Grammar, add_fn, deck, model, label_fn):
    errors = []
    nb_created = 0
    nb_skipped = 0
    nb_updated = 0
    for note in notes:
        try:
            if not check_note(note):
                add_fn(note, deck, model)
                nb_created += 1
            elif toUpdate(note):
                updateNotefields(note)
                nb_updated += 1
            else:
                nb_skipped += 1

        except Exception as e:
            logging.error(f"couldn't create note for {label_fn(note)}")
            errors.append(note)
    logging.info(f"{nb_created} notes  created")
    logging.info(f"{nb_skipped} notes  skipped")
    logging.info(f"{nb_updated} notes  updated")

    logging.info(f"{len(errors)} errors")
    for error in errors:
        logging.info(f"couldn't create note for {label_fn(error)}")


# Required columns per note type. Everything not listed here is optional and may
# stay empty: an empty cell often means "not applicable" (`bil` has no plural),
# not "missing" — and an optional column is filled later by an in-place update,
# which preserves the SRS. Only these must be present for a line to be imported:
#   - the natural-key columns, or the note could never be matched back to Anki
#     (and several keyless lines would collide on the same empty key);
#   - the answer side, or there is nothing to review.
REQUIRED_FIELDS: dict[type, tuple[str, ...]] = {
    Verb: ("verb", "tense", "conjugation"),
    Vocab: ("transliteration", "meaning"),
    Sentence: ("topic", "order", "meaning"),
    Grammar: ("rule", "explanation"),
}

# Which persons a verb must carry, per tense. The imperative only addresses the
# listener, so it has no 1st/3rd person: requiring the 8 forms there would
# reject every (correct) imperative line. Any other tense needs all 8.
IMPERATIVE_PRONOUNS = ("enta", "ente", "ento")


def expected_pronouns(tense: str) -> tuple[str, ...]:
    """The pronouns a verb is expected to fill for this tense."""
    if tense.strip().lower() == "imperative":
        return IMPERATIVE_PRONOUNS
    return tuple(PRONOUNS)


def missing_pronouns(note: Verb) -> list[str]:
    """Pronouns expected for this verb's tense that carry no form."""
    return [
        p
        for p in expected_pronouns(note.tense)
        if not note.conjugation.get(p, "").strip()
    ]


def missing_required_fields(note: Verb | Vocab | Sentence | Grammar) -> list[str]:
    """Names of the required columns that are empty for this note.

    A partially conjugated verb is NOT reported here: it still produces one
    valid card per filled form, and blocking it would stop syncing a note that
    already lives in Anki with its own review history. Only a verb with no form
    at all is missing something required — it would create a note with zero
    card. Partial conjugations are surfaced by missing_pronouns() as a warning."""
    required = REQUIRED_FIELDS.get(type(note))
    if required is None:
        raise ValueError(f"Unknown note type: {type(note)}")

    missing = []
    for name in required:
        value = getattr(note, name)
        if isinstance(value, dict):
            if not any(v.strip() for v in value.values()):
                missing += list(expected_pronouns(getattr(note, "tense", "")))
        elif not (value or "").strip():
            missing.append(name)
    return missing


def split_valid(
    notes: list[Verb | Vocab | Sentence | Grammar], label_fn
) -> tuple[list, list]:
    """Split notes into (importable, skipped) on their required columns.

    Imported-but-incomplete notes are only warned about: they are still worth
    syncing, and the missing forms can be added later by an in-place update."""
    valid, skipped, partial = [], [], []
    for note in notes:
        missing = missing_required_fields(note)
        if missing:
            skipped.append((note, missing))
            continue
        valid.append(note)
        if isinstance(note, Verb) and missing_pronouns(note):
            partial.append((note, missing_pronouns(note)))

    for note, missing in skipped:
        logging.warning(
            f"SKIP {label_fn(note)} — missing required column(s): {', '.join(missing)}"
        )
    for note, pronouns in partial:
        logging.warning(
            f"INCOMPLETE {label_fn(note)} — no form for: {', '.join(pronouns)} "
            f"(imported anyway, {len(pronouns)} card(s) not generated)"
        )
    if skipped:
        logging.warning(
            f"{len(skipped)} line(s) skipped. "
            f"Fill them in, or re-run with --force to import anyway."
        )
    if partial:
        logging.warning(f"{len(partial)} line(s) imported with missing forms.")
    return valid, skipped


def run_dryrun(notes: Verb | Vocab | Sentence | Grammar, label_fn) -> int:
    """Print the plan and return the number of pending changes (create + update)."""
    to_create = 0
    no_op = 0
    to_update = 0

    for note in notes:
        if not check_note(note):
            to_create += 1
            logging.info(f"{label_fn(note, 'create')}")
        elif toUpdate(note):
            # TODO: list the fields that will change (initial -> desired value)
            to_update += 1
            logging.info(f"{label_fn(note, 'update')}")
        else:
            no_op += 1
    logging.info(f"Summary: {to_create} create, {no_op} no-op, {to_update} to update")
    return to_create + to_update


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "type",
        type=str,
        help="type of notes",
        choices=["verb", "vocab", "sentence", "grammar"],
    )
    parser.add_argument("tsv", type=str, help="the tsv file")
    parser.add_argument("--apply", help="create cards", action="store_true")
    parser.add_argument(
        "--force",
        help="import lines whose natural key is incomplete (not recommended)",
        action="store_true",
    )
    args = parser.parse_args()

    target_file = Path(args.tsv)
    if not target_file.exists():
        print("The target file doesn't exist")
        raise SystemExit(1)

    if args.type == "verb":
        notes = parse_verb(args.tsv)
        add_fn = add_notes_verb
        create_model_fn = create_model_verb
        deck = DECK_NAME_VERB
        model = MODEL_NAME_VERB
    elif args.type == "vocab":
        notes = parse_vocab(args.tsv)
        add_fn = add_notes_vocab
        create_model_fn = create_model_vocab
        deck = DECK_NAME_VOCAB
        model = MODEL_NAME_VOCAB
    elif args.type == "sentence":
        notes = parse_sentence(args.tsv)
        add_fn = add_notes_sentence
        create_model_fn = create_model_sentence
        deck = DECK_NAME_SENTENCE
        model = MODEL_NAME_SENTENCE
    elif args.type == "grammar":
        notes = parse_grammar(args.tsv)
        add_fn = add_notes_grammar
        create_model_fn = create_model_grammar
        deck = DECK_NAME_GRAMMAR
        model = MODEL_NAME_GRAMMAR

    nb_skipped = 0
    if args.force:
        valid = notes
        logging.warning("--force: importing lines with an incomplete key too.")
    else:
        valid, skipped = split_valid(notes, label_run_error)
        nb_skipped = len(skipped)

    nb_changes = run_dryrun(valid, label_dryrun)

    if args.apply:
        # The model is source of truth for presentation, so it converges on every
        # apply — before, and independently of, any content change. Otherwise a
        # collection already in sync (0 create, 0 update) would exit below and
        # never pick up a new field, CSS or template.
        create_model_fn(model)

        if nb_changes == 0:
            logging.info("Nothing to apply.")
            # skipped lines are still an error: the file needs fixing
            raise SystemExit(1 if nb_skipped else 0)
        reponse = input("Apply these changes? [y/N] ").strip().lower()
        if reponse in ("y", "yes", "o", "oui"):
            create_deck(deck)
            run_import(valid, add_fn, deck, model, label_run_error)

    # exit code != 0 if at least one line was rejected (spec 8.5)
    if nb_skipped:
        raise SystemExit(1)
