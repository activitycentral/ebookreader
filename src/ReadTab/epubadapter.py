from gi.repository import Gtk
import os
from gi.repository import GObject
import shutil
from decimal import *

from gettext import gettext as _
from documentviewercommonutils import DocumentViewerCommonUtils
from utils import is_machine_a_xo
from epubview.epub import _Epub
from epubview.webkitbackend import Browser

TOO_FAST_MESSAGE = 'You are scrolling pages way too fast. To ' + \
                   'navigate to particular locations, use "Bookmarks", or "Search"'

class EpubViewer(Browser, DocumentViewerCommonUtils):

    def __init__(self, main_instance, app):
	getcontext().prec = 15
        Browser.__init__(self, main_instance)
        DocumentViewerCommonUtils.__init__(self, main_instance, app)

	self._app = app
        self._new_file_loaded = None
        self._resume_characteristics_done = False
        self._first_time_load_flag = False
        self._go_to_flag = True

        self._view.connect('document-load-finished',
                self.perform_actions_upon_loading_if_any)

    def __load_file(self, filenum, timeout=5000):
        if self._new_file_loaded is False:
            return

        self._new_file_loaded = False
        self._sub_file_number = filenum
        self._maximum_offset_calculated = False

        self._previous_file_loaded = None

        self._current_uri = self._filelist[filenum]

        for extension in 'xhtml','xml','htm':
            if self._current_uri.endswith(extension):
                dest = self._current_uri.replace(extension, 'html')
                shutil.copy(self._current_uri.replace('file://', ''), dest)
                self._current_uri = dest.replace('file://', '')

        self._view.open(self._current_uri)
        self._main_instance.window.force_ui_updates()

    def perform_actions_upon_loading_if_any(self, first=None, second=None, third=None):
        self._main_instance.window.force_ui_updates()

        self.get_maximum_offset_possible()
        self._maximum_offset_calculated = True
        self._first_time_load_flag = True

        self._next_file_loaded = True

        if self._resume_characteristics_done is True:
            self._new_file_loaded = True

    def do_view_specific_sync_operations(self):
        self.__sync_in_case_internal_bookmarks_are_navigated()
        self.__update_percentage_of_document_completed_reading()

        # Always keep calling this function, as this is a
        # "GObject.timeout" function.
        return True

    def __sync_in_case_internal_bookmarks_are_navigated(self):
        if self._new_file_loaded is False:
            return

        if self._new_file_loaded is False:
            return

        uri_to_test = self.get_currently_loaded_uri()
        if uri_to_test == self._current_uri:
            return

        # Sometimes, the URI could be None or "blank". Do nothing in that case.
        if uri_to_test is None:
            return

        if uri_to_test[0] != '/':
            return

        for i in range(0, len(self._filelist)):
            initial_complete_uri_file_path = \
                    os.path.join(self._document._tempdir, self._filelist[i])
            if initial_complete_uri_file_path == uri_to_test:
                self._current_uri = initial_complete_uri_file_path
                self._sub_file_number = i
                return

    def __update_percentage_of_document_completed_reading(self):
        if self._new_file_loaded == False:
            return

        current_y_scroll = self.get_y_scroll()
        maximum_y_scroll = self.get_maximum_offset_possible()
        if maximum_y_scroll != 0:
            current_percentage_of_page_navigated = \
                    (1.0 * current_y_scroll) / maximum_y_scroll
        else:
            current_percentage_of_page_navigated = 0

        effective_share_of_current_page = \
                ((1.0 * self._filesizes[self._sub_file_number])/(self._total_file_size)) * current_percentage_of_page_navigated

        total_percentage = 0
        for i in range (0, self._sub_file_number):
            total_percentage = total_percentage + ((1.0 * self._filesizes[i])/(self._total_file_size))
        total_percentage = total_percentage + effective_share_of_current_page

        # Special case : if this is the absolute end of the document,
        # show "100%".
        if (self._last_y_scroll == self.get_y_scroll()) and \
           (self._sub_file_number == (len(self._filelist) - 1)):
            total_percentage = 1

        self._progress_bar.set_fraction(total_percentage)


    def load_document(self, file_path, sub_file_number, metadata, readtab):
        self._metadata = metadata
        self._readtab = readtab

        self._document = _Epub(file_path.replace('file://', ''))

        self._filelist = []
        self._filesizes = []
        self._coverfile_list = []
        self._total_file_size = 0

        for i in self._document._navmap.get_flattoc():
            self._filelist.append(os.path.join(self._document._tempdir, i))

        for j in self._document._navmap.get_cover_files():
            self._coverfile_list.append(os.path.join(self._document._tempdir, j))

        shutil.copy('./ReadTab/epubview/scripts.js', self._document._tempdir)

        for file_path in self._filelist:
            size = int(os.stat(file_path).st_size)
            self._filesizes.append(size)
            self._total_file_size = self._total_file_size + size
            try:
                #if self._document._navmap.is_tag_present(file_path, 'img') is False:
                self._insert_js_reference(file_path, self._document._tempdir)
            except:
                pass


        self._total_sub_files = len(self._filelist)

        # Before loading, remove all styling, else the bookmarks will
        # start failing way too quickly.
        dirname = os.path.dirname(self._filelist[0])
        """
        for f in os.listdir(dirname):
            if f.endswith('.css'):
                os.unlink(os.path.join(dirname, f))
        """

        # Finally, load the file.
        self.__load_file(sub_file_number, timeout=100)
        GObject.timeout_add(100, self.__reload_previous_settings)

    def _insert_js_reference(self, file_name, tempdir):
        js_reference = '<script type="text/javascript" src="' + tempdir + '/scripts.js"></script>'
        o = open(file_name + '.tmp', 'a')
        for line in open(file_name):
            line = line.replace('</head>', js_reference + '</head>')
            o.write(line + "\n")
        o.close()
        shutil.copy(file_name + '.tmp', file_name)

    def __reload_previous_settings(self):
        if self._first_time_load_flag is True:
            if len(self._metadata.keys()) > 0:
                self.resume_previous_characteristics(self._metadata,
                                                     self._readtab)
            else:
                self.resumption_complete()

            return False
        else:
            return True

    def resumption_complete(self):
        self.get_maximum_offset_possible()
        self._maximum_offset_calculated = True

        self._resume_characteristics_done = True
        self._new_file_loaded = True

        self._main_instance.set_ui_sensitive(True)
        self._go_to_flag = True
        # Initialize and reset the js plugin
        self._view.execute_script('reset()');

    def __load_previous_file(self, scroll_to_end=True):
        if self._sub_file_number > 0:
            self.__load_file(self._sub_file_number - 1)
            if scroll_to_end is True:
                GObject.timeout_add(100, self.__scroll_to_end_of_loaded_file)
            else:
                self._previous_file_loaded = True

    def __scroll_to_end_of_loaded_file(self):
        if self._new_file_loaded is True:
            if not self.is_current_segment_an_image_segment():
                self.scroll_to_page_end()

            self._previous_file_loaded = True
            return False
        else:
            return True

    def is_current_segment_an_image_segment(self):
        return self._current_uri in self._coverfile_list

    def previous_page(self):
        self.remove_focus_from_location_text()

        if self.is_current_segment_an_image_segment():
            self.__load_previous_file()
            return

        current_y_scroll = self.get_y_scroll()
        self.scroll(Gtk.ScrollType.PAGE_BACKWARD, False)
        new_y_scroll = self.get_y_scroll()

        if current_y_scroll == new_y_scroll:
            self.__load_previous_file()

    def __load_next_file(self):
        if self._sub_file_number < (self._total_sub_files - 1):
            self.__load_file(self._sub_file_number + 1)

    def next_page(self):
        self.remove_focus_from_location_text()

        if self.is_current_segment_an_image_segment():
            self.__load_next_file()
            return

        current_y_scroll = self.get_y_scroll()
        self.scroll(Gtk.ScrollType.PAGE_FORWARD, False)
        new_y_scroll = self.get_y_scroll()

        if current_y_scroll == new_y_scroll:
            self.__load_next_file()

    def handle_left_keyboard_key(self):
        self.previous_page()

    def handle_left_game_key(self):
        self.handle_left_keyboard_key()

    def handle_page_up_key(self):
        self.handle_left_keyboard_key()

    def handle_right_keyboard_key(self):
        self.next_page()

    def handle_right_game_key(self):
        self.handle_right_keyboard_key()

    def handle_page_down_key(self):
        self.handle_right_keyboard_key()

    def handle_up_keys(self):
        self.handle_left_keyboard_key()

    def handle_down_keys(self):
        self.handle_right_keyboard_key()

    def get_bookmark_identifier(self):
        return self.get_y_scroll()

    def go_to_bookmark(self, subfilenumber, identifier):
        if self._sub_file_number != subfilenumber:
            self.__load_file(subfilenumber, timeout=100)

        GObject.timeout_add(100,
                            self.__scroll_to_bookmark_position_in_file,
                            identifier)

    def __scroll_to_bookmark_position_in_file(self, y_scroll):
        if (self._new_file_loaded is True) and \
           (self._maximum_offset_calculated is True):
            self.scroll_to_absolute_location(self.get_x_scroll(),
                                             y_scroll)
            return False
        else:
            return True

    def get_back_to_last_persisted_state(self):
        self._resume_characteristics_done = False
        self._first_time_load_flag = False

        self.__load_file(self._metadata['sub_file_number'], timeout=100)
        GObject.timeout_add(100, self.__reload_previous_settings)

    def find_text_first(self, text):
        self._metadata = self._main_instance.get_current_state(False)

        if self.find_first_text_and_return_status(text) is False:
            self._main_instance.set_ui_sensitive(False)
            self.__load_next_file_and_highlight_first_word(text)

    def find_text_prev(self, text):
        self._metadata = self._main_instance.get_current_state(False)

        if self.find_previous_text_and_return_status(text) is False:
            self._main_instance.set_ui_sensitive(False)
            self.__load_previous_file_and_highlight_last_word(text)

    def __load_previous_file_and_highlight_last_word(self, text):
        if self._sub_file_number == 0:
            self.get_back_to_last_persisted_state()
            return

        self._previous_file_loaded = False
        self.__load_previous_file(scroll_to_end=False)
        GObject.timeout_add(100, self.__highlight_last_word_in_file,
                            text)

    def __highlight_last_word_in_file(self, text):
        if (self._previous_file_loaded == True) and \
           (self._new_file_loaded == True):
            # Now, it may happen, that the word ins not found in the
            # file. Thus, navigate to the previous file.
            if self.find_first_text_and_return_status(text) is False:
                self._main_instance.set_ui_sensitive(False)
                self.__load_previous_file_and_highlight_last_word(text)
                return False

            while 1:
                if self.find_next_text_and_return_status(text) is False:
                    break

            # At this point, we have indeed found the last occurrence
            # of "text" :)
            self._main_instance.set_ui_sensitive(True)

            return False
        else:
            return True

    def find_text_next(self, text, text_changed):
        self._metadata = self._main_instance.get_current_state(False)

        if text_changed is True:
            self.find_text_first(text)
            return

        if self.find_next_text_and_return_status(text) is False:
            self._main_instance.set_ui_sensitive(False)
            self.__load_next_file_and_highlight_first_word(text)

    def __load_next_file_and_highlight_first_word(self, text):
        if self._sub_file_number == (self._total_sub_files - 1):
            self.get_back_to_last_persisted_state()
            return

        self._next_file_loaded = False
        self.__load_next_file()
        GObject.timeout_add(100, self.__highlight_first_word_in_file,
                            text)

    def __highlight_first_word_in_file(self, text):
        if self._next_file_loaded == True:
            # Now, it may happen, that the word ins not found in the
            # file. Thus, navigate to the next file.
            if self.find_first_text_and_return_status(text) is False:
                GObject.idle_add(self.__load_next_file_and_highlight_first_word,
                                 text)
            else:
                self._main_instance.set_ui_sensitive(True)
            return False
        else:
            return True

    def set_progress_bar(self, bar):
        self._progress_bar = bar

    def show_progress_bar(self):
        return True

    def get_zoom_icons(self):
        return ['bookreader-popup-textsizeup',
                'bookreader-popup-textsizedown',
                'bookreader-textsizeup',
                'bookreader-textsizedown']

    def get_zoom_text(self):
        return _('Change Letter Size')

    def get_current_location(self):
        if self._new_file_loaded is True:
            return str(Decimal(self._progress_bar.get_fraction()) * Decimal(self._total_file_size))
        else:
            return ''

    def get_location_label_text(self):
        return ' / ' + str(self._total_file_size)

    def go_to_location(self, location_text):
        self._main_instance.set_ui_sensitive(False)

        location = None
        try:
            location = Decimal(location_text) / Decimal(self._total_file_size)
        except Exception, e:
            self._main_instance.set_ui_sensitive(True)
            return

        # Calculate the file number first.
        previous_total_percentage = 0
        current_total_percentage = 0
        sub_file_number = None
        for i in range (0, len(self._filelist)):
            previous_total_percentage = current_total_percentage
            current_total_percentage = Decimal(current_total_percentage) + Decimal(self._filesizes[i])/Decimal(self._total_file_size)
            if location < (current_total_percentage - Decimal('0.00000000009999999999')):
                sub_file_number = i
                break

        if sub_file_number is None:
            self._main_instance.set_ui_sensitive(True)
            return

        self._resume_characteristics_done = False
        self._first_time_load_flag = False
        self._go_to_flag = False

        # Initially, we will have to load the file at the beginning.
        self._metadata = self._main_instance.set_new_state(sub_file_number, 0,
                                                           self.get_x_scroll(), 0)

        self.__load_file(self._metadata['sub_file_number'], timeout=100)
        GObject.timeout_add(100, self.__go_to_file_now,
                            previous_total_percentage,
                            current_total_percentage, location)

    def __go_to_file_now(self, previous_total_percentage, current_total_percentage, location):
        GObject.timeout_add(100, self.__reload_previous_settings)
        GObject.timeout_add(100, self.__go_to_location_now,
                            previous_total_percentage, current_total_percentage, location)

    def __go_to_location_now(self, previous_total_percentage, current_total_percentage, location):
        if self._go_to_flag is True:
            file_contribution = current_total_percentage - previous_total_percentage
            current_percentage_location = location - previous_total_percentage

            y_scroll = int(Decimal(current_percentage_location) / Decimal(file_contribution) * Decimal(self.get_maximum_offset_possible()))

            self.do_absolute_scroll(self.get_x_scroll(), y_scroll)
            self._main_instance.set_ui_sensitive(True)

            return False
        else:
            return True
