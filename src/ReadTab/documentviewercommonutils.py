from gi.repository import GObject

class DocumentViewerCommonUtils:
    def __init__(self, main_instance, app):
	self._app = app
        self._main_instance = main_instance
        self._number_of_times_zoomed = 0
        self._scale = 0
        self._sub_file_number = 0

    def perform_actions_upon_loading_if_any(self):
        # Nothing to be done as per say.
        return False

    def do_view_specific_sync_operations(self):
        raise NotImplementedError

    def can_zoom_in(self):
        from readtab import MAXIMUM_ZOOM_INS
        from readtab import MAX_SCALE
        if self._number_of_times_zoomed < MAXIMUM_ZOOM_INS and self._scale < MAX_SCALE:
            return True
        return False

    def can_zoom_out(self):
        from readtab import MAXIMUM_ZOOM_OUTS
        from readtab import MIN_SCALE
        if self._number_of_times_zoomed > MAXIMUM_ZOOM_OUTS and self._scale > MIN_SCALE:
            return True
        return False

    def get_bookmark_identifier(self):
        raise NotImplementedError

    def go_to_bookmark(self, subfilenumber, identifier):
        raise NotImplementedError

    def get_x_scroll(self):
        raise NotImplementedError

    def get_y_scroll(self):
        raise NotImplementedError

    def scroll_to_absolute_location(self, scrollX, scrollY, keep_trying=False):
        if keep_trying:
            GObject.timeout_add(1000, self.__try_absolute_scrolling,
                                scrollX, scrollY)
        else:
            self.do_absolute_scroll(scrollX, scrollY)

    def __try_absolute_scrolling(self, scrollX, scrollY):
        if self._resume_zoom_completed is True:
            self.do_absolute_scroll(scrollX, scrollY)
            self._resume_scrolls_completed = True

            # We are done. Do not call this again.
            self._readtab.secondary_toolbar.dummy_view_toolbar.update_offset(True)
            self.resumption_complete()
            return False
        else:
            # Keep trying.
            return True

    def is_view_fully_available(self):
        raise NotImplementedError

    def resume_zoom_completed(self):
        self._resume_zoom_completed = True

    def resume_scrolls_completed(self):
        self._resume_scrolls_completed = True

    def resume_previous_characteristics(self, metadata, main_instance):
        self._resume_zoom_completed = False
        self._resume_scrolls_completed = False
        self._readtab = main_instance

        zoom = metadata['zoom']
        object_to_invoke = main_instance.secondary_toolbar.dummy_view_toolbar

        # First disable updating offsets.
        object_to_invoke.update_offset(False)

        if zoom > 0:
            GObject.idle_add(object_to_invoke._zoom_in_cb, None, zoom)
        elif zoom < 0:
            GObject.idle_add(object_to_invoke._zoom_out_cb, None, (-1 * zoom))
        GObject.idle_add(self.resume_zoom_completed)

        object_to_invoke = main_instance._view
        x_scroll = metadata['x_scroll']
        y_scroll = metadata['y_scroll']
        object_to_invoke.scroll_to_absolute_location(x_scroll, y_scroll,
                                                     keep_trying=True)

    def find_text_first(self, text):
        raise NotImplementedError

    def find_text_prev(self, text):
        raise NotImplementedError

    def find_text_next(self, text, text_changed):
        raise NotImplementedError

    def show_progress_bar(self):
        return False

    def get_zoom_icons(self):
        raise NotImplementedError

    def get_zoom_text(self):
        raise NotImplementedError

    def get_current_location(Self):
        raise NotImplementedError

    def get_location_label_text(self):
        raise NotImplementedError

    def go_to_location(self, location_text):
        raise NotImplementedError

    def remove_focus_from_location_text(self):
        location_widget = self._app.get_reader_tab().secondary_toolbar._location_entry

        location_widget.hide()
        location_widget.show()
