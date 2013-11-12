#! /usr/bin/env python

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

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfparser import PDFDocument
from pdfminer.pdftypes import resolve1

from collections import defaultdict
from xml.etree import ElementTree as ET

from epubzilla.epubzilla import Epub

RDF_NS = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
XML_NS = '{http://www.w3.org/XML/1998/namespace}'

NS_MAP = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#'    : 'rdf',
    'http://purl.org/dc/elements/1.1/'               : 'dc',
    'http://ns.adobe.com/xap/1.0/'                   : 'xap',
    'http://ns.adobe.com/pdf/1.3/'                   : 'pdf',
    'http://ns.adobe.com/xap/1.0/mm/'                : 'xapmm',
    'http://ns.adobe.com/pdfx/1.3/'                  : 'pdfx',
    'http://prismstandard.org/namespaces/basic/2.0/' : 'prism',
    'http://crossref.org/crossmark/1.0/'             : 'crossmark',
    'http://ns.adobe.com/xap/1.0/rights/'            : 'rights',
    'http://www.w3.org/XML/1998/namespace'           : 'xml'}

class XmpParser(object):
    """
    Parses an XMP string into a dictionary.

    Usage:

        parser = XmpParser(xmpstring)
        meta = parser.meta
    """

    def __init__(self, xmp):
        
        self.tree = ET.XML(xmp)
        self.rdftree = self.tree.find(RDF_NS+'RDF')

    @property
    def meta(self):
        """
        A dictionary of all the parsed metadata.
        """
        
        meta = defaultdict(dict)
        
        for desc in self.rdftree.findall(RDF_NS+'Description'):
            for el in desc.getchildren():
                ns, tag =  self._parse_tag(el)
                value = self._parse_value(el)
                meta[ns][tag] = value
                
        return dict(meta)

    def _parse_tag(self, el):
        """
        Extract the namespace and tag from an element.
        """
        
        ns = None
        tag = el.tag
        
        if tag[0] == "{":
            ns, tag = tag[1:].split('}',1)
            
            if ns in NS_MAP:
                ns = NS_MAP[ns]
                
        return ns, tag

    def _parse_value(self, el):
        """
        Extract the metadata value from an element.
        """
        
        if el.find(RDF_NS+'Bag') is not None:
            value = []
            
            for li in el.findall(RDF_NS+'Bag/'+RDF_NS+'li'):
                value.append(li.text)
                
        elif el.find(RDF_NS+'Seq') is not None:
            value = []
            
            for li in el.findall(RDF_NS+'Seq/'+RDF_NS+'li'):
                value.append(li.text)
                
        elif el.find(RDF_NS+'Alt') is not None:
            value = {}
            
            for li in el.findall(RDF_NS+'Alt/'+RDF_NS+'li'):
                value[li.get(XML_NS+'lang')] = li.text
                
        else:
            value = el.text
            
        return value

def xmp_to_dict(xmp):
    """
    Shorthand function for parsing an XMP string into a python dictionary.
    """
    
    return XmpParser(xmp).meta

def getPDFMetadata(path):

    result = {}

    fp = open(path, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument()
    parser.set_document(doc)
    doc.set_parser(parser)
    doc.initialize()

    result = doc.info

    if 'Metadata' in doc.catalog:
        metadata = resolve1(doc.catalog['Metadata']).get_data()
        
        try:
            result.update( metadata ) # The raw XMP metadata
            
        except:
            pass
            
        try:
            result.update( xmp_to_dict(metadata) )
            
        except:
            pass

    return result[0]

def getEPUBMetadata(path):
    
    epub = Epub.from_file(path)
    
    result = {}

    for element in epub.metadata:
        result [ element.tag.localname ] = element.tag.text

    return result
