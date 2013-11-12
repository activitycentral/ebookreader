from gi.repository import Gtk
import os
import env_settings as env

LAST_FILE_INFO_FILE_PATH = os.path.join(env.EBOOKREADER_LOCAL_DATA_DIRECTORY, 'last_file_read')


class EBookReaderTab(Gtk.VBox):
    def __init__(self, app):
        Gtk.VBox.__init__(self)

	self._app = app
        self._pagenum = -1
        self._main_window = None


    def get_tab_toolbar(self):
        """
        Pages that need to show the secondary toolbar, must override
        this method
        """

        return None


    def get_tab_toolbar_icon_name(self):
        """
        Every page MUST implement this method
        """

        raise Exception('Function Not Implemened')


    def get_tab_label(self):
        """
        Every page MUST implement this method.
        """

        raise Exception('Function Not Implemened')


    def get_widget_to_attach_notebook_tab(self):
        return self


    def take_action_for_key_press(self, widget, event):
        """
        IF a page needs to take actions when some key(s) is(are)
        pressed, it MUST override this method.
        """

        pass


    def get_pagenum(self):
        if self._pagenum == -1:
            raise Exception('ERROR: Page number not set up yet !!!!')

        return self._pagenum


    def set_pagenum(self, pagenum):
        self._pagenum = pagenum


    def get_main_window(self):
        if self._main_window is None:
            raise Exception('ERROR: Main Window not set up yet !!!!')

        return self._main_window


    def set_main_window(self, window):
        self._main_window = window


    def get_bookmark_widget(self):
        if self._bookmark_widget is None:
            raise Exception('ERROR: Bookmark widget not set up yet !!!!')

        return self._bookmark_widget


    def set_bookmark_widget(self, widget):
        self._bookmark_widget = widget


    def get_metadata(self, filehash):
        return self._app.get_reader_tab()._bookmarkmanager.get_resumption_metadata(filehash)


    def persist_metadata(self, filehash, metadata, basename):
        self._app.get_reader_tab()._bookmarkmanager.add_resumption_metadata(filehash,
                                                                  metadata)

        # Also, save the name of the last-file being read.
        f = open(LAST_FILE_INFO_FILE_PATH,  'w')
        f.write(str(basename))
        f.close()


    def delete_metadata_given_filehash(self, filehash):
        self._app.get_reader_tab()._bookmarkmanager.delete_resumption_metadata(filehash)


    def get_path_of_last_file_read(self):
        if not os.path.exists(LAST_FILE_INFO_FILE_PATH):
            return None

        f = open(LAST_FILE_INFO_FILE_PATH)
        file_base_name = f.read()
        f.close()

        last_file_read_path = os.path.join(os.path.expanduser('~'), 'BOOKs', file_base_name)
        if os.path.exists(last_file_read_path):
            return last_file_read_path

        return None


    def hide_related_stuff_when_switching_tab(self):
        pass
