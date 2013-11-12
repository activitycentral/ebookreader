# Copyright 2009 One Laptop Per Child
# Author: Sayamindu Dasgupta <sayamindu@laptop.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging
import env_settings as env
import os
import shutil
import sqlite3
import time
import env_settings as env
from gi.repository import GConf

from readbookmark import Bookmark

_logger = logging.getLogger(__name__)


def _init_db():
    dbpath = os.path.join(env.EBOOKREADER_LOCAL_DATA_DIRECTORY, 'read_v1.db')

    # Check the db, remove if it is corrupted
    testconn = sqlite3.connect(dbpath)
    try:
        testconn.execute("PRAGMA integrity_check;")
    except:
        os.remove(dbpath)

    conn = sqlite3.connect(dbpath)
    conn.execute("CREATE TABLE IF NOT EXISTS bookmarks (md5 TEXT, subfilenumber INTEGER, zoom INTEGER, " + \
        "identifier UNSIGNED BIG INT, timestamp TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS resumption (md5 TEXT, subfilenumber INTEGER, zoom INTEGER, " + \
        "x_scroll UNSIGNED BIG INT, y_scroll UNSIGNED BIG INT)")
    conn.commit()
    conn.close()

    return dbpath


def _init_db_highlights(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS HIGHLIGHTS ' +
                '(md5 TEXT, page INTEGER, ' +
                'init_pos INTEGER, end_pos INTEGER)')
    conn.commit()


class BookmarkManager:

    def __init__(self, filehash, view, main_instance):
        self._filehash = filehash
        self._view = view
        self._main_instance = main_instance

        dbpath = _init_db()

        assert dbpath != None

        self._conn = sqlite3.connect(dbpath)
        #_init_db_highlights(self._conn)

        self._conn.text_factory = lambda x: unicode(x, "utf-8", "ignore")

        self._bookmarks = []
        self._reversed_bookmarks = []
        if filehash is not None:
            self._populate_bookmarks()

        client = GConf.Client.get_default()
        self._user = client.get_string("/desktop/sugar/user/nick")
        self._color = client.get_string("/desktop/sugar/user/color")

    def add_resumption_metadata(self, filehash, metadata):
        t = (filehash, metadata['sub_file_number'],
                       metadata['zoom'],
                       metadata['x_scroll'],
                       metadata['y_scroll'])
        self._conn.execute('insert into resumption values ' + \
                           '(?, ?, ?, ?, ?)', t)
        self._conn.commit()

    def get_resumption_metadata(self, filehash):
        metadata =  {}
        rows = self._conn.execute('select * from resumption ' + \
                                  'where md5=? ', (filehash,))
        for row in rows:
            metadata['sub_file_number'] = row[1]
            metadata['zoom'] = row[2]
            metadata['x_scroll'] = row[3]
            metadata['y_scroll'] = row[4]

        self._conn.commit()
        return metadata

    def delete_resumption_metadata(self, filehash):
        t = ([filehash])
        self._conn.execute('delete from resumption ' + \
                           'where md5=?', t)

        self._conn.commit()

    def add_bookmark(self, number_of_times_zoomed):
        from readtab import MAXIMUM_ZOOM_OUTS, MAXIMUM_ZOOM_INS

        ################################################################
        """
        # Go the smallest zoom.
        for zoom in range(MAXIMUM_ZOOM_OUTS, number_of_times_zoomed):
            self._main_instance.secondary_toolbar.dummy_view_toolbar.zoom_out()
        """
        ################################################################

        # Now, iterate over each zoom, and store the bookmark for each
        # zoom. Also, take the  timestamp as the unique-id for this
        # class of bookamrks.
        timestamp = int(time.time())
        for zoom in range(MAXIMUM_ZOOM_OUTS, MAXIMUM_ZOOM_INS + 1):
            sub_file_number = self._view._sub_file_number
            bookmark_identifier = self._view.get_bookmark_identifier()

            self.__add_bookmark_in_db(sub_file_number, zoom, bookmark_identifier, timestamp)
            """
            self._main_instance.secondary_toolbar.dummy_view_toolbar.zoom_in()
            """

        ################################################################
        # Bring back to the original zoom.
        """
        for zoom in range(number_of_times_zoomed, MAXIMUM_ZOOM_INS + 1):
            self._main_instance.secondary_toolbar.dummy_view_toolbar.zoom_out()
        """
        ################################################################

        self._conn.commit()

    def __add_bookmark_in_db(self, sub_file_number, zoom, bookmark_identifier, timestamp):
        t = (self._filehash, sub_file_number, zoom, bookmark_identifier, str(timestamp))
        self._conn.execute('insert into bookmarks values ' + \
                '(?, ?, ?, ?, ?)', t)

        self._resync_bookmark_cache()

    def del_bookmark(self, number_of_times_zoomed):
        # Get the bookmark(s), associated with the combination of
        # "current-sub-file=number PLUS current-zoom PLUS current-vertical-offset"
        current_sub_file_number = self._view._sub_file_number
        current_bookmark_identifier = self._view.get_bookmark_identifier()

        rows = self._conn.execute('select * from bookmarks ' + \
                                  'where md5=? ' + \
                                  'and subfilenumber=? ' + \
                                  'and zoom=? ' +  \
                                  'and identifier=?',          \
                        (self._filehash,
                         current_sub_file_number,
                         number_of_times_zoomed,
                         current_bookmark_identifier))

        for row in rows:
            bookmark = Bookmark(row)
            timestamp = bookmark.timestamp

            # Now, delete all the bookmarks, with the current
            # timestamp.
            t = ([timestamp])
            self._conn.execute('delete from bookmarks ' + \
                               'where timestamp=?', t)

        # Finally, commit if we reach here (without any errors
        # obviosuly :) )
        self._conn.commit()

        self._resync_bookmark_cache()

    def _populate_bookmarks(self):
        # TODO: Figure out if caching the entire set of bookmarks
        # is a good idea or not
        rows = self._conn.execute('select * from bookmarks ' + \
            'where md5=? order by zoom ASC, subfilenumber ASC, identifier ASC', (self._filehash, ))

        for row in rows:
            self._bookmarks.append(Bookmark(row))
            self._reversed_bookmarks.append(Bookmark(row))

        # Finally, reverse the second list.
        self._reversed_bookmarks.reverse()

    def is_current_page_bookmarked(self, number_of_times_zoomed):
        current_sub_file_number = self._view._sub_file_number
        current_bookmark_identifier = self._view.get_bookmark_identifier()

        for bookmark in self._bookmarks:
            if (bookmark.subfilenumber == current_sub_file_number) and \
               (bookmark.zoom == number_of_times_zoomed) and \
               (bookmark.identifier) == current_bookmark_identifier:
                   return True
        return False

    def get_prev_bookmark(self, number_of_times_zoomed):
        current_sub_file_number = self._view._sub_file_number
        current_bookmark_identifier = self._view.get_bookmark_identifier()

        for bookmark in self._reversed_bookmarks:
            if bookmark.zoom == number_of_times_zoomed:
                if bookmark.subfilenumber > current_sub_file_number:
                    continue # the previous bookmark cannot be in a
                             # next file

                elif bookmark.subfilenumber == current_sub_file_number:
                    if bookmark.identifier >= current_bookmark_identifier:
                        continue # if the file is same, the identifier
                                 # should be smaller than the
                                 # identifier of the current file.
                    else:
                        return bookmark

                else:
                    return bookmark # we have just crossed over to the
                                    # previous file.

        return None

    def get_next_bookmark(self, number_of_times_zoomed):
        current_sub_file_number = self._view._sub_file_number
        current_bookmark_identifier = self._view.get_bookmark_identifier()

        for bookmark in self._bookmarks:
            if bookmark.zoom == number_of_times_zoomed:
                if bookmark.subfilenumber < current_sub_file_number:
                    continue # the next bookmark cannot be in a previous file

                elif bookmark.subfilenumber == current_sub_file_number:
                    if bookmark.identifier <= current_bookmark_identifier:
                        continue # if the file is same, the identifier
                                 # should be greater than the
                                 # identifier of the current file.
                    else:
                        return bookmark

                else:
                    return bookmark # we have just crossed over to the
                                    # next file.

        return None

    def show_all_bookmarks(self):
        for bookmark in self._bookmarks:
            print str(bookmark.subfilenumber) + ' ' + \
                  str(bookmark.zoom) + ' ' + \
                  str(bookmark.identifier) + ' ' + \
                  str(bookmark.timestamp)

    def _resync_bookmark_cache(self):
        # To be called when a new bookmark has been added/removed
        self._bookmarks = []
        self._reversed_bookmarks = []
        self._populate_bookmarks()
