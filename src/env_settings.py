""" Place here all the environment variables"""
import os
import logging

os.environ['SUGAR_ACTIVITY_ROOT'] = os.getcwd() + '/'

if 'SUGAR_BUNDLE_ID' in os.environ:
	SUGAR_BUNDLE_ID = os.environ['SUGAR_BUNDLE_ID']

SUGAR_ACTIVITY_ROOT = os.environ['SUGAR_ACTIVITY_ROOT']

APP_NAME='EBookReader'

COMPILED_LOCALE_FILE_NAME = 'org.ac.EBookReader'

LOCALE_DIR = SUGAR_ACTIVITY_ROOT + 'locale'

HOME = os.environ['HOME']

EBOOKREADER_LOCAL_DATA_DIRECTORY = os.path.join(HOME, 'BOOKs/.metadata')

MYLIBPATH = os.path.join(HOME, 'BOOKs')

ICONS_PATH = os.path.join (SUGAR_ACTIVITY_ROOT, 'icons')

LOG_LEVEL = logging.DEBUG
