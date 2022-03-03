#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2008,2011  Gary Burton
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2011       Heinz Brinker
# Copyright (C) 2012       Eric Doutreleau
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#


"""Parenty Report"""

from collections import defaultdict
import logging

#------------------------------------------------------------------------
#
# gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.simple import SimpleAccess
from gramps.gen.plug.menu import FilterOption, PlaceListOption, EnumeratedListOption, \
                          BooleanOption,BooleanListOption
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import MenuReportOptions
from gramps.gui.utils import ProgressMeter
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle, TableStyle,
                            TableCellStyle, FONT_SANS_SERIF, FONT_SERIF,
                            INDEX_TYPE_TOC, PARA_ALIGN_CENTER)
from gramps.gen.proxy import PrivateProxyDb, LivingProxyDb
import gramps.gen.datehandler
from gramps.gen.sort import Sort
from gramps.gen.lib import PlaceType
from gramps.gen.display.name import displayer as _nd
from gramps.gen.display.place import displayer as _pd
from gramps.gen.relationship import get_relationship_calculator

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
LOG = logging.getLogger(".ParentyReport")

class ParentyReport(Report):
    def __init__(self, database, options_class, user):

        Report.__init__(self, database, options_class, user)

        menu = options_class.menu
        self.user = user
        self.database = database
        self.home_person = self.database.get_default_person()
        self.nametag = menu.get_option_by_name('tag_option').get_value()
        if not self.home_person :
            self.sdoc.paragraph(_("Home person not set."))
            return
        self.rel_class = get_relationship_calculator(glocale)
        self.attr = ("MyHeritage : Segments partagés","MyHeritage : Segment le plus long","MyHeritage : ADN partagé","Geneanet : Segment le plus long","Geneanet : Segments partagés","Geneanet : ADN partagé","Gedmatch : Segments partagés","Gedmatch : Segment le plus long","Gedmatch : ADN partagé","FTDNA : Segment le plus long","FTDNA : ADN partagé")

        """
        The routine the actually creates the report. At this point, the
        document is opened and ready for writing.
        """

        # Create progress meter bar
        # Write the title line. Set in INDEX marker so that this section
        # will be identified as a major category if this is included in a
        # Book report.

    def write_report(self):
        nametag = self.nametag
        RES=defaultdict(lambda : defaultdict(str))
        LOG.debug("TAILLE %s\n" % nametag)
        star_nbr = 0
        self.NAME= defaultdict(str)
        self.PARENTY= defaultdict(str)
        self.REL= defaultdict(str)
        self.LEN= defaultdict(str)
        self.SITEGEN= defaultdict(str)
        self.stringgen='site geneanet'
        self.valeur= defaultdict(lambda : defaultdict(int))
        self.sdb = SimpleAccess(self.database)
        LOG.debug("DEBUT WRITE" )
        self.doc.start_paragraph('Eclair-Report')
        progress = ProgressMeter(_('People parcours'), can_cancel=True)
        length = self.database.get_number_of_people()
        progress.set_pass(nametag,length)
        p2 = self.home_person.get_primary_name().get_name()
        for person in self.database.iter_people():
            self.person = person
            progress.step()
            state = 0
            if self.person.handle == self.home_person.handle :
                next
            else:
                for tag_handle in person.get_tag_list():
                    tag = self.database.get_tag_from_handle(tag_handle)
                    tname = tag.get_name()
                    if tname == nametag:
                        state= 1
                        p1 = self.person.get_primary_name().get_name()
                        LOG.debug("TAG trouve %s" % tname)
                        common, self.msg_list = self.rel_class.get_relationship_distance_new(
                              self.database, self.person, self.home_person,
                        all_families=True,
                        all_dist=True,
                        only_birth=False)
                        (parenty,rel) = self.get_parenty(common)
                        numlinks=len(common)
                        if parenty > 0.0:
                            attributes = self.person.get_attribute_list()
                            attributes.sort(key=lambda a: a.get_type().value)
                            result=""
                            self.PARENTY[p1]=parenty
                            self.LEN[p1]=numlinks
                            self.REL[p1]=rel
                            if nametag == 'ADN':
                                for attribute in attributes:
                                    attr_type = attribute.get_type()
                                    attr_val  = attribute.get_value()
                                    if str(attr_type) in self.attr:
                                        result = result + str(attr_type) + " # " + str(attr_val) + " # "
                                        RES[p1][str(attr_type)]=attr_val
                            if nametag == 'cousingen':
                                for attribute in attributes:
                                    attr_type = attribute.get_type()
                                    attr_val  = attribute.get_value()
                                    if str(attr_type) == self.stringgen:
                                        RES[p1][self.stringgen]=attr_val
                            msg = p1 + "  " + result + " parenté : " +  str(format(parenty, '.10f')) +" " + str(rel) + "\n"
                            LOG.debug("parente%s P1 %s" % (msg,p1))
        num=len(self.PARENTY.keys())
        msg =  nametag  + " Occurences <BR><BR>\n"
        self.doc.write_text(msg)
        if nametag == "cousingen":
            msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH>"
            msg = msg + "<TH>" + self.stringgen + "</TH>"
            msg = msg + "</tr>"
            self.doc.write_text(msg)
#            LOG.debug("longueyr attribut %d" % len(self.attr))
            num = 1
            sortedDict = sorted(self.PARENTY.items(), reverse=True, key=lambda kv: kv[1])
            for key, value in sortedDict:
                msg = "<TR><TD>" + key + "</TD><TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[key]) + "</TD><TD>" + str(self.LEN[key]) + "</TD>"
                LOG.debug("NUM %d Nom %s REL %s" % (num,key,str(self.REL[key])))
                num = num + 1
                if RES[key][self.stringgen]:
                    url = str(RES[key][self.stringgen])
                    msg = msg + "<TD> <A HREF=\"" + url + "\">" + url + "</A></TD>"
                else:
                    msg = msg + "<TD> </TD>"
                msg = msg + "</TR>\n"
                self.doc.write_text(msg)
            msg = "</TABLE>"
            self.doc.write_text(msg)
        if nametag == 'star':
            sortedDict = sorted(self.PARENTY.items(), reverse=True, key=lambda kv: kv[1])
            msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TR>"
            self.doc.write_text(msg)
            for key, value in sortedDict:
                msg = "<TR><TD>" + key + "</TD><TD>" + str(format(value, '.10f')) +  "</TD><TD>" +str(self.REL[key]) + "</TD><TD>" + str(self.LEN[key]) +"</TD></TR>\n"
                self.doc.write_text(msg)

            msg = "</TABLE>"
            self.doc.write_text(msg)
        if nametag == 'ADN':
            msg = "<TABLE class=\"tabwiki\"><TR><TH>Anom</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH>"
            LOG.debug("longueyr attribut %d" % len(self.attr))
            for att in self.attr:
                msg = msg + "<TH>" + att + "</TH>"
                LOG.debug("parente%s P1 %s" % (msg,p1))
            msg = msg + "</tr>"
            self.doc.write_text(msg)
#            LOG.debug("longueyr attribut %d" % len(self.attr))
            num = 1
            sortedDict = sorted(self.PARENTY.items(), reverse=True, key=lambda kv: kv[1])
            for key, value in sortedDict:
                msg = "<TR><TD>" + str(num) + "</TD><TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[key]) + "</TD><TD>" + str(self.LEN[key]) + "</TD>"
                LOG.debug("NUM %d Nom %s REL %s" % (num,key,str(self.REL[key])))
                num = num + 1
                for attr in self.attr:
                    msg = msg + "<TD>" + str(RES[key][attr]) + "</TD>"
                msg = msg + "</TR>"
                self.doc.write_text(msg)
            msg = "</TABLE>"
            self.doc.write_text(msg)

        LOG.debug("FIN WRITE" )
        progress.close()
        self.doc.end_paragraph()

    def get_parenty(self, relations):
    
        if not relations or relations[0][0] == -1:
            parenty = 0
            LOG.debug("pas de parente" )
            return (parenty,"pas de parente")
        pct = 0.0
        num=0
        rel_str=""
        LOG.debug("DEBUT RELATION")
        for relation in relations:
            birth = self.rel_class.only_birth(relation[2])\
                    and self.rel_class.only_birth(relation[4])
            distorig = len(relation[4])
            distother = len(relation[2])
            dist = distorig + distother
            pct = pct + 1 / 2 ** dist
            num = num + 1
            #LOG.debug("NUM %d d1 %d d2 %d parenty %2.10f" % ( num, distorig , distother , pct))
            if not rel_str:
                rel_str = self.rel_class.get_single_relationship_string(
                         distorig, distother,
                         self.home_person.get_gender(),
                         self.person.get_gender(),
                         relation[4], relation[2],
                         only_birth = birth,
                         in_law_a = False, in_law_b = False)

        parenty = pct * 100
        return (parenty,rel_str)

#------------------------------------------------------------------------
#
# ParentyOptions
#
#------------------------------------------------------------------------
class ParentyOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):
        """
        Add options to the menu for the place report.
        """
        category_name = _("Report Options")
        tag_option = EnumeratedListOption('Tag', 'Tag')
        tag_option.set_items([('star', 'star') , ('cousingen', 'cousingen') , ('ADN', 'ADN')])
        tag_option.set_help("Type de rapport")
        menu.add_option(category_name, "tag_option", tag_option)


    def make_default_style(self, default_style):

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=16, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(1)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_('The style used for the liste eclair.'))
        default_style.add_paragraph_style("Eclair-Report", para)

        """
        Define the style used for the place title
        """
        font = FontStyle()
        font.set(face=FONT_SERIF, size=12, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=-1.5, lmargin=1.5)
        para.set_top_margin(0.75)
        para.set_bottom_margin(0.25)
        para.set_description(_('The style used for place title.'))
        default_style.add_paragraph_style("Eclair-ReportTitle", para)
