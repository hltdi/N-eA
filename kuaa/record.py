#   
#   Mainumby: sentences and how to parse and translate them.
#
########################################################################
#
#   This file is part of the HLTDI L^3 project
#   for parsing, generation, translation, and computer-assisted
#   human translation.
#
#   Copyright (C) 2016 HLTDI <gasser@indiana.edu>
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

import datetime, sys, os
from werkzeug.security import generate_password_hash, check_password_hash

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), 'sessions')

SESSION_PRE = '⌨'
TIME_PRE = '☽'
SENTENCE_PRE = '✍'
SEGMENT_PRE = '⧦'
FEEDBACK_PRE = "⇐"
USER_PRE = "☻"
TIME_FORMAT = "%d.%m.%Y/%H:%M:%S:%f"
# Time format without microseconds; used in Session ID
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

    def __repr__(self):
        return "{} {}".format(SESSION_PRE, self.id)

    @staticmethod
    def time2str(time):
        return time.strftime(TIME_FORMAT)

    @staticmethod
    def str2time(string):
        return datetime.datetime.strptime(string, TIME_FORMAT)

    def make_id(self):
        self.id = "{}::{}".format(self.user.username, self.start.strftime(SHORT_TIME_FORMAT))

    def get_path(self):
        userfilename = self.user.username + '.usr'
#        month = "{}.{}".format(self.start.year, self.start.month)
        return os.path.join(SESSIONS_DIR, userfilename)

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
        """Set the end time and stop running."""
        # Save any new users (can there be more than 1?)
        User.write_new()
        User.new_users.clear()
        self.running = False
        self.end = get_time()
        self.save()

    def record_translation(self, sentrecord, translation):
        """Only record a verbatim translation of the sentence."""
        sentrecord.translation = translation

    def record(self, sentrecord, trans_dict):
        """Record feedback about a segment's or entire sentence's translation."""
        print("{} recording translation for sentence {}".format(self, sentrecord))
        segrecord = None
        if trans_dict.get("UTraOra"):
            translation = trans_dict.get("UTraOra")
            translation = self.target.ortho_clean(translation)
            print("Alternate sentence translation: {}".format(translation))
            sentrecord.record(translation)
        else:
            # It might be capitalized
            segment_key = trans_dict.get('seg').lower()
            segrecord = sentrecord.segments.get(segment_key)
            print("Segment to record: {}".format(segrecord))

            # There might be both segment and whole sentence translations.
            if trans_dict.get("UTraSeg"):
                translation = trans_dict.get("UTraSeg")
                translation = self.target.ortho_clean(translation)
                print("Alternate segment translation: {}".format(translation))
                segrecord.record(translation=translation)
            else:
                # If alternative is given, don't record any choices
                tra_choices = []
                for key, value in trans_dict.items():
                    if key.isdigit():
                        key = int(key)
                        tra_choices.append((key, value))
                print(" Choices: {}".format(segrecord.choices))
#                for k, v in  tra_choices:
#                    print("  Chosen for {}: {}".format(k, v))
#                    print("  Alternatives: {}".format(segrecord.choices[k]))
                segrecord.record(choices=tra_choices)

    def save(self):
        """Write the session feedback to the user's file."""
        with open(self.get_path(), 'a', encoding='utf8') as file:
            self.write(file=file)

    def write(self, file=sys.stdout):
        print("{}".format(self), file=file)
        print("{} {}".format(TIME_PRE, Session.time2str(self.start)), file=file)
        if not self.running:
            print("{} {}".format(TIME_PRE, Session.time2str(self.end)), file=file)
        for sentence in self.sentences:
            sentence.write(file=file)

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
        # Also include analyses??
        self.session = session
        self.raw = sentence.raw
        self.tokens = sentence.tokens
        self.time = get_time()
        self.user = user
        # Add to parent Session
        session.sentences.append(self)
        # a dict of SegRecord objects, with token strings as keys
        self.segments = {}
        self.feedback = None
        # Verbatim translation of the sentence
        self.translation = ''

    def __repr__(self):
#        session = "{}".format(self.session) if self.session else ""
        return "{} {}".format(SENTENCE_PRE, self.raw)

    def record(self, translation):
        """Record user's translation for the whole sentence."""
        feedback = Feedback(translation=translation)
        print("{} recording translation {}, feedback: {}".format(self, translation, feedback))
        self.feedback = feedback

    def write(self, file=sys.stdout):
        print("{}".format(self), file=file)
        if self.feedback:
            print("{}".format(self.feedback), file=file)
        # Can there be feedback for segments *and* for whole sentence?
        for key, segment in self.segments.items():
            if segment.feedback:
                segment.write(file=file)

class SegRecord:
    """A record of a sentence segment and its translation by a user."""

    def __init__(self, solseg, sentence=None, session=None):
        # a SentRecord instance
        self.sentence = sentence
        self.session = session
        self.indices = solseg.indices
        self.translation = solseg.translation
        self.tokens = solseg.token_str
        # Add to parent SentRecord
        self.sentence.segments[self.tokens] = self
        # These get filled in during set_html() in SolSeg
        self.choices = []
        self.feedback = None

    def __repr__(self):
#        session =  "{}".format(self.session) if self.session else ""
        return "{} {}".format(SEGMENT_PRE, self.tokens)

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
            self.id += "{}".format(translation)
        elif choices:
            choice_string = ','.join(["{}={}".format(pos, c) for pos, c in choices])
            self.id += "{}".format(choice_string)
        else:
            self.id += "ACC"

    def __repr__(self):
        return "{} {}".format(FEEDBACK_PRE, self.id)

ACCEPT = Feedback()

class User:
    """User of the system who is registered and whose feedback is saved."""

    users = {}
    new_users = {}

    def __init__(self, username='', email='', password='', name='', level=1, pw_hash='',
                 new=False):
        """name and level are optional. Other fields are required."""
        self.username = username
        self.email = email
        # Guarani ability
        self.level = level
        self.name = name
        if pw_hash:
            self.pw_hash = pw_hash
        else:
            self.set_password(password)
        # Add to list of all users
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
        return check_password_hash(self.pw_hash, password)

    def add_user(self):
        User.users[self.username] = self

    @staticmethod
    def dict2user(dct):
        level = dct.get('level', 1)
        if isinstance(level, str):
            level = int(level)
        return User(username=dct.get('username', ''),
                    password=dct.get('password', ''),
                    email=dct.get('email', ''),
                    name=dct.get('name', ''),
                    level=level,
                    new=True)

    @staticmethod
    def get_user(username):
       return User.users.get(username)

    def write(self, file=sys.stdout):
        print("{};{};{};{};{}".format(self.username, self.pw_hash, self.email, self.name, self.level), file=file)

    @staticmethod
    def get_users_path():
        return os.path.join(SESSIONS_DIR, 'all.usr')

    def get_path():
        filename = "{}.usr".format(self.username)
        return os.path.join(SESSIONS_DIR, filename)

    @staticmethod
    def read_all():
        """Read in current users from all.usr, adding them to User.users."""
        with open(User.get_users_path(), encoding='utf8') as file:
            for line in file:
                username, pw_hash, email, name, level = line.split(';')
                user = User(username=username, pw_hash=pw_hash, email=email, name=name, level=level,
                            new=False)
                User.users[username] = user

    @staticmethod
    def write_new():
        with open(User.get_users_path(), 'a', encoding='utf8') as file:
            for username, user in User.new_users.items():
                user.write(file=file)

    @staticmethod
    def get_user(username):
        return User.users.get(username)
