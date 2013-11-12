import os
import env_settings as env
from gi.repository import Gtk
from lxml import etree 

class NavPoint(object):

    def __init__(self, label, contentsrc, children=[]):
        self._label = label
        self._contentsrc = contentsrc
        self._children = children

    def get_label(self):
        return self._label

    def get_contentsrc(self):
        return self._contentsrc

    def get_children(self):
        return self._children


class NavMap(object):
    def __init__(self, opffile, ncxfile, basepath):
        self._basepath = basepath
        self._opffile = opffile
        self._tree = etree.parse(ncxfile)
        self._root = self._tree.getroot()
        self._gtktreestore = Gtk.TreeStore(str, str)
        self._flattoc = []
        self._css_files = []
        self._cover_files = []

        self._populate_flattoc()
        self._populate_toc()

    def _populate_flattoc(self):
        tree = etree.parse(self._opffile)
        root = tree.getroot()

        itemmap = {}
        manifest = root.find('.//{http://www.idpf.org/2007/opf}manifest')
        for element in manifest.iterfind('{http://www.idpf.org/2007/opf}item'):
            itemmap[element.get('id')] = element

            # Add the styling option in each CSS file, so that
            # scrollbars are not shown.
            if element.get('media-type') == 'text/css':
                href = element.get('href')
                self._css_files.append(self._basepath + href)


        spine = root.find('.//{http://www.idpf.org/2007/opf}spine')
        for element in spine.iterfind('{http://www.idpf.org/2007/opf}itemref'):
            idref = element.get('idref')
            href = itemmap[idref].get('href')

            # Only show linear files, else the application will crash.
            linearity = element.get('linear')
            if (linearity == 'yes') or (linearity == None):
                self._flattoc.append(self._basepath + href)


        guide = root.find('.//{http://www.idpf.org/2007/opf}guide')
        for element in guide.iterfind('{http://www.idpf.org/2007/opf}reference'):
            element_type = element.get('type')

            if element_type == 'cover':
                href_key = element.get('href')
                self._cover_files.append(self._basepath + href_key)

        self._opffile.close()

    def add_additional_styling(self, filepath):
        styling_file = os.path.join(env.SUGAR_ACTIVITY_ROOT,
                'styling', 'webkit.css')
        f = open(styling_file, 'r')
        lines = f.readlines()
        f.close()

        if os.path.exists(filepath):
            f = open(filepath, 'a')

            for line in lines:
                f.write(line)

            f.close()

    def get_cover_files(self):
        return self._cover_files

    def _populate_toc(self):
        navmap = self._root.find(
                '{http://www.daisy.org/z3986/2005/ncx/}navMap')
        for navpoint in navmap.iterfind(
                './{http://www.daisy.org/z3986/2005/ncx/}navPoint'):
            self._process_navpoint(navpoint)

    def _gettitle(self, navpoint):
        text = navpoint.find('./{http://www.daisy.org/z3986/2005/ncx/}' +
                'navLabel/{http://www.daisy.org/z3986/2005/ncx/}text')
        return text.text

    def _getcontent(self, navpoint):
        text = navpoint.find(
                './{http://www.daisy.org/z3986/2005/ncx/}content/')
        if text is not None:
            return self._basepath + text.get('src')
        else:
            return

    def _process_navpoint(self, navpoint, parent=None):
        title = self._gettitle(navpoint)
        content = self._getcontent(navpoint)

        #print title, content

        iter = self._gtktreestore.append(parent, [title, content])
        #self._flattoc.append((title, content))

        childnavpointlist = list(navpoint.iterfind(
                './{http://www.daisy.org/z3986/2005/ncx/}navPoint'))

        if len(childnavpointlist):
            for childnavpoint in childnavpointlist:
                self._process_navpoint(childnavpoint, parent=iter)
        else:
            return

    def get_gtktreestore(self):
        '''
        Returns a GtkTreeModel representation of the
        Epub table of contents
        '''
        return self._gtktreestore

    def get_flattoc(self):
        '''
        Returns a flat (linear) list of files to be
        rendered.
        '''
        return self._flattoc

    def is_tag_present(self, filepath, tag):
        tree = etree.parse(filepath)
        return self.__find_if_tag_present(tree.getroot(), tag)

    def __find_if_tag_present(self, root, tag):
        for child in root.getchildren():

            try:
            	if child.tag.endswith('}' + tag):
                	return True
	    except:	
            	pass

            if self.__find_if_tag_present(child, tag) is True:
                return True
            else:
                continue

        return False

#t = TocParser('/home/sayamindu/Desktop/Test/OPS/fb.ncx')
