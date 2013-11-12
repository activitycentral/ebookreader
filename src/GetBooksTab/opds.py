#! /usr/bin/env python

# Copyright (C) 2009 Sayamindu Dasgupta <sayamindu@laptop.org>
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

import threading
import os
import urllib
from gi.repository import GObject
from gi.repository import Gtk
import time
import csv
import env_settings as env

from sugar3 import network

import sys
sys.path.insert(0, './')
import feedparser

_logger = logging.getLogger(__name__)

_REL_OPDS_ACQUISTION = u'http://opds-spec.org/acquisition'
_REL_SUBSECTION = 'subsection'
_REL_OPDS_POPULAR = u'http://opds-spec.org/sort/popular'
_REL_OPDS_NEW = u'http://opds-spec.org/sort/new'
_REL_ALTERNATE = 'alternate'
_REL_CRAWLABLE = 'http://opds-spec.org/crawlable'

GObject.threads_init()


class ReadURLDownloader(network.GlibURLDownloader):
    """URLDownloader that provides content-length and content-type."""

    def get_content_length(self):
        """Return the content-length of the download."""
        if self._info is not None:
            length = self._info.headers.get('Content-Length')
            if length is not None:
                return int(length)
            else:
                return 0

    def get_content_type(self):
        """Return the content-type of the download."""
        if self._info is not None:
            return self._info.headers.get('Content-type')
        return None


class DownloadThread(threading.Thread):

    def __init__(self, obj, midway):
        threading.Thread.__init__(self)
        self.midway = midway
        self.obj = obj
        self.stopthread = threading.Event()

    def _download(self):

        def entry_type(entry):
            for link in entry['links']:
                if link['rel'] in \
                    [_REL_OPDS_POPULAR, _REL_OPDS_NEW, _REL_SUBSECTION]:
                    return "CATALOG"
                else:
                    return 'BOOK'

        _logger.debug('feedparser version %s', feedparser.__version__)
        if not self.obj.is_local() and self.midway == False:
            uri = self.obj._uri + self.obj._queryterm.replace(' ', '+')
            headers = {}
            if self.obj._language is not None and self.obj._language != 'all':
                headers['Accept-Language'] = self.obj._language
                if "?" in uri:
                    uri = uri + '&lang=' + self.obj._language
            _logger.error('Searching URL %s headers %s' % (uri, headers))
            feedobj = feedparser.parse(uri, request_headers=headers)
        else:
            feedobj = feedparser.parse(self.obj._uri)

        # Get catalog Type
        CATALOG_TYPE = 'COMMON'
        if 'links' in feedobj['feed']:
            for link in feedobj['feed']['links']:
                if link['rel'] == _REL_CRAWLABLE:
                    CATALOG_TYPE = 'CRAWLABLE'
                    break

        for entry in feedobj['entries']:
            if entry_type(entry) == 'BOOK' and CATALOG_TYPE is not 'CRAWLABLE':
                self.obj._booklist.append(Book(self.obj._configuration, entry))
            elif entry_type(entry) == 'CATALOG' or CATALOG_TYPE == 'CRAWLABLE':
                self.obj._cataloglist.append( \
                    Book(self.obj._configuration, entry))

        self.obj._feedobj = feedobj
        self.obj._ready = True
        GObject.idle_add(self.obj.notify_updated, self.midway)
        return False

    def run(self):
        self._download()

    def stop(self):
        self.stopthread.set()


class Book(object):

    def __init__(self, configuration, entry, basepath=None):
        self._entry = entry
        self._basepath = basepath
        self._configuration = configuration

    def get_title(self):
        try:
            ret = self._entry['title']
        except KeyError:
            ret = 'Unknown'

        return ret

    def get_author(self):
        try:
            ret = self._entry['author']
        except KeyError:
            ret = 'Unknown'

        return ret

    def get_download_links(self):
        ret = {}
        for link in self._entry['links']:
            if link['rel'] == _REL_OPDS_ACQUISTION:
                if self._basepath is not None and \
                        not (link['href'].startswith('http') or \
                                link['href'].startswith('ftp')):
                    ret[link['type']] = 'file://' \
                        + os.path.join(self._basepath, link['href'])
                else:
                    ret[link['type']] = link['href']
            elif link['rel'] in \
            [_REL_OPDS_POPULAR, _REL_OPDS_NEW, _REL_SUBSECTION]:
                ret[link['type']] = link['href']
            else:
                pass
        return ret

    def get_publisher(self):
        try:
            ret = self._entry['dcterms_publisher']
        except KeyError:
            ret = 'Unknown'

        return ret

    def get_published_year(self):
        try:
            ret = self._entry['published']
        except KeyError:
            ret = 'Unknown'

        return ret

    def get_language(self):
        try:
            ret = self._entry['dcterms_language']
        except KeyError:
            ret = 'Unknown'

        return ret

    def get_image_url(self):
        try:
            ret = {}
            for link in self._entry['links']:
                if link['rel'] == self._configuration['opds_cover']:
                    if self._basepath is not None and \
                            not (link['href'].startswith('http') or \
                                    link['href'].startswith('ftp')):
                        ret[link['type']] = 'file://' \
                            + os.path.join(self._basepath, link['href'])
                    else:
                        ret[link['type']] = link['href']
        except KeyError:
            ret = 'Unknown'
        return ret

    def get_summary(self):
        if self._configuration is not None \
            and 'summary_field' in self._configuration:
                try:
                    ret = self._entry[self._configuration['summary_field']]
                except KeyError:
                    ret = 'Unknown'
        else:
                ret = 'Unknown'
        return ret

    def get_object_id(self):
        try:
            ret = self._entry['object_id']
        except KeyError:
            ret = 'Unknown'

        return ret

    def match(self, terms):
        #TODO: Make this more comprehensive
        for term in terms.split('+'):
            if term in self.get_title():
                return True
            if term in self.get_author():
                return True
            if term in self.get_publisher():
                return True
        return False


class QueryResult(GObject.GObject):

    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([GObject.TYPE_BOOLEAN])),
    }

    def __init__(self, configuration, queryterm, language):
        GObject.GObject.__init__(self)
        self._configuration = configuration
        self._uri = self._configuration['query_uri']
        self._queryterm = queryterm
        self._language = language
        self._feedobj = None
        self._next_uri = ''
        self._ready = False
        self._booklist = []
        self._cataloglist = []
        self.threads = []
        self._start_download()

    def _start_download(self, midway=False):
        d_thread = DownloadThread(self, midway)
        self.threads.append(d_thread)
        d_thread.start()

    def notify_updated(self, midway):
        self.emit('updated', midway)

    def __len__(self):
        return len(self._booklist)

    def has_next(self):
        '''
        Returns True if more result pages are
        available for the resultset
        '''
        if not 'links' in self._feedobj['feed']:
            return False
        for link in self._feedobj['feed']['links']:
            if link['rel'] == u'next':
                self._next_uri = link['href']
                return True

        return False

    def update_with_next(self):
        '''
        Updates the booklist with the next resultset
        '''
        if len(self._next_uri) > 0:
            self._ready = False
            self._uri = self._next_uri
            self.cancel()  # XXX: Is this needed ?
            self._start_download(midway=True)

    def cancel(self):
        '''
        Cancels the query job
        '''
        for d_thread in self.threads:
            d_thread.stop()

    def get_book_n(self, n):
        '''
        Gets the n-th book
        '''
        return self._booklist[n]

    def get_book_list(self):
        '''
        Gets the entire booklist
        '''
        return self._booklist

    def get_catalog_list(self):
        '''
        Gets the entire catalog list
        '''
        return self._cataloglist

    def is_ready(self):
        '''
        Returns False if a query is in progress
        '''
        return self._ready

    def is_local(self):
        '''
        Returns True in case of a local school
        server or a local device
        (yay! for sneakernet)
        '''
        return False


class LocalVolumeQueryResult(QueryResult):

    def __init__(self, path, queryterm, language):
        configuration = {'query_uri': os.path.join(path, 'catalog.xml')}
        QueryResult.__init__(self, configuration, queryterm)

    def is_local(self):
        return True

    def get_book_list(self):
        ret = []
        if self._queryterm is None or self._queryterm is '':
            for entry in self._feedobj['entries']:
                ret.append(Book(entry, basepath=os.path.dirname(self._uri)))
        else:
            for entry in self._feedobj['entries']:
                book = Book(entry, basepath=os.path.dirname(self._uri))
                if book.match(self._queryterm.replace(' ', '+')):
                    ret.append(book)
        return ret


class RemoteQueryResult(QueryResult):

    def __init__(self, configuration, queryterm, language):
        QueryResult.__init__(self, configuration, queryterm, language)


class IABook(Book):

    def __init__(self, configuration, entry, basepath=None):
        Book.__init__(self, configuration, entry, basepath=None)

    def get_download_links(self):
        return self._entry['links']

    def get_image_url(self):
        return {'jpg': self._entry['cover_image']}


class DownloadIAThread(threading.Thread):

    def __init__(self, obj, midway):
        threading.Thread.__init__(self)
        self.midway = midway
        self.obj = obj
        self._download_content_length = 0
        self._download_content_type = None
        self._booklist = []
        queryterm = self.obj._queryterm
        search_tuple = queryterm.lower().split()
        FL = urllib.quote('fl[]')
        SORT = urllib.quote('sort[]')
        self.search_url = 'http://www.archive.org/advancedsearch.php?q=' +  \
            urllib.quote('(title:(' + self.obj._queryterm.lower() + ') OR ' + \
            'creator:(' + queryterm.lower() + ')) AND format:(DJVU)')
        self.search_url += '&' + FL + '=creator&' + FL + '=description&' + \
            FL + '=format&' + FL + '=identifier&' + FL + '=language'
        self.search_url += '&' + FL + '=publisher&' + FL + '=title&' + \
            FL + '=volume'
        self.search_url += '&' + SORT + '=title&' + SORT + '&' + \
            SORT + '=&rows=500&save=yes&fmt=csv&xmlsearch=Search'
        self.stopthread = threading.Event()

    def _download(self):
        GObject.idle_add(self.download_csv, self.search_url)

    def download_csv(self, url):
        _logger.debug('get csv from %s', url)
        path = os.path.join(self.obj._activity.get_activity_root(), 'instance',
                'tmp%i.csv' % time.time())
        print 'path=', path
        getter = ReadURLDownloader(url)
        getter.connect("finished", self._get_csv_result_cb)
        getter.connect("progress", self._get_csv_progress_cb)
        getter.connect("error", self._get_csv_error_cb)
        _logger.debug("Starting download to %s...", path)
        try:
            getter.start(path)
        except:
            pass
        self._download_content_type = getter.get_content_type()

    def _get_csv_progress_cb(self, getter, bytes_downloaded):
        if self._download_content_length > 0:
            _logger.debug("Downloaded %u of %u bytes...",
                          bytes_downloaded, self._download_content_length)
        else:
            _logger.debug("Downloaded %u bytes...",
                          bytes_downloaded)

    def _get_csv_error_cb(self, getter, err):
        _logger.debug("Error getting CSV: %s", err)
        self._download_content_length = 0
        self._download_content_type = None

    def _get_csv_result_cb(self, getter, tempfile, suggested_name):
        print 'Content type:',  self._download_content_type
        if self._download_content_type.startswith('text/html'):
            # got an error page instead
            self._get_csv_error_cb(getter, 'HTTP Error')
            return
        self.process_downloaded_csv(tempfile,  suggested_name)

    def process_downloaded_csv(self,  tempfile,  suggested_name):
        reader = csv.reader(open(tempfile,  'rb'))
        reader.next()  # skip the first header row.
        for row in reader:
            if len(row) < 7:
                _logger.debug("Server Error",  self.search_url)
                return
            entry = {}
            entry['author'] = row[0]
            entry['description'] = row[1]
            entry['format'] = row[2]
            entry['identifier'] = row[3]
            entry['dcterms_language'] = row[4]
            entry['dcterms_publisher'] = row[5]
            entry['title'] = row[6]
            volume = row[7]
            if volume is not None and len(volume) > 0:
                entry['title'] = row[6] + 'Volume ' + volume

            entry['links'] = {}
            url_base = 'http://www.archive.org/download/' + \
                        row[3] + '/' + row[3]

            if entry['format'].find('DjVu') > -1:
                entry['links']['image/x.djvu'] = url_base + '.djvu'
            if entry['format'].find('Grayscale LuraTech PDF') > -1:
                # Fake mime type
                entry['links']['application/pdf-bw'] = url_base + '_bw.pdf'
            if entry['format'].find('PDF') > -1:
                entry['links']['application/pdf'] = url_base + '_text.pdf'
            if entry['format'].find('EPUB') > -1:
                entry['links']['application/epub+zip'] = url_base + '.epub'
            entry['cover_image'] = 'http://www.archive.org/download/' + \
                        row[3] + '/page/cover_thumb.jpg'

            self.obj._booklist.append(IABook(None, entry, ''))

        os.remove(tempfile)
        GObject.idle_add(self.obj.notify_updated, self.midway)
        self.obj._ready = True
        return False

    def run(self):
        self._download()

    def stop(self):
        self.stopthread.set()


class InternetArchiveQueryResult(QueryResult):

    # Search in internet archive does not use OPDS
    # because the server implementation is not working very well

    def __init__(self, queryterm, language, activity):
        GObject.GObject.__init__(self)
        self._activity = activity
        self._queryterm = queryterm
        self._language = language
        self._next_uri = ''
        self._ready = False
        self._booklist = []
        self._cataloglist = []
        self.threads = []
        self._start_download()

    def notify_updated(self, midway):
        self.emit('updated', midway)

    def _start_download(self, midway=False):
        d_thread = DownloadIAThread(self, midway)
        self.threads.append(d_thread)
        d_thread.start()


class ImageDownloaderThread(threading.Thread):

    def __init__(self, obj):
        threading.Thread.__init__(self)
        self.obj = obj
        self._getter = ReadURLDownloader(self.obj._url)
        self._download_content_length = 0
        self._download_content_type = None
        self.stopthread = threading.Event()

    def _download_image(self):
        path = os.path.join(self.obj._activity.get_activity_root(),
                            'instance', 'tmp%i' % time.time())
        self._getter.connect("finished", self._get_image_result_cb)
        self._getter.connect("progress", self._get_image_progress_cb)
        self._getter.connect("error", self._get_image_error_cb)
        _logger.debug("Starting download to %s...", path)
        try:
            self._getter.start(path)
        except:
            _logger.debug("Connection timed out for")
            GObject.idle_add(self.obj.notify_updated, None)

        self._download_content_length = \
                self._getter.get_content_length()
        self._download_content_type = self._getter.get_content_type()

    def _get_image_result_cb(self, getter, tempfile, suggested_name):
        _logger.debug("Got Cover Image %s (%s)", tempfile, suggested_name)
        self._getter = None
        if not self.stopthread.is_set():
            GObject.idle_add(self.obj.notify_updated, tempfile)

    def _get_image_progress_cb(self, getter, bytes_downloaded):
        if self.stopthread.is_set():
            try:
                _logger.debug('The download %s was cancelled' % getter._fname)
                getter.cancel()
            except:
                _logger.debug('Got an exception while trying ' + \
                        'to cancel download')
        if self._download_content_length > 0:
            _logger.debug("Downloaded %u of %u bytes...", bytes_downloaded,
                        self._download_content_length)
        else:
            _logger.debug("Downloaded %u bytes...",
                          bytes_downloaded)
        while Gtk.events_pending():
            Gtk.main_iteration()

    def _get_image_error_cb(self, getter, err):
        _logger.debug("Error getting image: %s", err)
        self._download_content_length = 0
        self._download_content_type = None
        self._getter = None
        GObject.idle_add(self.obj.notify_updated, None)

    def run(self):
        self._download_image()

    def stop(self):
        self.stopthread.set()


class ImageDownloader(GObject.GObject):

    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([GObject.TYPE_STRING])),
    }

    def __init__(self, activity, url):
        GObject.GObject.__init__(self)
        self.threads = []
        self._activity = activity
        self._url = url
        self._start_download()

    def _start_download(self):
        d_thread = ImageDownloaderThread(self)
        self.threads.append(d_thread)
        d_thread.start()

    def notify_updated(self, temp_file):
        self.emit('updated', temp_file)

    def stop_download(self):
        for thread in self.threads:
            thread.stop()
