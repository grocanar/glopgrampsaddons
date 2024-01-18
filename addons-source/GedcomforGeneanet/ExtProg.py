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
from gramps.gen.lib.date import Today
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


RECTAG = ('recploug1946','recploug1936','recploug1931','recploug1926','recploug1921','recploug1911','recploug1906','recploug1901' , 'recploug1896' , 'recploug1891', 'recploug1886','recploug1881')    

NOTABSOLUTE = ('recploug1911','recploug1906','recploug1901','recploug1896','recploug1891','recploug1886','recploug1881')    

AGE = ('recploug1901','recploug1896','recploug1891','recploug1886','recploug1881')    

HEAD = {
        'recploug1946' : "Recensement 1946=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1946 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1936' : "= Recensement 1936=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1936 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1931' : "= Recensement 1931=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1931 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1926' : "= Recensement 1926=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1926 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1921' : "= Recensement 1921=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1921 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1911' : "= Recensement 1911=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1911 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1906' : "= Recensement 1906=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1906 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1901' : "= Recensement 1901=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1901 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1896' : "= Recensement 1896=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1901 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1891' : "= Recensement 1891=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1891 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1886' : "= Recensement 1886=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1886 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1881' : "= Recensement 1881=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1881 et le pourcentage de parenté avec moi meme\n<BR>\n",
        'recploug1876' : "= Recensement 1881=\n<BR><BR>\nCette page donne le recensement pour la commune de Plouguerneau en 1881 et le pourcentage de parenté avec moi meme\n<BR>\n"
        }

TABHEADER = {
        'recploug1946' : "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
        'recploug1936' :  "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
        'recploug1931' :  "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
        'recploug1926' :  "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
        'recploug1921' :  "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
        'recploug1911' :  "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
        'recploug1906' :  "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Lieu Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
         'recploug1901' :   "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Section</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Age</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
         'recploug1896' :   "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Age</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
         'recploug1891' :   "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Age</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
         'recploug1886' :   "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Age</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n",
         'recploug1881' :   "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Adresse</TH><TH>Num Maison</TH><TH>Num Foyer</TH><TH>Numéro</TH><TH>Relation</TH><TH>Age</TH><TH>Nationalité</TH><TH>Profession</TH><TH>Permalink</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n"
         }

NDXTAB = {
        'recploug1946' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Nationalité','Profession'),
        'recploug1936' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Lieu de naissance','Nationalité','Profession'),
        'recploug1931' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Lieu de naissance','Nationalité','Profession'),
        'recploug1926' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Lieu de naissance','Nationalité','Profession'),
        'recploug1921' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Lieu de naissance','Nationalité','Profession'),
        'recploug1911' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Lieu de naissance','Nationalité','Profession'),
        'recploug1906' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Année de naissance','Lieu de naissance','Nationalité','Profession'),
        'recploug1901' : ('Nom','Section','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Âge','Nationalité','Profession'),
        'recploug1896' : ('Nom','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Âge','Nationalité','Profession'),
        'recploug1891' : ('Nom','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Âge','Nationalité','Profession'),
        'recploug1886' : ('Nom','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Âge','Nationalité','Profession'),
        'recploug1881' : ('Nom','Adresse','Numéro Maison','Numéro Foyer','Numéro','Relation','Âge','Nationalité','Profession'),
         }

POPTOTAL = {
        'recploug1946' : '6048',
        'recploug1936' : '5707',
        'recploug1931' : '5845',
        'recploug1926' : '5702',
        'recploug1921' : '5682',
        'recploug1911' : '5813',
        'recploug1906' : '5691',
        'recploug1901' : '5511',
        'recploug1896' : '5455',
        'recploug1891' : '5624',
        'recploug1886' : '5779',
        'recploug1881' : '5821'
        }

class Extobj():
    
    def __init__(self):
        self.rec_file = defaultdict(str)
        self.WikiName = defaultdict(str)
        self.ATTRS=defaultdict(lambda : defaultdict(lambda : defaultdict(str)))
        self.PARENTY= defaultdict(str)
        self.LEN= defaultdict(str)
        self.REL= defaultdict(str)
        self.TIMS= defaultdict(lambda : defaultdict(str))

    def recheader(self):
        for rectag in RECTAG:
            print(" HEAD ", rectag )
            self.rec_file[rectag].write(HEAD[rectag])
            dateobj2=Today()
            text = glocale.date_displayer.display(dateobj2)

            msg = "Recensement mis a jour le " + text + "\n"
            self.rec_file[rectag].write(msg)

    def recwrite(self):

        database=self.database
        WikiName=self.WikiName

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
                                            if etname in NOTABSOLUTE:
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
                            (parenty,rel) = ComputeRelation.get_parenty(database,person,common)
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
        progress.close()
        for name in RECTAG:
            parentypers=0
            for hdl in self.TIMS[name].keys():
                if self.LEN[hdl]:
                    parentypers = parentypers + 1
            num2=len(self.TIMS[name].keys())
            numtotal=int(POPTOTAL[name])
            msg = "<BR>Nombre total de personnes dans le recensement : " + str(numtotal)  + "<BR>Nombre total de personnes dépouillées dans le recensement : " + str(num2)  + "<BR>Nombre total de personnes apparentés : " + str(parentypers)  + "<BR><BR>\n"
            self.rec_file[name].write(msg)
            if num2:
                pctapp = 100.0 * parentypers / num2
                pctdone= 100.0 * num2 / float(numtotal)
            else:
                pctapp=0.0
                pctdone=0
            msg = "<b>" + str(format(pctapp, '.2f')) + "%</b> de personnes apparentées<BR><BR><BR>\n"
            self.rec_file[name].write(msg)
            msg = "<b>" + str(format(pctdone, '.2f')) + "%</b> du recensement effectués<BR><BR><BR>\n"
            self.rec_file[name].write(msg)
            msg=TABHEADER[name]
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
                if WikiName[k]:
                    pname=WikiName[k]
                else:
                    pname=p1
                msg = "<TR bgcolor=" + couleur +"><TD>" +  pname + "</TD>"
                for attr in NDXTAB[name]:
                    msg = msg + "<TD>" + self.ATTRS[k][attr][name] + "</TD>"
                msg = msg + "<TD><A target=\"_blank\" rel=\"noreferre  r\" HREF=\"" + self.ATTRS[k]['Permalink'][name] + "\"</A>Lien</TD><TD>" + str(format(value, '.10f')) + "</  TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                msg = msg + "</TR>\n"
                self.rec_file[name].write(msg)
            msg = "</TABLE>\n"
            self.rec_file[name].write(msg)

    def write_rec_file(self,filename,database,WikiName):
        self.database=database
        self.WikiName=WikiName

        for rectag in RECTAG:
            print("NAMETAG ",rectag)
            filenam = filename + "." + rectag
            self.rec_file[rectag] = io.open(filenam, "w", encoding='utf-8')
            print("FILENAME ",filenam)
        self.recheader()
        self.recwrite()
        for rectag in RECTAG:
            self.rec_file[rectag].close()

    def _starwrite(self,nametag):
#
        self.olddepth=config.get('behavior.generation-depth')
        if not self.olddepth:
            self.olddepth=15
        maxgen=24
        config.set('behavior.generation-depth',maxgen)
        config.save
        RES=defaultdict(lambda : defaultdict(str))
        self.PARENTY= defaultdict(str)
        self.LEN= defaultdict(str)
        self.REL= defaultdict(str)
        self.TIMS= defaultdict(str)
        self.rel_class = get_relationship_calculator(glocale)
        self.home_person = self.database.get_default_person()
        self.starurl='star_url'
        p2 = self.home_person.get_primary_name().get_name()
        parentypers=0
        chaine='Export Star'
        progress = ProgressMeter(chaine, can_cancel=True)
        length = self.database.get_number_of_people()
        LOG.debug("Write ",length)
        progress.set_pass('star',length)
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
                        clas=""
                        p1 = self.person.get_primary_name().get_name()
                        phandle = self.person.handle
       #                 self.REC[phandle]=1
                        LOG.debug("TAG trouve %s" , tname)
                        common, self.msg_list = self.rel_class.get_relationship_distance_new(
                              self.database, self.person, self.home_person,
                        all_families=True,
                        all_dist=True,
                        only_birth=False)
                        (parenty,rel) = ComputeRelation.get_parenty(self.database,self.person,common)
                        numlinks=len(common)
                        LOG.debug("TAG parenty trouve %2.6f" , parenty)
                        if parenty > 0.0:
                            parentypers=parentypers + 1
                            attributes = self.person.get_attribute_list()
                            attributes.sort(key=lambda a: a.get_type().value)
                            result=""
                            LOG.debug("TAG parenty inside trouve %2.6f" , parenty)
                            self.PARENTY[phandle]=parenty
                            self.LEN[phandle]=numlinks
                            self.REL[phandle]=rel
                            for attribute in attributes:
                                attr_type = attribute.get_type()
                                attr_val  = attribute.get_value()
                                if str(attr_type) == self.starurl:
                                    RES[phandle][self.starurl]=attr_val
                        else:
                            self.PARENTY[phandle]=0
                            self.LEN[phandle]=0
                            self.REL[phandle]=""
        num=parentypers
        progress.close()
        msg = "= Mes cousins star =\n<BR><BR>"
        LOG.debug(msg)
        self.star_file.write(msg)
        msg = "Cette page donne la liste de mes cousins mondialement connu\n<BR>\n"
        LOG.debug(msg)
        self.star_file.write(msg)
        msg =  "<BR>Nombre total de stars : " + str(num)  + "<BR><BR>\n"
        self.star_file.write(msg)
        sortedDict = sorted(self.PARENTY.items(), reverse=True, key=lambda kv: kv[1])
        num2=len(sortedDict)
        LOG.debug(sortedDict)
        msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Lien</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TR>"
        LOG.debug(" nombre de parente " , num2 )
        self.star_file.write(msg)
        for k,val in sortedDict:
            msg = "<TR>"
            if RES[k][self.starurl]:
                url = str(RES[k][self.starurl])
                person = self.database.get_person_from_handle(k)
                p1 = person.get_primary_name().get_name()
                msg = msg + "<TD> <A HREF=\"" + url + "\">" + p1 + "</A></TD>"
            else:
                person = self.database.get_person_from_handle(k)
                p1 = person.get_primary_name().get_name()
                msg = msg + "<TD>" + p1 +" </TD>"
            url = self.WikiName[k]
            msg = msg + "<TD> " + url + "</TD>" + "<TD>" + str(format(val, '.10f')) +  "</TD><TD>" +str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) +"</TD></TR>\n"
            self.star_file.write(msg)
        msg = msg + "</TABLE>"
        self.star_file.write(msg)
        config.set('behavior.generation-depth',self.olddepth)
        config.save

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
            msg2  = p1 + " : " + genewebname + " : " + data + "\n"
            self.list2_file.write(msg2)
            self.list_file.write(msg)
        progress.close()
        msg = "</TABLE>"
        self.list_file.write(msg)

    def couswrite(self,nametag):
#
        database=self.database
        WikiName=self.WikiName


        RES=defaultdict(lambda : defaultdict(str))
        self.PARENTY= defaultdict(str)
        self.LEN= defaultdict(str)
        self.REL= defaultdict(str)
        self.TIMS= defaultdict(str)
        self.HANDL= defaultdict(set)
        self.ANCL= defaultdict(set)
        self.rel_class = get_relationship_calculator(glocale)
        self.home_person = self.database.get_default_person()
        self.stringgen='site geneanet'
        self.geneaneturl='geneanet_url'
        home_person = self.database.get_default_person()
        p2 = home_person.get_primary_name().get_name()
        parentypers=0
        chaine="Export cous"
        progress = ProgressMeter(chaine, can_cancel=True)
        length = self.database.get_number_of_people()
        LOG.debug("Write ",length)
        progress.set_pass('star',length)
        for person in self.database.iter_people():
            progress.step()
            state = 0
            if person.handle == home_person.handle :
                next
            else:
                for tag_handle in person.get_tag_list():
                    tag = self.database.get_tag_from_handle(tag_handle)
                    tname = tag.get_name()
                    if tname == nametag:
                        state= 1
                        clas=""
                        p1 = person.get_primary_name().get_name()
                        phandle = person.handle
       #                 self.REC[phandle]=1
                        LOG.debug("TAG trouve %s" , tname)
                        common, self.msg_list = self.rel_class.get_relationship_distance_new(
                              self.database, person, home_person,
                        all_families=True,
                        all_dist=True,
                        only_birth=False)
                        for relation in common:
                            handle=relation[1]
                            self.HANDL[person.handle].add(handle)
                        (parenty,rel) = ComputeRelation.get_parenty(self.database,person,common)
                        numlinks=len(common)
                        if parenty > 0.0:
                            parentypers=parentypers + 1
                            attributes = person.get_attribute_list()
                            attributes.sort(key=lambda a: a.get_type().value)
                            result=""
                            self.PARENTY[phandle]=parenty
                            self.LEN[phandle]=numlinks
                            self.REL[phandle]=rel
                            for attribute in attributes:
                                attr_type = attribute.get_type()
                                attr_val  = attribute.get_value()
                                if str(attr_type) == self.stringgen:
                                    RES[phandle][self.stringgen]=attr_val
                        else:
                            self.PARENTY[phandle]=0
                            self.LEN[phandle]=0
                            self.REL[phandle]=""
        num=parentypers
        progress.close()
        msg = "= Mes cousins Geneanet =\n<BR><BR>"
        self.cous_file.write(msg)
        msg = "Cette page donne la liste de mes cousins geneanet\n<BR>\n"
        self.cous_file.write(msg)
        msg =  "<BR>Nombre total de cousins : " + str(num)  + "<BR><BR>\n"
        self.cous_file.write(msg)
        sortedDict = sorted(self.PARENTY.items(), reverse=True, key=lambda kv: kv[1])
        msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></TR>"
        num2=len(sortedDict)
        self.cous_file.write(msg)
        for k,val in sortedDict:
            if val == 0.0:
                continue
            msg = "<TR>"
            span=str(len(self.HANDL[k]) + 2)
            if RES[k][self.stringgen]:
                url = str(RES[k][self.stringgen])
                person = self.database.get_person_from_handle(k)
                p1 = person.get_primary_name().get_name()
                msg = msg + "<TD rowspan=" + span +"> <A HREF=\"" + url + "\">" + p1 + "</A></TD>"
            else:
                person = self.database.get_person_from_handle(k)
                p1 = person.get_primary_name().get_name()
                msg = msg + "<TD rowspan=" + span +">" + p1 + "</TD>"
            msg = msg + "<TD rowspan=" + span +">" + str(format(val, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD></TR>\n"
            self.cous_file.write(msg)
            if self.HANDL[k]:
                msg="<TR><TH colspan=2> Liste des MRCA</TH></TR>\n"
                self.cous_file.write(msg)
                for hdl in self.HANDL[k]:
                    if hdl:
                        url = WikiName[hdl]
                        parurl = self.get_parurl(WikiName[hdl])
                        person2 = self.database.get_person_from_handle(hdl)
                        p2 = person2.get_primary_name().get_name()
                        msg = "<TR><TD>" + url + "</TD><TD><A HREF=\"" + parurl + "\">Lien de parenté</TD></TR>\n"
                        self.cous_file.write(msg)
        msg =  "</TABLE>"
        self.cous_file.write(msg)

    def get_parurl(self,chaine):
        (firstnam, surname , num,reste) = chaine.split('/',3)
        firstname=firstnam.replace("[[", "")
        urlbase="https://gw.geneanet.org/glopglop?lang=fr&pz=eric+christophe&nz=doutreleau&p=eric+christophe&n=doutreleau&m=A&t=D&"
        urlparbase="https://gw.geneanet.org/glopglop?lang=fr&pz=eric+christophe&nz=doutreleau&p=eric+christophe&n=doutreleau&m=A&t=D&"
        genewebparurl = urlparbase + 'p1=%s&n1=%s&oc1=%s' % (firstname , surname ,num) + "&l=20"
        return genewebparurl

    def write_star_file(self, filename):
        """
        Write the actual GEDCOM file to the specified filename.
        """

        self.dirname = os.path.dirname (filename)
        self.star_file = io.open(filename, "w", encoding='utf-8')
        nametag="star"
        self._starwrite(nametag=nametag)
        self.star_file.close()

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

    def write_cous_file(self, filename,database,WikiName):
        """
        Write the actual GEDCOM file to the specified filename.
        """

        self.database=database
        self.WikiName=WikiName

        self.dirname = os.path.dirname (filename)
        self.cous_file = io.open(filename, "w", encoding='utf-8')
        nametag="cousingen"
        self.couswrite(nametag=nametag)
        self.cous_file.close()

    def run(self,filename,database,WikiName):

        self.database = database
        self.WikiName = WikiName

        #ret2 = self.write_rec_file(filename,database,WikiName)
        #filenamestar = filename + ".star"
        #ret2 = self.write_star_file(filenamestar)
        #filenamecous = filename + ".cous"
        #ret2 = self.write_cous_file(filenamecous,database,WikiName)
        #filenamelist = filename + ".list"
        #ret2 = self.write_list_file(filenamelist)


