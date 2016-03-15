#   
#   Mbojereha languages: dictionaries of lexical/grammatical entries
#
########################################################################
#
#   This file is part of the Mbojereha project
#   for parsing, generation, translation, and computer-assisted
#   human translation.
#
#   Copyright (C) 2014, 2015, 2016 HLTDI <gasser@indiana.edu>
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

# 2014.02.09
# -- Created
# 2014.02.10
# -- Made entries a separate class.
# 2014.02.15
# -- Methods for serializing and deserializing languages (using YAML).
# 2014.03.24
# -- Words, lexemes, and classes are all in the same dictionary (self.words).
#    Lexemes start with %, classes with $.
# 2014.04.17
# -- Analysis and generation dicts for particular wordforms.
# 2014.04.30
# -- Eliminated entry types in lexicon other than Groups and forms.
# 2015.05.15
# -- Added morphology-related methods from ParaMorfo.
# 2015.06
# -- Updated group-reading methods.
# 2015.07.03
# -- Added abbreviations.
# 2015.09.26
# -- Groups with a particular key are ordered by the group priority method.
# 2016.01.10
# -- Group files can have comments (# at beginning of line only).
# 2016.02.29
# -- Group files can have features that are part of all entries (except those with the feature attribute specified).
# 2016.03.06
# -- Postprocessing dict for generation (e.g., ĝ -> g̃)

from .entry import *
from kuaa.morphology.morpho import Morphology, POS
from kuaa.morphology.semiring import FSSet, TOP

import os, yaml, re, copy

LANGUAGE_DIR = os.path.join(os.path.dirname(__file__), 'languages')

## Regexes for parsing language data
# Backup language abbreviation
# l...: 
BACKUP_RE = re.compile(r'\s*l.*?:\s*(.*)')
## preprocessing function
#PREPROC_RE = re.compile(r'\s*pre*?:\s*(.*)')
# Segments (characters)
# seg...: 
SEG_RE = re.compile(r'\s*seg.*?:\s*(.*)')
# Accent dictionary

ACC_RE = re.compile(r'\s*accent:\s*(.*)')
# Deaccent dictionary
# deaccent:
DEACC_RE = re.compile(r'\s*deaccent:\s*(.*)')
# Punctuation
# pun...: 
PUNC_RE = re.compile(r'\s*pun.*?:\s*(.*)')
# Part of speech categories
# pos: v verbo
POS_RE = re.compile(r'\s*pos:\s*(.*)\s+(.*)')
# Feature abbreviations
# ab...:
ABBREV_RE = re.compile(r'\s*ab.*?:\s*(.*)')
# Term translations
# tr...:
TRANS_RE = re.compile(r'\s*tr.*?:\s*(.*)')
# Beginning of feature-value list
FEATS_RE = re.compile(r'\s*feat.*?:\s*(.*)')
# Feature-value pair
FV_RE = re.compile(r'\s*(.*?)\s*=\s*(.*)')
# FV combinations, could be preceded by ! (= priority)
FVS_RE = re.compile(r'([!]*)\s*([^!]*)')
# Abbrev, with prefixes, and full name
ABBREV_NAME_RE = re.compile(r'([*%]*?)([^*%()]*?)\s*\((.*)\)\s*(\[.*\])?')
NAME_RE = re.compile(r'([*%]*)([^*%\[\]]*)\s*(\[.*\])?')
# Feature to be recorded in anal output; new 2015.03.10
# xf: g gender
# xf~: VOS voseo
EXPL_FEAT_RE = re.compile(r'\s*xf(.*):\s*(.*)\s*=\s*(.*)')
# Preprocessing: replace characters in first list with last char
# clean: â, ä = ã
CLEAN_RE = re.compile(r'\s*cle.*?:\s*(.*)\s*=\s*(.*)')
# postprocessing: ĝ = g̃
POSTPROC_RE = re.compile(r'\s*postproc.*?:\s*(.*)\s*=\s*(.*)')

## Regex for checking for non-ascii characters
ASCII_RE = re.compile(r'[a-zA-Z]')

## Separtes Morphosyn name from pattern and other attributes
MS_NAME_SEP = '::'

## Constants for language use
ANALYSIS = 0
GENERATION = 1
# translation
SOURCE = 2
TARGET = 3

## Strings used in groups file
GROUP_SEP = '***'
TRANS_START = '->'
HEAD_SEP = ';'

class Language:
    """Dictionaries of words, lexemes, grammatical features, and
    lexical classes."""

    languages = {}
    
    # Regular expressions for affix files
    pattern = re.compile('\s*pat.*:\s+(\w+)\s+(.+)')
    function = re.compile('\s*func.*:\s+(\w+)\s+(.+)')
    suffix = re.compile('\s*suf.*:\s+(\S+)(\s.+)?')   # a single space separates the suffix from the segmented form
    grammar = re.compile('\s*gram.*:\s+(\w+)\s+(.+)')
    POS = re.compile('\s*pos:\s+(\w+)')

    def __init__(self,
                 name, abbrev,
                 use=ANALYSIS,
#                 source=True, target=False,
#                 words=None, lexemes=None, grams=None, classes=None,
                 groups=None, groupnames=None,
#                 genforms=None,
                 # Added from morphology/language
                 pos=None, cache=True):
        """Initialize dictionaries and names."""
        self.name = name
        self.abbrev = abbrev
#        self.words = words or {}
#        self.forms = forms or {}
        self.groups = groups or {}
        # Explicit groups to load instead of default
        self.groupnames = groupnames
        self.ms = []
        self.use = use
#        self.source = source
#        self.target = target
        # Dict of groups with names as keys
        self.groupnames = {}
#        # Record possibilities for dependency labels, feature values, order constraints
#        self.possible = {}
        # Record whether language has changed since last loaded
        self.changed = False
        # For generation (target) language, a dictionary of morphologically generated words:
        # {lexeme: {(feat, val): {(feat, val): wordform,...}, ...}, ...}
#        if not source:
#        self.genforms = genforms or {}
        Language.languages[abbrev] = self
        ## 2015.5.15 Copied from morphology/language
        self.pos = pos or []
        # Dictionary of preprocessing character conversions
        self.clean = {}
        # Dictionary of postprocessing character conversions
        self.postproc = {}
        # Dictionary of suffixes and suffix sequences and what to do with them
        self.suffixes = {}
        self.accent = None
        self.deaccent = None
        # Dictionary of prefixes and prefix sequences and what to do with them
        self.prefixes = {}
 #       self.words = []
        self.punc = None
        self.seg_units = None
        # dict of POS: fst lists
        self.morphology = Morphology()
        self.morphology.directory = self.get_dir()
        self.morphology.language = self
        self.load_morpho_data()
        # Whether morphological data is loaded
        self.anal_loaded = False
        self.gen_loaded = False
        # Do this later
        self.load_morpho(use in (GENERATION, TARGET), False, False, False)
        # Categories (and other semantic features) of words and roots
        self.cats = {}
        self.read_cats()
        # List of abbreviations (needed for tokenization)
        self.abbrevs = []
        self.read_abbrevs()
        # Segmentation dicts
        self.segs = {}
        self.rev_segs = {}
        self.read_segs()
        # Cached entries read in when language is loaded if language will be used for analysis
        if use in (ANALYSIS, SOURCE):
            self.set_anal_cached()
        # Load groups now if not to be used for translation
        if use in (ANALYSIS,):
            self.read_groups(files=groupnames)

    def quit(self):
        """Do stuff when the program exits."""
        if self.use in (ANALYSIS, SOURCE):
            self.write_cache()
        if self.use in (GENERATION, TARGET):
            for pos in self.morphology.values():
                pos.quit()

    def __repr__(self):
        """Print name."""
        return '<<{}>>'.format(self.name)

    def is_punc(self, string):
        """Does the string consist of only punctuation characters?"""
        for char in string:
            if char not in self.morphology.punctuation:
                return False
        return True

    def ortho_clean(self, string):
        """Clean up orthographic variability."""
        for c, d in self.clean.items():
            if c in string:
                string = string.replace(c, d)
        return string

    @staticmethod
    def get_language_dir(abbrev):
        return os.path.join(LANGUAGE_DIR, abbrev)

    ### Methods copied from morphology/language
    def get_dir(self):
        """Where data for this language is kept."""
        return os.path.join(LANGUAGE_DIR, self.abbrev)

    def get_syn_dir(self):
        """Directory for .ms (MorphoSyn) files (at least)."""
        return os.path.join(self.get_dir(), 'syn')

    def get_fst_dir(self):
        return os.path.join(self.get_dir(), 'fst')

    def get_lex_dir(self):
        return os.path.join(self.get_dir(), 'lex')

    def set_anal_cached(self):
        self.cached = {}
        self.read_cache()
        # New analyses since language loaded,
        # each entry a wordform and list of (root, FS) analyses
        self.new_anals = {}

    def get_cache_dir(self):
        """Directory with cached analyses."""
        return os.path.join(self.get_dir(), 'cache')

    def get_group_dir(self):
        """Directory with group files."""
        return os.path.join(self.get_dir(), 'grp')

    def get_ms_file(self, target_abbrev):
        d = self.get_syn_dir()
        return os.path.join(d, target_abbrev + '.ms')

    def get_cache_file(self, name=''):
        d = self.get_cache_dir()
        if name == True or not name:
            name = self.abbrev
#        name = name or self.abbrev
        return os.path.join(d, name + '.cch')

    def get_sem_file(self, name=''):
        d = self.get_lex_dir()
        if name == True or not name:
            name = 'sem'
        return os.path.join(d, name + '.lex')

    def get_abbrev_file(self, name=''):
        d = self.get_lex_dir()
        if name == True or not name:
            name = 'abr'
        return os.path.join(d, name + '.lex')

    def get_group_files(self, names=None):
        d = self.get_group_dir()
        if not names:
            if self.morphology:
                # POS abbreviations
                names = ['misc'] + list(self.morphology.keys())
            else:
                names = [self.abbrev]
        paths = [os.path.join(d, name + '.grp') for name in names]
        return [path for path in paths if os.path.exists(path)]

    def get_seg_file(self):
        """Pathname for file containing segmentable forms, e.g., del, they're."""
        d = self.get_lex_dir()
        return os.path.join(d, 'seg.lex')

    def add_new_anal(self, word, anals):
        self.new_anals[word] = anals

    def read_cats(self):
        file = self.get_sem_file()
        try:
            with open(file, encoding='utf8') as f:
                for line in f:
                    form, sem = line.strip().split()
                    self.cats[form] = sem.split(',')
        except IOError:
            pass
#            print("El archivo semántico {} no existe".format(file))

    def get_cats(self, form):
#        print("Getting cats for {}".format(form))
        return self.cats.get(form, [])

    def read_abbrevs(self):
        """Read in abbreviations from abr file."""
        file = self.get_abbrev_file()
        try:
            with open(file, encoding='utf8') as f:
                for line in f:
                    self.abbrevs.append(line.strip())
        except IOError:
            pass
#            print("El archivo de abreviaturas {} no existe".format(file))

    def read_segs(self):
        """Read in segmentations from seg file."""
        file = self.get_seg_file()
        try:
            with open(file, encoding='utf8') as f:
                for line in f:
                    form, seg = line.split('=')
                    form = form.strip()
                    seg = seg.strip()
                    if self.use in [ANALYSIS, SOURCE]:
                        self.segs[form] = seg.split()
                    if self.use in [GENERATION, TARGET]:
                        self.rev_segs[seg] = form
        except IOError:
            print('El archivo de de segmentaciones {} no existe'.format(file))

    def write_cache(self, name=''):
        """Write a dictionary of cached entries to a cache file."""
        if self.new_anals:
            # Only attempt to cache analyses if there are new ones.
            file = self.get_cache_file(name=name)
            with open(file, 'a', encoding='utf8') as out:
                for word, analyses in self.new_anals.items():
                    if not analyses:
                        # The word is unanalyzed
                        print("{} || {}:".format(word, word), file=out)
                    # analyses is a list of root, fs pairs
#                    if len(analyses) == 1 and analyses[0][0] == word and not analyses[0][1]:
#                        # The word is unanalyzed
#                        print("{}:[]".format(word), file=out)
                    else:
                        anals = ["{}:{}".format(r, f.__repr__() if f else '') for r, f in analyses]
                        anals = ';'.join(anals)
                        print("{} || {}".format(word, anals), file=out)
        # Empty new_anals in case we want to add things later
        self.new_anals.clear()

    def read_cache(self, name='', expand=False):
        """Read cached entries into self.cached from a file.
        Modified 2015/5/17 to include Mbojereha categories."""
        cache = self.get_cache_file(name=name)
        try:
            with open(cache, encoding='utf8') as f:
#                print("Leyendo archivo almacenado")
                for line in f:
                    split_line = line.strip().split(" || ")
                    word, analyses = split_line
                    analyses = analyses.split(';')
                    anals = [a.split(':') for a in analyses]
                    alist = []
                    for r, a in anals:
                        if expand:
                            a = FeatStruct(a, freeze=True)
                        alist.append({'root': r, 'features': a})
                    if not expand:
                        # Put False at the front of the list to show that it hasn't been expanded
                        alist.insert(0, False)
                    self.cached[word] = alist
        except IOError:
            print('No such cache file as {}'.format(cache))

    def get_cached_anal(self, word, expand=True):
        """Return a list of dicts, one for each analysis of the word, or None."""
        entries = self.cached.get(word, None)
        if entries and expand and entries[0] is False:
            for entry in entries[1:]:
                feat = entry.get('features')
                if feat:
                    entry['features'] = FeatStruct(entry['features'], freeze=True)
                    pos = entry['features'].get('pos', '')
                    entry['root'] = Language.make_root(entry['root'], pos)
            self.cached[word] = entries[1:]
            return copy.deepcopy(entries[1:])
        return copy.deepcopy(entries)
    
    @staticmethod
    def make_char_string(chars):
        """Used in making list of seg units for language."""
        non_ascii = []
        for char in chars:
            if not ASCII_RE.match(char):
                non_ascii.append(char)
        non_ascii.sort()
        non_ascii_s = ''.join(non_ascii)
        return r'[a-zA-Z' + non_ascii_s + r']'

    @staticmethod
    def make_seg_units(segs):
        """Convert a list of segments to a seg_units list + dict."""
        singletons = []
        dct = {}
        for seg in segs:
            c0 = seg[0]
            if c0 in dct:
                dct[c0].append(seg)
            else:
                dct[c0] = [seg]
        for c0, segs in dct.items():
            if len(segs) == 1 and len(segs[0]) == 1:
                singletons.append(c0)
        for seg in singletons:
            del dct[seg]
        singletons.sort()
        return [singletons, dct]

    def load_morpho_data(self):
        """Load morphological data from .mrf file."""
        path = os.path.join(self.get_dir(), self.abbrev + '.mrf')
        if not os.path.exists(path):
            print("No existe archivo morfológico para {}".format(self.name))
            return
        print('Cargando datos morfológicos para {}'.format(self.name))
        with open(path, encoding='utf8') as data:
            contents = data.read()
            lines = contents.split('\n')[::-1]
#            lines = contents.split('\n')

            seg = []
            punc = []
            abbrev = {}
            fv_abbrev = {}
            trans = {}
            fv_dependencies = {}
            fv_priorities = {}
            fullpos = {}

            excl = {}
            feats = {}
            lex_feats = {}
            true_explicit = {}
            explicit = {}

            chars = ''

            current = None

            current_feats = []
            current_lex_feats = []
            current_excl = []
            current_abbrev = {}
            current_fv_abbrev = []
            current_fv_priority = []
            current_explicit = []
            current_true_explicit = []
            current_fv_dependencies = {}

            complex_feat = False
            current_feat = None
            current_value_string = ''
            complex_fvs = []

            while lines:

                line = lines.pop().split('#')[0].strip() # strip comments

                # Ignore empty lines
                if not line: continue

                # Beginning of segmentation units
                m = SEG_RE.match(line)
                if m:
                    current = 'seg'
                    seg = m.group(1).split()
                    continue

                m = ACC_RE.match(line)
                if m:
                    acc = m.group(1).split(',')
                    self.accent = {}
                    for c in acc:
                        u, a = c.split(':')
                        self.accent[u.strip()] = a.strip()
                    continue

                m = DEACC_RE.match(line)
                if m:
                    deacc = m.group(1).split(',')
                    self.deaccent = {}
                    for c in deacc:
                        a, u = c.split(':')
                        self.deaccent[a.strip()] = u.strip()
                    continue

#                m = LG_NAME_RE.match(line)
#                if m:
#                    name = m.group(1).strip()
#                    self.name = name
#                    continue

                m = PUNC_RE.match(line)
                if m:
                    current = 'punc'
                    punc = m.group(1).split()
                    continue

                m = TRANS_RE.match(line)
                if m:
                    current = 'trans'
                    w_g = m.group(1).split()
                    if '=' in w_g:
                        w, g = w_g.split('=')
                        # Add to the global TDict
                        Language.T.add(w.strip(), g.strip(), self.abbrev)
                    continue

                m = CLEAN_RE.match(line)
                if m:
                    dirty, clean = m.groups()
                    for d in dirty.split(','):
                        d = d.strip()
                        self.clean[d] = clean
                    continue

                m = POSTPROC_RE.match(line)
                if m:
                    dirty, clean = m.groups()
                    for d in dirty.split(','):
                        d = d.strip()
                        self.postproc[d] = clean
                    continue

                m = FEATS_RE.match(line)
                if m:
                    current = 'feats'
                    continue

                if current == 'feats':
                    m = POS_RE.match(line)
                    if m:
                        pos, fullp = m.groups()
                        pos = pos.strip()
                        fullp = fullp.strip()
                        self.pos.append(pos)
#                        print("Reading features for {}".format(pos))
                        current_feats = []
                        current_abbrev = {}
                        current_fv_abbrev = []
                        current_fv_priority = []
                        current_explicit = []
                        current_true_explicit = []
                        current_fv_dependencies = {}
                        feats[pos] = current_feats
                        abbrev[pos] = current_abbrev
                        fv_abbrev[pos] = current_fv_abbrev
                        fv_priorities[pos] = current_fv_priority
                        explicit[pos] = current_explicit
                        true_explicit[pos] = current_true_explicit
                        fullpos[pos] = fullp
                        fv_dependencies[pos] = current_fv_dependencies
                        continue

                    m = ABBREV_RE.match(line)
                    if m:
                        abb_sig = m.group(1).strip()
#                        print(" Current abbrev {}, adding {}".format(current_abbrev, abb_sig))
                        if '=' in abb_sig:
                            abb, sig = abb_sig.split('=')
                            current_abbrev[abb.strip()] = sig.strip()
                        continue

                    m = EXPL_FEAT_RE.match(line)
                    # Feature to include in pretty output
                    if m:
                        opt, fshort, flong = m.groups()
                        fshort = fshort.strip()
                        opt = opt.strip()
                        current_abbrev[fshort] = flong.strip()
                        current_explicit.append(fshort)
                        if opt and opt == '~':
                            current_true_explicit.append(fshort)
                        continue

                    m = FV_RE.match(line)
                    if m:
                        # A feature and value specification
                        feat, val = m.groups()
                        if '+' in feat or '-' in feat:
                            # Expansion for a set of boolean feature values
                            # See if there's a ! (=priority) prefix
                            m2 = FVS_RE.match(feat)
                            priority, fvs = m2.groups()
                            # An abbreviation for one or more boolean features with values
                            fvs = fvs.split(',')
                            fvs = [s.strip() for s in fvs]
                            fvs = [s.split('=') if '=' in s else [s[1:], (True if s[0] == '+' else False)] for s in fvs]
                            current_fv_abbrev.append((fvs, val))
                            if priority:
                                current_fv_priority.append(fvs)
                        elif '=' in val:
                            # Complex feature (with nesting)
                            complex_feat = self.proc_feat_string(feat, current_abbrev, current_excl, current_lex_feats,
                                                                 current_fv_dependencies)
                            vals = val.split(';')
                            for fv2 in vals:
                                fv2 = fv2.strip()
                                if fv2:
                                    m2 = FV_RE.match(fv2)
                                    if m2:
                                        feat2, val2 = m2.groups()
                                        f = self.proc_feat_string(feat2, current_abbrev, current_excl, current_lex_feats,
                                                                  current_fv_dependencies)
                                        v = self.proc_value_string(val2, f, current_abbrev, current_excl,
                                                                   current_fv_dependencies)
                                        complex_fvs.append((f, v))
                            if len(vals) == 1:
                                current_feats.append((complex_feat, complex_fvs))
                                complex_feat = None
                                complex_fvs = []

                        else:
                           fvs = line.split(';')
                           if len(fvs) > 1:
                               # More than one feature-value pair (or continuation)
                               if not complex_feat:
                                   complex_feat = current_feat
                               for fv2 in fvs:
                                   fv2 = fv2.strip()
                                   if fv2:
                                       m2 = FV_RE.match(fv2)
                                       if m2:
                                           # A single feature-value pair
                                           feat2, val2 = m2.groups()
                                           f = self.proc_feat_string(feat2, current_abbrev, current_excl, current_lex_feats,
                                                                     current_fv_dependencies)
                                           v = self.proc_value_string(val2, f, current_abbrev, current_excl,
                                                                      current_fv_dependencies)
                                           complex_fvs.append((f, v))
                           elif complex_feat:
                               # A single feature-value pair
                               f = self.proc_feat_string(feat, current_abbrev, current_excl, current_lex_feats,
                                                         current_fv_dependencies)
                               v = self.proc_value_string(val, f, current_abbrev, current_excl,
                                                          current_fv_dependencies)
                               complex_fvs.append((f, v))
                               current_feats.append((complex_feat, complex_fvs))
                               complex_feat = None
                               complex_fvs = []
                           else:
                               # Not a complex feature
                               current_feat = self.proc_feat_string(feat, current_abbrev, current_excl, current_lex_feats,
                                                                    current_fv_dependencies)
                               current_value_string = ''
                               val = val.strip()
                               if val:
                                   # The value is on this line
                                   # Split the value by |
                                   vals = val.split('|')
                                   vals_end = vals[-1].strip()
                                   if not vals_end:
                                       # The line ends with | so the value continues
                                       current_value_string = val
                                   else:
                                       v = self.proc_value_string(val, current_feat, current_abbrev, current_excl,
                                                                  current_fv_dependencies)
                                       current_feats.append((current_feat, v))
                    else:
                        # Just a value
                        val = line.strip()
                        current_value_string += val
                        # Split the value by | to see if it continues
                        vals = val.split('|')
                        if vals[-1].strip():
                            v = self.proc_value_string(current_value_string, current_feat, current_abbrev, current_excl,
                                                       current_fv_dependencies)
                            current_feats.append((current_feat, v))
                            current_value_string = ''

#                       # Handle other cases later
#                        continue

                elif current == 'seg':
                    seg.extend(line.strip().split())

                elif current == 'punc':
                    punc.extend(line.strip().split())

                elif current == 'pos':
                    pos.extend(line.strip().split())

                elif current == 'trans':
                    wd, gls = line.strip().split('=')
                    # Add to the global TDict
#                    print('Need to add {}: {} to global TDict'.format(wd.strip(), gls.strip()))
#                    Language.T.add(wd.strip(), gls.strip(), self.abbrev)

                else:
                    print("Warning: can't interpret line in .mrf file: {}".format(line))
#                    raise ValueError("bad line: {}".format(line))

            if punc:
                # Make punc list into a string
                self.punc = ''.join(punc)

            if seg:
                # Make a bracketed string of character ranges and other characters
                # to use for re
                chars = ''.join(set(''.join(seg)))
                chars = Language.make_char_string(chars)
                # Make the seg_units list, [chars, char_dict], expected for transduction,
                # composition, etc.
                self.seg_units = Language.make_seg_units(seg)

        if self.pos and not self.morphology:
#            print("Creating morphology...")
            for p in self.pos:
#                print(" Creating {}".format(p))
                self.morphology[p] = POS(p, self, fullname=fullpos[p])
                self.morphology[p].abbrevs = abbrev[p]
                self.morphology[p].fv_abbrevs = fv_abbrev[p]
                self.morphology[p].fv_priority = fv_priorities[p]
                self.morphology[p].true_explicit_feats = true_explicit[p]
                self.morphology[p].explicit_feats = explicit[p]
                self.morphology[p].feat_list = feats[p]
                self.morphology[p].make_rev_abbrevs()

    def proc_feat_string(self, feat, abbrev_dict, excl_values, lex_feats, fv_dependencies):
        prefix = ''
        depend = None
        m = ABBREV_NAME_RE.match(feat)

        if m:
            prefix, feat, name, depend = m.groups()
            abbrev_dict[feat] = name
        else:
            m = NAME_RE.match(feat)
            prefix, feat, depend = m.groups()

        # * means that the feature's values are not reported in analysis output
        if '*' in prefix:
            excl_values.append(feat)
        # % means that the feature is lexical
        if '%' in prefix:
            lex_feats.append(feat)

        if depend:
            # Feature and value that this feature value depends on
            # Get rid of the []
            depend = depend[1:-1]
            # Can be a comma-separated list of features
            depends = depend.split(',')
            for index, dep in enumerate(depends):
                dep_fvs = [fvs.strip() for fvs in dep.split()]
                if dep_fvs[-1] == 'False':
                    dep_fvs[-1] = False
                elif dep_fvs[-1] == 'True':
                    dep_fvs[-1] = True
                elif dep_fvs[-1] == 'None':
                    dep_fvs[-1] = None
                depends[index] = dep_fvs
            fv_dependencies[feat] = depends

        return feat

    def proc_value_string(self, value_string, feat, abbrev_dict, excl_values, fv_dependencies):
        '''value_string is a string containing values separated by |.'''
        values = [v.strip() for v in value_string.split('|')]
        res = []
        prefix = ''
        for value in values:
            if not value:
                continue
            if value == '+-':
                res.extend([True, False])
            else:
                m = ABBREV_NAME_RE.match(value)
                if m:
                    prefix, value, name, depend = m.groups()
                    abbrev_dict[value] = name
                else:
                    m = NAME_RE.match(value)
                    prefix, value, depend = m.groups()

                value = value.strip()

                if value == 'False':
                    value = False
                elif value == 'True':
                    value = True
                elif value == 'None':
                    value = None
                elif value == '...':
                    value = FeatStruct('[]')
                elif value.isdigit():
                    value = int(value)

                if '*' in prefix:
                    excl_values.append((feat, value))

                if depend:
                    # Feature and value that this feature value depends on
                    depend = depend[1:-1]
                    dep_fvs = [fvs.strip() for fvs in depend.split()]
                    if dep_fvs[-1] == 'False':
                        dep_fvs[-1] = False
                    elif dep_fvs[-1] == 'True':
                        dep_fvs[-1] = True
                    elif dep_fvs[-1] == 'None':
                        dep_fvs[-1] = None
                    elif dep_fvs[-1] == '...':
                        dep_fvs[-1] = FeatStruct('[]')
                    fv_dependencies[(feat, value)] = dep_fvs

                res.append(value)
        return tuple(res)

    def load_morpho(self, generate=False, segment=False, guess=True, verbose=False):
        """Load words and FSTs for morphological analysis and generation."""
        if verbose:
            print('Loading morphological data for {} {}'.format(self.name, "(gen)" if generate else "(anal)"))
        # Load pre-analyzed words
        self.set_analyzed()
        self.set_suffixes(verbose=verbose)
        self.morphology.set_words()
        for pos in self.morphology:
            posmorph = self.morphology[pos]
            # Load pre-analyzed words if any
            posmorph.set_analyzed()
            if generate:
#                posmorph.make_generated()
                posmorph.read_gen_cache()
            # Load FST
            posmorph.load_fst(generate=generate, guess=guess, segment=segment,
                              verbose=verbose)
            # Do others later
        if generate:
            self.gen_loaded = True
        else:
            self.anal_loaded = True

        return True

    def load_gen(self, verbose=False):
        """Just load the generation FSTs."""
        if self.gen_loaded:
            return
        print('Loading morphological generation data for {}'.format(self.name))
        self.gen_loaded = True
        for pos in self.morphology:
            self.morphology[pos].make_generated()
            # Load FST
            self.morphology[pos].load_fst(generate=True, guess=False, segment=False,
                                          verbose=verbose)

    def set_analyzed(self, filename='analyzed.lex', verbose=False):
        '''Set the dict of analyzed words, reading them in from a file, one per line.'''
        path = os.path.join(self.get_lex_dir(), filename)
        if os.path.exists(path):
            file = open(path, encoding='utf8')
            if verbose:
                print('Storing pre-analyzed forms')
            for line in file:
                # Word and FS separated by two spaces
                word, anal = line.split('  ')
                fs = FSSet.parse(anal.strip())
                self.analyzed[word] = fs
            file.close()

    def set_suffixes(self, filename='suf.lex', verbose=False):
        '''Set the dict of suffixes that can be stripped off.'''
        path = os.path.join(self.get_lex_dir(), filename)
        if os.path.exists(path):
            if verbose:
                print("Loading suffixes from {}".format(path))
            
            # Make 'v' the default POS
            current_pos = 'v'
            current_suffix = None
            current_attribs = None
            functions = {}
            patterns = {}
            grams = {}

            with open(path, encoding='utf8') as file:
                for line in file:
                    line = line.split('#')[0].strip() # strip comments

                    if not line:
                        continue

                    m = Language.pattern.match(line)
                    if m:
                        patname = m.group(1)
                        regex = m.group(2)
#                        print("Pattern {} with regex {}".format(patname, regex))
                        patterns[patname] = re.compile(regex)
                        continue
                    m = Language.POS.match(line)
                    if m:
                        current_pos = m.group(1)
                        continue
                    m = Language.grammar.match(line)
                    if m:
                        gname = m.group(1)
                        fs = m.group(2)
#                        print("Grammar pattern {} with FS {}".format(fname, fs))
                        grams[gname] = FSSet.parse(fs)
                        continue
                    m = Language.function.match(line)
                    if m:
                        name = m.group(1)
                        args = m.group(2)
                        lg_arg = "lg=self, "
                        curry = "kuaa.morphology.strip.sub_curry("
                        call = curry + lg_arg + args + ")"
                        function = eval(call)
                        functions[name] = function
                        continue
                    m = Language.suffix.match(line)
                    if m:
                        if current_suffix:
                            if current_suffix in self.suffixes:
                                self.suffixes[current_suffix].extend(current_attribs)
                            else:
                                self.suffixes[current_suffix] = current_attribs
                        current_suffix = m.group(1)
                        current_attribs = m.group(2)
                        if current_attribs:
                            current_attribs = [current_attribs.strip()]
                        else:
                            current_attribs = []
                        continue
                    if current_suffix:
                        # This line represents a dict of suffix attribs for a particular case
                        # ; separate different attribs
                        attrib_dict = {}
                        suff_attribs = line.split(';')
                        for attrib in suff_attribs:
                            # We need partition instead of split because there
                            # can be other = to the right in a feature-value expression
                            typ, x, value = attrib.strip().partition('=')
                            if typ == 'pat':
                                if value not in patterns:
                                    print("Pattern {} not in pattern dict".format(value))
                                else:
                                    value = patterns[value]
                            elif typ == 'change':
                                if value not in functions:
                                    print("Function {} not in function dict".format(value))
                                else:
                                    value = functions[value]
                            elif typ == 'gram':
                                if value in grams:
                                    value = grams[value]
                                else:
                                    value = FSSet.parse(value)
                            attrib_dict[typ] = value
                        if 'pos' not in attrib_dict:
                            attrib_dict['pos'] = current_pos
                        current_attribs.append(attrib_dict)
                if current_suffix:
                    # Current suffix attribs not yet added to suffixes
                    if current_suffix in self.suffixes:
                        self.suffixes[current_suffix].extend(current_attribs)
                    else:
                        self.suffixes[current_suffix] = current_attribs

    def strip_suffixes(self, word, guess=False, segment=False, verbose=False, pretty=False):
        '''Check to see if the word can be directly segmented into a stem and one or more suffixes.'''
        if self.suffixes:
            result = []
            stripped = kuaa.morphology.strip.sufstrip(word, self.suffixes)
            if stripped:
                for segs, gram, anal in stripped:
                    if anal:
                        # 'segs' needs to be analyzed further
                        # First separate the stem from segs and find the POS
                        stem, x, suffixes = segs.partition('+')
                        # There may be a category name for pretty output
                        suffixes, x, sufcat = suffixes.partition(' ')
                        # Now use the anal FST for that POS to transduce the stem starting
                        # from the grammatical FSSet as an initial weight
                        fst = self.morphology[anal].get_fst(generate=False, guess=guess, segment=segment)
                        anals = fst.transduce(stem, seg_units=self.seg_units, reject_same=guess,
                                              init_weight=gram)
                        if not anals:
                            continue
                        # Return each root and FS combination, as expected by language.anal_word()
                        for root, anls in anals:
                            for a in anls:
                                if pretty:
                                    a = self.morphology[anal].fs2prettylist(a)
                                    if sufcat:
                                        a.append((sufcat, suffixes))
                                        result.append([root, self.morphology[anal].fullname, a])
                                    else:
                                        result.append([root + '+' + suffixes, self.morphology[anal].fullname, a])
                                else:
                                    result.append([root + '+' + suffixes, a])
                    else:
                        if pretty:
                            gram = self.morphology[anal].fs2pretty(gram)
                        result.append([segs, gram])
            return result

    def anal_word(self, word, guess=True, only_guess=False, segment=False, 
                  root=True, stem=True, citation=True, gram=True,
                  # Whether to return a pretty list of feature values
                  # (doesn't work within Mbojereha yet)
                  pretty=False,
                  # Whether to return empty analyses / all analyses
                  unanal=False, get_all=True,
                  to_dict=False, preproc=False, postproc=False,
                  # Whether to cache new entries
                  cache=True,
                  no_anal=None,
                  string=False, print_out=False,
                  rank=True, report_freq=True, nbest=100,
                  only_anal=False,
                  verbosity=0):
        '''Analyze a single word, trying all existing POSs, both lexical and guesser FSTs.'''
        # Before anything else, check to see if the word is in the list of words that
        # have failed to be analyzed
        if no_anal != None and word in no_anal:
            return None
        # Next clean up using character conversion dict
        for d, c in self.clean.items():
            if d in word:
                word = word.replace(d, c)
        analyses = []
        to_cache = [] if cache else None
        # See if the word is cached (before preprocessing/romanization)
        cached = self.get_cached_anal(word)
        if cached:
            if verbosity:
                print("Found {} in cached analyses".format(word))
            if not pretty:
                analyses = cached
            else:
                analyses = self.prettify_analyses(cached)
            return analyses
        form = word
        # Try stripping off suffixes
        suff_anal = self.strip_suffixes(form, pretty=pretty)
        if suff_anal:
            analyses.extend(suff_anal)
            if cache and not pretty:
                to_cache.extend(suff_anal)

        if not analyses or get_all:
            if not only_guess:
                for pos, POS in self.morphology.items():
                    #... or already analyzed within a particular POS
                    preanal = POS.get_analyzed(form, sep_anals=True, pretty=pretty)
                    if preanal:
                        analyses.extend(preanal)
                        if cache and not pretty:
                            to_cache.extend(preanal)
                if not analyses or get_all:
                    if not only_guess:
                        # We have to really analyze it; first try lexical FSTs for each POS
                        for pos, POS in self.morphology.items():
                            analysis = POS.analyze(form, segment=segment,
                                                   to_dict=to_dict, sep_anals=True, pretty=pretty)
                            if analysis:
                                analyses.extend(analysis)
                                if cache and not pretty:
                                    to_cache.extend(analysis)
                    # If nothing has been found, try guesser FSTs for each POS
                    if not analyses and guess:
                        # Accumulate results from all guessers
                        for pos, POS in self.morphology.items():
                            analysis = POS.analyze(form, guess=True, segment=segment,
                                                   to_dict=to_dict, sep_anals=True, pretty=pretty)
                            if analysis:
                                analyses.extend(analysis)
                                if cache and not pretty:
                                    to_cache.extend(analysis)

        if cache and not pretty:
            # Cache new analyses
            self.add_new_anal(word, to_cache)

        return self.dictify_analyses(analyses)

    def dictify_analyses(self, anals):
        """Convert a list of (root, FS) analyses to a list of dicts,
        and convert roots to _ form."""
        dicts = []
        for root, anal in anals:
            pos = anal.get('pos', '')
            dicts.append({'root': Language.make_root(root, pos), 'features': anal})
        return dicts

    @staticmethod
    def make_root(root, pos):
        """Add the _ expected for roots."""
        if '_' not in root:
#        if root[-1] != '_':
            root = root + '_' + pos
        return root

    def prettify_analyses(self, anals):
        a = []
        for root, fs in anals:
            pos = fs.get('pos')
            posmorph = self.morphology.get(pos)
            a.append((root, posmorph.fullname, posmorph.fs2prettylist(fs)))
        return a

#    def gen(self, root, features=None, pos=None, guess=False, roman=True):
#        '''Generate a word, given stem/root and features (replacing those in default).
#        If pos is specified, check only that POS; otherwise, try all in order until one succeeeds.
#
#        @param root:     string (roman); root or stem of a word
#        @param features: FeatStruct: grammatical features to be added to default
#        @param pos:      string: part-of-speech: use only the generator for this POS
#        @param guess:    boolean: whether to use guess generator if lexical generator fails
#        @param roman:    boolean: whether the language uses a roman script
#        '''
#        is_not_roman = not roman
#        morf = self.morphology
#        output = []
#        features = features or []
#        if pos:
#            posmorph = morf[pos]
#            output = posmorph.gen(root, update_feats=features, guess=guess)
#        else:
#            for posmorph in list(morf.values()):
#                output.extend(posmorph.gen(root, update_feats=features, guess=guess))
#        if output:
#            o = [out[0] for out in output]
#            return o
#        print("This word can't be generated!")
#        return output

    def get_gen_fvs(self):
        gf = []
        for f, m in self.morphology.items():
            gf.append(((f, m.fullname), m.get_gen_fvs()))
        return gf

    def form2fvs(self, selpos, form):
        """Convert a dict of feature, value pairs from web form to L3Morpho feat val dicts,
        one for the form, one for generation.
        Record only those features belonging to the selected POS. Features are those keys
        containing ':'."""
        fvs = {}
        longfvs = {}
        for f, v in form.items():
            if ':' not in f:
                continue
            fsplit = f.split(':')
            pos = fsplit[0]
            if pos == selpos:
                posmorph = self.morphology[pos]
                f1long = fsplit[1]
                f1 = posmorph.exrevab(f1long)
                f2 = None
                if len(fsplit[1:]) == 2:
                    f2long = fsplit[2]
                    f2 = posmorph.exrevab(f2long)
                if f2:
                    if f1 not in fvs:
                        fvs[f1] = {}
                        longfvs[f1long] = {}
                    fvs[f1][f2] = True
                    longfvs[f1long][f2long] = 'on'
                else:
                    fvs[f1] = posmorph.exrevab(v)
                    if v is True:
                        longfvs[f1long] = 'on'
                    else:
                        longfvs[f1long] = v
        return fvs, longfvs

    ### End of morphology stuff

    def to_dict(self):
        """Convert the language to a dictionary to be serialized as a yaml file."""
        d = {}
        d['name'] = self.name
        d['abbrev'] = self.abbrev
        if self.groups:
            groups = {}
            for head, v in self.groups.items():
                groups[head] = [g.to_dict() for g in v]
            d['groups'] = groups
        if self.forms:
            forms = {}
            for k, v in self.forms.items():
                # v is an fv dict or a list of fv dicts
                forms[k] = v
        return d

    def write(self, directory, filename=''):
        """Serialize the language."""
        filename = filename or self.abbrev + '.lg'
        path = os.path.join(directory, filename)
        with open(path, 'w', encoding='utf8') as file:
            yaml.dump(self.to_dict(), file)

    def read_groups(self, files=None, target=None):
        """Read in groups from .grp files. If target is not None (must be a language), read in translation groups
        and cross-lingual features as well."""
        target_abbrev = target.abbrev if target else None
        source_groups = []
        target_groups = []
        for gfile in self.get_group_files(files):
            with open(gfile, encoding='utf8') as file:
                print("Leyendo grupos para {} de {}".format(self.name, gfile))
                # Groups separated by GROUP_SEP string
                groups = file.read().split(GROUP_SEP)
                transadd = ''
                sourceadd = ''
                # Preamble precedes first instance of GROUP_SEP
                preamble = groups[0]
                # Handle preamble ...
                for line in preamble.split("\n"):
                    line = line.strip()
                    if not line or line[0] == '#':
                        continue
                    if line[0] == '+':
                        tp, x, addition = line.partition(' ')[2].partition(' ')
                        if line[1] == 't':
#                            print("Each group translation has {}: {}".format(tp, addition))
                            transadd = tp, addition
                        else:
                            sourceadd = addition
                for group_spec in groups[1:]:
                    group_trans = group_spec.split('\n')
                    n = 0
                    group_line = group_trans[n].strip()
                    while len(group_line) == 0 or group_line[0] == '#':
                        # Skip comment lines
                        n += 1
                        group_line = group_trans[n].strip()
                    # A string starting with tokens and with other attributes separated by ;
                    source_group = group_line
#                    group_trans = group_spec.split(TRANS_START)
#                    source_group = group_trans[0].strip()
                    # Not sure whether head should be used to speed up reading group from string?
#                    head, source_group = source_group.split(HEAD_SEP)
#                    source_group = source_group.strip()
                    source_groups.append(source_group)
                    translations = []
                    n += 1
                    if target:
#                        for t in group_trans[1:]:
                        for t in group_trans[n:]:
                            # Skip comment lines
                            if len(t) > 0 and t[0] == '#':
                                continue
                            t = t.partition(TRANS_START)[2].strip()
                            if t:
                                tlang, x, tgroup = t.strip().partition(' ')
                                if transadd:
                                    tp, ad = transadd
#                                    if tp in tgroup:
#                                        print("  feature {} already in tgroup {}".format(tp, tgroup))
                                    if tp not in tgroup:
                                        tgroup += " " + ad
                                if tlang == target_abbrev:
                                    translations.append(tgroup)
                        target_groups.extend(translations)
                    # Creates the group and any target groups specified and adds them to self.groups
                    Group.from_string(source_group, self, translations, target=target, trans=False)

        # Sort groups for each key by priority
        for key, groups in self.groups.items():
            if len(groups) > 1:
                groups.sort(key=lambda g: g.priority(), reverse=True)

    def read_ms(self, target=None, verbosity=0):
        """Read in MorphoSyns for target from a .ms file. If target is not None (must be a language), read in translation groups
        and cross-lingual features as well."""
        path = self.get_ms_file(target.abbrev)
        try:
            with open(path, encoding='utf8') as f:
                print("Leyendo morphosyns para {}".format(path))
                lines = f.read().split('\n')[::-1]
                # the order of MorphoSyns matterns
                while lines:
                    # Strip comments
                    line = lines.pop().split('#')[0].strip()
                    # Ignore empty lines
                    if not line: continue
                    name, x, pattern = line.partition(MS_NAME_SEP)
                    morphosyn = MorphoSyn(self, name=name.strip(), pattern=pattern.strip())
                    self.ms.append(morphosyn)
        except IOError:
            print('No such MS file as {}'.format(path))

    @staticmethod
    def from_dict(d, reverse=True, use=ANALYSIS):
        """Convert a dict (loaded from a yaml file) to a Language object."""
        l = Language(d.get('name'), d.get('abbrev'), use=use)
#        l.possible = d.get('possible')
#        groups = d.get('groups')
#        if groups:
#            l.groups = {}
#            for head, v in groups.items():
#                group_objs = [Group.from_dict(g, l, head) for g in v]
#                l.groups[head] = group_objs
#                # Add groups to groupnames dict
#                for go in group_objs:
#                    l.groupnames[go.name] = go
#        forms = d.get('forms')
#        if forms:
#            l.forms = {}
#            for k, v in forms.items():
#                # v should be a dict or a list of dicts
#                # Convert features value to a FeatStruct object
#                if isinstance(v, dict):
#                    if 'features' in v:
#                        v['features'] = FeatStruct(v['features'])
#                else:
#                    for d in v:
#                        if 'features' in d:
#                            d['features'] = FeatStruct(d['features'])
#                l.forms[k] = v
#                if reverse:
#                    # Add item to genform dict
#                    if isinstance(v, dict):
#                        if 'seg' not in v:
#                            l.add_genform(k, v['root'], v.get('features'))
#                    else:
#                        for d in v:
#                            l.add_genform(k, d['root'], d.get('features'))
        return l

    @staticmethod
    def read(path, use=ANALYSIS):
        """Create a Language from the contents of a yaml file, a dict
        that must be then converted to a Language."""
        with open(path, encoding='utf8') as file:
            dct = yaml.load(file)
            return Language.from_dict(dct, use=use)

    @staticmethod
    def load_trans(source, target, groups=None):
        """Load a source and a target language, given as abbreviations.
        Read in groups for source language, including target language translations at the end.
        If the languages are already loaded, don't load them."""
        srclang = Language.languages.get(source)
        targlang = Language.languages.get(target)
        loaded = False
        if srclang and targlang and srclang.use == SOURCE and targlang.use == TARGET:
            loaded = True
        else:
            try:
                srcpath = os.path.join(Language.get_language_dir(source), source + '.lg')
                srclang = Language.read(srcpath, use=SOURCE)
                print("Lengua fuente {} cargada".format(srclang))
                targpath = os.path.join(Language.get_language_dir(target), target + '.lg')
                targlang = Language.read(targpath, use=TARGET)
                print("Lengua destino {} cargada".format(targlang))
            except IOError:
                print("One of these languages doesn't exist.")
                return
        # Load groups for source language now
        if not loaded:
            srclang.read_groups(files=groups, target=targlang)
            srclang.read_ms(target=targlang)
        return srclang, targlang
        
    @staticmethod
    def load(*abbrevs):
        """Load languages, given as abbreviations."""
        languages = []
        for abbrev in abbrevs:
            if abbrev in Language.languages:
                language = Language.languages[abbrev]
                languages.append(language)
            else:
                path = os.path.join(Language.get_language_dir(abbrev), abbrev + '.lg')
                try:
                    language = Language.read(path)
                    languages.append(language)
                    print("Loaded language {}".format(language))
                except IOError:
                    print("That language doesn't seem to exist.")
                    return
        return languages

    ### Basic setters. Create entries (dicts) for item. For debugging purposes, include name
    ### in entry.

#    def add_form(self, form, dct, reverse=True):
#        """Form dict has root, features, cats.
#        If reverse is True, also add the form to the genforms dict."""
#        if form not in self.forms:
#            self.forms[form] = dct
#        else:
#            entry = self.forms[form]
#            if isinstance(entry, dict):
#                # Make this the second entry
#                self.forms[form] = [entry, dct]
#            else:
#                # There are already two or more entries in a list
#                entry.append(dct)
#        if reverse:
#            lexeme = dct['root']
#            features = dct['features']
#            self.add_genform(form, lexeme, features)
#
#    def add_genform(self, form, lexeme, features):
#        """Add the form to a lexeme- and feature-keyed dict."""
#        if lexeme not in self.genforms:
#            self.genforms[lexeme] = {}
#        featdict = self.genforms[lexeme]
#        # features is a FeatStruct object; convert it to a list of tuples
#        features = tuple(features.to_list())
#        featdict[features] = form
##        feat = features.pop(0)
##        self.make_featdict(featdict, feat, features, form)

#    def add_group(self, tokens, head_index=-1, head='', name='', features=None):
#        group = Group(tokens, head_index=head_index, head=head,
#                      language=self, name=name, features=features)
##        print('Group {}, head {}'.format(group, group.head))
#        if features:
#            head_i = tokens.index(group.head)
#            head_feats = features[head_i]
#        else:
#            head_feats = None
#        self.add_group_to_lexicon(group.head, group, head_feats)
#        self.groupnames[group.name] = group
#        self.changed = True
#        return group

    def add_group(self, group):
        """Add group to dict, indexed by head."""
        head = group.head
        if head in self.groups:
            self.groups[head].append(group)
        else:
            self.groups[head] = [group]
        self.groupnames[group.name] = group
        self.changed = True

#    def add_group_to_lexicon(self, head, group, features):
#        if not features:
#            # Add the group to the list of groups for the head word/lexeme
#            if head not in self.groups:
#                self.groups[head] = {}
#            if () not in self.groups[head]:
#                self.groups[head][()] = []
#            self.groups[head][()].append(group)
#        else:
#            # Convert fv dict to an alphabetized tuple of fv pairs
#            fvs = list(features.items())
#            fvs.sort()
#            fvs = tuple(fvs)
#            if head not in self.groups:
#                self.groups[head] = {}
#            if fvs not in self.groups[head]:
#                self.groups[head][fvs] = []
#            self.groups[head][fvs].append(group)

    ### Basic getters.

    ### Generation of word forms

    def generate(self, root, features, pos=None, guess=False, roman=True, verbosity=0):
        if verbosity:
            print("Generating {}:{}".format(root, features.__repr__()))
#        if not features:
#            features = FeatStruct({})
#        features = features.freeze()
        if not pos:
            print("Warning: no POS for generation of {}:{}".format(root, features.__repr__()))
        is_not_roman = not roman
        morf = self.morphology
        output = []
        if pos:
            if pos not in morf:
                print("POS {} not in morphology {}".format(pos, morf))
                return [root]
            posmorph = morf[pos]
#            print("Generating root {} with features {}".format(root, features.__repr__()))
            output = posmorph.gen(root, update_feats=features, guess=guess, only_words=True)
        else:
            for posmorph in list(morf.values()):
                output.extend(posmorph.gen(root, update_feats=features, guess=guess, only_words=True))
        if output:
#            o = [out[0] for out in output]
            # if there is a postprocessing dict, apply it
            if self.postproc:
                for oi, outp in enumerate(output):
                    for d, c in self.postproc.items():
                        if d in outp:
                            output[oi] = outp.replace(d, c)
            return output
        else:
            print("The root/feature combination {}:{} word can't be generated!".format(root, features.__repr__()))
            return [root]

class LanguageError(Exception):
    '''Class for errors encountered when attempting to update the language.'''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

