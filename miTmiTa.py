#!/usr/bin/env python3

# Mainumby: Parsing and translation with minimal dependency grammars.
#
########################################################################
#
#   This file is part of the HLTDI L^3 project
#   for parsing, generation, translation, and computer-assisted
#   human translation.
#
#   Copyleft 2014, 2015, 2016, 2017; HLTDI, PLoGS <gasser@indiana.edu>
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

# 2017.4
# -- English->Amharic
# -- Split off from mainumby as miTmiTa.py

__version__ = 1.0

import iwqet

## shortcuts

def generate(language, stem, feats=None, pos='v'):
    if not feats:
        feats = iwqet.FeatStruct("[]")
    else:
        feats = iwqet.FeatStruct(feats)
    return language.generate(stem, feats, pos)

def solve1(sentence):
    """Solve; print and return solutions."""
    sentence.solve()
    output_sols(sentence)
    return sentence.solutions

def load1(lang='eng'):
    l = iwqet.Language.load_lang(lang)
    return l

def ea_doc(text, process=True):
    e = iwqet.Language.languages.get('eng')
    a = iwqet.Language.languages.get('amh')
    if not e:
        e, a = load_ea()
#        e = load1()
    d = iwqet.Document(e, a, text=text, proc=process)
    return d

def output_sols(sentence):
    """Show target outputs for all solutions for sentence."""
    for sol in sentence.solutions:
        print(sol.get_ttrans_outputs())

def load_ea(train=False):
    eng, amh = iwqet.load('eng', 'amh')
    return eng, amh

def ea_sentence(sentence, ambig=True, solve=False, user=None, segment=False,
                verbosity=0):
    e, a = load_ea()
    session = iwqet.start(e, a, user)
    d = iwqet.Document(e, a, sentence, True, session=session)
    s = d[0]
    s.initialize(ambig=ambig, verbosity=verbosity)
    if solve or segment:
        s.solve(all_sols=ambig)
        if s.solutions and segment:
            solution = s.solutions[0]
            solution.get_segs()
    return s

def ley_bidoc(init=True, train=True):
    d = eg_arch_doc("../LingData/EsGn/Corp/FromCarlos/ley4251_e0.txt",
                    ruta_meta="../LingData/EsGn/Corp/FromCarlos/ley4251_g0.txt")
    if init:
        d.initialize()
    if train:
        trainer = iwqet.Trainer(d)
        return trainer
    return d

def eg_doc(text, proc=True):
    e, g = cargar_eg()
    d = iwqet.Document(e, g, text, proc=proc)
    return d

def eg_arch_doc(ruta, proc=True, reinit=False, user=None, session=None,
                ruta_meta=None):
    """Crear un documento del contenido de un archivo."""
    e, g = cargar_eg(train=ruta_meta)
    session = session or iwqet.start(e, g, user)
    arch = open(ruta, encoding='utf8')
    texto = arch.read()
    if ruta_meta:
        arch_meta = open(ruta_meta, encoding='utf8')
        texto_meta = arch_meta.read()
        d = iwqet.Document(e, g, texto, proc=proc, reinitid=reinit, session=session,
                          biling=True, target_text=texto_meta)
    else:
        d = iwqet.Document(e, g, texto, proc=proc, reinitid=reinit, session=session)
    return d

def arch_doc(lengua, ruta, session=None, user=None, proc=False):
    """Crear un documento del contenido de un archivo, solo para análisis."""
    l = cargar(lengua)
    session = session or iwqet.start(l, None, user)
    arch = open(ruta, encoding='utf8')
    texto = arch.read()
    d = iwqet.Document(l, None, texto, proc=proc, session=session)
    return d

def usuario(username):
    return iwqet.User.users.get(username)

## Cargar una lengua, solo para análisis.
def cargar(lang='spa'):
    spa = iwqet.Language.load_lang(lang)
    return spa

if __name__ == "__main__":
    print("ወደ ሚጥሚጣ እንኳን ደህና መጡ! version {}\n".format(__version__))
