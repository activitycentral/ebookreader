from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import WebKit

import os
import env_settings as env
_ZOOM_AMOUNT = 0.1

class Browser(Gtk.ScrolledWindow):
    def __init__(self, main_instance):
        Gtk.ScrolledWindow.__init__(self)

        self._main_instance = main_instance
        self._view = WebKit.WebView()

        self._last_y_scroll = -1
        self._latest_y_scroll = -2

        settings = self._view.get_settings()
        settings.props.zoom_step = _ZOOM_AMOUNT

        additional_css_path = \
                os.path.join(env.SUGAR_ACTIVITY_ROOT,'styling', 'webkit.css')
        settings.props.user_stylesheet_uri = 'file://'  + additional_css_path

        self._view.set_highlight_text_matches(True)

        self._view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._view.connect('button-press-event', self._disable_click)

        self.add(self._view)
        self.get_vscrollbar().set_child_visible(False)

        self.show_all()

    def setup(self):
        return

    def zoom_in(self, zoom_amount = 1):
        self._main_instance.set_ui_sensitive(False)
        current_location = self.get_current_location()

        new_zoom_level = self._view.get_zoom_level() + (_ZOOM_AMOUNT * zoom_amount)

	self._scale = new_zoom_level
	self._view.zoom_in()

        self._main_instance.window.force_ui_updates()

        if self._resume_characteristics_done is True:
            self.go_to_location(current_location)

    def zoom_out(self, zoom_amount = 1):
        self._main_instance.set_ui_sensitive(False)
        current_location = self.get_current_location()

        new_zoom_level = self._view.get_zoom_level() - (_ZOOM_AMOUNT * zoom_amount)
	self._scale = new_zoom_level
	self._view.zoom_out()

        self._main_instance.window.force_ui_updates()

        if self._resume_characteristics_done is True:
            self.go_to_location(current_location)

    def scroll(self, scroll_type, direction_horizontal):
        if direction_horizontal == True:
            return

        self._last_y_scroll = self.get_y_scroll()

        screen_scroll = self.get_allocation().height


        if scroll_type == Gtk.ScrollType.PAGE_FORWARD:
            screen_scroll = self.get_allocation().height
            self.do_absolute_scroll(self.get_x_scroll(), self.get_y_scroll() + screen_scroll)
        elif scroll_type == Gtk.ScrollType.PAGE_BACKWARD:
            screen_scroll = self.get_allocation().height / 2
            self.do_absolute_scroll(self.get_x_scroll(), self.get_y_scroll() - screen_scroll)
        elif scroll_type == Gtk.ScrollType.STEP_BACKWARD:
            self._view.move_cursor(Gtk.MovementStep.DISPLAY_LINES, -1)
        elif scroll_type == Gtk.ScrollType.STEP_FORWARD:
            self._view.move_cursor(Gtk.MovementStep.DISPLAY_LINES, 1)

        # Very important, else the app behaves as if it is drunk !!
        self._main_instance.window.force_ui_updates()

        self._latest_y_scroll = self.get_y_scroll()

    def get_maximum_offset_possible(self):
        return self.get_vscrollbar().props.adjustment.props.upper

    def get_minimum_offset_possible(self):
        return self.get_vscrollbar().props.adjustment.props.lower

    def scroll_to_page_end(self):
        self.get_vscrollbar().set_value(self.get_maximum_offset_possible())
        self._main_instance.window.force_ui_updates()

    def get_x_scroll(self):
        return self.get_hscrollbar().get_value()

    def get_y_scroll(self):
        return self.get_vscrollbar().get_adjustment().get_value()

    def do_absolute_scroll(self, scrollX, scrollY):
        self.get_hscrollbar().set_value(scrollX)
        self.get_vscrollbar().set_value(scrollY)

        self._main_instance.window.force_ui_updates()

    def is_view_fully_available(self):
        return self._new_file_loaded == True

    def get_currently_loaded_uri(self):
        uri = self._view.props.uri
        if uri is not None:
            uri = uri.replace('file://', '').split('#')[0]

        return uri

    def find_first_text_and_return_status(self, text):
        return (self._view.search_text(text, case_sensitive=False,
                                       forward=True, wrap=False) == True)

    def find_previous_text_and_return_status(self, text):
        return (self._view.search_text(text, case_sensitive=False,
                                       forward=False, wrap=False) == True)

    def find_next_text_and_return_status(self, text):
        return (self._view.search_text(text, case_sensitive=False,
                                       forward=True, wrap=False) == True)

    def add_bottom_padding(self, incr):
        return

        '''
        Adds incr pixels of padding to the end of the loaded (X)HTML page.
        This is done via javascript at the moment
        '''
        js = ('var newdiv = document.createElement("div");' + \
        'newdiv.style.height = "%dpx";document.body.appendChild(newdiv);' \
        % incr)
        self._view.execute_script(js)

    def _disable_click(self, w, e):
        self.remove_focus_from_location_text()
        return True
