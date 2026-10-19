import logging
from pathlib import Path
from typing import Any

from anki.api import invoke
from models.models import Grammar, Sentence, Verb, Vocab

MODEL_NAME_VERB = "LebaneseConjugator"
MODEL_NAME_VOCAB = "LebaneseVocab"
MODEL_NAME_SENTENCE = "LebaneseSentence"
MODEL_NAME_GRAMMAR = "LebaneseGrammar"

PRONOUNS = ["Ana", "Enta", "Ente", "Houwe", "Hiye", "Nehna", "Ento", "Henne"]
INORDERFIELDS_VERB = [
    "Verb",
    "Meaning",
    "Tense",
    "Ana",
    "Enta",
    "Ente",
    "Houwe",
    "Hiye",
    "Nehna",
    "Ento",
    "Henne",
    "FormVariant",
    "Arabic",
    "Ask",
]

INORDERFIELDS_VOCAB = [
    "Transliteration",
    "Meaning",
    "Arabic",
    "Dual",
    "Feminine",
    "Plural",
    "Source",
    "Ask",
]

INORDERFIELDS_SENTENCE = [
    "Topic",
    "Order",
    "Type",
    "Transliteration",
    "Meaning",
    "Arabic",
    "Source",
    "Ask",
]

INORDERFIELDS_GRAMMAR = [
    "Rule",
    "Explanation",
    "Example",
    "Arabic",
    "Source",
    "Ask",
]

SHARED_CSS = (Path(__file__).parent / "card.css").read_text(encoding="utf-8")


def build_field_verb(verb: Verb) -> dict:
    return {
        "Verb": verb.verb,
        "Meaning": verb.meaning,
        "Tense": verb.tense,
        **{
            p.capitalize(): verb.conjugation.get(p.lower(), "").split(" / ")[0].strip()
            for p in PRONOUNS
        },
        "FormVariant": " | ".join(
            f"{p}: {v}" for p, v in verb.conjugation.items() if " / " in v
        ),
        "Arabic": verb.arabic,
    }


def build_field_vocab(vocab: Vocab) -> dict:
    return {
        "Transliteration": vocab.transliteration,
        "Meaning": vocab.meaning,
        "Arabic": vocab.arabic,
        "Dual": vocab.dual,
        "Feminine": vocab.feminine,
        "Plural": vocab.plural,
        "Source": vocab.source,
    }


def build_field_sentence(sentence: Sentence) -> dict:
    return {
        "Topic": sentence.topic,
        "Order": sentence.order,
        "Type": sentence.type,
        "Transliteration": sentence.transliteration,
        "Meaning": sentence.meaning,
        "Arabic": sentence.arabic,
        "Source": sentence.source,
    }


def build_field_grammar(grammar: Grammar) -> dict:
    return {
        "Rule": grammar.rule,
        "Explanation": grammar.explanation,
        "Example": grammar.example,
        "Arabic": grammar.arabic,
        "Source": grammar.source,
    }


def check_model(modelName: str) -> bool:
    models = invoke("modelNames")
    return modelName in models


def natural_key_query(note: Verb | Vocab | Sentence | Grammar) -> str:
    # restrict to our own note-type so we never match notes from other decks/models
    if isinstance(note, Verb):
        return f'"note:{MODEL_NAME_VERB}" "Verb:{note.verb}" "Tense:{note.tense}"'
    if isinstance(note, Vocab):
        return f'"note:{MODEL_NAME_VOCAB}" "Transliteration:{note.transliteration}"'
    if isinstance(note, Sentence):
        return f'"note:{MODEL_NAME_SENTENCE}" "Topic:{note.topic}" "Order:{note.order}"'
    if isinstance(note, Grammar):
        return f'"note:{MODEL_NAME_GRAMMAR}" "Rule:{note.rule}"'
    raise ValueError(f"Unknown note type: {type(note)}")


def get_note_id(note: Verb | Vocab | Sentence | Grammar) -> list[int]:
    result = invoke("findNotes", query=natural_key_query(note))
    return result


def check_note(note: Verb | Vocab | Sentence | Grammar) -> bool:
    """True if a note with this natural key already exists."""
    return get_note_id(note) != []


def make_template(pronom: str) -> dict:
    return {
        "Name": f"Card {pronom}",
        "Front": f"""{{{{#Ask}}}}<div class="ask-flag">?</div>{{{{/Ask}}}}
            <div class="prompt">({{{{Meaning}}}})</div>
            <div class="tense">{pronom} — {{{{Tense}}}}</div>
            {{{{type:{pronom}}}}}""",
        "Back": f"""{{{{#Ask}}}}<div class="ask-flag">?</div>{{{{/Ask}}}}
            <div class="prompt">({{{{Meaning}}}})</div>
            <div class="tense">{pronom} — {{{{Tense}}}}</div>
            {{{{type:{pronom}}}}}
            <hr id="answer">
            <span class="translit">{{{{hint:Verb}}}}</span>
            {{{{#FormVariant}}}}
            <hr>
            <div class="forms">{{{{FormVariant}}}}</div>
            {{{{/FormVariant}}}}
            {{{{#Ask}}}}<div class="ask">{{{{Ask}}}}</div>{{{{/Ask}}}}""",
    }


def ensure_model(modelName: str, inOrderFields: list, cardTemplates: list):
    """Create the model if missing, otherwise update its CSS and templates
    so that SHARED_CSS / templates stay the source of truth for presentation."""
    if not check_model(modelName):
        logging.info(f"{modelName} model doesn't exist, creating...")
        invoke(
            "createModel",
            modelName=modelName,
            inOrderFields=inOrderFields,
            css=SHARED_CSS,
            isCloze=False,
            cardTemplates=cardTemplates,
        )
        return

    logging.info(f"{modelName} model exists, updating styling and templates...")
    invoke("updateModelStyling", model={"name": modelName, "css": SHARED_CSS})
    templates = {t["Name"]: {"Front": t["Front"], "Back": t["Back"]} for t in cardTemplates}
    invoke("updateModelTemplates", model={"name": modelName, "templates": templates})


def create_model_verb(modelName: str):
    ensure_model(
        modelName,
        INORDERFIELDS_VERB,
        [make_template(p) for p in PRONOUNS],
    )


def create_model_vocab(modelName: str):
    ensure_model(
        modelName,
        INORDERFIELDS_VOCAB,
        [
            {
                "Name": "Card VOCAB",
                "Front": """{{#Ask}}<div class="ask-flag">?</div>{{/Ask}}
                <div class="prompt">{{Meaning}}</div>""",
                "Back": """{{#Ask}}<div class="ask-flag">?</div>{{/Ask}}
                <div class="prompt">{{Meaning}}</div>
                <hr>
                <div class="translit">{{Transliteration}}</div>
                {{#Arabic}}<div class="arabic">{{Arabic}}</div>{{/Arabic}}
                {{#Feminine}}<div class="forms">féminin : {{Feminine}}</div>{{/Feminine}}
                {{#Dual}}<div class="forms">duel : {{Dual}}</div>{{/Dual}}
                {{#Plural}}<div class="forms">pluriel : {{Plural}}</div>{{/Plural}}
                {{#Source}}<div class="source">{{Source}}</div>{{/Source}}
                {{#Ask}}<div class="ask">{{Ask}}</div>{{/Ask}}""",
            }
        ],
    )


def create_model_sentence(modelName: str):
    ensure_model(
        modelName,
        INORDERFIELDS_SENTENCE,
        [
            {
                "Name": "Card SENTENCE",
                "Front": """{{#Ask}}<div class="ask-flag">?</div>{{/Ask}}
{{#Type}}<div class="badge">{{Type}}</div>{{/Type}}
<div class="sentence-tr">{{Meaning}}</div>""",
                "Back": """{{#Ask}}<div class="ask-flag">?</div>{{/Ask}}
{{#Type}}<div class="badge">{{Type}}</div>{{/Type}}
<div class="sentence-tr">{{Meaning}}</div>
<hr>
<div class="sentence">{{Transliteration}}</div>
{{#Arabic}}<div class="arabic">{{Arabic}}</div>{{/Arabic}}
{{#Source}}<div class="source">{{Source}}</div>{{/Source}}
{{#Ask}}<div class="ask">{{Ask}}</div>{{/Ask}}""",
            }
        ],
    )


def create_model_grammar(modelName: str):
    ensure_model(
        modelName,
        INORDERFIELDS_GRAMMAR,
        [
            {
                "Name": "Card GRAMMAR",
                "Front": """{{#Ask}}<div class="ask-flag">?</div>{{/Ask}}
<div class="rule">{{Rule}}</div>""",
                "Back": """{{#Ask}}<div class="ask-flag">?</div>{{/Ask}}
<div class="rule">{{Rule}}</div>
<hr>
<div class="explanation">{{Explanation}}</div>
{{#Example}}<div class="example">{{Example}}</div>{{/Example}}
{{#Arabic}}<div class="arabic">{{Arabic}}</div>{{/Arabic}}
{{#Source}}<div class="source">{{Source}}</div>{{/Source}}
{{#Ask}}<div class="ask">{{Ask}}</div>{{/Ask}}""",
            }
        ],
    )


def check_deck(deckName: str) -> bool:
    decks = invoke("deckNames")
    return deckName in decks


def create_deck(deckName: str):
    if check_deck(deckName):
        logging.info(f"{deckName} deck already exist")

    else:
        logging.info(f"{deckName} deck doesn't exist")
        logging.info("Creating...")
        invoke("createDeck", deck=deckName)
        logging.info("Deck created")


def add_notes_verb(verb: Verb, deckName: str, modelName: str) -> bool:
    params_addNote = {
        "note": {
            "deckName": deckName,
            "modelName": modelName,
            "fields": build_field_verb(verb),
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Default",
                    "checkChildren": False,
                    "checkAllModels": False,
                },
            },
            "tags": ["type::verb", f"verb::tense::{verb.tense}"],
        }
    }
    # verifier d'abord que la note existe ou pas
    if check_note(verb):
        logging.info(f"Note for {verb.verb} {verb.tense} already exist")
        return False
    else:
        logging.info(f"Creation of note for {verb.verb} {verb.tense} ")
        invoke("addNote", **params_addNote)
        return True
    # ensuite montrer toute les cartes qui vont etre crées


def add_notes_vocab(vocab: Vocab, deckName: str, modelName: str) -> bool:
    params_addNote = {
        "note": {
            "deckName": deckName,
            "modelName": modelName,
            "fields": build_field_vocab(vocab),
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Default",
                    "checkChildren": False,
                    "checkAllModels": False,
                },
            },
            "tags": ["type::vocab"],
        }
    }
    # verifier d'abord que la note existe ou pas
    if check_note(vocab):
        logging.info(f"Note for {vocab.transliteration} already exist")
        return False

    else:
        logging.info(f"Creation of note for {vocab.transliteration} ")
        invoke("addNote", **params_addNote)
        return True


def add_notes_sentence(sentence: Sentence, deckName: str, modelName: str) -> bool:
    params_addNote = {
        "note": {
            "deckName": deckName,
            "modelName": modelName,
            "fields": build_field_sentence(sentence),
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Default",
                    "checkChildren": False,
                    "checkAllModels": False,
                },
            },
            "tags": ["type::sentence"],
        }
    }
    # verifier d'abord que la note existe ou pas
    if check_note(sentence):
        logging.info(f"Note for {sentence.topic} - {sentence.order} already exist")
        return False

    else:
        logging.info(f"Creation of note for {sentence.topic} - {sentence.order} ")
        invoke("addNote", **params_addNote)
        return True


def add_notes_grammar(grammar: Grammar, deckName: str, modelName: str) -> bool:
    params_addNote = {
        "note": {
            "deckName": deckName,
            "modelName": modelName,
            "fields": build_field_grammar(grammar),
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Default",
                    "checkChildren": False,
                    "checkAllModels": False,
                },
            },
            "tags": ["type::grammar"],
        }
    }
    # verifier d'abord que la note existe ou pas
    if check_note(grammar):
        logging.info(f"Note for {grammar.rule} already exist")
        return False

    else:
        logging.info(f"Creation of note for {grammar.rule}")
        invoke("addNote", **params_addNote)
        return True


def build_fields(elem: Verb | Vocab | Sentence | Grammar) -> dict:
    """Dispatch to the right build_field_* according to the note type."""
    if isinstance(elem, Verb):
        return build_field_verb(elem)
    if isinstance(elem, Vocab):
        return build_field_vocab(elem)
    if isinstance(elem, Sentence):
        return build_field_sentence(elem)
    if isinstance(elem, Grammar):
        return build_field_grammar(elem)
    raise ValueError(f"Unknown note type: {type(elem)}")


def toUpdate(elem: Verb | Vocab | Sentence | Grammar) -> bool:
    """True if the existing note differs from the desired (CSV) state."""
    note_id = get_note_id(elem)
    if not note_id:
        return False  # no existing note -> not an update (it's a create)
    result = invoke("notesInfo", notes=note_id)
    actual_state = result[0]["fields"]
    desired_state = build_fields(elem)
    for field, desired_value in desired_state.items():
        actual_value = actual_state[field][
            "value"
        ]  # value level, not object comparison
        if actual_value != desired_value:
            return True
    return False


def updateNotefields(elem: Verb | Vocab | Sentence | Grammar):
    """Update an existing note in place (preserves SRS) if its content changed."""
    if toUpdate(elem):
        note_id = get_note_id(elem)
        params_updateNoteFields = {
            "note": {
                "id": note_id[0],
                "fields": build_fields(elem),
            }
        }
        invoke("updateNoteFields", **params_updateNoteFields)
