# Mainumby. Parsing and translation with minimal dependency grammars.
#
########################################################################
#
#   This file is part of the PLoGS project
#   for parsing, generation, translation, and computer-assisted
#   human translation.
#
#   Copyleft 2015, 2016, 2017, 2018, 2019 HLTDI, PLoGS <gasser@indiana.edu>
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
#    Sentence translations are added to document TextArea in sent.html.
# 2017.11
# -- Document TextArea gets cleared when "Salir" happens.
# 2018.01-03
# -- Comments in sent, error message for empty Doc in doc.
# 2018.07-08
# -- New GT-like interface: tra.html; OF_HTML, OM1
# 2019.03
# -- GUI class holds variables that used to be global. The one
#    global is the instance of GUI.

from flask import request, session, g, redirect, url_for, abort, render_template, flash
from kuaa import app, make_document, make_text, gui_trans, doc_trans, quit, start, get_human, create_human, sentence_from_textseg
from . import gui
from docx import Document

# Global variable and basic functions for the container holding all the gui-related variables that need to
# persist between calls to render_template()

GUI = None

def create_gui():
    global GUI
    print("$$Creating new GUI")
    GUI = gui.GUI(list_texts=True)

def end_gui():
    global GUI
    print("Ending GUI {}".format(GUI))
    if GUI:
        quit(GUI.session)
        GUI = None

def trad_doc():
    """Traducir todas las oraciones en el documento, devolviendo una lista
    de 'cadenas finales' de de cada oración."""
    return doc_trans(doc=GUI.doc, textid=GUI.textid, gui=GUI)

def solve(isdoc=False, choose=False, index=0, source=''):
    """Attempt to translate the currently selected sentence, assigning segmentation
    and HTML for the translation segmentation visualization. If choose is True,
    present no options in the HTML."""
    if choose:
        segmentation = gui_trans(GUI, choose=True)
        trans = segmentation.final
        GUI.init_sent(index, choose=True, isdoc=isdoc, trans=trans, source=source)
    else:
        GUI.segs, GUI.tra_seg_html = gui_trans(GUI, choose=False)
#    print("Solved segs: {}, html: {}".format(SEGS, SEG_HTML))
        GUI.init_sent(index, choose=False, isdoc=isdoc)
    if isdoc and not choose:
        GUI.update_doc(index, choose=choose)

@app.route('/', methods=['GET', 'POST'])
def index():
    print("In index...")
    return render_template('index.html')

@app.route('/acerca', methods=['GET', 'POST'])
def acerca():
    print("In acerca...")
    return render_template('acerca.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not GUI:
        create_gui()
    form = request.form
    print("Form for login: {}".format(form))
#    if not GUI.users_initialized:
#        init_users(GUI)
    if request.method == 'POST' and 'login' in form:
        # Try to find user with username username
        username = form.get('username')
        user = get_human(username)
        if not user:
            print("No such user as {}".format(username))
            return render_template('login.html', error='user')
        else:
            print("Found user {}".format(user))
            password = form.get('password')
            if user.check_password(password):
                GUI.user = user
                return render_template('logged.html', user=username)
            else:
                return render_template('login.html', error='password')
    return render_template('login.html')

@app.route('/logged', methods=['GET', 'POST'])
def logged():
    form = request.form
#    print("Form for logged: {}".format(form))
    return render_template('logged.html')

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    form = request.form
#    print("Form for reg: {}".format(form))
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
            user = create_human(form)
            print("Created user {}".format(user))
            GUI.user = user
            return render_template('acct.html', user=form.get('username'))
    return render_template('reg.html')

@app.route('/acct', methods=['POST'])
def acct():
#    print("In acct...")
    return render_template('acct.html')

# View for the window that does all the work. Whew.
@app.route('/tra', methods=['GET', 'POST'])
def tra():
    global GUI
    if not GUI:
        create_gui()
    form = request.form
#    print("**FORM DICT FOR tra.html (isdoc {}, modo {}, tradtodo {}, textid {}, text_html {})**".format(form.get('isdoc', None),
#                                                                                          form.get('modo', None),
#                                                                                          form.get('tradtodo', None),
#                                                                                          form.get('textid', None),
#                                                                                          ("+" if 'textid' in form and form['textid'] else '-')))
#    print("GUI props: {}".format(GUI.props))
#    if GUI.text_select_html:
#        print("GUI has text_select_html")
#    else:
#        print("GUI doesn't have text_select_html")
    if not GUI.source:
#        print("Ninguna lengua fuente")
        start(gui=GUI, use_anon=False, create_memory=False)
    # Translating document?
    isdoc = form.get('isdoc') == "true" or form.get('modo') == 'doc'
    if isdoc:
        print("TRANSLATING DOCUMENT")
        if GUI.doc:
            print("Document loaded")
        else:
            print("No document yet")
    else:
        print("TRANSLATING SENTENCE")
    # Initialize various window parameters
    GUI.set_props(form, ['ocultar', 'sinopciones', 'nocorr'], ['tfuente'])
    GUI.props['isdoc'] = isdoc
#    print("GUI props: {}".format(GUI.props))
    # Pick translation without offering options
    choose = GUI.props.get('sinopciones', False)
    username = GUI.user.username if GUI.user else ''
    tradtodo = form.get('tradtodo') == 'true'
    abandonar_doc = form.get('abandonardoc') == 'true'
    if abandonar_doc:
        print("Abandonando actual documento...")
        GUI.clear(isdoc=True)
    if 'ayuda' in form and form['ayuda'] == 'true':
        # Opened help window. Keep everything else as is.
        return render_template('tra.html', doc=isdoc, documento=GUI.doc_html, props=GUI.props, user=username,
                               choose=choose, tradtodo=tradtodo)
    # No document loaded from file or from DB
    no_doc = isdoc and not GUI.doc and not GUI.doc_html
    # No sentence entered in sentence UI
    no_ora = not isdoc and not 'ofuente' in form
#    print("nodoc {}, noora {}".format(no_doc, no_ora))
    if no_doc or no_ora and 'modo' in form and form['modo']:
#        print("modo in form: {}".format(form.get('modo')))
        # Mode (sentence vs. document) has changed
        isdoc = form.get('modo') == 'doc'
        if 'documento' in form and form['documento']:
            # A document has been loaded, make it into a Document object
            make_document(GUI, form['documento'], html=True)
#            print("PROCESANDO TEXTO EN ARCHIVO {}".format(GUI.doc))
            # Re-render, using HTML for Document
            return render_template('tra.html', documento=GUI.doc.html, doc=True, props=GUI.props, user=username,
                                   text_html=GUI.text_select_html,
                                   choose=choose, tradtodo=tradtodo)
        elif isdoc: # and form.get('docsrc') == 'almacén':
            # A Text object is to be loaded; create the text list and HTML
            textid = form.get('textid', '')
            if textid:
                print("Making text doc from text {}".format(textid))
                make_text(GUI, int(textid))
                return render_template('tra.html', documento=GUI.doc_html, doc=True, props=GUI.props, user=username,
                                       text_html=GUI.text_select_html,
                                       choose=choose, tradtodo=tradtodo)
            else:
                # Re-render, displaying domain/text dropdowns
#                print("DISPLAY DOMAINS")
                return render_template('tra.html', doc=True, props=GUI.props, text_html=GUI.text_select_html,
                                       user=username, choose=choose, tradtodo=tradtodo)
        else:
            # Clear the GUI and re-render, keeping the mode setting
            GUI.clear(isdoc=isdoc)
            return render_template('tra.html', doc=isdoc, props=GUI.props, user=username, choose=choose, tradtodo=tradtodo)
    if form.get('borrar') == 'true':
#        print("Clearing text, isdoc? {}, tradtodo {}".format(isdoc, tradtodo))
        record = form.get('registrar') == 'true'
        if record:
            trans = form.get('ometa')
#            print("Recording translation: {}".format(trans))
            GUI.clear(record=True, translation=trans, isdoc=True)
        else:
            GUI.clear(record=False, isdoc=isdoc, tradtodo=tradtodo)
            #, form.get('ometa'))
        # Start over with no current sentence or translation (translating sentence)
        GUI.props['tfuente'] = "120%"
        return render_template('tra.html', oracion=None, tra_seg_html=None, user=username, props=GUI.props,
                               documento=GUI.doc_html,
                               text_html=GUI.text_select_html, doc=isdoc, choose=choose, tradtodo=tradtodo)
    GUI.props['isdoc'] = isdoc
    if not 'ofuente' in form:
        # No sentence entered or selected
#        print("NO SENTENCE ENTERED")
        return render_template('tra.html', user=username, props=GUI.props, doc=isdoc, choose=choose, tradtodo=tradtodo)
    if not GUI.doc and not GUI.has_text:
        # Create a new document
        print("CREANDO NUEVO DOCUMENTO.")
        make_document(GUI, form['ofuente'], html=False)
        if len(GUI.doc) == 0:
#            print(" pero documento está vacío.")
            return render_template('tra.html', error=False, user=username, doc=isdoc, props=GUI.props,
                                   text_html=GUI.text_select_html, choose=choose, tradtodo=tradtodo)
    oindex = int(form.get('oindex', 0))
#    print("oindex {}".format(oindex))
    docscrolltop = form.get('docscrolltop', 0)
    if 'tacept' in form and form['tacept']:
        # A new translation to be added to the accepted sentence translations.
#        print("ACCEPTING NEW TRANSLATION {}".format(form['tacept']))
        GUI.accept_sent(oindex, form['tacept'])
        aceptado = GUI.doc_tra_acep_str
        return render_template('tra.html', oracion='', doc=True, tra_seg_html='', tra='', oindex=-1,
                               documento=GUI.doc_html, aceptado=aceptado,
                               user=username, props=GUI.props, choose=choose, tradtodo=tradtodo)
    if GUI.doc_tra_acep and GUI.doc_tra_acep[oindex]:
        error = "¡Ya aceptaste una traducción para esta oración; por favor seleccioná otra oración para traducir!"
        return render_template('tra.html', oracion='', doc=True, error=error, tra_seg_html='', tra='',
                               aceptado=GUI.doc_tra_acep_str, docscrolltop=docscrolltop,
                               documento=GUI.doc_html, user=username, props=GUI.props, choose=choose, tradtodo=tradtodo)
    if GUI.doc_tra_html and GUI.doc_tra_html[oindex]:
        # Find the previously generated translation
        tra_seg_html = GUI.doc_tra_html[oindex]
        tra = GUI.doc_tra[oindex]
#        print("Looking for previous translation... (oindex={}, isdoc={}, tra {})".format(oindex, isdoc, tra))
        # Highlight selected source sentence with segments
        GUI.update_doc(oindex, repeat=True)
#        print("SENTENCE at {} ALREADY TRANSLATED".format(oindex))
        return render_template('tra.html', oracion=GUI.fue_seg_html, tra_seg_html=tra_seg_html, tra=tra,
                               documento=GUI.doc_html, doc=True, oindex=oindex, docscrolltop=docscrolltop,
                               aceptado=GUI.doc_tra_acep_str, user=username, props=GUI.props,
                               choose=choose, tradtodo=tradtodo)
    
    # Here's where a sentence or a whole document gets translated
    if tradtodo:
        print("TRADUCIENDO EL DOCUMENTO ENTERO, documento: {}".format(GUI.doc))
#        sentences = doc_sentences(doc=GUI.doc, textid=GUI.textid, gui=GUI)
        all_trans = trad_doc()
#        print("Traducciones: {}".format(all_trans[:3]))
        doctrans = '\n'.join(all_trans)
        GUI.props['tfuente'] = '100%'
#        translations = ''
#        for sentence in sentences:
#            print("Translating sentence {}".format(sentence))
#            translation = gui_trans(GUI, choose=True, return_string=True, sentence=sentence)
#            translations += translations + "\n" + translation
        return render_template('tra.html', documento=GUI.doc_html, doc=True,
                               aceptado=doctrans, docscrolltop=docscrolltop, choose=True,
                               user=username, props=GUI.props, tradtodo=True)
    else:
        # Get the sentence, the only one in GUI.doc if isdoc is False.
        if GUI.has_text:
            # Make the sentence from the TextSeg object
            GUI.sentence = sentence_from_textseg(source=GUI.source, target=GUI.target,
                                                textid=GUI.textid, oindex=oindex)
        else:
            GUI.sentence = GUI.doc[oindex]
        print("ORACIÓN ACTUAL {}".format(GUI.sentence))
        print("isdoc {}".format(isdoc))
        # Translate and segment the sentence, assigning GUI.segs
        source = form.get('ofuente', '')
        solve(isdoc=isdoc, index=oindex, choose=choose, source=source)
        oracion = source if choose else GUI.fue_seg_html
        return render_template('tra.html', oracion=oracion, tra_seg_html=GUI.tra_seg_html, tra=GUI.tra,
                               documento=GUI.doc_html, doc=isdoc, oindex=oindex,
                               aceptado=GUI.doc_tra_acep_str, docscrolltop=docscrolltop, choose=choose,
                               user=username, props=GUI.props, tradtodo=False)

@app.route('/fin', methods=['GET', 'POST'])
def fin():
    form = request.form
    print("Form for fin: {}".format(form))
    modo = form.get('modo')
    end_gui()
    return render_template('fin.html', modo=modo)

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
