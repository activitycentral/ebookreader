#!/usr/bin/env python

import os
import sys
import subprocess
import gettext
import env_settings as env

# Set the file-path, if provided.
filepath = None
if len(sys.argv) is 2:
    filepath = sys.argv[1]

# Make the localization work.
COMPILED_LOCALE_FILE_NAME = 'org.ac.EBookReader'
gettext.bindtextdomain(COMPILED_LOCALE_FILE_NAME, env.LOCALE_DIR)
gettext.textdomain(COMPILED_LOCALE_FILE_NAME)

from ebookreader import EBookReader
EBookReader((filepath, None,)).main()
