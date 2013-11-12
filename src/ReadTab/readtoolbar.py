# Copyright (C) 2006, Red Hat, Inc.
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

from gettext import gettext as _
import logging

from gi.repository import GObject
from gi.repository import Gtk
import os
import simplejson

from sugar3.graphics.combobox import ComboBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.toolcombobox import ToolComboBox
from sugar3.graphics.menuitem import MenuItem
from sugar3.graphics import iconentry


class ViewToolbar(Gtk.Toolbar):
    __gtype_name__ = 'ViewToolbar'

    __gsignals__ = {
        'go-fullscreen': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        self._view = None
        self._bookmarkmanager = None
        self._update_offset = True

        self._zoom_out = ToolButton('zoom-out')
        self._zoom_out.set_tooltip(_('Zoom out'))
        self._zoom_out.connect('clicked', self._zoom_out_cb)
        self.insert(self._zoom_out, -1)
        self._zoom_out.show()

        self._zoom_in = ToolButton('zoom-in')
        self._zoom_in.set_tooltip(_('Zoom in'))
        self._zoom_in.connect('clicked', self._zoom_in_cb)
        self.insert(self._zoom_in, -1)
        self._zoom_in.show()

        self._zoom_to_width = ToolButton('zoom-best-fit')
        self._zoom_to_width.set_tooltip(_('Zoom to width'))
        self._zoom_to_width.connect('clicked', self._zoom_to_width_cb)
        self.insert(self._zoom_to_width, -1)
        self._zoom_to_width.show()

        palette = self._zoom_to_width.get_palette()
        menu_item = MenuItem(_('Zoom to fit'))
        menu_item.connect('activate', self._zoom_to_fit_menu_item_activate_cb)
        palette.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Actual size'))
        menu_item.connect('activate', self._actual_size_menu_item_activate_cb)
        palette.menu.append(menu_item)
        menu_item.show()

        tool_item = Gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self._zoom_spin = Gtk.SpinButton()
        self._zoom_spin.set_range(5.409, 400)
        self._zoom_spin.set_increments(1, 10)
        self._zoom_spin_notify_value_handler = self._zoom_spin.connect(
                'notify::value', self._zoom_spin_notify_value_cb)
        tool_item.add(self._zoom_spin)
        self._zoom_spin.show()

        zoom_perc_label = Gtk.Label(_("%"))
        zoom_perc_label.show()
        tool_item_zoom_perc_label = Gtk.ToolItem()
        tool_item_zoom_perc_label.add(zoom_perc_label)
        self.insert(tool_item_zoom_perc_label, -1)
        tool_item_zoom_perc_label.show()

        spacer = Gtk.SeparatorToolItem()
        spacer.props.draw = False
        self.insert(spacer, -1)
        spacer.show()

        self._fullscreen = ToolButton('view-fullscreen')
        self._fullscreen.set_tooltip(_('Fullscreen'))
        self._fullscreen.connect('clicked', self._fullscreen_cb)
        self.insert(self._fullscreen, -1)
        self._fullscreen.show()

        self._view_notify_zoom_handler = None

    def set_view(self, view):
        self._view = view

    def set_bookmarkmanager(self, bookmarkmanager):
        self._bookmarkmanager = bookmarkmanager

    def _zoom_spin_notify_value_cb(self, zoom_spin, pspec):
        self._view.set_zoom(zoom_spin.props.value)

    def _view_notify_zoom_cb(self, model, pspec):
        self._zoom_spin.disconnect(self._zoom_spin_notify_value_handler)
        try:
            self._zoom_spin.props.value = round(self._view.get_zoom())
        finally:
            self._zoom_spin_notify_value_handler = self._zoom_spin.connect(
                    'notify::value', self._zoom_spin_notify_value_cb)

    def __set_progress_if_applicable(self):
        if (self._view.show_progress_bar() is True) and \
           (self._update_offset is True):
            self._view.get_maximum_offset_possible()

    def zoom_in(self, zoom_amount):
        self._view.zoom_in(zoom_amount)
        self._view._main_instance.window.force_ui_updates()
        self.__set_progress_if_applicable()

    def _zoom_in_cb(self, button, zoom_amount = 1):
        if self._view.can_zoom_in():
            self.zoom_in(zoom_amount)
            self._view._number_of_times_zoomed = \
                    self._view._number_of_times_zoomed + zoom_amount

    def zoom_out(self, zoom_amount):
        self._view.zoom_out(zoom_amount)
        self._view._main_instance.window.force_ui_updates()
        self.__set_progress_if_applicable()


    def _zoom_out_cb(self, button, zoom_amount = 1):
        if self._view.can_zoom_out():
            self.zoom_out(zoom_amount)
            self._view._number_of_times_zoomed = \
                    self._view._number_of_times_zoomed - zoom_amount

    def update_offset(self, update):
        self._update_offset = update

    def zoom_to_width(self):
        self._view.zoom_to_width()

    def _zoom_to_width_cb(self, button):
        self.zoom_to_width()

    def _zoom_to_fit_menu_item_activate_cb(self, menu_item):
        self._view.zoom_to_best_fit()

    def _actual_size_menu_item_activate_cb(self, menu_item):
        self._view.zoom_to_actual_size()

    def _fullscreen_cb(self, button):
        self.emit('go-fullscreen')


class SpeechToolbar(Gtk.Toolbar):

    def __init__(self, activity):
        Gtk.Toolbar.__init__(self)
        voicebar = Gtk.Toolbar()
        self._activity = activity
        if not speech.supported:
            return

        self.load_speech_parameters()

        self.sorted_voices = [i for i in speech.voices()]
        self.sorted_voices.sort(self.compare_voices)
        default = 0
        for voice in self.sorted_voices:
            if voice[0] == speech.voice[0]:
                break
            default = default + 1

        # Play button
        self.play_btn = ToggleToolButton('media-playback-start')
        self.play_btn.show()
        self.play_btn.connect('toggled', self.play_cb)
        self.insert(self.play_btn, -1)
        self.play_btn.set_tooltip(_('Play / Pause'))

        self.voice_combo = ComboBox()
        for voice in self.sorted_voices:
            self.voice_combo.append_item(voice, voice[0])
        self.voice_combo.set_active(default)

        self.voice_combo.connect('changed', self.voice_changed_cb)
        combotool = ToolComboBox(self.voice_combo)
        self.insert(combotool, -1)
        combotool.show()

        self.pitchadj = Gtk.Adjustment(0, -100, 100, 1, 10, 0)
        pitchbar = Gtk.HScale(self.pitchadj)
        pitchbar.set_draw_value(False)
        pitchbar.set_update_policy(Gtk.UPDATE_DISCONTINUOUS)
        pitchbar.set_size_request(150, 15)
        self.pitchadj.set_value(speech.pitch)
        pitchtool = Gtk.ToolItem()
        pitchtool.add(pitchbar)
        pitchtool.show()
        self.insert(pitchtool, -1)
        pitchbar.show()

        self.rateadj = Gtk.Adjustment(0, -100, 100, 1, 10, 0)
        ratebar = Gtk.HScale(self.rateadj)
        ratebar.set_draw_value(False)
        ratebar.set_update_policy(Gtk.UPDATE_DISCONTINUOUS)
        ratebar.set_size_request(150, 15)
        self.rateadj.set_value(speech.rate)
        ratetool = Gtk.ToolItem()
        ratetool.add(ratebar)
        ratetool.show()
        self.insert(ratetool, -1)
        ratebar.show()
        self.pitchadj.connect("value_changed", self.pitch_adjusted_cb)
        self.rateadj.connect("value_changed", self.rate_adjusted_cb)

    def compare_voices(self,  a,  b):
        if a[0].lower() == b[0].lower():
            return 0
        if a[0] .lower() < b[0].lower():
            return -1
        if a[0] .lower() > b[0].lower():
            return 1

    def voice_changed_cb(self, combo):
        speech.voice = combo.props.value
        speech.say(speech.voice[0])
        self.save_speech_parameters()

    def pitch_adjusted_cb(self, get):
        speech.pitch = int(get.value)
        speech.say(_("pitch adjusted"))
        self.save_speech_parameters()

    def rate_adjusted_cb(self, get):
        speech.rate = int(get.value)
        speech.say(_("rate adjusted"))
        self.save_speech_parameters()

    def load_speech_parameters(self):
        speech_parameters = {}
        data_path = os.path.join(self._activity.get_activity_root(), 'data')
        data_file_name = os.path.join(data_path, 'speech_params.json')
        if os.path.exists(data_file_name):
            f = open(data_file_name, 'r')
            try:
                speech_parameters = simplejson.load(f)
                speech.pitch = speech_parameters['pitch']
                speech.rate = speech_parameters['rate']
                speech.voice = speech_parameters['voice']
            finally:
                f.close()

    def save_speech_parameters(self):
        speech_parameters = {}
        speech_parameters['pitch'] = speech.pitch
        speech_parameters['rate'] = speech.rate
        speech_parameters['voice'] = speech.voice
        data_path = os.path.join(self._activity.get_activity_root(), 'data')
        data_file_name = os.path.join(data_path, 'speech_params.json')
        f = open(data_file_name, 'w')
        try:
            simplejson.dump(speech_parameters, f)
        finally:
            f.close()

    def play_cb(self, widget):
        if widget.get_active():
            self.play_btn.set_named_icon('media-playback-pause')
            if speech.is_stopped():
                speech.play(self._activity._view.get_marked_words())
        else:
            self.play_btn.set_named_icon('media-playback-start')
            speech.stop()
