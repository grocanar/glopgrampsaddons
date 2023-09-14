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
from gramps.gui.utils import ProgressMeter

RECTAG = ('recploug1946','recploug1936','recploug1931','recploug1926','recploug1921','recploug1911')    

HEAD = {
        'recploug1946' : "Recensement 1946=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1946 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1936' : "= Recensement 1936=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1936 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1931' : "= Recensement 1931=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1931 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1926' : "= Recensement 1926=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1926 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1921' : "= Recensement 1921=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1921 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1911' : "= Recensement 1911=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1911 et le pourcentage de parenté avec moi meme\n<BR>\n"
        }

class RecFile():
    
    def __init__(self):
       toto=""

    def _recheader(self):
        for rectag in HEAD:
            self.rec_file[rectag].write(MSG[nametag])
            msg = "Recensement mis a jour le 26 aout 2923\n"
            self.rec_file[rectag].write(msg)


    def _recwrite(self,nametag,database,WikiName):

        RES=defaultdict(lambda : defaultdict(str))
        self.ATTRS=defaultdict(lambda : defaultdict(lambda : defaultdict(str)))
        self.PARENTY= defaultdict(str)
        self.LEN= defaultdict(str)
        self.REL= defaultdict(str)
        self.TIMS= defaultdict(lambda : defaultdict(str))
        home_person = database.get_default_person()
        p2 = home_person.get_primary_name().get_name()
        parentypers=0
        couleur1="7FD5CE"
        couleur2="D5C17F"
        couleur=couleur1
        chaine = "Export Census " 
        progress = ProgressMeter((chaine), can_cancel=True)
        length = database.get_number_of_people()
        progress.set_pass("Census",length)
        self.rel_class = get_relationship_calculator(glocale)
        numpers=0
        for person in database.iter_people():
            phandle = person.handle
            progress.step()
            numpers = numpers + 1
            state = 0
            if person.handle == home_person.handle :
                next
            else:
                for tag_handle in person.get_tag_list():
                    tg = database.get_tag_from_handle(tag_handle)
                    tname = tg.get_name()
                    if tname in RECTAG:
                        state= 1
                        clas=""
                        p1 = person.get_primary_name().get_name()
                        LOG.debug("TAG trouve %s" % tname)
                        LOG.debug("personne trouve %s" % p1)
                        for event_ref in person.get_event_ref_list():
                            event = database.get_event_from_handle(event_ref.ref)
                            if not event:
                                continue
                            if event.get_type() == EventType.CENSUS:
                                for t_handle in event.get_tag_list():
                                    tag = database.get_tag_from_handle(t_handle)
                                    etname = tag.get_name()
                                    if etname == tname:
                                        attrs = event_ref.get_attribute_list()
                                        rang=0
                                        foyer=0
                                        numero=0
                                        maison=0
                                        if len(attrs):
                                            for attribute in attrs:
                                                attr_type = str(attribute.get_type()).strip()
                                                attr_val  = str(attribute.get_value())
                                                self.ATTRS[phandle][attr_type][etname]=attr_val
                                                if attr_type == "Rang":
                                                    rang=attr_val
                                                if attr_type == "Numéro Foyer":
                                                    foyer=attr_val
                                                if attr_type == "Numéro Maison":
                                                    maison=attr_val
                                                if attr_type == "Numéro":
                                                    numero=attr_val
                                            clas=str(foyer) + "." + str(rang)
                                            if etname == "recploug1911":
                                                self.TIMS[etname][phandle]=1000000*int(maison) + 1000 * int(foyer) + int(numero)
                                            else:
                                                self.TIMS[etname][phandle]=int(numero)
                                            for cit in event.get_citation_list():
                                                cita=self.database.get_citation_from_handle(cit)
                                                attrs = cita.get_attribute_list()
                                                for attr in attrs:
                                                    typ = str(attr.get_type()).strip()
                                                    if typ == "Permalink":
                                                        attr_val  = str(attr.get_value())
                                                        self.ATTRS[phandle][typ][etname]=attr_val

                        if not self.PARENTY[phandle]:
                            LOG.debug("calcul rerlationship ",p1)
                            common, self.msg_list = self.rel_class.get_relationship_distance_new(
                                  database, person, home_person,
                                  all_families=True,
                                  all_dist=True,
                                  only_birth=False)
                            LOG.debug("calcul parenty ")
                            LOG.debug(common)
                            (parenty,rel) = ComputeRelation.get_parenty(self,common)
                            LOG.debug("parenty2 ",parenty)
                            numlinks=len(common)
                            if parenty > 0.0:
                                parentypers=parentypers + 1
                                print("PARENTYNUM %d NUMPERS %d" % ( parentypers, numpers))
                                attributes = person.get_attribute_list()
                                attributes.sort(key=lambda a: a.get_type().value)
                                result=""
                                self.PARENTY[phandle]=parenty
                                self.LEN[phandle]=numlinks
                                self.REL[phandle]=rel
                            else:
                                self.PARENTY[phandle]=0
                                self.LEN[phandle]=0
                                self.REL[phandle]="pas relié"
        num=parentypers
        progress.close()
        for name in nametag:
            parentypers=0
            for hdl in self.TIMS[name].keys():
                if self.LEN[phandle]:
                    parentypers = parentypers + 1
            num2=len(self.TIMS[name].keys())
            msg =  "<BR>Nombre total de personnes dans le recensement : " + str(num2)  + "<BR>Nombre total de personnes apparentés : " + str(parentypers)  + "<BR><BR>\n"
            self.rec_file[name].write(msg)
            if num2:
                pct = 100.0 * parentypers / num2
            else:
                pct=0.0
            msg = "<b>" + str(format(pct, '.2f')) + "%</b> de personnes apparentées<BR><BR><BR>\n"
            self.rec_file[name].write(msg)
            if name == "recploug1946":
                msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n"
            else:
                msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n"
            self.rec_file[name].write(msg)
            num = 1
            sortedDict = sorted(self.TIMS[name].items(), reverse=False,key=lambda kv: int(kv[1]))
            LOG.debug(sortedDict)
            preval=""
            couleur= couleur1
            for k,val in sortedDict:
                valstr=self.ATTRS[k]['Numéro Foyer'][name]
                if valstr != preval:
                    if couleur == couleur1:
                        couleur = couleur2
                    else:
                        couleur = couleur1
                preval = valstr
                if k not in self.PARENTY:
                    value = 0
                else:
                    value=self.PARENTY[k]
                person = self.database.get_person_from_handle(k)
                p1 = person.get_primary_name().get_name()
                phandle=k
                if name == "recploug1946":
                    if WikiName[phandle]:
                        msg = "<TR bgcolor=" + couleur +"><TD>" +  WikiName[phandle] + "</TD><TD>" + self.ATTRS[phandle]['Nom'][name] + "</TD><TD>" + self.ATTRS[phandle]['Section'][name] + "</TD><TD>" + self.ATTRS[phandle]['Adresse'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Maison'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Foyer'][name] + "</TD><TD>"+ self.ATTRS[phandle]['Numéro'][name] + "</TD><TD>" + self.ATTRS[phandle]['Relation'][name] + "</TD><TD>" + self.ATTRS[phandle]['Année de naissance'][name] + "</TD><TD>" + self.ATTRS[phandle]['Nationalité'][name] + "</TD><TD>" + self.ATTRS[phandle]['Profession'][name] + "</TD><TD><A target=\"_blank\" rel=\"noreferrer\" HREF=\"" + self.ATTRS[phandle]['Permalink'][name] + "\"</A>Lien</TD><TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                    else:
                        msg = "<TR bgcolor=" + couleur +"><TD>" +  p1 + "</TD><TD>" + self.ATTRS[phandle]['Nom'][name] + "</TD><TD>" + self.ATTRS[phandle]['Section'][name] + "</TD><TD>" + self.ATTRS[phandle]['Adresse'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Maison'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Foyer'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro'][name] + "</TD><TD>" + self.ATTRS[phandle]['Relation'][name] + "</TD><TD>" + self.ATTRS[phandle]['Année de naissance'][name] + "</TD><TD>" + self.ATTRS[phandle]['Nationalité'][name] + "</TD><TD>" + self.ATTRS[phandle]['Profession'][name] + "</TD><TD><A target=\"_blank\" rel=\"noreferrer\" HREF=\"" + self.ATTRS[phandle]['Permalink'][name] + "\"</A>Lien</TD><TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                else:
                    if WikiName[phandle]:
                        msg = "<TR bgcolor=" + couleur +"><TD>" +  WikiName[phandle] + "</TD><TD>" + self.ATTRS[phandle]['Nom'][name] + "</TD><TD>" + self.ATTRS[phandle]['Section'][name] + "</TD><TD>" + self.ATTRS[phandle]['Adresse'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Maison'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Foyer'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro'][name] + "</TD><TD>" + self.ATTRS[phandle]['Relation'][name] + "</TD><TD>" + self.ATTRS[phandle]['Année de naissance'][name] + "</TD><TD>" + self.ATTRS[phandle]['Lieu de naissance'][name] + "</TD><TD>" + self.ATTRS[phandle]['Nationalité'][name] + "</TD><TD>" + self.ATTRS[phandle]['Profession'][name] + "</TD><TD><A target=\"_blank\" rel=\"noreferrer\" HREF=\"" + self.ATTRS[phandle]['Permalink'][name] + "\"</A>Lien</TD><TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                    else:
                        msg = "<TR bgcolor=" + couleur +"><TD>" +  p1 + "</TD><TD>" + self.ATTRS[phandle]['Nom'][name] + "</TD><TD>" + self.ATTRS[phandle]['Section'][name] + "</TD><TD>" + self.ATTRS[phandle]['Adresse'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Maison'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro Foyer'][name] + "</TD><TD>" + self.ATTRS[phandle]['Numéro'][name] + "</TD><TD>" + self.ATTRS[phandle]['Relation'][name] + "</TD><TD>" + self.ATTRS[phandle]['Année de naissance'][name] + "</TD><TD>" + self.ATTRS[phandle]['Lieu de naissance'][name] + "</TD><TD>" + self.ATTRS[phandle]['Nationalité'][name] + "</TD><TD>" + self.ATTRS[phandle]['Profession'][name] + "</TD><TD><A target=\"_blank\" rel=\"noreferrer\" HREF=\"" + self.ATTRS[phandle]['Permalink'][name] + "\"</A>Lien</TD><TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                msg = msg + "</TR>\n"
                self.rec_file[name].write(msg)
            msg = "</TABLE>\n"
            self.rec_file[name].write(msg)
    def write_rec_file(self, filename):
        self.rec_file = defaultdict(str)

        for rectag in RECTAG:
            print("NAMETAG ",rectag)
            filenam = filename + "." + rectag
            self.rec_file[rectag] = io.open(filenam, "w", encoding='utf-8')
            print("FILENAME ",filenam)
        self._recheader()
        self._recwrite()
        for rectag in RECTAG:
            self.rec_file[rectag].close()


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

    def get_parenty(database, person,relations):

        if not relations or relations[0][0] == -1:
            parenty = 0
            return (parenty,"pas de parente")
        home_person=database.get_default_person()
        pct = 0.0
        num=0
        rel_str=""
        rel_class = get_relationship_calculator(glocale)
        for relation in relations:
            birth = rel_class.only_birth(relation[2])\
                    and rel_class.only_birth(relation[4])
            distorig = len(relation[4])
            distother = len(relation[2])
            dist = distorig + distother
            pct = pct + 1 / 2 ** dist
            num = num + 1
            if not rel_str:
                rel_str = rel_class.get_single_relationship_string(
                         distorig, distother,
                         home_person.get_gender(),
                         person.get_gender(),
                         relation[4], relation[2],
                         only_birth = birth,
                         in_law_a = False, in_law_b = False)

        parenty = pct * 100
        return (parenty,rel_str)


