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

import libxml2

_ISO_639_XML_PATH = '/usr/share/xml/iso-codes/iso_639.xml'


def singleton(object, instantiated=[]):
    # From http://norvig.com/python-iaq.html
    "Raise an exception if an obj of this class has been instantiated before"
    assert object.__class__ not in instantiated, \
    "%s is a Singleton class but is already instantiated" % object.__class__
    instantiated.append(object.__class__)


class LanguageNames(object):
    def __init__(self):
        singleton(self)
        try:
            self._xmldoc = libxml2.parseFile(_ISO_639_XML_PATH)
            self._cache = None
        except libxml2.parserError:
            self._xmldoc = None
            return

        self._eroot = self._xmldoc.getRootElement()

    def close(self):
        if self._xmldoc is not None:
            self._xmldoc.freeDoc()

    def get_full_language_name(self, code):
        if self._cache == None:
            self._cache = {}
            for child in self._eroot.children:
                if child.properties is not None:
                    lang_code = None
                    lang_name = None
                    for property in child.properties:
                        if property.get_name() == 'name':
                            lang_name = property.get_content()
                        elif property.get_name() == 'iso_639_1_code':
                            lang_code = property.get_content()

                    if lang_code is not None and lang_name is not None:
                        self._cache[lang_code] = lang_name
            self._xmldoc.freeDoc()
            self._xmldoc = None

        return self._cache[code]
