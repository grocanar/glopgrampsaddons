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
Utilities for exporting Gedcom to Geneanet
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
from gramps.gen.display import place
from gramps.gen.lib import (EventRoleType, FamilyRelType, Citation, EventType,Date, \
 PlaceType,Person, AttributeType, NameType, NoteType, ChildRefType)
from gramps.gen.relationship import get_relationship_calculator

    
class PlaceDisplayGeneanet(place.PlaceDisplay):
    
    def __init__(self):
        super(PlaceDisplayGeneanet,self).__init__()

    def display(self, db, place, date=None, fmt=-1):
        if not place:
            return ""
        if not config.get('preferences.place-auto'):
            return place.title
        else:
            if fmt == -1:
                fmt = config.get('preferences.place-format')
            pf = self.place_formats[fmt]
            lang = pf.language
            places = get_location_list(db, place, date, lang)
            visited = [place.handle]
            postal_code = place.get_code()
            if not postal_code:
                place2 =""
                for placeref in place.placeref_list:
                    place2 = db.get_place_from_handle(placeref.ref)
                    if place2:
                        postal_code = self._find_postal_code(db,place2,visited)
                        if postal_code:
                            break
            return  self._find_populated_place(places,place,postal_code)

    def _find_postal_code(self,db,place,visited):
        postal_code = place.get_code()
        if postal_code:
            return postal_code
        else:
            for placeref in place.placeref_list:
                if placeref.ref not in visited:
                    place2 = db.get_place_from_handle(placeref.ref)
                    if place2:
                        visited.append(place2.handle)
                        postal_code = self._find_postal_code(db,place2,visited)
                        if postal_code:
                            break
            return postal_code
 
    def _find_populated_place(self,places,place,postal_code):
        populated_place = ""
        level = 0
        for index, item in enumerate(places):
            if int(item[1]) in [PlaceType.NUMBER, PlaceType.BUILDING , PlaceType.FARM , PlaceType.HAMLET, PlaceType.NEIGHBORHOOD , PlaceType.STREET , PlaceType.PARISH , PlaceType.LOCALITY , PlaceType.BOROUGH, PlaceType.UNKNOWN , PlaceType.CUSTOM]:
                level = 1
                if populated_place == "":
                    populated_place = "[ " + item[0]
                else :
                    populated_place = populated_place + " - " + item[0] 
            elif int(item[1]) in [PlaceType.CITY, PlaceType.VILLAGE,
                            PlaceType.TOWN , PlaceType.MUNICIPALITY]:
                level = 2
                if populated_place == "":
                    populated_place = item[0]
                else:
                    populated_place = populated_place + " ] - " + item[0]
                populated_place = populated_place + ", "  + postal_code
            elif int(item[1]) in [PlaceType.COUNTY, PlaceType.DEPARTMENT ]:
                if populated_place == "":
                    populated_place = item[0]
                else:
                    if level == 1:
                        populated_place = populated_place + " ] - ,, " + item[0]
                    else:
                        populated_place = populated_place + ", " + item[0]
                    level = 3
            elif int(item[1]) in [PlaceType.STATE, PlaceType.REGION , PlaceType.PROVINCE ]:
                if populated_place == "":
                    populated_place = item[0]
                else:
                    if level == 1:
                        populated_place = populated_place + " ] - ,,, " + item[0]
                    elif level ==  2:
                        populated_place = populated_place + ",, " + item[0]
                    else:
                         populated_place = populated_place + ", " + item[0]
                    level = 4
            elif int(item[1]) in [PlaceType.COUNTRY ]:
                if populated_place == "":
                    populated_place = item[0]
                else:
                    if level == 1:
                        populated_place = populated_place + " ] - ,,,, " + item[0]
                    elif level ==  2:
                        populated_place = populated_place + ",,, " + item[0]
                    elif level == 3:
                        populated_place = populated_place + ",, " + item[0]
                    else:
                        populated_place = populated_place + ", " + item[0]
                    level = 5
        return populated_place

class ComputeRelation:

    def __init__(self):
        toto=""

    def get_parenty(self, relations):

        if not relations or relations[0][0] == -1:
            parenty = 0
            return (parenty,"pas de parente")
        pct = 0.0
        num=0
        rel_str=""
        self.rel_class = get_relationship_calculator(glocale)
        for relation in relations:
            birth = self.rel_class.only_birth(relation[2])\
                    and self.rel_class.only_birth(relation[4])
            distorig = len(relation[4])
            distother = len(relation[2])
            dist = distorig + distother
            pct = pct + 1 / 2 ** dist
            num = num + 1
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


