
# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007 Collabora Ltd. <http://www.collabora.co.uk/>
# Copyright 2008 One Laptop Per Child
# Copyright 2009 Simon Schampijer
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
import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics import iconentry
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.icon import Icon
from sugar3.activity.widgets import StopButton
from sugar3 import mime

from widgets import constants
from mode import Mode
from ebookreadertab import EBookReaderTab
from secondarytoolbarbutton import SecondaryToolbarButton

from readtoolbar import ViewToolbar
from readsidebar import Sidebar
from readdb import BookmarkManager

import epubadapter
import evinceadapter
import env_settings as env

MAXIMUM_ZOOM_OUTS = -5
MAXIMUM_ZOOM_INS  =  10
MAX_SCALE = 1.8
MIN_SCALE = 0.6

_logger = logging.getLogger(__name__)


def _get_screen_dpi():
    xft_dpi = Gtk.Settings.get_default().get_property('gtk-xft-dpi')
    _logger.debug('Setting dpi to %f', float(xft_dpi / 1024))
    return float(xft_dpi / 1024)


class SecondaryToolBar(Gtk.Toolbar):
    def __init__(self, main_widget):
        Gtk.Toolbar.__init__(self)

        self._event_box = Gtk.EventBox()
        self._event_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#000000'))
        self._event_box.add(self)
        self.show_all()

        TYPE_LEFT_AND_RIGHT = 1
        TYPE_TOP_AND_BOTTOM = 2
        TYPE_INDIVIDUAL = 3
        TYPE_CUSTOM = 4

        self._main_widget = main_widget

        self.dummy_view_toolbar = ViewToolbar()

        buttons_list = [
                [
                    TYPE_INDIVIDUAL,
                    _('Previous Bookmark'),
                    'bookreader-left',
                    self._main_widget._prev_bookmark_activate_cb,
                    Gtk.IconSize.SMALL_TOOLBAR,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Toggle Bookmark'),
                    'bookreader-addmark',
                    self._main_widget._toggle_bookmark_activate_cb,
                    Gtk.IconSize.LARGE_TOOLBAR,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Next Bookmark'),
                    'bookreader-right',
                    self._main_widget._next_bookmark_activate_cb,
                    Gtk.IconSize.SMALL_TOOLBAR,
                    2
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Decrease size'),
                    'bookreader-textsizedown',
                    self.dummy_view_toolbar._zoom_out_cb,
                    Gtk.IconSize.SMALL_TOOLBAR,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Increase size'),
                    'bookreader-textsizeup',
                    self.dummy_view_toolbar._zoom_in_cb,
                    Gtk.IconSize.SMALL_TOOLBAR,
                    2
                ],
                [
                    TYPE_CUSTOM,
                    self._add_search_entry,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Search Previous'),
                    'bookreader-prev',
                    self._find_prev_cb,
                    Gtk.IconSize.LARGE_TOOLBAR,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Search Next'),
                    'bookreader-next',
                    self._find_next_cb,
                    Gtk.IconSize.LARGE_TOOLBAR,
                    2
                ],
                [
                    TYPE_CUSTOM,
                    self._add_current_location_entry,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Go to location'),
                    'bookreader-gotopage',
                    self._main_widget._go_to_location,
                    Gtk.IconSize.LARGE_TOOLBAR,
                    0
                ],
                [
                    TYPE_INDIVIDUAL,
                    _('Fullscreen'),
                    'bookreader-view-fullscreen',
                    self._main_widget.fullscreen,
                    Gtk.IconSize.LARGE_TOOLBAR,
                    0
                ],
                       ]

        for item in buttons_list:
            hbox = Gtk.HBox(homogeneous=False)
            hbox.set_spacing(int(0.5 * style.DEFAULT_SPACING))

            button_type = item[0]

            if button_type == TYPE_TOP_AND_BOTTOM:
                icon_size = Gtk.IconSize.LARGE_TOOLBAR

                hbox.pack_start(Icon(icon_name=item[2],
                                     icon_size=icon_size), False,
                                     False, 0)

                vbox = Gtk.VBox(homogeneous=True)
                top_widget = SecondaryToolbarButton('bookreader-up',
                                                    ('Zoom In'),
                                                    item[3],
                                                    Gtk.IconSize.SMALL_TOOLBAR)
                vbox.pack_start(top_widget, True, True, 0)

                bottom_widget = SecondaryToolbarButton('bookreader-down',
                                                       ('Zoom Out'),
                                                       item[4],
                                                       Gtk.IconSize.SMALL_TOOLBAR)
                vbox.pack_start(bottom_widget, True, True, 0)

                hbox.pack_start(vbox, False, False, 0)

                widget = hbox

            elif button_type == TYPE_INDIVIDUAL:
                if item[3] == None:
                    widget = Icon(icon_name=item[2], icon_size=item[4])
                else:
                    widget = SecondaryToolbarButton(item[2], item[1], item[3], item[4])

                # HACK
                if item[3] == self._find_prev_cb:
                    self._prev_search_widget = widget
                elif item[3] == self._find_next_cb:
                    self._next_search_widget = widget
                elif item[3] == self.dummy_view_toolbar._zoom_in_cb:
                    self._zoom_in_widget = widget
                elif item[3] == self.dummy_view_toolbar._zoom_out_cb:
                    self._zoom_out_widget = widget

            elif button_type == TYPE_CUSTOM:
                item[1]()
                continue

            toolitem = Gtk.ToolItem()
            toolitem.add(widget)
            self.insert(toolitem, -1)

            string = ''
            for i in range(0, item[-1]):
                string = string + ' '
            toolitem = Gtk.ToolItem()
            toolitem.add(Gtk.Label(string))
            self.insert(toolitem, -1)
            widget.show()

        self._prev_search_widget.set_sensitive(False)
        self._next_search_widget.set_sensitive(False)

        self.show_all()

    def set_view(self, view):
        self.dummy_view_toolbar.set_view(view)

    def set_bookmarkmanager(self, bookmarkmanager):
        self.dummy_view_toolbar.set_bookmarkmanager(bookmarkmanager)

    def _add_current_location_entry(self):
        self._location_entry = iconentry.IconEntry()
        self._location_entry.set_sensitive(True)

        self._location_entry.set_width_chars(8)

        # Add a label too, for PDFs.
        self._pdf_label = Gtk.Label()

        box = Gtk.HBox()
        box.pack_start(self._location_entry, False, False, 0)
        box.pack_start(self._pdf_label, False, False, 0)

        toolitem = Gtk.ToolItem()
        toolitem.add(box)
        self.insert(toolitem, -1)
        self.add_spacing()

    def _add_search_entry(self):
        self._text_changed = False

        self._search_entry = iconentry.IconEntry()
        self._search_entry.connect('changed', self._find_first_cb)
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self._search_entry.add_clear_button()

        width = int(Gdk.Screen.width() / 6)
        self._search_entry.set_size_request(width, -1)

        self._search_entry.show()
        toolitem = Gtk.ToolItem()
        toolitem.add(self._search_entry)
        self.insert(toolitem, -1)
        self.add_spacing()

    def add_spacing(self):
        toolitem = Gtk.ToolItem()
        toolitem.add(Gtk.Label('  '))
        self.insert(toolitem, -1)

    def _find_first_cb(self, widget):
        self._text_changed = True
        self._prev_search_widget.set_sensitive(False)
        if self._search_entry.get_text() == '':
            self._next_search_widget.set_sensitive(False)
        else:
            self._next_search_widget.set_sensitive(True)


    def _find_prev_cb(self, widget):
        self._main_widget._view.find_text_prev(self._search_entry.get_text())

    def _find_next_cb(self, widget):
        self._main_widget._view.find_text_next(self._search_entry.get_text(),
                self._text_changed)
        self._text_changed = False
        self._prev_search_widget.set_sensitive(True)


class ReadTab(EBookReaderTab, Mode):
    """The Read sugar activity."""

    def __init__(self, app):
        EBookReaderTab.__init__(self, app)

        _logger.debug('Starting Read...')

        self._app = app
        self._view = Gtk.Label(_('No file opened'))
        self.dpi = _get_screen_dpi()
        self._sidebar = Sidebar()
        self.secondary_toolbar = SecondaryToolBar(self)
        self.secondary_toolbar.set_sensitive(False)

        self._bookmark_widget_added = False

        self._sync_func_id = None

        self.pack_start(self._view, True, True, 0)

        self._special_dual_keys = ['s', 'a', 'w', 'd', 'plus', 'minus',
                                   'space', 'Left', 'Right']
        self._bookmarkmanager = BookmarkManager(None, None, self)

    def init_key_handler_map_if_not_already(self):
        Mode.__init__(self, self.get_main_window())

        if self._key_handler_map is not None:
            return

        self._key_handler_map = {
                'Up'          : [self._view.handle_up_keys],
                'KP_Up'       : [self._view.handle_up_keys],
                'Down'        : [self._view.handle_down_keys],
                'KP_Down'     : [self._view.handle_down_keys],
                'Left'        : [self._view.handle_left_keyboard_key],
                'KP_Left'     : [self._view.handle_left_game_key],
                'Right'       : [self._view.handle_right_keyboard_key],
                'KP_Right'    : [self._view.handle_right_game_key],
                'plus'        : [self.secondary_toolbar.dummy_view_toolbar._zoom_in_cb, (None,)],
                'minus'       : [self.secondary_toolbar.dummy_view_toolbar._zoom_out_cb, (None,)],
                'Tab'         : [self._next_bookmark_activate_cb, (None,)],
                'Page_Up'     : [self._view.handle_page_up_key],
                'Page_Down'   : [self._view.handle_page_down_key],
                'KP_Home'     : [self.switch_to_zoom_mode],
                'KP_Page_Up'  : [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_Page_Up',)],
                'KP_End'      : [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_End',)],
                'KP_Page_Down': [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_Page_Down',)],
                'Return'      : [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_End',)],
                'space'       : [self.toggle_fullscreen],
                's'           : [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_Page_Down',)],
                'a'           : [self.switch_to_zoom_mode],
                'w'           : [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_Page_Up',)],
                'd'           : [self._app._process_bookmarks_in_ebook_mode_widget.do_operation, ('KP_End',)],
                               }

    def get_tab_toolbar(self):
        return self.secondary_toolbar._event_box

    def get_tab_toolbar_icon_name(self):
        return 'bookreader-read'

    def get_tab_label(self):
        return _('Read')

    def take_action_for_key_press(self, widget, event):
        return self._key_press_event_cb(widget, event)

    def toggle_fullscreen(self):
        window = self.get_main_window().window
        if window._is_fullscreen is True:
            window.unfullscreen()
        else:
            window.fullscreen()

    def fullscreen(self, widget):
        self.get_main_window().window.fullscreen()

    def _load_document(self, (filepath, journal_id,), file_encrypted,
                       original_path=None):
        self._epub_loaded = False
        if self._sync_func_id is not None:
            GObject.source_remove(self._sync_func_id)

        for child in self.get_children():
            self.remove(child)

        if self._bookmark_widget_added is True:
            self.get_main_window()._bookmark_widget.unparent()

        if filepath is not None:
            filename = filepath.replace('file://', '')
        else:
            self._view = Gtk.Label(_('File failed to load'))
            self.pack_start(self._view, True, True, 0)
            return

        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return

        mimetype = mime.get_for_file(filepath)
        if mimetype == 'application/epub+zip':
            self._view = epubadapter.EpubViewer(self.get_main_window(), self._app)
            self._epub_loaded = True
        elif mimetype == 'text/plain' or mimetype == 'application/zip':
            self._view = textadapter.TextViewer()
        else:
            self._view = evinceadapter.EvinceViewer(self.get_main_window(), self._app)

        self.secondary_toolbar.set_sensitive(True)
        self._view.setup()

        if journal_id is None:
            if original_path is None:
                self._basename = os.path.basename(filename)
            else:
                self._basename = os.path.basename(original_path.replace('file://', ''))
        else:
            self._basename = journal_id

        from utils import get_md5
        self._filehash = get_md5(filepath)

        metadata = self.get_metadata(self._filehash)

        sub_file_number = 0
        if len(metadata.keys()) > 0:
            sub_file_number = int(metadata['sub_file_number'])

        self._view.load_document(filepath, sub_file_number, metadata, self)

        if file_encrypted is True:
            os.remove(filepath.replace('file://', ''))

        # Also, update the zoom-icons of the secondary-menu.
        zoom_icons = self._view.get_zoom_icons()
        self.secondary_toolbar._zoom_in_widget.get_icon_widget().props.icon_name  = zoom_icons[2]
        self.secondary_toolbar._zoom_out_widget.get_icon_widget().props.icon_name = zoom_icons[3]

        self._sync_func_id = GObject.timeout_add(500, self.sync_up)

        self.secondary_toolbar.set_view(self._view)

        # Add the document-container.
        self.pack_start(self.secondary_toolbar._event_box, False, False, 0)

        overlay = Gtk.Overlay()
        overlay.add(self._view)
        overlay.add_overlay(self.get_main_window()._bookmark_widget)
        self._bookmark_widget_added = True

        self.pack_start(overlay, True, True, 0)
        overlay.show()

        if self._epub_loaded == True:
            progress_bar = Gtk.ProgressBar()
            self.pack_start(progress_bar, False, False, 0)
            self._view.set_progress_bar(progress_bar)

        # Generate the boomark-manager for the recently opened file.
        self._bookmarkmanager = BookmarkManager(self._filehash, self._view, self)
        self._sidebar.set_bookmarkmanager(self._bookmarkmanager)
        self._sidebar.set_view(self._view)

        self.secondary_toolbar.set_bookmarkmanager(self._bookmarkmanager)

        self.secondary_toolbar.show_all()
        self._view.show_all()

    def sync_up(self):
        self._add_or_remove_bookmark_in_UI()
        self._view.do_view_specific_sync_operations()

        if not self.secondary_toolbar._location_entry.has_focus():
            self.secondary_toolbar._location_entry.set_text(str(int(float(self._view.get_current_location()))))
        self.secondary_toolbar._pdf_label.set_text(self._view.get_location_label_text())

        return True

    def _go_to_location(self, menuitem):
        location_text = self.secondary_toolbar._location_entry.get_text()

        # Hack to remove the focus.
        self.secondary_toolbar._location_entry.hide()
        self.secondary_toolbar._location_entry.show()

        self._view.go_to_location(location_text)

    def _toggle_bookmark_activate_cb(self, menuitem):
        self._view.hide()

        if self._bookmarkmanager.is_current_page_bookmarked(self._view._number_of_times_zoomed):
            GObject.idle_add(self._sidebar.del_bookmark, self._view._number_of_times_zoomed)
        else:
            GObject.idle_add(self._sidebar.add_bookmark, self._view._number_of_times_zoomed)

        GObject.idle_add(self._view.show)

    def _prev_bookmark_activate_cb(self, menuitem):
        prev_bookmark = \
                self._bookmarkmanager.get_prev_bookmark(self._view._number_of_times_zoomed)
        if prev_bookmark is not None:
            self._view.go_to_bookmark(prev_bookmark.subfilenumber,
                                      prev_bookmark.identifier)

    def _next_bookmark_activate_cb(self, menuitem):
        next_bookmark = \
                self._bookmarkmanager.get_next_bookmark(self._view._number_of_times_zoomed)
        if next_bookmark is not None:
            self._view.go_to_bookmark(next_bookmark.subfilenumber,
                                      next_bookmark.identifier)

    def _add_or_remove_bookmark_in_UI(self, first=None, second=None,
                                      third=None):
        if not self._view.is_view_fully_available():
            return True

        if self._bookmarkmanager.is_current_page_bookmarked(self._view._number_of_times_zoomed):
            # Only show the bookmark-widget, if we are in  "Reader"
            # tab.
            if self._app.pages_list[self.get_main_window()._last_page] == get_reader_tab():
                self.get_main_window()._bookmark_widget.show_overlay_widget()
        else:
            self.get_main_window()._bookmark_widget.hide()

        return True

    def _key_press_event_cb(self, widget, event):
        # Initialize the key-handlers maps for all the modes.
        app = self.get_main_window()
        for key in app._modes.keys():
            app._modes[key].init_key_handler_map_if_not_already()

        keyname = Gdk.keyval_name(event.keyval)

        # If the keyname is any of the keys that can be used as text in
        # "search-box", and if the search-box, or the location-box has focus, return, and
        # process the key from the search-perspective.
        if (keyname in self._special_dual_keys) and \
           ((self.secondary_toolbar._search_entry.has_focus() is True) or \
            (self.secondary_toolbar._location_entry.has_focus() is True)):
            return False

        # If the search-text has focus, and the "Returh" key is
        # pressed, do "Search Next".
        if (keyname == 'Return') and \
           (self.secondary_toolbar._search_entry.has_focus() is True):
            self.secondary_toolbar._find_next_cb(None)
            return True

        # If the location-box has focus, and the "Returh" key is
        # pressed, go to the location.
        if (keyname == 'Return') and \
           (self.secondary_toolbar._location_entry.has_focus() is True):
            self._go_to_location(None)
            return True

        # Now, if the search-entry does not have focus, we should not
        # process the 'a' key, on non-XO machines.
        from utils import is_machine_a_xo
        if (keyname == 'a') and (is_machine_a_xo() is False):
            return True


        # If the keyname is not mapped to any of the modes, return
        # False, so that the key can be processed natively.
        mapping_found = False
        for key in app._modes.keys():
            mode = app._modes[key]
            if keyname in mode._key_handler_map.keys():
                mapping_found = True
                break
        if mapping_found == False:
            return False

        current_mode = app.get_mode()
        if keyname in current_mode._key_handler_map.keys():
            current_mode.now_handle_key(current_mode._key_handler_map[keyname])

        return True

    def switch_to_zoom_mode(self):
        self._app.set_mode(self._app._modes[constants.MODE_ZOOM])
        self._app._process_zoom_in_ebook_mode_widget.show_idle_state()

    def hide_related_stuff_when_switching_tab(self):
        self.get_main_window()._process_zoom_in_ebook_mode_widget.switch_to_normal_mode()
        self.get_main_window()._process_files_in_ebook_mode_widget.switch_to_normal_mode()
        self.get_main_window()._bookmark_widget.hide()
