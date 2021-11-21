#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2007-2009  Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# $Id: Parenty.py 18915 2012-02-17 16:51:40Z romjerome $

"""Reports/Text Reports/Parenty Report"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
import copy
import os
import gettext
import operator

#------------------------------------------------------------------------
#
# gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

from gramps.gen.simple import SimpleAccess
from gramps.gen.display.name import displayer as global_name_display
from gramps.gen.errors import ReportError
from gramps.gen.lib import Person, NoteType
from gramps.gen.plug.menu import (NumberOption, PersonOption, BooleanOption, EnumeratedListOption)
from gramps.gui.plug.export import WriterOptionBox
from gramps.gen.errors import DatabaseError
from collections import defaultdict
import logging
from gramps.gen.relationship import get_relationship_calculator
LOG = logging.getLogger("parenty")
#
# CSVWriter Options
#
#-------------------------------------------------------------------------


class ParentyOptionBox(WriterOptionBox):
    """
    Create a VBox with the option widgets and define methods to retrieve
    the options.

    """
    def __init__(self, person, dbstate, uistate, track=[], window=None):
        WriterOptionBox.__init__(self, person, dbstate, uistate, track=track,
                                 window=window)
        ## TODO: add place filter selection
        self.star = 0
        self.star_check = None
        self.adn = 1
        self.adn_check = None

    def get_option_box(self):
        from gi.repository import Gtk
        option_box = WriterOptionBox.get_option_box(self)

        self.star_check = Gtk.CheckButton(label=_("Star Report"))
        self.adn_check = Gtk.CheckButton(label=_("DNA Report"))

        self.star_check.set_active(1)
        self.adn_check.set_active(1)

        option_box.pack_start(self.star_check, False, True, 0)
        option_box.pack_start(self.adn_check, False, True, 0)

        return option_box

    def parse_options(self):
        WriterOptionBox.parse_options(self)
        if self.star_check:
            self.star = self.star_check.get_active()
        if self.adn_check:
            self.adn = self.adn_check.get_active()


#------------------------------------------------------------------------
#
# ParentyReport
#
#------------------------------------------------------------------------
class ParentyWriter(object):
    """
    Parenty Report class
    """
    def __init__(self, database, filename, user, option_box=None):
        if option_box:
            self.star=option_box.star
            self.adn=option_box.adn
        else:
            self.star = 0
            self.adn= 1

        self.database = database
        self.filename = filename
        self.user = user
        self.option_box = option_box
        self.trouve= defaultdict(lambda : defaultdict(int))
        self.personsex= defaultdict(lambda : defaultdict(int))
        self.STAR= defaultdict(str)
        self.PARENTY= defaultdict(str)
        self.REL= defaultdict(str)
        self.LEN= defaultdict(str)
        self.valeur= defaultdict(lambda : defaultdict(int))
        if option_box:
            self.option_box.parse_options()
            self.dbstar = option_box.get_filtered_database(self.database)
        self.rel_class = get_relationship_calculator(glocale)
        self.home_person = self.database.get_default_person()



    def write_ped_file(self):

        self.dirname = os.path.dirname (self.filename)
        try:
            self.g = open(self.filename, "w")
        except IOError as msg:
            msg2 = _("Could not create %s") % self.filename
            self.user.notify_error(msg2, str(msg))
            return False
        except:
            self.user.notify_error(_("Could not create %s") % self.filename)
            return False

        self.attr = ("MyHeritage : Segments partagés","MyHeritage : Segment le plus long","MyHeritage : ADN partagé","Geneanet : Segment le plus long","Geneanet : Segments partagés","Geneanet : ADN partagé","Gedmatch : Segments partagés","Gedmatch : Segment le plus long","Gedmatch : ADN partagé")
        RES=defaultdict(lambda : defaultdict(str))
        self.sdb = SimpleAccess(self.database)
        star_nbr = 0
        LOG.debug("DEBUT WRITE" )
        self.dstar = self.dbstar.iter_person_handles()
        LOG.debug("TAILLE self.filtre %d\n" % len(self.dstar))
        LOG.debug("TAILLE attribut %d\n" % len(self.attr))
        LOG.debug("ADN %d\n" % self.adn)
        for handle in self.dstar:
            self.person = self.database.get_person_from_handle(handle)
            p2 = self.sdb.name(self.home_person)
            p1 = self.sdb.name(self.person)
            #LOG.debug("recherche parente P1 %s" % p1)
            if self.person.handle == self.home_person.handle :
                parente=1
                if self.star:
                    self.STAR[p1] = parenty
            else:
                common, self.msg_list = self.rel_class.get_relationship_distance_new(
                self.database, self.person, self.home_person,
                all_families=True,
                all_dist=True,
                only_birth=False)
                (parenty,min_rel) = self.get_parenty(common,self.person)
                numlinks=len(common)
                result=""
                if self.star:
                    msg = p1 + str(format(parenty, '.10f'))
                    if parenty  > 0.0:
                        self.STAR[p1] = parenty
                if self.adn:
                    self.PARENTY[p1]=parenty
                    self.REL[p1]=min_rel
                    self.LEN[p1]=numlinks
                    LOG.debug("on est dans ADN %s\n" % p1)
                    attributes = self.person.get_attribute_list()
                    attributes.sort(key=lambda a: a.get_type().value)
                    for attribute in attributes:
                        LOG.debug("on est dans attribut \n")
                        attr_type = attribute.get_type()
                        attr_val  = attribute.get_value()
                        LOG.debug("attribut type  %s" % str(attr_type))
                        if str(attr_type) in self.attr:
                            RES[p1][str(attr_type)]=attr_val
                            result = result + str(attr_type) + " # " + str(attr_val) + " # "
                    msg = p1 + " # " + result + " parenté : " +  str(format(parenty, '.10f')) + "\n"
            #    LOG.debug("parente%s P1 %s" % (msg,p1))
        if self.star:
            sortedDict = sorted(self.STAR.items(), reverse=True, key=lambda kv: kv[1])
            msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>% parenté</TH></TR>"
            self.writeln(msg)
            for key, value in sortedDict:
                msg = "<TR><TD>" + key + "</TD><TD>" + str(format(value, '.10f')) + "</TD></TR>"
                self.writeln(msg)

            msg = "</TABLE>"
            self.writeln(msg)
        if self.adn:
            msg = "<TABLE class=\"tabwiki\"><TR><TH>Anom</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH>"
            LOG.debug("longueyr attribut %d" % len(self.attr))
            for att in self.attr:
                msg = msg + "<TH>" + att + "</TH>"
                LOG.debug("parente%s P1 %s" % (msg,p1))
            msg = msg + "</tr>"
            self.writeln(msg)
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
                self.writeln(msg)
            msg = "</TABLE>"
            self.writeln(msg)
        return True

    def get_parenty(self, relations , person):

        if not relations or relations[0][0] == -1:
            parenty = 0
            LOG.debug("pas de parente" )
            return parenty
        pct = 0.0
        num=0
        mindist=0
        rel_str =""
#        LOG.debug("DEBUT RELATION")
        for relation in relations:
            birth = self.rel_class.only_birth(relation[2])\
                        and self.rel_class.only_birth(relation[4])
            distorig = len(relation[4])
            distother = len(relation[2])
            dist = distorig + distother
            num = num + 1
            if not rel_str:
                rel_str = self.rel_class.get_single_relationship_string(
                                    distorig, distother,
                                    self.home_person.get_gender(),
                                    person.get_gender(),
                                    relation[4], relation[2],
                                    only_birth = birth,
                                    in_law_a = False, in_law_b = False)

            #LOG.debug(relation[4])
            #LOG.debug(relation[2])
            #LOG.debug("NUM %d d1 %d d2 %d parenty %2.10f" % ( num, distorig , distother , pct))
            pct = pct + 1 / 2 ** dist
            num = num + 1
        parenty = pct * 100
        LOG.debug("NUM %d parenty %2.10f rel %s" % ( num, pct, rel_str))
        return (parenty,rel_str)

    def writeln(self, text):
        self.g.write('%s\n' % (text))


def export_data(database, filename, user, option_box=None):

        ret = False

        try:
            ped_write = ParentyWriter(database, filename ,  user, option_box)
#pylint: disable=maybe-no-member

            ret = ped_write.write_ped_file()
        except IOError as msg:
            msg2 = _("Could not create %s") % filename
            user.notify_error(msg2, msg)
        except DatabaseError as msg:
            user.notify_db_error(_("Export failed"), msg)
        return ret

