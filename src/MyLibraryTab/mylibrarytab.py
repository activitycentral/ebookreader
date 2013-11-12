#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2013 Rafael Ortiz rafael@activitycentral.com
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
from gi.repository import GObject
import logging
import subprocess
import env_settings as env

from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics import iconentry
from sugar3 import mime

from utils import is_ubuntu,get_active_desktop
from ReadTab.decryptfile import is_file_encrypted, decrypt_and_return_path_of_decrypted_file

desktop = get_active_desktop()

if desktop is "Sugar":
    from sugar3.graphics.objectchooser import ObjectChooser

from ebookreadertab import EBookReaderTab
from GetBooksTab import readerUtilities as RU

_logger = logging.getLogger(__name__)


COVERHEIGHT = 150
COVERWIDTH = 100

if not os.path.exists(env.MYLIBPATH):
    os.mkdir(env.MYLIBPATH)
    os.chmod(env.MYLIBPATH, 0755)
    

def get_separador(draw=False, width=0, expand=False):
    
    separador = Gtk.SeparatorToolItem()
    separador.props.draw = draw
    separador.set_size_request(width, -1)
    separador.set_expand(expand)
    
    return separador

def utf_get(text):
    
    ret = ""
    
    try:
        ret = u"%s" % text
        
    except:
        ret = ""
        
    return ret
    
class ToolBar(Gtk.Toolbar):
    
    def __init__(self):
        
        Gtk.Toolbar.__init__(self)
        
        self.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)
        
        ### ComboBox for languages
        self.source_combo = ComboLanguages()
        self.source_combo.connect('changed', self.__source_changed)
        self.source_combo.set_tooltip_text(_("Select the Language."))
        self.wrap = Gtk.Alignment(xalign=0.0, yalign=0.5, xscale=0.0, yscale=0.0)
        self.wrap.add(self.source_combo)
        
        item = Gtk.ToolItem()
        item.set_expand(False)
        item.add(self.wrap)
        self.insert(item, -1)
        
        self.insert(get_separador(
            draw=False, width=20,
            expand=False), -1)
        
        ### Entry text for search
        search_entry = iconentry.IconEntry()
        
        search_entry.modify_bg(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#ebecd3"))
            
        search_entry.modify_base(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#ebecd3"))

        #search_entry.set_has_frame(False)

        search_entry.set_icon_from_name(
            iconentry.ICON_ENTRY_PRIMARY,
            'system-search')
            
        search_entry.add_clear_button()
        search_entry.connect('activate',
           self.__search_entry_activate)
        
        width = int(Gdk.Screen.width() / 4)
        search_entry.set_size_request(width, -1)
        search_entry.set_tooltip_text(_("Type to Search."))
        
        item = Gtk.ToolItem()
        item.set_expand(True)
        item.add(search_entry)
        search_entry.show()
        item.show()
        
        self.insert(item, -1)
        
        self.insert(get_separador(
            draw=False, width=10,
            expand=False), -1)
        
        ### button to import
        button = Gtk.ToolButton()
        button.set_tooltip_text(_("Import a book."))
        image = Gtk.Image()
        
        size = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-import.svg'),
                size[1], size[2]))
            
        button.set_icon_widget(image)
        button.connect("clicked", self.__import_file)
        image.show()
        button.show()
        
        self.insert(button, -1)
        
        self.insert(get_separador(
            draw=False, width=0,
            expand=True), -1)
            
        self.show_all()

    def __search_entry_activate(self, widget):
        """
        Perform a search.
        """
        
        title_or_autor = widget.get_text()
        
        language = False
        
        model = self.source_combo.get_model()
        first = model.get_value(model.get_iter_first(), 0)
        active = model.get_value(self.source_combo.get_active_iter(), 0)
        
        if active != first:
            language = self.source_combo.get_active_text()
        
        self.get_parent().search(title_or_autor, language)
        
    def __import_file(self, widget):
        
        if desktop is "Sugar":
            self.__show_journal_object()
            
        else:
            self.__show_file_object()
    
    def __show_file_object(self):
        """
        Open a filechooser to select a file.
        """
        
        filechooser = My_FileChooser(
            parent_window = self.get_toplevel(),
            action_type = Gtk.FileChooserAction.OPEN,
            filter_type = "Ebook",
            title = _('Choose document'),
            mymes = [
                "application/pdf",
                "application/pdf-bw",
                "application/epub+zip",
                "image/x.djvu",
                "application/x-ceibal"])
    
        filechooser.connect("load", self.__run_import_file)
        
    def __run_import_file(self, widget, file_path):
        
        self.read_file(file_path)
        
    def __show_journal_object(self):
        """
        Open a view of the journal to select a file.
        """
        
        #FIXME: Add Filter to import from the journal.
        chooser = ObjectChooser(parent=self.get_toplevel())
            #what_filter=mime.GENERIC_TYPE_TEXT)
            
        try:
            result = chooser.run()
            
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                
                if jobject and jobject.file_path:
                    if os.path.islink(jobject.file_path):
                        self.read_file(os.readlink(jobject.file_path), jobject.metadata['title'])
                    else: 
                        self.read_file(jobject.file_path, jobject.metadata['title'])
                    
        finally:
            chooser.destroy()
            del chooser
            
    def __source_changed(self, widget):
        """
        When the user selects an item in the combo.
        """
        
        # FIXME: implement (Now it is not necessary)
        pass # widget.get_active_text()
        
    def read_file(self, file_path, title=None):
        """
        Read the selected file in the view of jurnal
        and adds it to the list of MyLibraryTab.
        """
        
        self.get_parent().save_ebook(file_path, title)
        self.get_parent().treeview.select_last()

class MyLibraryTab(EBookReaderTab):

    __gsignals__ = {
    "load":(GObject.SignalFlags.RUN_FIRST,
        None, (GObject.TYPE_PYOBJECT,))}
        
    def __init__(self, app):
        
        EBookReaderTab.__init__(self, app)
        _logger.debug('Starting mylibrarytab...')
        
        self._app = app
        self.pack_start(ToolBar(), False, False, 0)
        
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        
        sw.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC)
            
        self.pack_start(sw, True, True, 0)

        self.treeview = TreeView()
        sw.add_with_viewport(self.treeview)
        
        self.toolbar_info = SkirtWidget()
        
        ### Only one edge to provide the desired color
        aestheticbox = Gtk.EventBox()
        aestheticbox.modify_bg(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#943a43"))
            
        aestheticbox.add(self.toolbar_info)
        
        self.pack_end(aestheticbox, False, False, 0)
        
        self.show_all()
        
        self.treeview.connect("new_selection", self.__new_selection)
        
        self.toolbar_info.connect("load",
            self.load_selected_entry,
            self.treeview)
        
        self.load_ebooks(self.treeview)
        
        self.toolbar_info.connect("delete", self.__delete_book)
        
    def __delete_book(self, widget):
        """
        Removes a book and cover.
        """
        
        model, iter = self.treeview.get_selection().get_selected()
        
        if iter is None: return

        file_path = model.get_value(iter, 3)
        
        dir_name = os.path.dirname(file_path)
        extension = os.path.splitext(os.path.split(os.path.basename(file_path))[1])[1]
        file_name = os.path.basename(file_path).split(extension)[0]
        thumbnail_path = os.path.join(dir_name, "%s.png" % file_name)
        
        if os.path.exists(file_path):
            os.remove("%s" % (os.path.join(file_path)) )
        
        if os.path.exists(thumbnail_path):
            os.remove("%s" % (os.path.join(thumbnail_path)) )
        
        self.treeview.get_model().remove(iter)
        
    def load_file(self, filepath):
        """
        Open the book on the reader.
        """
        
        self._app.load_and_read_book((filepath, None,))

    def select_previous_entry(self, treeview):
        (current_row, current_column) = treeview.get_cursor()
        if str(current_row) == '0':
            return

        treeview.set_cursor_on_cell(Gtk.TreePath(int(str(current_row))
            - 1), None, None, False)

    def select_next_entry(self, treeview):
        (current_row, current_column) = treeview.get_cursor()
        if str(current_row) == str((len(treeview.get_model()) - 1)):
            return

        treeview.set_cursor_on_cell(Gtk.TreePath(int(str(current_row))
            + 1), None, None, False)
        
    def load_selected_entry(self, widget, treeview):
        """
        Send open a book.
        """
        
        model, iter = treeview.get_selection().get_selected()
        
        if iter is None: return

        file_path = model.get_value(iter, 3)
        
        self.load_file(file_path)
        
    def __new_selection(self, widget, selection):
        """
        receives information from the selected book
        """
        
        self.toolbar_info.set_info(selection)

    def get_field_from_metadata_or_return_default(self, field, file_path):
        metadata_file_path = file_path + '.metadata'
        if os.path.exists(metadata_file_path):
            fp = open(metadata_file_path, 'r')
            metadata = eval(fp.read().strip('\n'))

            value = None
            if field in metadata.keys():
                value =  metadata[field]
            else:
                value = ""

            fp.close()
            return value
        else:
            return ""

    def append_book(self, file_path, treeview):
        """
        Read a file and adds it to the
        list of MyLibraryTab.
        """
        
        decrypted_filepath = False

        title = self.get_field_from_metadata_or_return_default('title', file_path)
        author = self.get_field_from_metadata_or_return_default('author', file_path)
        language = self.get_field_from_metadata_or_return_default('lang',file_path)

        metadata = {}
        
        file = file_path
        
        if is_file_encrypted(file_path):
            decrypted_filepath = decrypt_and_return_path_of_decrypted_file(file_path).replace('file://', '')
                
        if decrypted_filepath:
            if os.path.exists(decrypted_filepath):
                file = decrypted_filepath
                
        f = os.path.basename(file)
        extension = str(os.path.splitext(os.path.split(f)[1])[1]).lower()
        
        ### Generate the name for the cover
        dir_name = os.path.dirname(file_path)
        file_name = os.path.basename(file_path).split(
            str(os.path.splitext(os.path.split(f)[1])[1]))[0]
        thumbnail_path = os.path.join(dir_name, "%s.png" % file_name)
            
        ### Obtain its metadata
        if extension in [".epub"]:
            try:
                metadata = RU.getEPUBMetadata(file)
            
            except:
                pass
            
            if "title" in metadata:
                if title == "":
                    title = utf_get(metadata["title"])

            if "creator" in metadata:
                if author == "":
                    author = utf_get(metadata["creator"])

            if "language" in metadata:
                if language == "":
                    language = str(utf_get(metadata["language"]))
                
            if not os.path.exists(thumbnail_path):
                import epubcover as ep
                ep.get_epub_covert(file, thumbnail_path)
                
        ### Obtain its metadata
        else:
            try:
                metadata = RU.getPDFMetadata(file)
                
            except:
                pass
            
            if "Title" in metadata:
                if title == "":
                    title = utf_get(metadata["Title"])
            if "Creator" in metadata:
                if author == "":
                    author = utf_get(metadata["Creator"])
                
            ### Build the cover to pdf, djvu and dvi
            if not os.path.exists(thumbnail_path):
                new_extension = str(os.path.splitext(os.path.split(file)[1])[1]).lower()
                
                if new_extension in [".pdf", ".djvu", ".dvi"]:
                    import commands
                    commands.getoutput('evince-thumbnailer %s --size 75 %s' % (file, thumbnail_path))
                
        ### Corrections to the outputs
        if not title:
            extension = str(os.path.splitext(os.path.split(file_path)[1])[1])
            title = utf_get(os.path.basename(file_path).split(extension)[0].replace("_", " ").strip())
        
        if language:
            basepath = os.path.dirname(__file__)
            path = os.path.join(basepath, "language.slv")
            
            import shelve
            
            dict = shelve.open(path)
            
            if dict.get(language, ""):
                language = dict[language]["nativeName"]
                
            dict.close()


        date, unused_err = subprocess.Popen(['date "+%d %b %Y" -d @' + str(int(os.stat(file_path).st_mtime))],
                                              stdout=subprocess.PIPE,
                                              shell=True).communicate()
        date = date.rstrip('\n')
            
        ### Add metadata to the list
        treeview.get_model().append(
            [title,
            author,
            language,
            file_path,
            date,
            str(int(os.stat(file_path).st_mtime))])
        
        ### Delete the file decryption
        if decrypted_filepath:
            if os.path.exists(decrypted_filepath):
                os.remove(decrypted_filepath)
        
    def normalize_path(self, file_path):
        
        if file_path.startswith('file://'):
            file_path = file_path.split('file://')[1]

        return file_path

    def save_ebook(self, file_path, title=None):
        """
        Save the book in the library.
        """

        file_path = self.normalize_path(file_path)
        
        if not os.path.exists(file_path): return
        
        extension = str(os.path.splitext(os.path.split(file_path)[1])[1]).lower()
        
        extensions = [
            ".epubceibal",
            ".djvu",
            ".pdf" ,
            ".epub",
            ".pdfceibal"]
        
        if extension in extensions:
            # FIXME: Each time you export one book from
            # the journal, it generates a different name as
            # the file copy journal for this particular instance.
            destination = os.path.join(env.MYLIBPATH, os.path.basename(file_path))
            if title is not None:
                destination = os.path.join(env.MYLIBPATH, title)

            if file_path != destination:
                expression = "cp \"" + file_path + "\" \"" + destination + "\""
                os.system(expression)
                os.chmod(destination, 0755)
            
            if not destination in self.__get_books_in_list():
                try:
                    self.append_book(destination, self.treeview)
                except:
                    pass

            self.display_books_reverse_sorted_by_date(self.treeview)
        else:
            return

    def display_books_reverse_sorted_by_date(self, treeview):
        date_column = treeview.get_column(4).emit('clicked')
        date_column = treeview.get_column(4).emit('clicked')
        
    def __get_books_in_list(self):
        """
        Returns the list of paths of those
        books loaded on MyLibraryTab.
        """
        
        paths = []
        
        model = self.treeview.get_model()
        item = model.get_iter_first()
        
        while item:
            paths.append(model.get_value(item, 3))
            item = model.iter_next(item)
            
        return paths
    
    def load_ebooks(self, treeview):
        """
        This function is not used in this class.
        """
        
        treeview.get_model().clear()
        
        for file_name in os.listdir(env.MYLIBPATH):
            path = os.path.join(env.MYLIBPATH, file_name)
            extension = os.path.splitext(os.path.split(os.path.basename(path))[1])[1]
            
            extensions = [
                ".epubceibal",
                ".djvu",
                ".pdf" ,
                ".epub",
                ".pdfceibal"]
                
            if extension.lower() in extensions:
                try:
                    self.append_book(os.path.join(env.MYLIBPATH, file_name),treeview)
                except:
                    pass

            self.display_books_reverse_sorted_by_date(treeview)
    
        treeview.set_cursor_on_cell(Gtk.TreePath(0), None, None, False)
        
    def get_tab_label(self):
        
        return _('My Library')

    def get_tab_toolbar_icon_name(self):
        
        return 'bookreader-libraries'
    
    def search(self, title_or_autor, language):
        """
        Perform a search for the user.
        """
        
        if not self.treeview.search(title_or_autor, language):
            dialog = My_Alert_Dialog(
                parent_window = self.get_toplevel(),
                label = _("No Matches were found."))
            
            response = dialog.run()
            dialog.destroy()

class SkirtWidget(Gtk.EventBox):
    
    __gsignals__ = {
    "load":(GObject.SignalFlags.RUN_FIRST,
        None,[]),
    "delete":(GObject.SignalFlags.RUN_FIRST,
        None, [])}
        
    def __init__(self):
        
        Gtk.EventBox.__init__(self)
        
        self.set_border_width(10)
        
        self.modify_bg(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#943a43"))
        
        basebox = Gtk.HBox()
        
        ### Bookcover
        self.image = Gtk.Image()
        
        self.image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-cover-placeholder.svg'),
                COVERWIDTH,COVERHEIGHT))
        
        basebox.pack_start(self.image, False, False, 5)
        
        ### Widget Text Info
        self.widget_info = WidgetInfo()
        
        basebox.pack_start(self.widget_info, True, True, 5)
        
        ### Delete button
        delbutton = Gtk.ToolButton()
        delbutton.modify_bg(Gtk.StateType.PRELIGHT, Gdk.color_parse("#ebecd3"))
        delbutton.set_tooltip_text(_("Delete this Book."))
        image = Gtk.Image()
        
        image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-deletebook.svg'),
                75, 75))
        
        delbutton.set_icon_widget(image)
        delbutton.connect("clicked", self.__emit_delete)
        basebox.pack_start(delbutton, False, False, 0)
        
        ### Button Read
        readbutton = Gtk.ToolButton()
        readbutton.set_tooltip_text(_("Read this Book."))
        
        image = Gtk.Image()
        
        image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-read-large-over.svg'),
                75,75))
            
        readbutton.set_icon_widget(image)
        readbutton.connect("clicked", self.__read_ebook)
        
        basebox.pack_end(readbutton, False, False, 0)
        
        self.add(basebox)
        
        self.show_all()
        
        
    def __emit_delete(self, widget):
        """
        When you click on delete.
        """
        self.emit("delete")
        self.set_info()
    
    def __read_ebook(self, widget):
        """
        Performs read this file.
        """
        self.emit("load")
    
    def set_info(self, selection):
        """
        Book Displays information selected by the user.
        """
        
        title, autor, language, path, date = selection
        
        self.widget_info.set_info(
            title=title,
            autor=autor,
            language=language)
            
        self.__set_covert(path)
        
    def __set_covert(self, path):
        """
        Gets the selected book cover.
        """
        
        dir_name = os.path.dirname(path)
        extension = os.path.splitext(os.path.split(os.path.basename(path))[1])[1]
        file_name = os.path.basename(path).split(extension)[0]
        thumbnail_path = os.path.join(dir_name, "%s.png" % file_name)
        
        if os.path.exists(thumbnail_path):
            self.image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                thumbnail_path,
                COVERWIDTH,COVERHEIGHT))
                
        else:
            self.image.set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(env.ICONS_PATH,
                'bookreader-cover-placeholder.svg'),
                COVERWIDTH,COVERHEIGHT))
        
class ComboLanguages(Gtk.ComboBoxText):
    
    def __init__(self):
        
        model = Gtk.ListStore(GObject.TYPE_STRING)
        cell = Gtk.CellRendererText()
        
        Gtk.ComboBoxText.__init__(self)
        
        self.modify_base(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#ebecd3"))
        
        self.pack_start(cell, True)
        #self.add_attribute(cell, 'text', 0)
        self.set_model(model)
        
        for language in [_("Any Language"), _("Spanish"), _("English")]:
            self.append_text(language)
        
        self.show_all()
        
        self.set_active(0)
        self.set_sensitive(True)
        
class TreeView(Gtk.TreeView):
    
    __gsignals__ = {
    "new-selection":(GObject.SignalFlags.RUN_FIRST,
        None, (GObject.TYPE_PYOBJECT, ))}
        
    def __init__(self):
        
        Gtk.TreeView.__init__(self,
            Gtk.ListStore(GObject.TYPE_STRING,
            GObject.TYPE_STRING, GObject.TYPE_STRING,
            GObject.TYPE_STRING, GObject.TYPE_STRING,
            GObject.TYPE_STRING))
            
        # Commenting out the changing of background and base colors, as
        # these are not working correctly in GTK3.
        """
        self.modify_bg(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#c2c079"))
        
        self.modify_base(
            Gtk.StateType.NORMAL,
            Gdk.color_parse("#ebecd3"))
        """
        
        self.__create_columns()
        self.set_property("rules-hint", True)
        
        self.value_select = False
        
        self.treeselection = self.get_selection()
        self.treeselection.set_select_function(self.__selection, None)
        
        self.connect("row-activated", self.__activate_row)
        
    def __create_columns(self):
        """
        create the columns.
        """
        
        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), render, text=0)
        column.set_property('resizable', True)
        column.set_property('visible', True)
        column.set_sort_column_id(0)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(column)
        
        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Author"), render, text=1)
        column.set_property('resizable', True)
        column.set_property('visible', True)
        column.set_sort_column_id(1)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(column)

        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Language"), render, text=2)
        column.set_property('resizable', True)
        column.set_property('visible', True)
        column.set_sort_column_id(2)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(column)
        
        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Path"), render, text=3)
        column.set_property('resizable', True)
        column.set_property('visible', False)
        column.set_sort_column_id(3)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(column)

        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Input Time"), render, text=4)
        column.set_property('resizable', True)
        column.set_property('visible', True)
        column.set_sort_column_id(5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(column)
        
    def __selection(self, widget, model=None, path=None,
            path_currently_selected=None,
            user_data=None):
        """
        When you select an item in the list.
        """
        
        iter = self.get_model().get_iter(path)
        model = self.get_model()
        
        valor = [
            model.get_value(iter, 0),
            model.get_value(iter, 1),
            model.get_value(iter, 2),
            model.get_value(iter, 3),
            model.get_value(iter, 4)]
        
        if self.value_select != valor:
            self.value_select = valor
            self.scroll_to_cell(path)
            self.emit('new-selection', self.value_select)
            
        return True

    def __activate_row(self, treeview, path, view_column):
        """
        When you double click on the list, the book opens.
        """
        
        iter = self.get_model().get_iter(path)
        model = self.get_model()
        
        self._app.load_and_read_book((model.get_value(iter, 3), None,))
        
        return True
    
    def select_last(self):
        """
        Select the last item in the list.
        """
        
        model = self.get_model()
        item = model.get_iter_first()
        
        iter = None
        
        while item:
            iter = item
            item = model.iter_next(item)
            
        if iter:
            self.treeselection.select_path(model.get_path(iter))
        
    def search(self, title_or_autor, language):
        """
        Find an item in the list that contains title_or_autor
        searched the title and author fields and the selected
        language in the field.
        
        If the search is successful, select the book and
        returns True, otherwise it returns False.
        """
        
        model = self.get_model()
        item = model.get_iter_first()
        
        iter = None
        found = False
        
        while item:
            iter = item
            
            valor = [
                str(model.get_value(iter, 0)).lower(),
                str(model.get_value(iter, 1)).lower(),
                str(model.get_value(iter, 2)).lower()]
            
            for word in title_or_autor.split():
                if word.lower() in valor[0] \
                    or word.lower() in valor[1]:
                        
                        if language:
                            if language.lower() in valor[2]:
                                found = True
                                
                            else:
                                found = False
                            
                        else:
                            found = True
                
                if found: break
                
            if found: break
        
            item = model.iter_next(item)
            
        if found:
            self.treeselection.select_path(model.get_path(iter))
            return True
        
        else:
            return False
        
class WidgetInfo(Gtk.VBox):
    
    __gsignals__ = {
    "delete":(GObject.SignalFlags.RUN_FIRST,
        None, [])}
        
    def __init__(self):
        
        Gtk.VBox.__init__(self)
        
        self.title = Gtk.Label()
        self.title.set_justify(Gtk.Justification.LEFT)
        self.title.set_line_wrap(True)
        
        self.autor = Gtk.Label()
        self.autor.set_justify(Gtk.Justification.LEFT)
        self.autor.set_line_wrap(True)
        
        box = Gtk.HBox()
        
        self.language = Gtk.Label()
        self.language.set_justify(Gtk.Justification.LEFT)
        self.language.set_line_wrap(True)
        
        
        for widget in [self.title, self.autor, self.language]:
            box = Gtk.HBox()
            box.pack_start(Gtk.Label(widget.get_text()), False, False, 10)
            box.pack_start(widget, False, False, 0)
            self.pack_start(box, True, True, 5)
        
        self.show_all()
        
    def __emit_delete(self, widget):
        """
        When you click on delete.
        """
        
        self.emit("delete")
        self.set_info()
        
    def set_info(self, title='', autor='', language=''):
        """
        Receives information from the selected book.
        """
        
        if not title:
            self.title.set_text("")
            
        else:
            self.title.set_markup("<big><b>%s</b></big>" % title)
            
        if not autor:
            self.autor.set_text("")
            
        else:
            self.autor.set_text("%s" % autor)
            
        if not language:
            self.language.set_text("")
        
        else:
            self.language.set_text(_("Language") + ": %s" % language)

class My_FileChooser(Gtk.FileChooserDialog):
    
    __gsignals__ = {
    "load":(GObject.SignalFlags.RUN_FIRST,
        None, (GObject.TYPE_PYOBJECT,))}
        
    def __init__(self,
        parent_window = None,
        action_type = None,
        filter_type = None,
        title = None,
        mymes = None):
        
        Gtk.FileChooserDialog.__init__(self,
            parent = parent_window,
            action = action_type,
            title = title)
            
        self.modify_bg(0, Gdk.color_parse("#A6A6A6"))
        
        self.set_modal(True)
        self.set_size_request( 640, 480 )
        self.set_select_multiple(False)
        
        default_path = os.path.join(HOME, "Descargas")
        
        if not os.path.exists(default_path):
            
            if os.path.exists(os.path.join(HOME, "Downloads")):
                default_path = os.path.join(HOME, "Downloads")
            
            elif os.path.exists(os.path.join(HOME, "Download")):
                default_path = os.path.join(HOME, "Download")
                
        self.set_current_folder_uri("file:///%s" % default_path)
        
        if filter_type != None:
            filter = Gtk.FileFilter()
            filter.set_name(filter_type)
            
            for myme in mymes:
                filter.add_mime_type(myme)
                
            self.add_filter(filter)
        
        hbox = Gtk.HBox()
        
        open = Gtk.Button(_("Open"))
        exit = Gtk.Button(_("Cancel"))
        
        hbox.pack_end(open, False, False, 5)
        hbox.pack_end(exit, False, False, 5)
        
        self.set_extra_widget(hbox)
        
        self.show_all()
        
        exit.connect("clicked", self.__exit)
        open.connect("clicked", self.__open)
        
        self.connect("file-activated", self.__file_activated)
        
    def __file_activated(self, widget):
        
        self.__open(None)
        
    def __open(self, widget):
        
        self.emit("load", self.get_filename())
        self.__exit(None)

    def __exit(self, widget):
        
        self.destroy()
        
class My_Alert_Dialog(Gtk.Dialog):
    
    def __init__(self, parent_window = None, label = ""):
        
        Gtk.Dialog.__init__(
            self, title = _("Attention") + " !",
            parent = parent_window,
            flags = Gtk.DialogFlags.MODAL,
            buttons = ("OK", Gtk.ResponseType.ACCEPT))
        
        self.modify_bg(0, Gdk.color_parse("#A6A6A6"))
        
        label = Gtk.Label(label)
        label.show()
        
        self.set_border_width(10)
        
        self.vbox.pack_start(label, True, True, 0)
        
