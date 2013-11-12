from gi.repository import GObject
import logging
import env_settings as env
from gi.repository import Gtk

from gi.repository import EvinceView
from gi.repository import EvinceDocument

from gettext import gettext as _


from documentviewercommonutils import DocumentViewerCommonUtils

_logger = logging.getLogger(__name__)


class EvinceViewer(Gtk.ScrolledWindow, DocumentViewerCommonUtils):

    def __init__(self, main_instance, app):
        Gtk.ScrolledWindow.__init__(self)
        DocumentViewerCommonUtils.__init__(self, main_instance, app)

        EvinceDocument.init()
	
	self._app = app
        self._view = EvinceView.View()
        self._view.find_set_highlight_search(True)

        self.add(self._view)

        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self._find_job = None
        self._new_text = False

    def setup(self):
        pass

    def do_view_specific_sync_operations(self):
        pass

    def load_document(self, file_path, sub_file_number, metadata,readtab):
        self._metadata = metadata
        self._readtab = readtab

        try:
            self._document = EvinceDocument.Document.factory_get_document(file_path)
        except GObject.GError, e:
            _logger.error('Can not load document: %s', e)
            return
        else:
            self._model = EvinceView.DocumentModel()
            self._model.set_document(self._document)
            self._model.set_sizing_mode(EvinceView.SizingMode.FIT_WIDTH)
            self._view.set_model(self._model)

            GObject.timeout_add(100, self.__reload_previous_settings)

    def __reload_previous_settings(self):
        if self.is_view_fully_available():
            if len(self._metadata.keys()) > 0:
                self.resume_previous_characteristics(self._metadata,
                                                     self._readtab)
            else:
                self.resumption_complete()

            return False
        else:
            return True

    def zoom_in(self, zoom_amount = 1):
        '''
        Zooms in (increases zoom level by 0.1)
        '''
        self._model.props.sizing_mode = EvinceView.SizingMode.FREE
        self._view.zoom_in()

    def zoom_out(self, zoom_amount = 1):
        '''
        Zooms out (decreases zoom level by 0.1)
        '''
        self._model.props.sizing_mode = EvinceView.SizingMode.FREE
        self._view.zoom_out()

    def can_zoom_in(self):
        '''
        Returns True if it is possible to zoom in further
        '''
        return self._view.can_zoom_in()

    def can_zoom_out(self):
        '''
        Returns True if it is possible to zoom out further
        '''
        return self._view.can_zoom_out()

    def scroll(self, scrolltype, horizontal):
        '''
        Scrolls through the pages.
        Scrolling is horizontal if horizontal is set to True
        Valid scrolltypes are:
        Gtk.ScrollType.PAGE_BACKWARD, Gtk.ScrollType.PAGE_FORWARD,
        Gtk.ScrollType.STEP_BACKWARD, Gtk.ScrollType.STEP_FORWARD,
        Gtk.ScrollType.START and Gtk.ScrollType.END
        '''
        _logger.error('scroll: %s', scrolltype)

        if scrolltype == Gtk.ScrollType.PAGE_BACKWARD:
            self._view.scroll(Gtk.ScrollType.PAGE_BACKWARD, horizontal)
        elif scrolltype == Gtk.ScrollType.PAGE_FORWARD:
            self._view.scroll(Gtk.ScrollType.PAGE_FORWARD, horizontal)
        elif scrolltype == Gtk.ScrollType.STEP_BACKWARD:
            self._scroll_step(False, horizontal)
        elif scrolltype == Gtk.ScrollType.STEP_FORWARD:
            self._scroll_step(True, horizontal)
        elif scrolltype == Gtk.ScrollType.START:
            self.set_current_page(0)
        elif scrolltype == Gtk.ScrollType.END:
            self.set_current_page(self._document.get_n_pages())
        else:
            print ('Got unsupported scrolltype %s' % str(scrolltype))

    def _scroll_step(self, forward, horizontal):
        if horizontal:
            adj = self.get_hadjustment()
        else:
            adj = self.get_vadjustment()
        value = adj.get_value()
        step = adj.get_step_increment()
        if forward:
            adj.set_value(value + step)
        else:
            adj.set_value(value - step)

    def handle_up_keys(self):
        self.remove_focus_from_location_text()
        self.scroll(Gtk.ScrollType.STEP_BACKWARD, False)

    def handle_down_keys(self):
        self.remove_focus_from_location_text()
        self.scroll(Gtk.ScrollType.STEP_FORWARD, False)

    def handle_left_keyboard_key(self):
        self.remove_focus_from_location_text()
        self.scroll(Gtk.ScrollType.PAGE_BACKWARD, False)

    def handle_left_game_key(self):
        self.handle_left_keyboard_key()

    def handle_page_up_key(self):
        self.handle_left_keyboard_key()

    def handle_right_keyboard_key(self):
        self.remove_focus_from_location_text()
        self.scroll(Gtk.ScrollType.PAGE_FORWARD, False)

    def handle_right_game_key(self):
        self.handle_right_keyboard_key()

    def handle_page_down_key(self):
        self.handle_right_keyboard_key()

    def get_bookmark_identifier(self):
        return self._model.props.page

    def go_to_bookmark(self, subfilenumber, identifier):
        self._model.props.page = identifier

    def get_x_scroll(self):
        return self.get_hadjustment().get_value()

    def get_y_scroll(self):
        return self.get_vadjustment().get_value()

    def do_absolute_scroll(self, scrollX, scrollY):
        self.get_hadjustment().set_value(scrollX)
        self.get_vadjustment().set_value(scrollY)

    def is_view_fully_available(self):
        return self._view.get_visible()

    def find_text_first(self, text):
        if text == "":
            self._view.find_set_highlight_search(False)
            return

        self._view.find_set_highlight_search(True)

        if self._find_job is not None:
            self._find_job.cancel()
            self._find_job.disconnect(self._find_updated_handler)
            self._find_job = None

        if text != "":
            self._find_job = EvinceView.JobFind.new(document=self._document, start_page=0,
                                            n_pages=self._document.get_n_pages(),
                                            text=text, case_sensitive=False)
            self._find_updated_handler = \
                    self._find_job.connect('updated', self.__find_updated_cb)

            self._view.find_started(self._find_job)
            EvinceView.Job.scheduler_push_job(self._find_job,
                                          EvinceView.JobPriority.PRIORITY_NONE)

    def find_text_prev(self, text):
        self._view.find_previous()

    def find_text_next(self, text, text_changed):
        if text_changed:
            self._new_text = True
            self.find_text_first(text)
        else:
            self._view.find_next()

    def __find_updated_cb(self, job, page=None):
        if self._new_text is True:
            self.find_text_next(None, False)
            self._new_text = False

    def resumption_complete(self):
        pass

    def get_zoom_icons(self):
        return ['bookreader-zoomup',
                'bookreader-zoomdown',
                'bookreader-menubar-zoomup',
                'bookreader-menubar-zoomdown']

    def get_zoom_text(self):
        return _('Change Zoom')

    def get_current_location(self):
        try:
            return str(self._model.props.page + 1)
        except:
            return ''

    def get_location_label_text(self):
        try:
            return ' / ' + str(self._document.get_n_pages())
        except:
            return ''

    def go_to_location(self, location_text):
        # Parse the page number to go to. If there is any problem, do
        # not do anything whatsoever.
        try:
            location = int(location_text)
            self._model.props.page = location - 1
        except Exception, e:
            print e
