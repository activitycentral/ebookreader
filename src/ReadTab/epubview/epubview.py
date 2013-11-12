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

from gi.repository import Gtk
from gi.repository import GObject
import widgets

import os.path
import math
import shutil
import BeautifulSoup

from epub import _Epub
from jobs import _JobPaginator as _Paginator
from jobs import get_number_of_pages_given_page_height

LOADING_HTML = '''
<div style="width:100%;height:100%;text-align:center;padding-top:50%;">
    <h1>Loading...</h1>
</div>
'''


class _View(Gtk.HBox):

    __gproperties__ = {
        'scale': (GObject.TYPE_FLOAT, 'the zoom level',
                   'the zoom level of the widget',
                   0.5, 4.0, 1.0, GObject.PARAM_READWRITE),
    }
    __gsignals__ = {
        'page-changed': (GObject.SignalFlags.RUN_FIRST, None,
                ([int, int])),
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None,
                              ([])),
    }

    def __init__(self):
        GObject.threads_init()
        Gtk.HBox.__init__(self)

        self.connect("destroy", self._destroy_cb)

        self._ready = False
        self._paginator = None
        self._loaded_page = -1
        #self._old_scrollval = -1
        self._loaded_filename = None
        self.__going_fwd = True
        self.__going_back = False
        self.__page_changed = False
        self._has_selection = False
        self.scale = 1.0
        self._epub = None
        self._findjob = None
        self.__in_search = False
        self.__search_fwd = True

        self._sw = Gtk.ScrolledWindow()
        self._view = widgets._WebView()
        self._view.load_string(LOADING_HTML, 'text/html', 'utf-8', '/')
        settings = self._view.get_settings()
        settings.props.default_font_family = 'DejaVu LGC Serif'
        settings.props.enable_plugins = False
        settings.props.default_encoding = 'utf-8'
        self._view.connect('load-finished', self._view_load_finished_cb)
        self._view.connect('scroll-event', self._view_scroll_event_cb)
        self._view.connect('selection-changed',
                self._view_selection_changed_cb)
        self._view.connect_after('populate-popup',
                self._view_populate_popup_cb)

        self._sw.add(self._view)
        self._sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self._v_vscrollbar = self._sw.get_vscrollbar()
        self._v_vscrollbar.set_child_visible(False)

        self.pack_start(self._sw, True, True, 0)

        self._view.set_flags(Gtk.CAN_DEFAULT | Gtk.CAN_FOCUS)

    def set_document(self, epubdocumentinstance):
        '''
        Sets document (should be a Epub instance)
        '''
        self._epub = epubdocumentinstance
        GObject.idle_add(self._paginate)

    def do_get_property(self, property):
        if property.name == 'has-selection':
            return self._has_selection
        elif property.name == 'scale':
            return self.scale
        else:
            raise AttributeError('unknown property %s' % property.name)

    def do_set_property(self, property, value):
        if property.name == 'scale':
            self.__set_zoom(value)
        else:
            raise AttributeError('unknown property %s' % property.name)

    def get_has_selection(self):
        '''
        Returns True if any part of the content is selected
        '''
        return self._has_selection

    def get_zoom(self):
        '''
        Returns the current zoom level
        '''
        return self.get_property('scale') * 100.0

    def set_zoom(self, value):
        '''
        Sets the current zoom level
        '''
        self._view.set_zoom_level(value / 100.0)

    def _get_scale(self):
        '''
        Returns the current zoom level
        '''
        return self.get_property('scale')

    def _set_scale(self, value):
        '''
        Sets the current zoom level
        '''
        self.set_property('scale', value)

    def get_current_number_of_pages(self):
        page_height = self._view.get_page_height()
        current_number_of_pages = get_number_of_pages_given_page_height(page_height)
        return current_number_of_pages

    def zoom_in(self):
        '''
        Zooms in (increases zoom level by 0.1)
        '''
        if self.can_zoom_in():
            self._set_scale(self._get_scale() + 0.1)
            self._load_page(1)
            return True
        else:
            return False

    def zoom_out(self):
        '''
        Zooms out (decreases zoom level by 0.1)
        '''
        if self.can_zoom_out():
            self._set_scale(self._get_scale() - 0.1)
            self._load_page(1)
            return True
        else:
            return False

    def can_zoom_in(self):
        '''
        Returns True if it is possible to zoom in further
        '''
        if self.scale < 4:
            return True
        else:
            return False

    def can_zoom_out(self):
        '''
        Returns True if it is possible to zoom out further
        '''
        if self.scale > 0.5:
            return True
        else:
            return False

    def get_current_page(self):
        '''
        Returns the currently loaded page
        '''
        return self._loaded_page

    def get_current_file(self):
        '''
        Returns the currently loaded XML file
        '''
        #return self._loaded_filename
        if self._paginator:
            return self._paginator.get_file_for_pageno(self._loaded_page)
        else:
            return None

    def scroll(self, scrolltype, horizontal):
        '''
        Scrolls through the pages.
        Scrolling is horizontal if horizontal is set to True
        Valid scrolltypes are:
        Gtk.ScrollType.PAGE_BACKWARD, Gtk.ScrollType.PAGE_FORWARD,
        Gtk.ScrollType.STEP_BACKWARD, Gtk.ScrollType.STEP_FORWARD
        Gtk.ScrollType.STEP_START and Gtk.ScrollType.STEP_STOP
        '''
        if scrolltype == Gtk.ScrollType.PAGE_BACKWARD:
            self.__going_back = True
            self.__going_fwd = False
            if not self._do_page_transition():
                self._view.move_cursor(Gtk.MovementStep.PAGES, -1)
        elif scrolltype == Gtk.ScrollType.PAGE_FORWARD:
            self.__going_back = False
            self.__going_fwd = True
            if not self._do_page_transition():
                self._view.move_cursor(Gtk.MovementStep.PAGES, 1)
        elif scrolltype == Gtk.ScrollType.STEP_BACKWARD:
            self.__going_fwd = False
            self.__going_back = True
            if not self._do_page_transition():
                self._view.move_cursor(Gtk.MovementStep.DISPLAY_LINES, -1)
        elif scrolltype == Gtk.ScrollType.STEP_FORWARD:
            self.__going_fwd = True
            self.__going_back = False
            if not self._do_page_transition():
                self._view.move_cursor(Gtk.MovementStep.DISPLAY_LINES, 1)
        elif scrolltype == Gtk.ScrollType.START:
            self.__going_back = True
            self.__going_fwd = False
            if not self._do_page_transition():
                self.set_current_page(1)
        elif scrolltype == Gtk.ScrollType.END:
            self.__going_back = False
            self.__going_fwd = True
            #if not self._do_page_transition():
            #    self.set_current_page(self._pagecount - 1)
        else:
            print ('Got unsupported scrolltype %s' % str(scrolltype))

    def copy(self):
        '''
        Copies the current selection to clipboard.
        '''
        self._view.copy_clipboard()

    def find_next(self):
        '''
        Highlights the next matching item for current search
        '''
        self._view.grab_focus()
        self._view.grab_default()

        if self._view.search_text(self._findjob.get_search_text(),
                self._findjob.get_case_sensitive(),
                True, False):
            return
        else:
            path = os.path.join(self._epub.get_basedir(),
                    self._findjob.get_next_file())
            self.__in_search = True
            self.__search_fwd = True
            self._load_file(path)

    def find_previous(self):
        '''
        Highlights the previous matching item for current search
        '''
        self._view.grab_focus()
        self._view.grab_default()

        if self._view.search_text(self._findjob.get_search_text(),
                                self._findjob.get_case_sensitive(),
                                False, False):
            return
        else:
            path = os.path.join(self._epub.get_basedir(),
                    self._findjob.get_prev_file())
            self.__in_search = True
            self.__search_fwd = False
            self._load_file(path)

    def _find_changed(self, job):
        self._view.grab_focus()
        self._view.grab_default()
        self._findjob = job
        self.find_next()

    def __set_zoom(self, value):
        self._view.set_zoom_level(value)
        self.scale = value

    def __set_has_selection(self, value):
        if value != self._has_selection:
            self._has_selection = value
            self.emit('selection-changed')

    def _view_populate_popup_cb(self, view, menu):
        menu.destroy()  # HACK
        return

    def _view_selection_changed_cb(self, view):
        # FIXME: This does not seem to be implemented in
        # webkitgtk yet
        print "epubview _view_selection_changed_cb", view.has_selection()
        self.__set_has_selection(view.has_selection())

    def _view_buttonrelease_event_cb(self, view, event):
        # Ugly hack
        print "epubview _view_buttonrelease_event_cb", view.has_selection(), \
                view.can_copy_clipboard(), view.can_cut_clipboard()
        self.__set_has_selection(view.can_copy_clipboard() \
                                 | view.can_cut_clipboard())

    def _view_keypress_event_cb(self, view, event):
        name = Gdk.keyval_name(event.keyval)
        if name == 'Page_Down' or name == 'Down':
            self.__going_back = False
            self.__going_fwd = True
        elif name == 'Page_Up' or name == 'Up':
            self.__going_back = True
            self.__going_fwd = False

        self._do_page_transition()

    def _view_scroll_event_cb(self, view, event):
        if event.direction == Gdk.ScrollDirection.DOWN:
            self.__going_back = False
            self.__going_fwd = True
        elif event.direction == Gdk.ScrollDirection.UP:
            self.__going_back = True
            self.__going_fwd = False

        self._do_page_transition()

    def _do_page_transition(self):
        if self.__going_fwd:
            if self._v_vscrollbar.get_value() >= \
                self._v_vscrollbar.props.adjustment.props.upper - \
                    self._v_vscrollbar.props.adjustment.props.page_size:
                self._load_next_file()
                return True
        elif self.__going_back:
            if self._v_vscrollbar.get_value() == \
                    self._v_vscrollbar.props.adjustment.props.lower:
                self._load_prev_file()
                return True

        return False

    def _view_load_finished_cb(self, v, frame):
        # Normally the line below would not be required - ugly workaround for
        # possible Webkit bug. See : https://bugs.launchpad.net/bugs/483231
        #self._sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)

        filename = self._view.props.uri.replace('file://', '')
        if os.path.exists(filename.replace('xhtml', 'xml')):
            # Hack for making javascript work
            filename = filename.replace('xhtml', 'xml')

        filename = filename.split('#')[0]  # Get rid of anchors

        if self._loaded_page < 1 or filename == None:
            return False

        self._loaded_filename = filename

        remfactor = self._paginator.get_remfactor_for_file(filename)
        pages = self._paginator.get_pagecount_for_file(filename)
        extra = int(math.ceil(remfactor *
                self._view.get_page_height() / (pages - remfactor)))
        if extra > 0:
            self._view.add_bottom_padding(extra)

        if self.__in_search:
            self._view.search_text(self._findjob.get_search_text(), \
                               self._findjob.get_case_sensitive(), \
                               self.__search_fwd, False)
            self.__in_search = False
        else:
            if self.__going_back:
                # We need to scroll to the last page
                self._scroll_page_end()
            else:
                self._scroll_page()

        base_pageno = self._paginator.get_base_pageno_for_file(filename)
        scrollval = self._v_vscrollbar.get_value()
        scroll_upper = self._v_vscrollbar.props.adjustment.props.upper

        if scroll_upper == 0:  # This is a one page file
            pageno = base_pageno
        else:
            offset = (scrollval / scroll_upper) * \
                    self._paginator.get_pagecount_for_file(filename)
            pageno = math.floor(base_pageno + offset)

        if pageno != self._loaded_page:
            self._on_page_changed(0, int(pageno))

        # prepare text to speech
        html_file = open(self._loaded_filename)
        soup = BeautifulSoup.BeautifulSoup(html_file)
        body = soup.find('body')
        tags = body.findAll(text=True)
        self._all_text = ''.join([tag for tag in tags])
        self._prepare_text_to_speech(self._all_text)

    def _prepare_text_to_speech(self, page_text):
        i = 0
        j = 0
        word_begin = 0
        word_end = 0
        ignore_chars = [' ',  '\n',  u'\r',  '_',  '[', '{', ']', '}', '|',
                '<',  '>',  '*',  '+',  '/',  '\\']
        ignore_set = set(ignore_chars)
        self.word_tuples = []
        len_page_text = len(page_text)
        while i < len_page_text:
            if page_text[i] not in ignore_set:
                word_begin = i
                j = i
                while  j < len_page_text and page_text[j] not in ignore_set:
                    j = j + 1
                    word_end = j
                    i = j
                word_tuple = (word_begin, word_end,
                        page_text[word_begin: word_end])
                if word_tuple[2] != u'\r':
                    self.word_tuples.append(word_tuple)
            i = i + 1

    def _scroll_page_end(self):
        v_upper = self._v_vscrollbar.props.adjustment.props.upper
        v_page_size = self._v_vscrollbar.props.adjustment.props.page_size
        self._v_vscrollbar.set_value(v_upper)

    def _scroll_page(self):
        pageno = self._loaded_page

        v_upper = self._v_vscrollbar.props.adjustment.props.upper
        v_page_size = self._v_vscrollbar.props.adjustment.props.page_size

        scrollfactor = self._paginator.get_scrollfactor_pos_for_pageno(pageno)
        self._v_vscrollbar.set_value((v_upper - v_page_size) * scrollfactor)

    def _paginate(self):
        filelist = []
        for i in self._epub._navmap.get_flattoc():
            filelist.append(os.path.join(self._epub._tempdir, i))

        self._paginator = _Paginator(filelist)
        self._paginator.connect('paginated', self._paginated_cb)

    def _load_next_page(self):
        self._load_page(self._loaded_page + 1)

    def _load_prev_page(self):
        self._load_page(self._loaded_page - 1)

    def _on_page_changed(self, oldpage, pageno):
        self.__page_changed = True
        self._loaded_page = pageno
        self.emit('page-changed', oldpage, pageno)

    def _load_page(self, pageno):
        self._on_page_changed(self._loaded_page, pageno)
        filename = self._paginator.get_file_for_pageno(pageno)
        if filename != self._loaded_filename:
            #self._loaded_filename = filename

            """
            TODO: disabled because javascript can't be executed
            with the velocity needed
            # Copy javascript to highligth text to speech
            destpath, destname = os.path.split(filename.replace('file://', ''))
            shutil.copy('./epubview/highlight_words.js', destpath)
            self._insert_js_reference(filename.replace('file://', ''),
                    destpath)
            """

            if filename.endswith('xml'):
                dest = filename.replace('xml', 'xhtml')
                shutil.copy(filename.replace('file://', ''),
                        dest.replace('file://', ''))
                self._view.open(dest)
            else:
                self._view.open(filename)
        else:
            self._scroll_page()

    def _insert_js_reference(self, file_name, path):
        js_reference = '<script type="text/javascript" ' + \
                'src="./highlight_words.js"></script>'
        o = open(file_name + '.tmp', 'a')
        for line in open(file_name):
            line = line.replace('</head>', js_reference + '</head>')
            o.write(line + "\n")
        o.close()
        shutil.copy(file_name + '.tmp', file_name)

    def _load_next_file(self):
        cur_file = self._paginator.get_file_for_pageno(self._loaded_page)
        pageno = self._loaded_page
        while pageno < self._paginator.get_total_pagecount():
            pageno += 1
            if self._paginator.get_file_for_pageno(pageno) != cur_file:
                break

        self._load_page(pageno)

    def _load_file(self, path):
        #TODO: This is a bit suboptimal - fix it
        for pageno in range(1, self.get_pagecount()):
            filepath = self._paginator.get_file_for_pageno(pageno)
            if filepath.endswith(path):
                self._load_page(pageno)
                break

    def _load_prev_file(self):
        if self._loaded_page == 1:
            return
        cur_file = self._paginator.get_file_for_pageno(self._loaded_page)
        pageno = self._loaded_page
        while pageno > 1:
            pageno -= 1
            if self._paginator.get_file_for_pageno(pageno) != cur_file:
                break

        self._load_page(pageno)

    def _paginated_cb(self, object):
        self._ready = True

        self._view.grab_focus()
        self._view.grab_default()
        if self._loaded_page < 1:
            self._load_page(1)

    def _destroy_cb(self, widget):
        self._epub.close()
