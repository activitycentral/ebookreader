#!/usr/bin/python
'''
Created on Jan 15, 2013


@author: odeegan
'''

import os.path
import zipfile


PATH_TO_CONTAINER_XML = "META-INF/container.xml"


XML_NAMESPACES = {
    'n':'urn:oasis:names:tc:opendocument:xmlns:container',
    'opf':'http://www.idpf.org/2007/opf',
    'dc':'http://purl.org/dc/elements/1.1/'}


class Epub(object):
  
    def __init__(self):
        self.filename = None
        self.package = Package()
        self.metadata = MetaData()
        self.manifest = Manifest()
        self.spine = Spine()
        self.guide = Guide()
        self.parts = []
        self.images = []
        self.css = []
        self._cover = None
   
    @property
    def title(self):
        """Returns the EPUBS title"""
        return self.metadata.get('title')
   
    @property
    def author(self):
        """Returns the value of the 'file-as' attribute of the first creator
        listed in the manifest file. If the attribute is not present, it returns
        the text value enclosed by the creator tag."""
        
        for item in self.metadata:
            if item.tag.localname == "creator":
                if  'file-as' in item.tag:
                    return item.tag['file-as']
                else:
                    return item.tag.text
  
    
    @property
    def cover(self):
        if self._cover:
            return self._cover
        
        for element in self.metadata:
            if element.tag.localname == 'meta' and 'name' in element.tag.attributes:
                if element.tag['name'] == 'cover':
                    self._cover = self.manifest.getElementById(element.tag['content'])
                    return self._cover
        return None
            
        
        
        
    @staticmethod
    def from_file(epub_file):
        
        """Creates an instance of Epub from an epub file
           Accepts epub_file as the fullpath to file or a file object 
        """
        self = Epub()

        #TODO: zipfile.ZipFile accepts a file or a fileobject.
        # That seems ambiguous. We should probably create a 
        # separate method to create an EPUB from a file object to be more
        # clear.
         
        if (isinstance(epub_file, file)):
            self.filename = file.name
            
        if (isinstance(epub_file, str)):
            self.filename = epub_file

        try:
            archive = zipfile.ZipFile(epub_file)
        except Exception as e:
            print 'Could not open zipfile "%s" \n' %self.filename
            print e

        # parse container.xml for full path to content.opf file
        container_xml = archive.read(PATH_TO_CONTAINER_XML)
        container_xml_tree = etree.fromstring(container_xml)
        fullpath = container_xml_tree.xpath('n:rootfiles/n:rootfile/@full-path',
                                             namespaces=XML_NAMESPACES)[0]

        # Each major XML element in the content.opf file is mapped to its own class.
        # This dict maps those classes to the XPaths that point to the corresponding XML
        # element.
        # 
        # for example: the XPath "opf:package" points to the '<package>' XML element
        #              which is mapped to the Package class
        element_map = [ {'name': 'package', 
                         'class': Package,
                         'element_xpath': '/opf:package'},
                        {'name': 'metadata',
                         'class': MetaData,
                         'element_xpath': '/opf:package/opf:metadata',
                         'sub_element_class': Element,
                         'sub_element_xpath': "./*"},
                        {'name': 'manifest',
                         'class': Manifest,
                         'element_xpath': '/opf:package/opf:manifest',
                         'sub_element_class': ManifestElement,
                         'sub_element_xpath': 'opf:item'},
                        {'name': 'spine',
                         'class': Spine,
                         'element_xpath': '/opf:package/opf:spine',
                         'sub_element_class': Element,
                         'sub_element_xpath': 'opf:itemref'},
                        {'name': 'guide',   
                         'class': Guide,
                         'element_xpath': '/opf:package/opf:guide',
                         'sub_element_class': Element,
                         'sub_element_xpath': 'opf:reference',
                         'optional': True}]
   

        tree = etree.fromstring(archive.read(fullpath))
        
        for element in element_map:
            try:
                element_tree = tree.xpath(element['element_xpath'], namespaces=XML_NAMESPACES)[0]
            except IndexError as e:
            # If the element is marked as optional, just keep going if we don't find it.
                if element['optional']:
                    continue
                else:
                    print element
            element_class = element['class']()
            element_class.as_xhtml = etree.tostring(element_tree)
            # Step through the attrib dict and replace each key with its localname version
            # i.e. if the key is '{namespace}event', replace it with 'event'.
            # There *shouldn't* be any collisions.

            element_class.tag.attributes = {}
            for key,value in element_tree.attrib.iteritems():
                keya = etree.QName(key).localname
                element_class.tag.attributes[keya] = value

            element_class.tag.localname = etree.QName(element_tree).localname
            element_class.tag.namespace = etree.QName(element_tree).namespace
            element_class.text = element_tree.text
            
            if 'sub_element_class' in element:
                sub_element_tree = element_tree.xpath(element['sub_element_xpath'], namespaces=XML_NAMESPACES)
                for k in sub_element_tree:
                    sub_element_class = element['sub_element_class']()
                    sub_element_class.as_xhtml = etree.tostring(k)

                    sub_element_class.tag.attributes = {}
                    for key,value in k.attrib.iteritems():
                        keya = etree.QName(key).localname
                        sub_element_class.tag.attributes[keya] = value

                    sub_element_class.tag.localname = etree.QName(k.tag).localname
                    sub_element_class.tag.namespace = etree.QName(k.tag).namespace
                    sub_element_class.tag.text = k.text
                    element_class.append(sub_element_class)


                    # if we just created a ManifestElement, we need to additionally
                    # pass it a reference to the epub archive and the dirname
                    # contained in the fullpath in order for it to access the file
                    # it points to

                    if type(sub_element_class) == ManifestElement:
                        # fullpath is the path to the content.opf file.
                        # This should also be the path to the manifest item files.
                        sub_element_class.basedir = os.path.dirname(fullpath)
                        sub_element_class.archive = archive
                        
            # Assigns the class we just created as an attribute of the Epub object.
            # The attr name is taken from the 'name' value in the element_map above.
            setattr(self, element['name'], element_class)

            # If we just created the spine element, we need to pass it
            # a reference to the manifest. This will enable the spine element to access
            # manifeset elements directly
            # note: this assumes the manifest element has alreay been created
            if element['name'] == 'spine':
                self.spine.manifest = self.manifest

        # read in the items from the manifest             
        for element in self.manifest:
            if element.isDocument():
                pass           
            if element.isImage():
                self.images.append(element)               
            if element.isCSS():
                self.css.append(element)
            if element.isTOC():
                pass
    
        # create an array called parts that references elements
        # listed in the spine
        
        for itemref in self.spine.list:
            self.parts.append(self.manifest.getElementById(itemref.tag.attributes['idref']))

        return self    


class Tag(object):
    def __init__(self):
        self.localname = ""
        self.namespace = ""
        self.attributes = {}
        self._text = ""   

    def __repr__(self):
        return "class <Epub.Tag>"
    
    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value):
        if value == None:
            self._text = ""
        else:
            self._text = value
    
    @property
    def name(self):
        return '{%s}%s' %(self.namespace, self.localname)
        
    def __getitem__(self, key):
        return self.attributes[key]
    
    def __setitem__(self, key, value):
        self.attributes[key] = value

    def iteritems(self):
        return self.attributes.iteritems()

    def __contains__(self, key):
        return key in self.attributes
    
    def iterkeys(self):
        return self.attributes.iterkeys()

class Element(object):
    
    def __init__(self):
        self.as_xhtml = ""
        self.tag = Tag()
        self.list = []
 
    def __repr__(self):
        return "class <Epub.Element>"
    
    def append(self, i):
        self.list.append(i) 

    def __len__(self):
        return len(self.list)

    def __getitem__(self, key):
        return self.list[key]

    def __setitem__(self, key, value):
        self.list[key] = value
        
    
    def __getattr__(self, name):
        newlist = []
        for element in self.list:
            if element.tag.localname == name:
                newlist.append(element)
        return newlist
    

class ManifestElement(Element):
    """A class representing the 'item' XHTML element in an epub manifest.
    """

    def __init__(self):
        """
        ManifestElement constructor
    
        @data_member archive: an instance of the epub archive as returned by
        zipfile.Zipfile(file.epub). 
    
        @data_member dirname: dirname contained in the epub's fullpath 
        attribute found in the container.xml file. The fullpath is the path
        to the epub content.opf file. 
        """
        super(ManifestElement, self).__init__()
        self.archive = None
        self.basedir = "" 
        
        
    def isImage(self):
        return 0 in [x.find('image') for x in self.tag.attributes.values()]
    
    def isDocument(self):
        return 0 in [x.find('application/xhtml+xml') for x in self.tag.attributes.values()]
    
    def isTOC(self):
        return 0 in [x.find('application/x-dtbncx+xml') for x in self.tag.attributes.values()]

    def isCSS(self):
        return 0 in [x.find('text/css') for x in self.tag.attributes.values()]
       
    def get_file(self):   
        """
        @return: the file referenced in the manifest as an str
        """
        
        return self.archive.read(self.basedir 
                                 + "/"
                                 + self.tag['href'])

    def get_file_stripped(self):
        if self.isDocument():
            # strip all tags from the xhtml
            xhtml = self.get_file()
            tree = etree.fromstring(xhtml)            
            return tree.xpath("string()")
        else:
            raise Exception("Element is not an XHTML document")


class Package(Element):
    """A class representing the package XHTML element found in the contents.opf
    file of an epub
    """    
    def __init__(self):
        super(Package, self).__init__()
    
    def __repr__(self):
        return "class <Epub.Package>"


class MetaData(Element):
    """A class representing the metadata XHTML element found in the contents.opf
    file of an epub
    """    
    def __init__(self):
        super(MetaData, self).__init__()

    def __repr__(self):
        return "class <Epub.MetaData>"
                
    def get(self, tag):
        for element in self.list:
            if tag == element.tag.localname:
                return element.tag.text


class Spine(Element):
    """A class representing the spine XHTML element found in the contents.opf
    file of an epub
    """
    def __init__(self):
        super(Spine, self).__init__()
        self.manifest = None
        
    def __repr__(self):
        return "class <Epub.Spine>"
    
    def get_manifest_element(self, element):
        for item in self.manifest:
            if element.tag['idref'] == item.tag['id']:
                return item
        return None


class Guide(Element):
    """A class representing the guide XHTML element found in the contents.opf
    file of an epub
    """    
    def __init__(self):
        super(Guide, self).__init__()
    
    def __repr__(self):
        return "class <Epub.Guide>"

class Manifest(Element):
    """A class representing the manifest XHTML element found in the contents.opf
    file of an epub
    """    
    def __init__(self):
        super(Manifest, self).__init__()

    def __repr__(self):
        return "class <Epub.Manifest>"

    def getElementById(self, element_id):
        for element in self.list:
            if element.tag['id'] == element_id:    
                return element
        raise Exception("Could not find element with id=%s in the manifest" %element_id)
            






