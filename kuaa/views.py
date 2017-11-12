# Mainumby. Parsing and translation with minimal dependency grammars.
#
########################################################################
#
#   This file is part of the HLTDI L^3 project
#   for parsing, generation, translation, and computer-assisted
#   human translation.
#
#   Copyleft 2015, 2016, 2017 HLTDI, PLoGS <gasser@indiana.edu>
#   
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#   
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#   
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# =========================================================================
#
# Created 2015.06.12
# 2015.07
# -- Views for loading languages, entering document, sentence, and translation.
# 2016.03
# -- sent view can either get new sentence or record translation for sentence segment.
# -- SESSION, SEGS, SEG_HTML globals added.
# 2016.04.03
# -- USER added; SESSION created only if there is one.
# 2016.04.05
# -- Login works.
# 2016.04.10
# -- Segment translation selections are added to sentence translation TextArea in sent.html.

from flask import request, session, g, redirect, url_for, abort, render_template, flash
from kuaa import app, make_document, load, seg_trans, quit, start, init_users, get_user, create_user

# Global variables for views; probably a better way to do this...
SESSION = SPA = GRN = DOC = SENTENCE = SEGS = SEG_HTML = USER = None
SINDEX = 0
USERS_INITIALIZED = False
# SOLINDEX = 0

def initialize():
    global USERS_INITIALIZED
    init_users()
    USERS_INITIALIZED = True

def init_session():
    global SESSION
    global GRN
    global SPA
    if not SPA:
        load_languages()
    # Load users and create session if there's a user
    if USER and not SESSION:
        SESSION = start(SPA, GRN, USER)

def load_languages():
    """Load Spanish and Guarani data."""
    global GRN, SPA
    SPA, GRN = load()

def make_doc(text):
    """Create a Document object from the text."""
    global DOC
    DOC = make_document(SPA, GRN, text, session=SESSION)

def get_sentence():
    global SINDEX
    global SENTENCE
    global DOC
    if SINDEX >= len(DOC):
        SENTENCE = None
        # Save DOC in database or translation cache here
        DOC = None
        SINDEX = 0
        return
    SENTENCE = DOC[SINDEX]
    SINDEX += 1

def solve_and_segment():
    global SEGS
    global SEG_HTML
    SEGS, SEG_HTML = seg_trans(SENTENCE, SPA, GRN)    

@app.route('/')
def index():
#    print("In index...")
    return redirect(url_for('base'))

@app.route('/base', methods=['GET', 'POST'])
def base():
#    print("In base...")
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    global USER
    form = request.form
    print("Form for login: {}".format(form))
    if not USERS_INITIALIZED:
        initialize()
    if request.method == 'POST' and 'login' in form:
        # Try to find user with username username
        username = form.get('username')
        user = get_user(username)
        if not user:
#            print("No such user as {}".format(username))
            return render_template('login.html', error='user')
        else:
#            print("Found user {}".format(user))
            password = form.get('password')
            if user.check_password(password):
                USER = user
                return render_template('logged.html', username=username)
            else:
#                print("Password doesn't match")
                return render_template('login.html', error='password')
    return render_template('login.html')

@app.route('/logged', methods=['GET', 'POST'])
def logged():
    form = request.form
#    print("Form for logged: {}".format(form))
    return render_template('logged.html')

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    global USER
    form = request.form
    print("Form for reg: {}".format(form))
    if request.method == 'POST' and 'username' in form:
        if form.get('cancel') == 'Cancelar':
            return render_template('login.html')
        elif not form.get('username'):
            return render_template('reg.html', error="username")
        elif not form.get('email'):
            return render_template('reg.html', error="email")
        elif form.get('password') != form.get('password2'):
            return render_template('reg.html', error="password")
        else:
            user = create_user(form)
#        print("Created user {}".format(user))
            USER = user
            return render_template('acct.html', username=form.get('username'))
    return render_template('reg.html')

@app.route('/acct', methods=['POST'])
def acct():
#    print("In acct...")
    return render_template('acct.html')

# View for document entry
@app.route('/doc', methods=['GET', 'POST'])
def doc():
    form = request.form
    print("Form for doc: {}".format(form))
#    print("SESSION {}, USER {}".format(SESSION, USER))
    # Initialize Session if there's a User and no Session
    if not SESSION:
        init_session()
    # Load Spanish and Guarani if they're not loaded.
#    if not SPA:
#        load_languages()
    return render_template('doc.html', user=USER)

# View for displaying parsed sentence and sentence translation and
# for recording translations selected/entered by user.
@app.route('/sent', methods=['GET', 'POST'])
def sent():
    form = request.form
    print("Form for sent: {}".format(form))
    if 'ayuda' in form and form['ayuda'] == 'true':
        # Opened help window. Keep everything else as is.
        raw = SENTENCE.raw if SENTENCE else None
        punc = SENTENCE.get_final_punc() if SENTENCE else None
        document = form.get('UTraDoc', '')
        return render_template('sent.html', sentence=SEG_HTML, raw=raw, punc=punc,
                               document=document, user=USER)
    if 'oratra' in form:
        # A sentence has been translated and the translation recorded.
        # Record the translation and the segment translations if any.
        translation = form.get('oratra')
        segments = form.get('fratra', '')
        document = form.get('UTraDoc', '')
        print("Registering sentence translation {} for {}".format(translation, SENTENCE))
        print(" Segment translations: {}".format(segments))
        print("Current document: {}".format(document))
        return render_template('sent.html', user=USER, document=document)
    if 'text' in form and not DOC:
        # Create a new document
        make_doc(form['text'])
        print("Created document {}".format(DOC))
    # Get the next sentence in the document, assigning SENTENCE
    get_sentence()
    print("Current sentence {}".format(SENTENCE))
    if not SENTENCE:
        # No more sentences, return to doc.html for a new document
        return render_template('doc.html', user=USER)
    else:
        # Translate and segment the sentence, assigning SEGS
        solve_and_segment()
        print("Solved and segmented")
    # Pass the sentence segmentation, the raw sentence, and the final punctuation to the page
    return render_template('sent.html', sentence=SEG_HTML, raw=SENTENCE.raw, document='',
                           record=SENTENCE.record, punc=SENTENCE.get_final_punc(), user=USER)

@app.route('/fin', methods=['POST'])
def fin():
#    print("In fin...")
    global SESSION
    global DOC
    global SENTENCE
    global SEGS
    global SEG_HTML
    global USER
    global SINDEX
    quit(SESSION)
    SESSION = DOC = SENTENCE = SEGS = SEG_HTML = USER = None
    SINDEX = 0
    return render_template('fin.html')

@app.route('/proyecto')
def proyecto():
    return render_template('proyecto.html')

@app.route('/uso')
def uso():
    return render_template('uso.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

# Not needed because this is in runserver.py.
if __name__ == "__main__":
    kuaa.app.run(host='0.0.0.0')
