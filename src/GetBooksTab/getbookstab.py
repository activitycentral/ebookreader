# -*- coding: utf-8 -*-

# Copyright (C) 2009 James D. Simmons
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
import os
import logging
import time
from gi.repository import Gtk
import urllib2
from gi.repository import Gdk, GdkPixbuf
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import GConf
import feedparser
import socket
import env_settings as env

GObject.threads_init()
COVERHEIGHT = 150
COVERWIDTH = 100

URL = None
OLD_TOOLBAR = False
try:
    from sugar3.graphics.toolbarbox import ToolbarBox
    from sugar3.activity.widgets import StopButton
except ImportError:
    OLD_TOOLBAR = True

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.toolcombobox import ToolComboBox
from sugar3.graphics.combobox import ComboBox
from sugar3.graphics import iconentry
from sugar3 import profile
#from sugar3.activity import activity
from sugar3.bundle.activitybundle import ActivityBundle
#from sugar3.datastore import datastore
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.alert import Alert
from sugar3.graphics.icon import Icon
from gettext import gettext as _
import dbus
from gi.repository import GObject
import ConfigParser
import base64
import threading

import opds
import languagenames
import devicemanager

from ebookreadertab import EBookReaderTab

#from ceibal import laptops

_SOURCES = {}
_SOURCES_CONFIG = {}

READ_STREAM_SERVICE = 'read-activity-http'

# directory exists if powerd is running.  create a file here,
# named after our pid, to inhibit suspend.
POWERD_INHIBIT_DIR = '/var/run/powerd-inhibit-suspend'

AUTO_SEARCH_REFRESH = GConf.Client.get_default().get_bool('/desktop/ebookreader/auto_search_refresh')


_logger = logging.getLogger(__name__)

def get_separador(draw=False, width=0, expand=False):

    separador = Gtk.SeparatorToolItem()
    separador.props.draw = draw
    separador.set_size_request(width, -1)
    separador.set_expand(expand)

    return separador


def _get_screen_dpi():
    xft_dpi = Gtk.Settings.get_default().get_property('gtk-xft-dpi')
    _logger.debug('Setting dpi to %f', float(xft_dpi / 1024))
    return float(xft_dpi / 1024)


class SecondaryToolBar():
    def __init__(self, iatab, config, catalogs_present):
        self.toolbar = Gtk.Toolbar()
        self.iatab = iatab

        hbox = Gtk.HBox()
        hbox.set_spacing(int(0.5 * style.DEFAULT_SPACING))

        # Separator
        self.toolbar.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)

        # library combo
        libs_combo = Gtk.ComboBoxText()
        libs_combo.props.sensitive = True

        libs = config.sections()
        for lib in libs:
            # Do not the entries, with no "query_uri" field.
            if 'query_uri' in config.options(lib):
                libs_combo.append_text(config.get(lib, 'name'))
        libs_combo.set_active(0)
        if AUTO_SEARCH_REFRESH is True:
            libs_combo.connect('changed', self.search)

        self.libs_combo = libs_combo
        
        wrap = Gtk.Alignment(xalign=0.0, yalign=0.5, xscale=0.0, yscale=0.0)
        wrap.add(self.libs_combo)

        item = Gtk.ToolItem()
        item.set_expand(False)
        item.add(wrap)
        self.toolbar.insert(item, -1)

        # Separator
        self.toolbar.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)

        # Catalogs button
        button = Gtk.ToolButton()
        button.set_tooltip_text(_("Show catalogs"))
        image = Gtk.Image()

        size = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'catalogs.svg'),
                size[1], size[2]))

        button.set_icon_widget(image)
        button.connect("clicked", self.toggleCatalogs)
        image.show()
        button.show()

        self.toolbar.insert(button, -1)
        if catalogs_present is False:
            button.set_sensitive(False)

        # Separator
        self.toolbar.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)

        # language combo
        languages = [_("Any Language"), "es", "en"]
        language_combo = Gtk.ComboBoxText()
        language_combo.props.sensitive = True
        for language in languages:
            language_combo.append_text(language)
        language_combo.set_active(0)
        if AUTO_SEARCH_REFRESH is True:
            language_combo.connect('changed', self.search)

        self.language_combo = language_combo

        wrap = Gtk.Alignment(xalign=0.0, yalign=0.5, xscale=0.0, yscale=0.0)
        wrap.add(self.language_combo)

        item = Gtk.ToolItem()
        item.set_expand(False)
        item.add(wrap)
        self.toolbar.insert(item, -1)

        # Separator
        self.toolbar.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)

        ### Entry text for search
        search_entry = iconentry.IconEntry()

        search_entry.set_icon_from_name(
            iconentry.ICON_ENTRY_PRIMARY,
            'system-search')

        search_entry.add_clear_button()
        search_entry.connect('activate',
           self.search)

        width = int(Gdk.Screen.width() / 4)
        search_entry.set_size_request(width, -1)
        search_entry.set_tooltip_text(_("Type to Search."))
        self.search_entry=search_entry

        item = Gtk.ToolItem()
        item.add(self.search_entry)
        self.toolbar.insert(item, -1)

        search_entry.show()
        item.show()
        

        # Separator
        self.toolbar.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)


    def toggleCatalogs(self, widget):
        self.iatab.tree_scroller.props.visible = not self.iatab.tree_scroller.props.visible 

    def search(self, widget):
        txt = self.search_entry.get_text().replace(" ","+") 
        if len(txt) > 0:
            self.iatab.searchLib(txt)

    def getCurrentLib(self):
        return self.libs_combo.get_active_text()

    def getCurrentLang(self):
        if self.language_combo.get_active_text() == _("Any Language"):
            return "all"
        else:
            return self.language_combo.get_active_text()


class ToolbarInfo(Gtk.Toolbar):

    def __init__(self,act):

        Gtk.Toolbar.__init__(self)

        self._activity = act

        self.modify_bg(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#943a43"))

        ### Bookcover
        image = Gtk.Image()

        image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-cover-placeholder.svg'),
                COVERWIDTH,COVERHEIGHT))

        image.show()
        
        self._bookcover = image

        item = Gtk.ToolItem()
          
        item.set_border_width(15)
        item.set_expand(False)
        item.add(image)
        self.insert(item, -1)

        self.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)

        ### Widget Text Info
        self.widget_info = WidgetInfo(self._activity)
        item = Gtk.ToolItem()
        item.set_expand(True)
        item.add(self.widget_info)
        self.insert(item, -1)

        # Right VBOX
        rightVBox = Gtk.VBox(homogeneous=False, spacing=0)

        ### Button download
        self.button = Gtk.ToolButton()
        self.button.set_tooltip_text(_("Download this Book."))
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-download-over.svg'),
                75,150))

        self.button.set_icon_widget(self.image)
        self.button.connect("clicked", self.downloadElement)
        self.button.set_no_show_all(True)
        rightVBox.pack_start(self.button, False, False, 10)

        # Download combo
        libs = ["EPUB", "PDF"]
        libs_combo = Gtk.ComboBoxText()
        libs_combo.props.sensitive = True
        for lib in libs:
            libs_combo.append_text(lib)
        libs_combo.set_active(0)
        self.downloadcombo = libs_combo
        self.downloadcombo.set_no_show_all(True)
        rightVBox.pack_start(libs_combo, False, False, 0)

        #self.insert(button, -1)
        item = Gtk.ToolItem()
        item.set_expand(False)
        item.add(rightVBox)
        self.insert(item, -1)

        self.insert(get_separador(
            draw=False, width=10,
            expand=False), -1)
        self.show_all()

    def downloadElement(self, widget):
        
        if self._activity.sectoolbar.getCurrentLib() == "Biblioteca Ceibal":
            self._activity.downloadAsCEIBAL(None)
            return
        if self.downloadcombo.get_active_text() == "PDF":
            self._activity.downloadAsPDF(None)
        elif self.downloadcombo.get_active_text() == "EPUB":
            self._activity.downloadAsEPUB(None)

    def getDownloadCombo(self):
        """
        Performs read this file.
        """
        #self.downloadcombo

        # FIXME: Implement.
        pass

    def reset(self):
        self.widget_info.title.set_markup("")
        self.widget_info.autor.set_markup("")
        self._bookcover.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-cover-placeholder.svg'),
                COVERWIDTH,COVERHEIGHT))

        self.downloadcombo.hide()
        self.button.hide()

    def set_info(self, title, author):
        self.widget_info.set_info(
            title=title,
            autor=author,
            url=self._activity._dl[title.decode('utf-8')][1],
            img=self._bookcover,
            act=self._activity)


class WidgetInfo(Gtk.VBox):

    def __init__(self,iatab):
        self.iatab = iatab
        Gtk.VBox.__init__(self)

        self.title = Gtk.Label("")
        self.autor = Gtk.Label("")

        self.set_homogeneous(True)

        self.title.set_line_wrap(False)
        self.autor.set_line_wrap(True)

        self.pack_start(self.title, False, False, 0)
        self.pack_start(self.autor, False, False, 0)
        self.title.set_alignment(0,0)
        self.autor.set_alignment(0,0)

        self.show_all()

    def set_info(self, title='', autor='', url='', img='', act=''):
        """
        receives information from the selected book.
        """
        from textwrap import wrap
        title='\n'.join(wrap(title, width=50))
        autor='\n'.join(wrap(autor, width=50))
        self.title.set_markup("<b><big>%s</big></b>" % title)
        self.autor.set_text("%s" % autor)

        if url:
            #act._statusbar.push(self._context_id, u"Descargando Caratula")
            mimetype = url.keys()[0]
            url = url[mimetype]
            global URL
            URL = url
            while Gtk.events_pending():
                Gtk.main_iteration()
            thread=download_cover(url,act,img,self.iatab)
            thread.start()
            #thread.join()
        else:
            img.set_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    os.path.join(env.ICONS_PATH,
                    'bookreader-cover-placeholder.svg'),
                    COVERWIDTH,COVERHEIGHT))

class download_cover(threading.Thread):  
    def __init__(self, url, act,img,iatab):
        threading.Thread.__init__(self)
        self.url=url
        self.act=act
        self.img=img
        self.iatab=iatab

    def run(self):
        try:
            response = urllib2.urlopen(self.url)
            loader=GdkPixbuf.PixbufLoader()
            loader.write(response.read())
        except urllib2.HTTPError, e:
            _logger.error(" Error al descargar cover HTTP Error: " + str(e.code) + " " + self.url)
        except urllib2.URLError, e:
            _logger.error(" Error al descargar cover URL Error: " + str(e.reason) + " " + self.url)
        else:

            loader.close()

            pixbuf = loader.get_pixbuf()
            scaled = pixbuf.scale_simple(COVERWIDTH,COVERHEIGHT, GdkPixbuf.InterpType.BILINEAR)

            # Do not set the image if the book list has already been cleared
            if not self.iatab.empty:
                # Do not replace img if this thread is not the last one
                if URL == self.url:
                    self.img.set_from_pixbuf(scaled)

class GetBooksTab(EBookReaderTab):

    def __init__(self, app):
        EBookReaderTab.__init__(self, app)
        _logger.debug('Starting Getbooks...')
        self._app = app
        self.dpi = _get_screen_dpi()

        self.selected_book = None
        self.queryresults = None
        self._getter = None
        self.show_images = True
        self.languages = {}
        self._lang_code_handler = languagenames.LanguageNames()
        self.catalogs_configuration = {}
        self.catalog_history = []
        self.catalogs_present = True

        # Read the config at startup.
        file_name = os.path.join(env.SUGAR_ACTIVITY_ROOT, 'GetBooksTab', 'get-books.cfg')
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(open(file_name))

        if os.path.exists('GetBooksTab/get-books.cfg'):
             self._read_configuration('GetBooksTab/get-books.cfg')
        else:
            self._read_configuration()


        # Main vbox
        vbox = Gtk.VBox()

        # Toolbar
        sectoolbar = SecondaryToolBar(self, self.config, self.catalogs_present)
        self.sectoolbar = sectoolbar
        sectoolbar = sectoolbar.toolbar
        vbox.pack_start(sectoolbar, False, False, 0)
        self.add(vbox)
        
        # Progress bar
        self._download_content_length = 0
        self._download_content_type = None
        self.progressbox = Gtk.Box(spacing=20,
                orientation=Gtk.Orientation.HORIZONTAL)
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_fraction(0.0)
        self.progressbox.pack_start(self.progressbar, expand=True, fill=True,
                padding=0)
        self.cancel_btn = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        self.cancel_btn.connect('clicked', self.__cancel_btn_clicked_cb)
        self.progressbox.pack_start(self.cancel_btn, expand=False,
                fill=False, padding=0)
        vbox.pack_start(self.progressbox, False, False, 10)
        self.progressbox.set_no_show_all(True)

        # Message box
        self.msg_box = Gtk.HBox(homogeneous=True, spacing=10)
        self.msg_box.set_no_show_all(True)
        self.readbutton = Gtk.Button(_("Open"))
        self.readbutton.set_no_show_all(True)
        self.readbutton.connect('clicked',self.readbutton_clicked)
        self.filepath = ""
        self.msg_label = Gtk.Label()
        self.msg_label.set_no_show_all(True)
        self.msg_box.pack_start(self.msg_label, False, False, 0)
        self.msg_box.pack_start(self.readbutton, False, False, 0)
        vbox.pack_start(self.msg_box, False, False, 10)

        # Hbox
        hbox = Gtk.HBox()

        # Catalogs treeview
        if self.catalogs_present:
            self.catalog_listview = Gtk.TreeView()
            self.catalog_listview.headers_clickble = True
            self.catalog_listview.hover_expand = True
            self.catalog_listview.rules_hint = True
            self.catalog_listview.set_size_request(300,-1)
            self._catalog_changed_id = self.catalog_listview.connect(
                    'cursor-changed', self.move_down_catalog)
            self.catalog_listview.set_enable_search(False)

            self.treemodel = Gtk.ListStore(str)
            self.treemodel.set_sort_column_id(0, Gtk.SortType.ASCENDING)
            self.catalog_listview.set_model(self.treemodel)

            renderer = Gtk.CellRendererText()
            renderer.set_property('wrap-mode', Pango.WrapMode.WORD)
            self.treecol = Gtk.TreeViewColumn("Catálogos", renderer, text=0)
            self.treecol.set_property('clickable', True)
            self.treecol.connect('clicked', self.move_up_catalog)
            self.catalog_listview.append_column(self.treecol)
            self.bt_move_up_catalog = ButtonWithImage(_("Catalogs"))
            self.bt_move_up_catalog.hide_image()
            self.treecol.set_widget(self.bt_move_up_catalog)


            self.tree_scroller = Gtk.ScrolledWindow(hadjustment=None,
                    vadjustment=None)
            self.tree_scroller.set_policy(Gtk.PolicyType.NEVER,
                    Gtk.PolicyType.AUTOMATIC)
            self.tree_scroller.add(self.catalog_listview)
            hbox.pack_start(self.tree_scroller, expand=False, fill=False, padding=0)

        # Table sidebar ( right )
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vadjustment = sw.get_vadjustment()
        vadjustment.connect ('value-changed', self.__vadjustment_value_changed_cb)
        hbox.pack_start(sw, True, True, 0)
        (store, rowmetadata) = self.create_model()
        treeView = Gtk.TreeView(store)

        treeView.set_rules_hint(True)
        sw.add(treeView)
        self.create_columns(treeView)
        treeView.connect("row-activated", self.on_activated, rowmetadata)

        treeView.connect('cursor-changed', self.on_selected)

        self.treeview = treeView
        self.store = store
        vbox.pack_start(hbox, True, True, 0)

        # Toolbar info
        self.toolbar_info = ToolbarInfo(self)
        vbox.pack_start(self.toolbar_info, False,False, 0)

        self.load_source_catalogs()
        # Statusbar
        #self._statusbar = Gtk.Statusbar()
        #vbox.pack_start(self._statusbar, False, True, 0)



    def __vadjustment_value_changed_cb(self, vadjustment):
        if not self.queryresults.is_ready():
            return
        
        try:
            # Use various tricks to update resultset as user scrolls down
            if ((vadjustment.props.upper - vadjustment.props.lower) > 1000 and \
                (vadjustment.props.upper - vadjustment.props.value - vadjustment.props.page_size) / \
                (vadjustment.props.upper - vadjustment.props.lower) < 0.3) or \
                ((vadjustment.props.upper - vadjustment.props.value - vadjustment.props.page_size) < 200):
                
                if self.queryresults.has_next():
                    self.queryresults.update_with_next()
        finally:
            return

    def readbutton_clicked(self,btn):
        self._app.load_and_read_book((self.filepath, None))

    def __cancel_btn_clicked_cb(self, btn):
        if self._getter is not None:
            try:
                self._getter.cancel()
            except:
                _logger.error('Got an exception while trying' + \
                        'to cancel download')
            self.progressbox.hide()
            self.treeview.props.sensitive = True

            if self.catalogs_present:
                self.catalog_listview.props.sensitive = True

            self.sectoolbar.search_entry.props.sensitive = True
            self.toolbar_info.button.props.sensitive = True
            _logger.debug('Download was canceled by the user.')

    def get_query_language(self):
        query_language = None
        if len(self.languages) > 0:
            query_language = self.sectoolbar.getCurrentLang()
        return query_language

    def filter_catalogs_by_source(self):
        self.catalogs = {}
        for catalog_key in self.catalogs_configuration:
            catalog = self.catalogs_configuration[catalog_key]
            if catalog['source'] == self.source:
                self.catalogs[catalog_key] = catalog

    def load_source_catalogs(self):
        self.filter_catalogs_by_source()

        if len(self.catalogs) > 0:
            self.categories = []
            self.path_iter = {}
            self.catalog_history = []
            self.catalog_history.append({'title': _('Catalogs'),
                'catalogs': self.catalogs})
            for key in self.catalogs.keys():
                self.categories.append({'text': key, _('within'): []})
            self.treemodel.clear()
            self.toolbar_info.reset()

            for p in self.categories:
                self.path_iter[p['text']] = self.treemodel.append([p['text']])

    def _read_configuration(self, file_name='get-books.cfg'):
        _logger.debug('Reading configuration from file %s', file_name)
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        config.readfp(open(file_name))
        if config.has_option('GetBooks', 'show_images'):
            self.show_images = config.getboolean('GetBooks', 'show_images')
        self.languages = {}
        if config.has_option('GetBooks', 'languages'):
            languages_param = config.get('GetBooks', 'languages')
            for language in languages_param.split(','):
                lang_code = language.strip()
                if len(lang_code) > 0:
                    self.languages[lang_code] = \
                    self._lang_code_handler.get_full_language_name(lang_code)

        for section in config.sections():
            if section != 'GetBooks' and not section.startswith('Catalogs'):
                name = config.get(section, 'name')
                _SOURCES[section] = name
                repo_config = {}
                repo_config['query_uri'] = config.get(section, 'query_uri')
                repo_config['opds_cover'] = config.get(section, 'opds_cover')
                if config.has_option(section, 'summary_field'):
                    repo_config['summary_field'] = \
                        config.get(section, 'summary_field')
                else:
                    repo_config['summary_field'] = None
                if config.has_option(section, 'blacklist'):
                    blacklist = config.get(section, 'blacklist')
                    repo_config['blacklist'] = blacklist.split(',')
                    # TODO strip?
                else:
                    repo_config['blacklist'] = []

                _SOURCES_CONFIG[section] = repo_config

        _logger.debug('_SOURCES %s', _SOURCES)
        _logger.debug('_SOURCES_CONFIG %s', _SOURCES_CONFIG)

        for section in config.sections():
            if section.startswith('Catalogs'):
                catalog_source = section.split('_')[1]
                if not catalog_source in _SOURCES_CONFIG:
                    _logger.error('There are not a source for the catalog ' +
                            'section  %s', section)
                    break
                source_config = _SOURCES_CONFIG[catalog_source]
                opds_cover = source_config['opds_cover']
                for catalog in config.options(section):
                    catalog_config = {}
                    catalog_config['query_uri'] = config.get(section, catalog)
                    catalog_config['opds_cover'] = opds_cover
                    catalog_config['source'] = catalog_source
                    catalog_config['name'] = catalog
                    catalog_config['summary_field'] = \
                        source_config['summary_field']
                    self.catalogs_configuration[catalog] = catalog_config

        if len(self.catalogs_configuration.keys()) == 0:
            self.catalogs_present = False

        self.source = _SOURCES_CONFIG.keys()[0]

        self.filter_catalogs_by_source()

        _logger.debug('languages %s', self.languages)
        _logger.debug('catalogs %s', self.catalogs)

    def set_downloaded_bytes(self, downloaded_bytes,  total):
        fraction = float(downloaded_bytes) / float(total)
        self.progressbar.set_fraction(fraction)

    def clear_downloaded_bytes(self):
        self.progressbar.set_fraction(0.0)

    def __bt_catalogs_clicked_cb(self, button):
        palette = button.get_palette()
        palette.popup(immediate=True, state=palette.SECONDARY)

    def __switch_catalog_cb(self, catalog_name):
        try:
            catalog_config = self.catalogs[catalog_name.decode('utf-8')]
            self.__activate_catalog_cb(None, catalog_config)
        except:
            pass

    def __activate_catalog_cb(self, menu, catalog_config):
        query_language = self.get_query_language()

        #self.enable_button(False)
        self.clear_downloaded_bytes()
        self.book_selected = False
        self.empty=True
        self.store.clear()
        _logger.debug('SOURCE %s', catalog_config['source'])
        #self._books_toolbar.search_entry.props.text = ''
        self.source = catalog_config['source']
        #position = _SOURCES_CONFIG[self.source]['position']
        #self._books_toolbar.source_combo.set_active(position)

        #if self.queryresults is not None:
        #    self.queryresults.cancel()
        #    self.queryresults = None

        self.queryresults = opds.RemoteQueryResult(catalog_config,
                '', query_language)
        self.show_message(_("Searching") + "...")
        self.toolbar_info.reset()

        # README: I think we should create some global variables for
        # each cursor that we are using to avoid the creation of them
        # every time that we want to change it
        self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))

        self.queryresults.connect('updated', self.__query_updated_cb)

    def show_message(self, text):
        self.msg_label.set_text(text)
        self.msg_label.show()
        self.msg_box.show()

    def hide_message(self):
        self.msg_label.hide()
        self.msg_box.hide()
        self.readbutton.hide()

    def _refresh_sources(self, toolbar):
        toolbar.source_combo.handler_block(toolbar.source_changed_cb_id)

        #TODO: Do not blindly clear this
        toolbar.source_combo.remove_all()

        position = 0
        for key in _SOURCES.keys():
            toolbar.source_combo.append_item(_SOURCES[key], key,
                icon_name='internet-icon')
            _SOURCES_CONFIG[key]['position'] = position
            position = position + 1

        # Add menu for local books
        if len(_SOURCES) > 0:
            toolbar.source_combo.append_separator()
        toolbar.source_combo.append_item('local_books', _('My books'),
                icon_name='activity-journal')

        devices = self._device_manager.get_devices()

        first_device = True
        for device_name in devices:
            device = devices[device_name]
            _logger.debug('device %s', device)
            if device['removable']:
                mount_point = device['mount_path']
                label = device['label']
                if label == '' or label is None:
                    capacity = device['size']
                    label = (_('%.2f GB Volume') % (capacity / (1024.0 ** 3)))
                _logger.debug('Adding device %s', (label))
                if first_device:
                    toolbar.source_combo.append_separator()
                    first_device = False
                toolbar.source_combo.append_item(mount_point, label)

        toolbar.source_combo.set_active(0)
        toolbar.source_combo.handler_unblock(toolbar.source_changed_cb_id)

    def move_up_catalog(self, treeview):
        len_cat = len(self.catalog_history)
        if len_cat == 1:
            return
        else:
            # move a level up the tree
            self.catalog_listview.handler_block(self._catalog_changed_id)
            self.catalog_history.pop()
            len_cat -= 1
            if(len_cat == 1):
                title = self.catalog_history[0]['title']
                self.bt_move_up_catalog.set_label(title)
                self.bt_move_up_catalog.hide_image()
            else:
                title = self.catalog_history[len_cat - 1]['title']
                self.bt_move_up_catalog.set_label(title)
                self.bt_move_up_catalog.show_image()
            self.catalogs = self.catalog_history[len_cat - 1]['catalogs']
            if len(self.catalogs) > 0:
                self.path_iter = {}
                self.categories = []
                for key in self.catalogs.keys():
                    self.categories.append({'text': key, _('within'): []})
                self.toolbar_info.reset()
                self.treemodel.clear()
                for p in self.categories:
                    self.path_iter[p['text']] = \
                            self.treemodel.append([p['text']])
            self.catalog_listview.handler_unblock(self._catalog_changed_id)

    def move_down_catalog(self, treeview):
        treestore, coldex = \
                self.catalog_listview.get_selection().get_selected()
        len_cat = len(self.catalog_history)
        if len_cat > 0 and self.catalog_history[len_cat - 1]['catalogs'] == []:
            self.catalog_history.pop()
            len_cat = len(self.catalog_history)

        # README: when the Activity starts by default there is nothing
        # selected and this signal is called, so we have to avoid this
        # 'append' because it fails
        if coldex is not None:
            self.catalog_history.append(
                    {'title': treestore.get_value(coldex, 0), 'catalogs': []})
            self.__switch_catalog_cb(treestore.get_value(coldex, 0))

    def _get_book_result_cb(self, getter, tempfile, suggested_name,
            path, title, author, lang):
        self.treeview.props.sensitive = True

        if self.catalogs_present:
            self.catalog_listview.props.sensitive = True

        self.sectoolbar.search_entry.props.sensitive = True
        self.toolbar_info.button.props.sensitive = True

        if self._download_content_type.startswith('text/html'):
            # got an error page instead
            self._get_book_error_cb(getter, 'HTTP Error')
            return

        # Write the title, author, language metadata.
        metadata = {}
        metadata['title'] = title
        metadata['author'] = author
        metadata['lang'] = lang

        metadata_file_path = path + '.metadata'
        fp = open(metadata_file_path, 'w')
        fp.write(str(metadata))
        fp.close()

        # Refresh mylibtab
        self._my_library_tab = self._app.get_my_library_tab()
        self._my_library_tab.load_ebooks(self._my_library_tab.treeview)
        self.progressbox.hide()
        self.show_message(_("Book added to Library"))
        self.readbutton.show()
        self.filepath = path
        self.progressbar.set_fraction(0.0)

    def _get_book_progress_cb(self, getter, bytes_downloaded):
        if self._download_content_length > 0:
            _logger.debug("Downloaded %u of %u bytes...",
                          bytes_downloaded, self._download_content_length)
        else:
            _logger.debug("Downloaded %u bytes...",
                          bytes_downloaded)
        total = self._download_content_length
        self.set_downloaded_bytes(bytes_downloaded,  total)
        while Gtk.events_pending():
            Gtk.main_iteration()

    def _get_book_error_cb(self, getter, err):
        self.listview.props.sensitive = True
        self.enable_button(True)
        self.progressbox.hide()
        _logger.error("Getting document: %s", err)
        self._download_content_length = 0
        self._download_content_type = None
        self._getter = None
        if self.source == 'Internet Archive' and \
           getter._url.endswith('_text.pdf'):
            # in the IA server there are files ending with _text.pdf
            # smaller and better than the .pdf files, but not for all
            # the books. We try to download them and if is not present
            # download the .pdf file
            self.download_url = self.download_url.replace('_text.pdf', '.pdf')
            self.get_book()
        else:
            self._allow_suspend()
            self._show_error_alert(_('Error: Could not download %s. ' +
                    'The path in the catalog seems to be incorrect') %
                    self.selected_title)

    def downloadAsEPUB(self, widget):
        tree_sel = self.treeview.get_selection()
        (tm, ti) = tree_sel.get_selected()

        title = tm.get_value(ti, 0)
        author = tm.get_value(ti, 1)
        lang = tm.get_value(ti, 2)
        dl = self._dl[title.decode('utf-8')][0]
        d = dl["application/epub+zip"]
        fn = d.split("/")
        fn = fn[-1]
        df = os.path.join(env.MYLIBPATH, fn)

        thread=downloadFile(d,df,self,title,author,lang)
        thread.start()
        thread.join()

    def downloadAsPDF(self, widget):
        tree_sel = self.treeview.get_selection()
        (tm, ti) = tree_sel.get_selected()

        title = tm.get_value(ti, 0)
        author = tm.get_value(ti, 1)
        lang = tm.get_value(ti, 2)
        dl = self._dl[title.decode('utf-8')][0]
        d = dl["application/pdf"]
        fn = d.split("/")
        fn = fn[-1]
        df = os.path.join(env.MYLIBPATH, fn)

        thread=downloadFile(d,df,self,title,author,lang)
        thread.start()
        thread.join()

    def downloadAsCEIBAL(self, widget):
        tree_sel = self.treeview.get_selection()
        (tm, ti) = tree_sel.get_selected()

        title = tm.get_value(ti, 0)
        author = tm.get_value(ti, 1)
        lang = tm.get_value(ti, 2)
        dl = self._dl[title.decode('utf-8')][0]
        for key, value in dl.iteritems():
            mime = key
            d = value
        fn = d.split("/")
        fn = fn[-1]
        df = os.path.join(env.MYLIBPATH, fn)
        
        if mime == None:
            mime = "Ceibal"

        thread=downloadFile(d,df,self,title,author,lang)
        thread.start()
        thread.join()

    def on_activated(self, widget, row, col, *data):
        rowmetadata = data[0]
        model = widget.get_model()

    def on_selected(self, widget, data = None):
        self.hide_message()
        if self.empty:
            return
        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        tree_model, tree_iter = selection.get_selected()
        if tree_iter is None:
            return
        title = tree_model.get_value(tree_iter, 0)
        author = tree_model.get_value(tree_iter, 1)

        self.toolbar_info.set_info(
            title=title,
            author=author)

        self.toolbar_info.image.show()
        self.toolbar_info.button.show()

        # if multiple formats, show selector
        mime_types = tree_model.get_value(tree_iter, 3)
        if " " in mime_types:
            self.toolbar_info.downloadcombo.show()
        else:
            self.toolbar_info.downloadcombo.hide()

            # By default, when the downloadcombo
            # (download-type-selector) is hidden, EPUB is the default
            # selected mime. Set it to PDF, if the file-format is PDF.
            if mime_types == 'PDF':
                self.toolbar_info.downloadcombo.set_active(1)
            else:
                self.toolbar_info.downloadcombo.set_active(0)

        return True

    def create_model(self):
        '''create the model - a ListStore'''

        rowmetadata = []
        store = Gtk.ListStore(str, str, str, str)

        return [ store, rowmetadata ]

    def create_columns(self, treeView):
        ''' create the columns '''
        # CellRendererText = an object that renders text into a Gtk.TreeView cell
        rendererText = Gtk.CellRendererText()
        rendererText.props.wrap_width = 300
        rendererText.props.wrap_mode = Gtk.WrapMode.WORD

        # column = a visible column in a Gtk.TreeView widget
        # param: title, cell_renderer, zero or more attribute=column pairs
        # text = 0 -> attribute values for the cell renderer from column 0 in the treemodel
        column = Gtk.TreeViewColumn(_("Title"), rendererText, text=0)
        # the logical column ID of the model to sort
        column.set_sort_column_id(0)
        # append the column
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Author"), rendererText, text=1)
        column.set_sort_column_id(1)
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Language"), rendererText, text=2)
        column.set_sort_column_id(2)
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Format"), rendererText, text=3)
        column.set_sort_column_id(3)
        treeView.append_column(column)

    def create_model_catalog(self):
        '''create the model - a ListStore'''

        rowmetadata = []
        store = Gtk.ListStore(str)

        return store

    def create_columns_catalog(self, treeView):
        ''' create the columns '''
        # CellRendererText = an object that renders text into a Gtk.TreeView cell
        rendererText = Gtk.CellRendererText()
        # column = a visible column in a Gtk.TreeView widget
        # param: title, cell_renderer, zero or more attribute=column pairs
        # text = 0 -> attribute values for the cell renderer from column 0 in the treemodel
        column = Gtk.TreeViewColumn(_("Catalogs"), rendererText, text=0)
        # the logical column ID of the model to sort
        column.set_sort_column_id(0)
        # append the column
        treeView.append_column(column)

    def get_tab_label(self):
        return _('Getbooks')

    def searchLib(self,txt):
        file_name = os.path.join(env.SUGAR_ACTIVITY_ROOT, 'GetBooksActivity', 'get-books.cfg')
        config = ConfigParser.ConfigParser()
        config.readfp(open(file_name))
        currentlib = self.sectoolbar.getCurrentLib()
        queryconfig = {}

        section = currentlib
        items = self.config.items(section)

        for item in items:
            queryconfig[item[0]] = item[1]

        assert 'query_uri' in queryconfig.keys()
        queryconfig['query_uri'] = queryconfig['query_uri'] + txt

        l = self.sectoolbar.getCurrentLang()

        #self._context_id = self._statusbar.get_context_id("Ebookreader")
        #self._statusbar.push(self._context_id, u"Buscando libros")
        
        self.empty=True
        self.toolbar_info.reset()
        self.show_message(_("Searching") + "...")
        self.store.clear()

        self.queryresults = opds.RemoteQueryResult(queryconfig,'', l)
        self.queryresults.connect('updated', self.__query_updated_cb)

    def parse_format(self,dl):
        mime = ""
        for key,value in dl.iteritems():
            if (key == "application/pdf") or \
               (key == "pdf"):
                mime=mime+"PDF "
            elif (key == "application/epub") or \
               (key == "epub") or \
               (key == "EPUB") or \
               (key == "application/epub+zip"):
                mime=mime+"EPUB "
            elif key == "application/x-mobipocket-ebook":
                pass
            elif key == "unknown":
                mime=mime+"CEIBAL "
            else:
                mime="ignore"
        return mime.rstrip()
            

    def __query_updated_cb(self, query, midway):
        model = self.treeview.get_model()
        self._dl = {}
        self.empty=False
        #self._statusbar.push(self._context_id, u"Busqueda finalizada")

        for book in self.queryresults.get_book_list():
            if book.get_language() == self.sectoolbar.getCurrentLang() or self.sectoolbar.getCurrentLang() == "all":
                lang = book.get_language()
                author = book.get_author()
                title = book.get_title()
                dl = book.get_download_links()
                url_image = book.get_image_url()
                mime = self.parse_format(dl)
                if mime != "ignore":
                    model.append([ title, author, lang, mime])
                    self._dl [ title ] = [dl,url_image]

        self.treeview.set_model(model)
        if 'bozo_exception' in self.queryresults._feedobj:
            # something went wrong and we have to inform about this
            bozo_exception = self.queryresults._feedobj.bozo_exception
            if not isinstance(bozo_exception, feedparser.CharacterEncodingOverride):
                if isinstance(bozo_exception, urllib2.URLError):
                    if isinstance(bozo_exception.reason, socket.gaierror):
                        if bozo_exception.reason.errno == -2:
                            self.show_message(_('Could not reach the server. '
                                'Maybe you are not connected to the network'))
                            self.window.set_cursor(None)
                            return
                self.show_message(_('There was an error downloading the list.'))
        if (len(self.queryresults.get_catalog_list()) > 0):
            self.hide_message()
            #self.show_message('New catalog list %s was found') \
            #    % self.queryresults._configuration["name"])
            self.catalogs_updated(query, midway)
        elif len(self.queryresults) == 0:
            self.show_message(_('Sorry, no books could be found.'))
        if not midway and len(self.queryresults) > 0:
            self.hide_message()
            query_language = self.get_query_language()
            if query_language != 'all' and query_language != 'en':
                # the bookserver send english books if there are not books in
                # the requested language
                only_english = True
                for book in self.queryresults.get_book_list():
                    if book.get_language() == query_language:
                        only_english = False
                        break
                if only_english:
                    self.show_message(
                            _('Sorry, we only found english books.'))
        self.get_window().set_cursor(None)

    def catalogs_updated(self, query, midway):
        self.catalogs = {}
        for catalog_item in self.queryresults.get_catalog_list():
            _logger.debug('Add catalog %s', catalog_item.get_title())
            catalog_config = {}
            download_link = ''
            download_links = catalog_item.get_download_links()
            for link in download_links.keys():
                download_link = download_links[link]
                break
            catalog_config['query_uri'] = download_link
            catalog_config['opds_cover'] = \
                catalog_item._configuration['opds_cover']
            catalog_config['source'] = catalog_item._configuration['source']
            source_config = _SOURCES_CONFIG[catalog_config['source']]
            catalog_config['name'] = catalog_item.get_title()
            catalog_config['summary_field'] = \
                catalog_item._configuration['summary_field']
            if catalog_item.get_title() in source_config['blacklist']:
                _logger.debug('Catalog "%s" is in blacklist',
                    catalog_item.get_title())
            else:
                self.catalogs[catalog_item.get_title().strip()] = \
                        catalog_config

        if len(self.catalogs) > 0:
            len_cat = len(self.catalog_history)
            self.catalog_history[len_cat - 1]['catalogs'] = self.catalogs
            self.path_iter = {}
            self.categories = []
            for key in self.catalogs.keys():
                self.categories.append({'text': key, _('within'): []})
            self.treemodel.clear()
            self.toolbar_info.reset()

            for p in self.categories:
                self.path_iter[p['text']] = \
                        self.treemodel.append([p['text']])

            title = self.catalog_history[len_cat - 1]['title']
            self.bt_move_up_catalog.set_label(title)
            self.bt_move_up_catalog.show_image()

        else:
            self.catalog_history.pop()


    def get_tab_toolbar_icon_name(self):
        return 'bookreader-mybooks'

class downloadFile(threading.Thread):
    def __init__(self, url, path, iatab, title, author, lang):
        threading.Thread.__init__(self)  
        self.url = url
        self.path = path
        self.iatab = iatab
        self.title = title
        self.author = author
        self.lang = lang

    def run(self):
        _logger.error('DOWNLOAD BOOK %s', self.url)
        self.iatab.hide_message()
        self.iatab.progressbox.show()
        self.iatab.progressbar.show()
        self.iatab.cancel_btn.show()
        self.iatab.treeview.props.sensitive = False

        if self.iatab.catalogs_present:
            self.iatab.catalog_listview.props.sensitive = False

        self.iatab.sectoolbar.search_entry.props.sensitive = False
        self.iatab.toolbar_info.button.props.sensitive = False

        # hack to get the redirected filename
        test=urllib2.urlopen(self.url)
        if test.info().has_key('Content-Disposition'):
            localName = test.info()['Content-Disposition'].split('filename=')[1]
            if localName[0] == '"' or localName[0] == "'":
                localName = localName[1:-1]
            self.path=os.path.join(env.MYLIBPATH, localName)

        self._getter = opds.ReadURLDownloader(self.url)
        self.iatab._getter=self._getter
        self._getter.connect("finished",
                self.iatab._get_book_result_cb, self.path, self.title,
                self.author, self.lang)
        self._getter.connect("progress", self.iatab._get_book_progress_cb)
        self._getter.connect("error", self.iatab._get_book_error_cb)
        _logger.debug("Starting download from %s to %s", self.url, self.path)
        try:
            self._getter.start(self.path)
        except:
            self.iatab._show_error_alert(_('Error'), _('Connection timed out for ') +
                    self.iatab.selected_title)

        self.iatab._download_content_length = self._getter.get_content_length()
        self.iatab._download_content_type = self._getter.get_content_type()



class ButtonWithImage(Gtk.Button):

    def __init__(self, label_text):
        GObject.GObject.__init__(self,)
        self.icon_move_up = Icon(icon_name='go-up')
        # self.remove(self.get_children()[0])
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(self.hbox)
        self.hbox.add(self.icon_move_up)
        self.label = Gtk.Label(label=label_text)
        self.hbox.add(self.label)
        self.show_all()

    def hide_image(self):
        self.icon_move_up.hide()

    def show_image(self):
        self.icon_move_up.show()

    def set_label(self, text):
        self.label.set_text(text)
