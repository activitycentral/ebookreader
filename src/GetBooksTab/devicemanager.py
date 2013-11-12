#! /usr/bin/env python

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
from gi.repository import GObject
import dbus
import env_settings as env

_logger = logging.getLogger(__name__)
UDISK_DEVICE_PATH = 'org.freedesktop.UDisks.Device'


class DeviceManager(GObject.GObject):

    __gsignals__ = {
        'device-changed': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._devices = {}
        self._bus = dbus.SystemBus()

        try:
            self._udisk_proxy = self._bus.get_object('org.freedesktop.UDisks',
                       '/org/freedesktop/UDisks')
            self._udisk_iface = dbus.Interface(self._udisk_proxy,
                        'org.freedesktop.UDisks')
            self._populate_devices()
            self._udisk_iface.connect_to_signal('DeviceChanged',
                    self.__device_changed_cb)
        except dbus.exceptions.DBusException, e:
            _logger.error('Exception initializing UDisks: %s', e)

    def _populate_devices(self):
        for device in self._udisk_proxy.EnumerateDevices():
            props = self._get_props_from_device(device)
            if props is not None:
                _logger.debug('Device mounted in %s', props['mount_path'])
                props['have_catalog'] = self._have_catalog(props)
                self._devices[device] = props

    def _get_props_from_device(self, device):
        # http://hal.freedesktop.org/docs/udisks/Device.html
        device_obj = self._bus.get_object('org.freedesktop.UDisks', device)
        device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
        props = {}
        props['mounted'] = bool(device_props.Get(UDISK_DEVICE_PATH,
                'DeviceIsMounted'))
        if props['mounted']:
            props['mount_path'] = str(device_props.Get(UDISK_DEVICE_PATH,
                    'DeviceMountPaths')[0])
            props['removable'] = bool(device_props.Get(UDISK_DEVICE_PATH,
                    'DriveCanDetach'))
            props['label'] = str(device_props.Get(UDISK_DEVICE_PATH,
                    'IdLabel'))
            props['size'] = int(device_props.Get(UDISK_DEVICE_PATH,
                    'DeviceSize'))
            return props
        return None

    def _have_catalog(self, props):
        # Apart from determining if this is a removable volume,
        # this also tries to find if there is a catalog.xml in the
        # root
        if not props['removable']:
            return False
        mount_point = props['mount_path']
        return os.path.exists(os.path.join(mount_point, 'catalog.xml'))

    def __device_changed_cb(self, device):
        props = self._get_props_from_device(device)
        if props is not None:
            self._devices[device] = props
            have_catalog = self._have_catalog(props)
            props['have_catalog'] = have_catalog
            if have_catalog:
                self.emit('device-changed')
            _logger.debug('Device was added %s' % props)
        else:
            if device in self._devices:
                props = self._devices[device]
                need_notify = props['have_catalog']
                _logger.debug('Device was removed %s', props)
                del self._devices[device]
                if need_notify:
                    self.emit('device-changed')

    def get_devices(self):
        return self._devices
