#!/usr/bin/env python

import os
import subprocess
import platform
import shutil
import env_settings as env

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
import sys
from utils import get_active_desktop

from sugar3.graphics.notebook import Notebook
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbarbox import ToolbarButton
from gi.repository import SugarExt

from widgets import constants
from mode import Mode

from gettext import gettext as _



from GetBooksTab.getbookstab import GetBooksTab
from MyLibraryTab.mylibrarytab import MyLibraryTab
from ReadTab.readtab import ReadTab
from HowToUseTab.howtousetab import HowToUseTab

from fullscreenwaitsignal import FullScreenWaitSignal
from bookmarkoverlaywidget import BookmarkOverlayWidget
from widgets.processzoominebookmodewidget import ProcessZoomInEBookModeWidget
from widgets.processfilesinebookmodewidget import ProcessFilesInEBookModeWidget
from widgets.processbookmarksinebookmodewidget import ProcessBookmarksInEBookModeWidget

from ebookreaderwindow import EBookReaderWindow
from secondarytoolbarbutton import SecondaryToolbarButton


Gtk.IconTheme.get_default().append_search_path(os.path.join('./icons'))



import icons

class EBookReader():
        
    def __init__(self, (filepath, journal_id,)):
    	self.pages_list = [MyLibraryTab(self), GetBooksTab(self), ReadTab(self), HowToUseTab(self)]

        if not os.path.exists(env.EBOOKREADER_LOCAL_DATA_DIRECTORY):
    		os.makedirs(env.EBOOKREADER_LOCAL_DATA_DIRECTORY)
	        os.chmod(env.EBOOKREADER_LOCAL_DATA_DIRECTORY, 0755)
	

        self.window = EBookReaderWindow(self)
        self._tab_toolbars_list = []
        self._toolbar_buttons_list = []

        self.window.connect('key-press-event', self.handle_key_press_cb)
        self._allow_keys_processing = True

        #if (os.path.isfile('/bin/evtest') or os.path.isfile('/usr/bin/evtest')):
        #    GObject.timeout_add(2000, self.__auto_move_between_normal_and_fullscreen_mode)

        self.notebook = Notebook()
        self._last_page = 0

        self._full_screen_wait_signal = FullScreenWaitSignal()
        self._full_screen_wait_signal.set_transient_for(self.window)

        self._bookmark_widget = BookmarkOverlayWidget()

        self._process_bookmarks_in_ebook_mode_widget = ProcessBookmarksInEBookModeWidget(self)
        self._process_bookmarks_in_ebook_mode_widget.set_transient_for(self.window)

        self._process_zoom_in_ebook_mode_widget = ProcessZoomInEBookModeWidget(self)
        self._process_zoom_in_ebook_mode_widget.set_transient_for(self.window)

        self._process_files_in_ebook_mode_widget = ProcessFilesInEBookModeWidget(self)
        self._process_files_in_ebook_mode_widget.set_transient_for(self.window)

        self._modes = {}
        self._modes[constants.MODE_NORMAL] = self.get_reader_tab()
        self._modes[constants.MODE_ZOOM] = self._process_zoom_in_ebook_mode_widget
        self._modes[constants.MODE_SELECT_FILE] = self._process_files_in_ebook_mode_widget

        self._current_mode = self._modes[constants.MODE_NORMAL]

        self._toolbar_box = ToolbarBox()
        # Remove the horizontal padding, being caused due to upstream
        # API.
        self._toolbar_box.props.padding = 0

        self.window.set_toolbar_box(self._toolbar_box)

        self._toolbar_box.toolbar.modify_bg(Gtk.StateType.NORMAL,
                                            Gdk.color_parse('#282828'))
        placeholder=SecondaryToolbarButton(None)
        placeholder.props.sensitive=False
        self._toolbar_box._toolbar.insert(placeholder, -1)

        pagenum = 0
        for page in self.pages_list:
            page.set_main_window(self)
            page.set_pagenum(pagenum)

            pagenum = pagenum + 1

            self.add_page(page)
            self.notebook.set_show_tabs(False)

        # Add the "stop" button, in the top-row.
        # But before that, put some space, by inserting a dummy widget,
        # containing only text.
        label_text = ''
        for i in range(0, 85):
            label_text = label_text + ' '
        dummy_label = Gtk.Label(label_text)
        toolitem = Gtk.ToolItem()
        toolitem.add(dummy_label)
        self._toolbar_box._toolbar.insert(toolitem, -1)

        self._stop_button = SecondaryToolbarButton(
                'bookreader-stop', _('Stop'), self.destroy)
                
        separador = Gtk.SeparatorToolItem()
        separador.props.draw = False
        separador.set_size_request(0, -1)
        separador.set_expand(True)
        self._toolbar_box._toolbar.insert(separador, -1)
        self._toolbar_box._toolbar.insert(self._stop_button, -1)
        placeholder=SecondaryToolbarButton(None)
        placeholder.props.sensitive=False
        self._toolbar_box._toolbar.insert(placeholder, -1)
        self._toolbar_box.show_all()

        if (filepath is not None) and (filepath != "") and \
           (filepath != '""'):
            self.load_and_read_book((filepath, journal_id,))
        else:
            self.notebook.set_current_page(0)
            self._last_page = 0

        self.window.set_canvas(self.notebook)
        self.window.show_all()

        self.window.maximize()
        self.window.show_all()

        if get_active_desktop()=="Sugar":
            for i in range(0, len(sys.argv)):
                if sys.argv[i] == '-a':
                    activity_id = sys.argv[i+1]
                    break
            xid = self.window.get_window().get_xid()
            SugarExt.wm_set_bundle_id(xid, env.SUGAR_BUNDLE_ID)
            SugarExt.wm_set_activity_id(xid, activity_id)


    def get_reader_tab(self):
        return self.pages_list[2]

    def get_my_library_tab(self):
        return self.pages_list[0]

    def load_and_read_book(self,(filepath, journal_id,)):
        if filepath.startswith('file://') == False:
        	filepath = 'file://' + filepath

        self.do_load_corresponding_page(self._toolbar_buttons_list[2], 2)

        # Add the book (if not already), in the "My Library" and "Reader
        # pop-up file-slector".
        self.get_my_library_tab().save_ebook(filepath)

        from ReadTab.decryptfile import is_file_encrypted, decrypt_and_return_path_of_decrypted_file

        file_encrypted = False
        original_path = None
        if is_file_encrypted(filepath) is True:
            file_encrypted = True
            original_path = filepath
            filepath = decrypt_and_return_path_of_decrypted_file(filepath)

        self.save_resumption_information()
        self.get_reader_tab()._load_document((filepath, journal_id,), file_encrypted, original_path)
        GObject.idle_add(self.window.fullscreen)



    def set_mode(self, mode):
        self._current_mode = mode

    def get_mode(self):
        return self._current_mode

    def __auto_move_between_normal_and_fullscreen_mode(self):
        if self.__is_handheld_mode():
            self.window.fullscreen(normal_mode=False)
        elif self.window._ebookreader_fullscreen_in_normal_mode is False:
            self.window.unfullscreen()

        return True

    def __is_handheld_mode(self):
        is_ebook_mode = False

        command = 'evtest --query /dev/input/event4 EV_SW SW_TABLET_MODE; echo $?'
        try:
            return_code = subprocess.Popen([command],
                                           stdout=subprocess.PIPE,
                                           shell=True).stdout.readlines()[0].rstrip('\n')

            if return_code == '10':
                is_ebook_mode = True
        except Exception, e:
            pass

        return is_ebook_mode

    def main(self):
        Gtk.main()

    def get_current_state(self, update_zoom=True):
        view = self.get_reader_tab()._view

        if isinstance(view, Gtk.Label) is False:
            metadata = {}
            metadata['sub_file_number'] = view._sub_file_number

            if update_zoom is True:
                metadata['zoom'] = view._number_of_times_zoomed
            else:
                metadata['zoom'] = 0

            metadata['x_scroll'] = view.get_x_scroll()
            metadata['y_scroll'] = view.get_y_scroll()

            return metadata

        return None

    def set_new_state(self, sub_file_number, zoom, x_scroll, y_scroll):
        view = self.get_reader_tab()._view

        if isinstance(view, Gtk.Label) is False:
            metadata = {}
            metadata['sub_file_number'] = sub_file_number
            metadata['zoom'] = zoom
            metadata['x_scroll'] = x_scroll
            metadata['y_scroll'] = y_scroll

            return metadata

        return None

    def save_resumption_information(self, widget=None):
        metadata = self.get_current_state()
        if metadata is not None:
            self.get_reader_tab().persist_metadata(self.get_reader_tab()._filehash,
                                              metadata,
                                              self.get_reader_tab()._basename)

    def destroy(self, widget=None):
        self.save_resumption_information()
        Gtk.main_quit()

    def set_ui_sensitive(self, sensitive):
        if sensitive == False:
            self._full_screen_wait_signal.show_overlay_widget()
            self.window.force_ui_updates()
            self._allow_keys_processing = False

        self._toolbar_box.set_sensitive(sensitive)
        for toolbar in self._tab_toolbars_list:
            toolbar.set_sensitive(sensitive)

        if sensitive is True:
            self.window.get_root_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR))
        else:
            self.window.get_root_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))

        if sensitive == True:
            self._full_screen_wait_signal.hide_overlay_widget()
            self.window.force_ui_updates()
            self._allow_keys_processing = True

    def add_page(self, ebook_reader_tab_instance):
        # Add the "content" for the section.
        tab_name = ebook_reader_tab_instance.get_tab_label()
        tab_widget = ebook_reader_tab_instance.get_widget_to_attach_notebook_tab()
        tab_toolbar = ebook_reader_tab_instance.get_tab_toolbar()

        if tab_toolbar is not None:
            tab_widget.pack_start(tab_toolbar, False, False, 0)
            tab_widget.reorder_child(tab_toolbar, 0)
            self._tab_toolbars_list.append(tab_toolbar)

        self.notebook.add_page(tab_name, tab_widget)

        # Add the "(secondary) toolbar" for the section.
        icon_name = \
                ebook_reader_tab_instance.get_tab_toolbar_icon_name()
        toolbar_button = ToolbarButton(page=None,
                                       icon_name=icon_name + '-select')
        self._toolbar_buttons_list.append(toolbar_button)

        toolbar_button.connect('clicked',
                               self.load_corresponding_page,
                               ebook_reader_tab_instance.get_pagenum())
        ebook_reader_tab_instance.show()

        toolbar_button.set_tooltip(tab_name)
        self._toolbar_box._toolbar.insert(toolbar_button, -1)
        toolbar_button.show()
        self._toolbar_box.show_all()

    def load_corresponding_page(self, last_page_toolbar_button, num_pageto):
        self.do_load_corresponding_page(last_page_toolbar_button, num_pageto)

        # Also, resume the last book read, if there is no book
        # currently loaded.
        if self.pages_list[num_pageto] == self.get_reader_tab():
            if isinstance(self.get_reader_tab()._view, Gtk.Label) is True:
                last_file = self.get_reader_tab().get_path_of_last_file_read()
                if last_file is not None:
                    self.load_and_read_book((last_file, None,))

            self.window.fullscreen()

    def do_load_corresponding_page(self, last_page_toolbar_button, num_pageto):
        self.pages_list[self._last_page].hide_related_stuff_when_switching_tab()

        # Highlight the selected button.
        for button in self._toolbar_buttons_list:
            icon_widget = button.get_icon_widget()
            if icon_widget.props.icon_name.endswith('-click'):
                icon_widget.props.icon_name = \
                        icon_widget.props.icon_name.replace('-click', '-select')

        icon_widget = last_page_toolbar_button.get_icon_widget()
        icon_widget.props.icon_name = icon_widget.props.icon_name.replace('-select', '-click')


        # Here widget is the "toolbarbutton" which was clicked. Use
        # this information to advantage, to hide the secondary-toolbar
        # of this previous-page (if at all it "was" in expanded-state).
        try:
            last_page_toolbar_button.toolbar_box.expanded_button.set_expanded(False)
        except:
            pass

        # Now, load the new page as usual.
        self.notebook.set_current_page(num_pageto)
        self._last_page = num_pageto

    def handle_key_press_cb(self, widget, event):
        # Do not allow any key-proessing whatsoever, during the time UI
        # in insensitive.
        if self._allow_keys_processing is False:
            return True

        # For keys that need to be handled globally, do it here.
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'q' and event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            self.destroy()
            return True

        # Else, delegate to the appropriate tab.
        current_page_number = self.notebook.get_current_page()
        return self.pages_list[current_page_number].take_action_for_key_press(widget, event)




