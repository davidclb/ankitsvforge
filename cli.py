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
from parsing.parser_verb import parse_verb
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

    nb_changes = run_dryrun(notes, label_dryrun)

    if args.apply:
        # The model is source of truth for presentation, so it converges on every
        # apply — before, and independently of, any content change. Otherwise a
        # collection already in sync (0 create, 0 update) would exit below and
        # never pick up a new field, CSS or template.
        create_model_fn(model)

        if nb_changes == 0:
            logging.info("Nothing to apply.")
            return
        reponse = input("Apply these changes? [y/N] ").strip().lower()
        if reponse in ("y", "yes", "o", "oui"):
            create_deck(deck)
            run_import(notes, add_fn, deck, model, label_run_error)

