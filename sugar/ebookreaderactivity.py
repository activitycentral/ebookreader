#!/usr/bin/env python

# This script wraps the EBookReader class around activity.Activity

import os
import sys
import gettext
import env_settings as env

from sugar3.activity import activity


# Set the file-path, if provided.
filepath = None
if sys.argv[2] == "%f":
    filepath = sys.argv[3]
else:
    filepath = sys.argv[2]

if not os.path.exists(env.MYLIBPATH):
    os.mkdir(env.MYLIBPATH)

# Make the localization work.
gettext.bindtextdomain(env.COMPILED_LOCALE_FILE_NAME, env.LOCALE_DIR)
gettext.textdomain(env.COMPILED_LOCALE_FILE_NAME)

# Search if there is an argument corresponding to "-o" flag.
# If yes, retrieve the "journal-"file.
journal_file_id = None
filepath = None
for i in range(0, len(sys.argv)):
    if sys.argv[i] == '-o':
        journal_file_id = sys.argv[i+1]
        break

if journal_file_id is not None:
    first_two_chars = journal_file_id[0:2]
    filepath = os.path.join(os.path.expanduser('~'),
                            '.sugar/default/datastore', first_two_chars,
                            journal_file_id, 'data')
    if not os.path.exists(filepath):
        filepath = None
        journal_file_id = None

    if filepath is not None and "sugar/default/datastore" in filepath:
        mimefile=open(os.path.join(os.path.dirname(filepath), "metadata/mime_type"), "r")
        mime = mimefile.read()
        if "ceibal" in mime:
            titlefile=open(os.path.join(os.path.dirname(filepath), "metadata/description"), "r")
            title = os.path.basename(titlefile.read())
        else:
            titlefile=open(os.path.join(os.path.dirname(filepath), "metadata/title"), "r")
            title = os.path.basename(titlefile.read())
            if not ".pdf" in title or ".epub" in title:
                if mime is "application/pdf":
                    title=title+".pdf"
                else:
                    title=title+".epub"
        os.system('install -m 644 "' + filepath + '" "' + os.path.join(MYLIBPATH, title)+ '"')
        filepath=os.path.join(env.MYLIBPATH, title)


class EBookReaderActivity(activity.Activity):
    def __init__(self, handle):

        super(EBookReaderActivity, self).__init__(handle)
	
        from ebookreader import EBookReader
        EBookReader((filepath, journal_file_id,)).main()
        self.close()
        self.destroy()
