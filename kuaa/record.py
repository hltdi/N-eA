#   
#   Mainumby: records kept for system translations and user feedback
#
########################################################################
#
#   This file is part of the Mainumby project within the PLoGS metaproject
#   for parsing, generation, translation, and computer-assisted
#   human translation.
#
#   Copyright (C) 2016, 2017, 2018 PLoGS <gasser@indiana.edu>
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

# 2016.02.29
# -- Created.
# 2016.03
# -- Lots of additions and fixes.
# 2016.04.02-3
# -- Added users, with hashed passwords
# 2018.01.19
# -- User files are YAML.
#    There is a separate file for each user's data: <username>.usr
#    -- Contents are a dict
#    Sessions go in another file: <username>.sess
#    -- Contents are a list of Sessions
#       Each Session is a dict: id, date, SentRecords
#       Each SentRecord is a dict: source, translation, SegRecord
#       Each SegRecord is a triple: source, translation, feedback_code

import datetime, sys, os, yaml
from werkzeug.security import generate_password_hash, check_password_hash

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), 'sessions')
USERS_FILE = "users"

SESSION_PRE = '{$}'
TIME_PRE = '{t}'
TIME_PRE_END = '{T}'
SENTENCE_PRE = '{S:'
SENTENCE_POST = ':S}'
SEGMENT_PRE = '{{s:'
SEGMENT_POST = ':s}}'
FEEDBACK_PRE = "{F}"
TRANS_PRE = "{->"
TRANS_POST = "<-}"
USER_PRE = "{U}"
TIME_FORMAT = "%d.%m.%Y/%H:%M:%S:%f"
# Time format without microseconds; used in Session ID and for User creation and update times
SHORT_TIME_FORMAT = "%d.%m.%Y/%H:%M:%S"

ZERO_TIME = datetime.timedelta()
TIME0 = datetime.datetime.utcnow()

def get_time():
    return datetime.datetime.utcnow()

def get_time_since0(time):
    return time - TIME0

class Session:
    """A record of a single user's responses to a set of sentences."""

    def __init__(self, user=None, source=None, target=None):
        self.start = get_time()
        self.user = user
        # Source and target languages
        self.source = source
        self.target = target
        self.end = None
        self.running = True
        # List of SentRecord objects
        self.sentences = []
        self.make_id()
        print("Creando sesión {}".format(self))

    def __repr__(self):
        return "{} {}".format(SESSION_PRE, self.id)

    def to_dict(self):
        """Create dictionary from Session, after it stops."""
        d = {}
        d['start'] = Session.time2shortstr(self.start)
        d['end'] = Session.time2shortstr(self.end)
        d['id'] = self.id
        d['sents'] = [s.to_dict() for s in self.sentences]
        return d

    @staticmethod
    def time2str(time):
        return time.strftime(TIME_FORMAT)

    @staticmethod
    def time2shortstr(time):
        return time.strftime(SHORT_TIME_FORMAT)

    @staticmethod
    def str2time(string):
        return datetime.datetime.strptime(string, TIME_FORMAT)

    def make_id(self):
        self.id = "{}::{}".format(self.user.username, Session.time2shortstr(self.start))

    def get_path(self):
        sessionfilename = self.user.username + '.sess'
        return os.path.join(SESSIONS_DIR, sessionfilename)

    def length(self):
        """Length of the session as a time delta object."""
        if self.running:
            return ZERO_TIME
        else:
            return self.end - self.start

#    def user_input(self, string):
#        """Clean up the user input."""
#        return self.target.ortho_clean(string)

    def quit(self):
        """Save new users, set the end time, save the session, and stop running."""
        # Save any new users (can there be more than 1?)
        User.write_new()
        User.new_users.clear()
        self.running = False
        self.end = get_time()
        self.save()

#    def record_translation(self, sentrecord, translation):
#        """Only record a verbatim translation of the sentence."""
#        sentrecord.translation = translation

    def record(self, sentrecord, translation=None, segtrans=None):
        """Record feedback about a sentence's translation."""
        print("{} recording translation for sentence {} with translation {} and seg trans {}".format(self, sentrecord, translation, segtrans))
        segrecord = None
        if translation:
            translation = self.target.ortho_clean(translation)
            print("Recorded sentence translation: {}".format(translation))
            sentrecord.record(translation)

        # There might be both segment and whole sentence translations.
        if segtrans:
            segrecords = sentrecord.segments
#            segreclist = sentrecord.seg_list
            print("Seg list in sent record: {}".format(segrecords))
            seg_src_trans = segtrans.split('|||')
            for src_trans in seg_src_trans:
                # index || selected_choice? || source_phrase = translation
                print("  src_trans: {}".format(src_trans))
                index, agreed, src_trans = src_trans.split('||')
                src, trans = src_trans.split('=')
                index = int(index)
                # Get the segrecord from the dict
                segrecord1 = segrecords.get(src.lower())
                # Get the segrecord from the list
#                segrecord1 = segreclist[index]
                print("  src {}, trans {}, index {}, agreed? {}".format(src, trans, index, agreed))
#                if segrecord1:
#                    print("  segrecord {}, translation {}".format(segrecord1, segrecord1.translation))
                if segrecord1:
                    segrecord1.response_code = 1 if agreed else 0
                    segrecord1.seltrans = trans
                    print("  segrecord {}, trans {}, code {}".format(segrecord1, segrecord1.seltrans, segrecord1.response_code))
#            translation = self.target.ortho_clean(translation)
#            print("Segment translation: {}".format(translation))
#            segrecord.record(translation=translation)
#        else:
#            # If alternative is given, don't record any choices
#            tra_choices = []
#            for key, value in trans_dict.items():
#                if key.isdigit():
#                    key = int(key)
#                    tra_choices.append((key, value))
#            print(" Choices: {}".format(segrecord.choices))
#            segrecord.record(choices=tra_choices)

    def save(self):
        """Write the session feedback to the user's file."""
        with open(self.get_path(), 'a', encoding='utf8') as file:
            self.write(file=file)

    def write(self, file=sys.stdout):
        """Write the Session's information and contents to a file our stdout."""
        d = [self.to_dict()]
        yaml.dump(d, file, default_flow_style=False)

#    def write(self, file=sys.stdout):
#        print("{}".format(self), file=file)
#        print("{} {}".format(TIME_PRE, Session.time2shortstr(self.start)), file=file)
#        for sentence in self.sentences:
#            sentence.write(file=file)
#        if not self.running:
#            print("{} {}".format(TIME_PRE_END, Session.time2shortstr(self.end)), file=file)

    def write_doc(self, file=sys.stdout, tm=False):
        """Write the source and target translations in raw form to file."""
        for sentence in self.sentences:
            if tm:
                print("<tu><tuv><seg>", file=file)
            print("{}".format(sentence.raw), file=file)
            if tm:
                print("</seg></tuv><tuv><seg>", file=file)
            print("{}".format(sentence.translation), file=file)
            if tm:
                print("</seg></tuv></tu>", file=file)

class SentRecord:
    """A record of a Sentence and a single user's response to it."""

    def __init__(self, sentence, session=None, user=None):
        self.sentence = sentence
        self.session = session
        self.raw = sentence.original
        self.tokens = sentence.tokens
        self.analyses = sentence.analyses
        self.time = get_time()
        self.user = user
        # Add to parent Session
        session.sentences.append(self)
        # a dict of SegRecord objects, with token strings as keys
        self.segments = {}
        # a list of SegRecord objects
        self.seg_list = []
        self.feedback = None
        # Verbatim translation of the sentence
        self.translation = ''

    def __repr__(self):
#        session = "{}".format(self.session) if self.session else ""
        return "{} {} {}".format(SENTENCE_PRE, self.raw, SENTENCE_POST)

    ## Methods to stringify Sentence Morphosyn matches, tokens, and morphology
    def get_morphosyns(self):
        return [SentRecord.MS_match2string(ms) for ms in self.sentence.morphosyns]

    def get_tokens(self):
        result = []
        for analysis in self.sentence.analyses:
            dct = analysis[1][0]
            result.append("{};;{};;{};;{}".format(analysis[0], dct.get('pos'), dct.get('root'),
                                                  SentRecord.stringify_feats(dct.get('features'))))
        return result

#    def get_tokens(self):
#        return ';;'.join([a[0] for a in self.sentence.analyses])

#    def get_pos(self):
#        analyses = self.sentence.analyses
#        return [anals[0].get('pos') for anals in [a[1] for a in analyses]]

#    def get_roots(self):
#        analyses = self.sentence.analyses
#        return ";;".join([anals[0].get('root') for anals in [a[1] for a in analyses]])

#    def get_features(self):
#        analyses = self.sentence.analyses
#        return ";;".join([SentRecord.stringify_feats(anals[0].get('features')) for anals in [a[1] for a in analyses]])

    @staticmethod
    def stringify_feats(feats):
        if feats:
            return feats.__repr__()
        else:
            return '[]'

    @staticmethod
    def MS_match2string(ms_match):
        """Convert a Morphosyn match to a string."""
        return "{} {} {}".format(ms_match[0].__repr__(), ms_match[1], ms_match[2])

    def to_dict(self):
        d = {}
        d['s_raw'] = self.raw
        d['s_tok'] = self.get_tokens()
#        d['s_feat'] = self.get_features()
#        d['s_root'] = self.get_roots()
#        d['s_pos'] = self.get_pos()
        d['s_ms'] = self.get_morphosyns()
        d['trg'] = self.translation
        d['time'] = Session.time2shortstr(self.time)
        d['segs'] = [s.to_dict() for s in self.segments.values()]
        return d

    def record(self, translation):
        """Record user's translation for the whole sentence."""
        self.translation = translation
#        feedback = Feedback(translation=translation)
#        print("{} recording translation {}, feedback: {}".format(self, translation, feedback))
#        self.feedback = feedback

    def write(self, file=sys.stdout):
        d = self.to_dict()
        yaml.dump(d, file, default_flow_style=False)        

#    def write(self, file=sys.stdout):
#        print("{}".format(SENTENCE_PRE), file=file)
#        print("{}".format(self.raw), file=file)
#        if self.feedback:
#            print("{}".format(self.feedback), file=file)
#        # Can there be feedback for segments *and* for whole sentence?
#        for key, segment in self.segments.items():
#            if segment.feedback:
#                segment.write(file=file)
#        print("{}".format(SENTENCE_POST), file=file)

class SegRecord:
    """A record of a sentence solution segment and its translation by a user."""

    def __init__(self, solseg, sentence=None, session=None):
        # a SentRecord instance
        self.sentence = sentence
        self.session = session
        self.indices = solseg.indices
        # translation options presented by the system
        self.translation = solseg.translation
        self.tokens = solseg.token_str
        self.gname = solseg.gname
        self.merger_gnames = solseg.merger_gnames
        # Add to parent SentRecord
        self.sentence.segments[self.tokens] = self
#        self.sentence.seg_list.append(self)
        # These get filled in during set_html() in SolSeg
        self.choices = []
        # Translation selected or provided by user
        self.seltrans = ''
        # Code representing user's response --
        # 1: agrees with Mbojereha's choices,
        # 0: alternative response
        self.response_code = 0
        self.feedback = None
#        print("   Creating segment record {}".format(self))

    def __repr__(self):
#        session =  "{}".format(self.session) if self.session else ""
        return "{} {} {}".format(SEGMENT_PRE, self.tokens, SEGMENT_POST)

    def to_dict(self):
        """Create dictionary from SegRecord."""
        d = {}
        d['src'] = self.tokens
        d['gname'] = self.gname
        d['resp'] = self.response_code
        d['trg'] = self.seltrans
        return d
        
    def record(self, choices=None, translation=None):
        print("{} recording translation {}, choices {}".format(self, translation, choices))
        if choices:
            self.feedback = Feedback(choices=choices)
            print("{}".format(self.feedback))
        elif translation:
            self.feedback = Feedback(translation=translation)
            print("{}".format(self.feedback))
        else:
            print("Something wrong: NO FEEDBACK TO RECORD")

    def write(self, file=sys.stdout):
        print("{}".format(self), file=file)
        print("{}".format(self.gname), file=file)
        print("{}".format(self.merger_gnames), file=file)
        print("{}".format(self.feedback), file=file)

class Feedback:
    """Feedback from a user about a segment or sentence and its translation."""

    def __init__(self, accept=True, choices=None, translation=None):
        """
        EITHER the user simply
        -- accepts the system's translation (accept=True) OR
        -- makes selection from the alternatives offered by the system
           (choices is a list of pos_index, choice pairs) OR
        -- provides an alternate translation (translation is not None).
        No backpointer to the SegRecord or SentRecord that this refers to.
        """
        self.accept = accept
        self.choices = choices
        self.translation = translation
#        self.id = '@'
        self.id = ''
        if translation:
            self.id += TRANS_PRE + " {} ".format(translation) + TRANS_POST
        elif choices:
            choice_string = ','.join(["{}={}".format(pos, c) for pos, c in choices])
            self.id += "{}".format(choice_string)
        else:
            self.id += "ACC"

    def __repr__(self):
        return self.id
#        return "{} {}".format(FEEDBACK_PRE, self.id)

ACCEPT = Feedback()

class User:
    """User of the system who is registered and whose feedback is saved."""

    # Dictionary of users, with usernames as keys.
    users = {}
    # Dictionary of users created during the most recent session, with usernames as keys.
    new_users = {}

    def __init__(self, username='', email='', password='', name='', level=1, pw_hash='',
                 creation=None, nsessions=0, nsentences=0, update=None, score=0.0,
                 new=False):
        """name and level are optional. Other fields are required."""
        self.username = username
        self.email = email
        # Guarani ability
        self.level = level
        self.name = name
        self.creation = creation if creation else User.time()
        if pw_hash:
            self.pw_hash = pw_hash
        else:
            self.set_password(password)
        # Initial values to be updated later
        self.nsessions = nsessions
        self.nsentences = nsentences
        # Time data last updated
        self.update = update or self.creation
        # Score based on evaluation of translations
        self.score = score
        # Add to dict of all users
        User.users[self.username] = self
        # If this is a new user, save it here so it can be written to all.usr at the end
        # of the session.
        if new:
            User.new_users[self.username] = self

    def __repr__(self):
        return "{} {}".format(USER_PRE, self.username)

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)

    def check_password(self, password):
#        print("Checking password {} with hash {}".format(password, self.pw_hash))
        res = check_password_hash(self.pw_hash, password)
#        print("Result {}".format(res))
        return check_password_hash(self.pw_hash, password)

    def add_user(self):
        User.users[self.username] = self

    @staticmethod
    def time():
        time = get_time()
        return time.strftime(SHORT_TIME_FORMAT)

    @staticmethod
    def from_file(username):
        path = User.get_path(username)
        with open(path, encoding='utf8') as file:
            d = yaml.load(file)
            u = User.dict2user(d, new=False)
        return u

    def user2dict(self):
        """Create a dictionary or user properties."""
        d = {}
        d['username'] = self.username
        d['level'] = self.level
        d['name'] = self.name
        d['email'] = self.email
        d['creation'] = self.creation
        d['update'] = self.update
        d['nsentences'] = self.nsentences
        d['nsessions'] = self.nsessions
        d['score'] = self.score
        d['pw_hash'] = self.pw_hash
        return d

    @staticmethod
    def dict2user(dct, new=True):
        level = dct.get('level', 1)
#        if isinstance(level, str):
#            level = int(level)
        return User(username=dct.get('username', ''),
                    password=dct.get('password', ''),
                    pw_hash=dct.get('pw_hash'),
                    email=dct.get('email', ''),
                    name=dct.get('name', ''),
                    creation=dct.get('creation'),
                    update=dct.get('update'),
                    nsentences=dct.get('nsentences', 0),
                    nsessions=dct.get('nsessions', 0),
                    score=dct.get('score', 0.0),
                    level=level,
                    new=new)

    @staticmethod
    def get_user(username):
       return User.users.get(username)

    def write(self, file=sys.stdout):
        print("{};{};{};{};{}".format(self.username, self.pw_hash, self.email, self.name, self.level), file=file)

    @staticmethod
    def get_users_path():
        return os.path.join(SESSIONS_DIR, USERS_FILE)

    @staticmethod
    def get_path(username):
        # File where the user's data is stored
        filename = "{}.usr".format(username)
        return os.path.join(SESSIONS_DIR, filename)

#    def get_path(self):
#        # File where the user's data is stored
#        filename = "{}.usr".format(self.username)
#        return os.path.join(SESSIONS_DIR, filename)

    def get_sessions_path():
        # File where the user's sessions are stored
        filename = "{}.sess".format(self.username)
        return os.path.join(SESSIONS_DIR, filename)

    @staticmethod
    def read_all():
        """Read in current users from all.usr, adding them to User.users."""
        with open(User.get_users_path(), encoding='utf8') as file:
            for line in file:
                username, pw_hash, email, name, level = line.strip().split(';')
                level = int(level)
                user = User.from_file(username)
#                userfile = User.get_path()
#                user = User(username=username, pw_hash=pw_hash, email=email, name=name, level=level,
#                            new=False)
                User.users[username] = user

    @staticmethod
    def write_new():
        """Enter all new users (normally at most one) in the users file.
        Create a user file for each new user.
        """
        with open(User.get_users_path(), 'a', encoding='utf8') as file:
            for username, user in User.new_users.items():
                user.write(file=file)

    def create_user_file(self):
        """Create user file with basic data about the user (to be changed later)."""
        d = self.user2dict()
        with open(User.get_path(self.username), 'w', encoding='utf8') as file:
            yaml.dump(d, file, default_flow_style=False)

    @staticmethod
    def get_user(username):
        return User.users.get(username)
