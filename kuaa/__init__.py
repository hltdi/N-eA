"""Ñe'ẽasa: Create simple bilingual lexicons and grammars for language pairs."""

__all__ = ['language', 'entry', 'ui', 'constraint', 'db', 'views', 'variable', 'sentence', 'cs', 'learn', 'utils']

from flask import Flask, url_for, render_template

from .sentence import *
from .learn import *
from .morphology import *
from . import db

## Instantiate the Flask class to get the application
app = Flask(__name__)
app.config.from_object(__name__)

def load(source='spa', target='grn'):
    """Load source and target languages for translation."""
    return kuaa.Language.load_trans(source, target)

def translate(sentence, source, target,
              all_sols=False, all_trans=True, interactive=False, verbosity=0):
    """Translate sentence from source to target language."""
#    s = kuaa.Sentence(raw=sentence, language=source, target=target)
    sentence.initialize(verbosity=verbosity)
    sentence.solve(translate=True,
                   all_sols=all_sols, all_trans=False, interactive=interactive, verbosity=verbosity)
    return sentence.get_complete_trans()

def make_document(source, target, text):
    """Create an Mbojereha document with the text."""
    d = kuaa.Document(source, target, text, True)
    return d

def quit():
    """Quit the program, cleaning up in various ways."""
    for language in Language.languages.values():
        # Store new cached analyses or generated forms for
        # each active language.
        language.quit()

import kuaa.views

