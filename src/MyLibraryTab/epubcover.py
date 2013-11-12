#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   epubcover.py
#   Adapted by Flavio Danesse <fdanesse@gmail.com>
#   based on: epub-thumbnailer
#   Author: Mariano Simone (marianosimone@gmail.com)

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import zipfile
import sys
import shutil
import os
import re
from xml.dom import minidom
from StringIO import StringIO

def get_cover_by_filename(epub):
    """
    Search the cover.
    """
    
    cover_regex = re.compile(".*cover.*\.(jpg|jpeg|png)")

    for fileinfo in epub.filelist:
        if cover_regex.match(os.path.basename(fileinfo.filename).lower()):
            return fileinfo.filename

    return None

def get_cover_from_manifest(epub):
    """
    Search the cover.
    """
    
    img_ext_regex = re.compile("^.*\.(jpg|jpeg|png)$")

    # open the main container
    container = epub.open("META-INF/container.xml")
    container_root = minidom.parseString(container.read())

    # locate the rootfile
    elem = container_root.getElementsByTagName("rootfile")[0]
    rootfile_path = elem.getAttribute("full-path")

    # open the rootfile
    rootfile = epub.open(rootfile_path)
    rootfile_root = minidom.parseString(rootfile.read())

    # find the manifest element
    manifest = rootfile_root.getElementsByTagName("manifest")[0]
    
    for item in manifest.getElementsByTagName("item"):
        item_id = item.getAttribute("id")
        item_href = item.getAttribute("href")
        
        if "cover" in item_id and img_ext_regex.match(item_href.lower()):
            
            cover_path = os.path.join(
                os.path.dirname(rootfile_path),
                item_href)
                
            return cover_path
        
    return None

def extract_cover(epub, cover_path, output_file, width, height):
    """
    Get the cover and saves it to a file.
    """
    try:
        cover = epub.open(cover_path)
        target = open(output_file,'w+')
        shutil.copyfileobj(cover, target)
    finally:
        if cover != None:
                cover.close()
        if target != None:
                target.close()

    return output_file

def get_epub_covert(input_file, output_file, width=75, height=78):
    """
    Get epub file path,
    path for the output file of the title,
    width and height of the cover.
    
    Returns the path to an image file with the cover
    """
    
    if not os.path.exists(input_file): return

    epub = zipfile.ZipFile(input_file, "r")
    
    cover_path = ''
    
    try:
        cover_path = get_cover_from_manifest(epub)
        
    except:
        pass
    
    if not cover_path:
        try:
            cover_path = get_cover_by_filename(epub)
            
        except:
            pass
    
    if cover_path:
        return extract_cover(epub, cover_path, output_file, width, height)
