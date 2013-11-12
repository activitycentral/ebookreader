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


from gi.repository import GObject
from gi.repository import Gtk
import widgets
import cairo

import math
import os.path
import BeautifulSoup

import epub

import threading

PAGE_WIDTH = 135
PAGE_HEIGHT = 216


def _pixel_to_mm(pixel, dpi):
    inches = pixel / dpi
    return int(inches / 0.03937)


def _mm_to_pixel(mm, dpi):
    inches = mm * 0.03937
    return int(inches * dpi)


class SearchThread(threading.Thread):

    def __init__(self, obj):
        threading.Thread.__init__(self)
        self.obj = obj
        self.stopthread = threading.Event()

    def _start_search(self):
        for entry in self.obj.flattoc:
            if self.stopthread.isSet():
                break
            filepath = os.path.join(self.obj._document.get_basedir(), entry)
            f = open(filepath)
            if self._searchfile(f):
                self.obj._matchfilelist.append(entry)
            f.close()

        Gdk.threads_enter()
        self.obj._finished = True
        self.obj.emit('updated')
        Gdk.threads_leave()

        return False

    def _searchfile(self, fileobj):
        soup = BeautifulSoup.BeautifulSoup(fileobj)
        body = soup.find('body')
        tags = body.findChildren(True)
        for tag in tags:
            if not tag.string is None:
                if tag.string.find(self.obj._text) > -1:
                    return True

        return False

    def run(self):
        self._start_search()

    def stop(self):
        self.stopthread.set()


class _JobPaginator(GObject.GObject):

    __gsignals__ = {
        'paginated': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, filelist):
        GObject.GObject.__init__(self)

        self._filelist = filelist
        self._filedict = {}
        self._pagemap = {}

        self._bookheight = 0
        self._count = 0
        self._pagecount = 0

        self._screen = Gdk.Screen.get_default()
        self._old_fontoptions = self._screen.get_font_options()
        options = cairo.FontOptions()
        options.set_hint_style(cairo.HINT_STYLE_MEDIUM)
        options.set_antialias(cairo.ANTIALIAS_GRAY)
        options.set_subpixel_order(cairo.SUBPIXEL_ORDER_DEFAULT)
        options.set_hint_metrics(cairo.HINT_METRICS_DEFAULT)
        self._screen.set_font_options(options)

        self._temp_win = Gtk.Window()
        self._temp_view = widgets._WebView()

        settings = self._temp_view.get_settings()
        settings.props.default_font_family = 'DejaVu LGC Serif'
        settings.props.sans_serif_font_family = 'DejaVu LGC Sans'
        settings.props.serif_font_family = 'DejaVu LGC Serif'
        settings.props.monospace_font_family = 'DejaVu LGC Sans Mono'
        settings.props.enforce_96_dpi = True
        #FIXME: This does not seem to work
        #settings.props.auto_shrink_images = False
        settings.props.enable_plugins = False
        settings.props.default_font_size = 12
        settings.props.default_monospace_font_size = 10
        settings.props.default_encoding = 'utf-8'

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self._dpi = 96
        sw.set_size_request(_mm_to_pixel(PAGE_WIDTH, self._dpi),
                _mm_to_pixel(PAGE_HEIGHT, self._dpi))
        sw.add(self._temp_view)
        self._temp_win.add(sw)
        self._temp_view.connect('load-finished', self._page_load_finished_cb)

        self._temp_win.show_all()
        self._temp_win.unmap()

        self._temp_view.open(self._filelist[self._count])

    def _page_load_finished_cb(self, v, frame):
        f = v.get_main_frame()
        pageheight = v.get_page_height()

        if pageheight <= _mm_to_pixel(PAGE_HEIGHT, self._dpi):
            pages = 1
        else:
            pages = pageheight / float(_mm_to_pixel(PAGE_HEIGHT, self._dpi))
        for i in range(1, int(math.ceil(pages) + 1)):
            if pages - i < 0:
                pagelen = (pages - math.floor(pages)) / pages
            else:
                pagelen = 1 / pages
            self._pagemap[float(self._pagecount + i)] = \
                    (f.props.uri, (i - 1) / math.ceil(pages), pagelen)

        self._pagecount += int(math.ceil(pages))
        self._filedict[f.props.uri.replace('file://', '')] = \
                (math.ceil(pages), math.ceil(pages) - pages)
        self._bookheight += pageheight

        if self._count + 1 >= len(self._filelist):
            self._temp_win.destroy()
            self._screen.set_font_options(self._old_fontoptions)
            self.emit('paginated')
        else:
            self._count += 1
            self._temp_view.open(self._filelist[self._count])

    def get_file_for_pageno(self, pageno):
        '''
        Returns the file in which pageno occurs
        '''
        return self._pagemap[pageno][0]

    def get_scrollfactor_pos_for_pageno(self, pageno):
        '''
        Returns the position scrollfactor (fraction) for pageno
        '''
        return self._pagemap[pageno][1]

    def get_scrollfactor_len_for_pageno(self, pageno):
        '''
        Returns the length scrollfactor (fraction) for pageno
        '''
        return self._pagemap[pageno][2]

    def get_pagecount_for_file(self, filename):
        '''
        Returns the number of pages in file
        '''
        return self._filedict[filename][0]

    def get_base_pageno_for_file(self, filename):
        '''
        Returns the pageno which begins in filename
        '''
        for key in self._pagemap.keys():
            if  self._pagemap[key][0].replace('file://', '') == filename:
                return key

        return None

    def get_remfactor_for_file(self, filename):
        '''
        Returns the remainder
        factor (1 - fraction length of last page in file)
        '''
        return self._filedict[filename][1]

    def get_total_pagecount(self):
        '''
        Returns the total pagecount for the Epub file
        '''
        return self._pagecount

    def get_total_height(self):
        '''
        Returns the total height of the Epub in pixels
        '''
        return self._bookheight


class _JobFind(GObject.GObject):
    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, document, start_page, n_pages, text,
            case_sensitive=False):
        GObject.GObject.__init__(self)
        Gdk.threads_init()

        self._finished = False
        self._document = document
        self._start_page = start_page
        self._n_pages = n_pages
        self._text = text
        self._case_sensitive = case_sensitive
        self.flattoc = self._document.get_flattoc()
        self._matchfilelist = []
        self._current_file_index = 0
        self.threads = []

        s_thread = SearchThread(self)
        self.threads.append(s_thread)
        s_thread.start()

    def cancel(self):
        '''
        Cancels the search job
        '''
        for s_thread in self.threads:
            s_thread.stop()

    def is_finished(self):
        '''
        Returns True if the entire search job has been finished
        '''
        return self._finished

    def get_next_file(self):
        '''
        Returns the next file which has the search pattern
        '''
        self._current_file_index += 1
        try:
            path = self._matchfilelist[self._current_file_index]
        except IndexError:
            self._current_file_index = 0
            path = self._matchfilelist[self._current_file_index]

        return path

    def get_prev_file(self):
        '''
        Returns the previous file which has the search pattern
        '''
        self._current_file_index -= 1
        try:
            path = self._matchfilelist[self._current_file_index]
        except IndexError:
            self._current_file_index = -1
            path = self._matchfilelist[self._current_file_index]

        return path

    def get_search_text(self):
        '''
        Returns the search text
        '''
        return self._text

    def get_case_sensitive(self):
        '''
        Returns True if the search is case-sensitive
        '''
        return self._case_sensitive


def get_number_of_pages_given_page_height(pageheight):
    if pageheight <= _mm_to_pixel(PAGE_HEIGHT, 96):
        return 1
    else:
        return int(math.ceil(pageheight / float(_mm_to_pixel(PAGE_HEIGHT, 96))))
