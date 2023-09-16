#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2023  Eric Doutreleau
# Copyright (C) 2012  Doug Blank <doug.blank@gmail.com>
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

# $Id: $

"""
External librar for exporting Gedcom to Geneanet
"""
#-------------------------------------------------------------------------
#
# Standard Python Modules
#
#-------------------------------------------------------------------------

#------------------------------------------------------------------------
#
# GTK modules
#
#------------------------------------------------------------------------

from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.display.place import displayer as _pd
from gramps.gen.utils.location import get_main_location
from gramps.gen.utils.location import get_location_list
from gramps.gen.utils.place import conv_lat_lon
from gramps.gen.lib import (EventRoleType, FamilyRelType, Citation, EventType,Date, \
 PlaceType,Person, AttributeType, NameType, NoteType, ChildRefType)
from gramps.gen.relationship import get_relationship_calculator
from gramps.gui.utils import ProgressMeter
from collections import defaultdict
from GeneanetUtils import ComputeRelation
from GeneanetUtils import PlaceDisplayGeneanet
import io
import os
import time
import re
import logging
from gramps.gen.config import config

LOG = logging.getLogger("gedcomforgeneanet")


class Extobj():
    
    def __init__(self):
        self.rec_file = defaultdict(str)
        self.WikiName = defaultdict(str)
        self.ATTRS=defaultdict(lambda : defaultdict(lambda : defaultdict(str)))
        self.PARENTY= defaultdict(str)
        self.LEN= defaultdict(str)
        self.REL= defaultdict(str)
        self.TIMS= defaultdict(lambda : defaultdict(str))

    def pers_dumpdata(self,person):

        msg=person.get_gramps_id()
        return msg

    def _listwrite(self,nametag):
#
        limit=0
        chaine="Export Liste"
        progress = ProgressMeter(chaine, can_cancel=True)
        length = self.database.get_number_of_people()
        LOG.debug("Write ",length)
        progress.set_pass('star',length)
        msg = "= list =\n<BR><BR>"
        self.list_file.write(msg)
        msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>GenewebName</TH><TH>url</TH><TH>Data</TH></TR>"
        self.list_file.write(msg)
        for person in self.database.iter_people():
            msg=""
            progress.step()
            state = 0
            p1 = person.get_primary_name().get_name()
            handle=person.get_handle()
            data=self.pers_dumpdata(person)
            url=self.WikiName[handle]
            genewebname = ""
            msg = msg + "<TR><TD>" + p1 + "</TD><TD>" + url + "</TD>"
            msg = msg + "<TD>"  + genewebname + "</TD><TD>" + data + "</TD></TR>\n"
            self.list_file.write(msg)
        progress.close()
        msg = "</TABLE>"
        self.list_file.write(msg)

    def write_list_file(self, filename):
        """
        Write list of person.
        """

        self.dirname = os.path.dirname (filename)
        self.list_file = io.open(filename, "w", encoding='utf-8')
        filenameall = filename + "all"
        self.list2_file = io.open(filenameall, "w", encoding='utf-8')
        nametag="list"
        self._listwrite(nametag=nametag)
        self.list_file.close()

    def run(self,filename,database,WikiName):

        self.database = database
        self.WikiName = WikiName

        filenamelist = filename + ".list"
        ret2 = self.write_list_file(filenamelist)


