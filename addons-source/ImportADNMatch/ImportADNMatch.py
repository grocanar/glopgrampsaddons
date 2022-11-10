#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007  Donald N. Allingham
# Copyright (C) 2008  Brian Matherly
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

# $Id: ImportADNMatchTool.py 1739 2013-04-21 00:46:48Z jralls $

"Set Private Tool"

#-------------------------------------------------
#
# python modules
#
#-------------------------------------------------
import time

#-------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------
from gramps.gui.plug import tool as Tool
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.utils import ProgressMeter
from gramps.gui.plug import MenuToolOptions, PluginWindows
from gramps.gen.plug.menu import StringOption, FilterOption, PersonOption, \
    EnumeratedListOption, BooleanOption , NumberOption , DestinationOption
from collections import defaultdict
from gramps.gen.lib import (Attribute, AttributeType, Citation , Name, NameType, Note, NoteType, Person , PersonRef , Source , Surname)
import csv
from gramps.gen.db import DbTxn
from gramps.gen.errors import ReportError

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

import logging
LOG = logging.getLogger(".importadnmatch")

#-------------------------------------------------
#
# Tool Classes
#
#-------------------------------------------------
class ImportADNMatchTool(PluginWindows.ToolManagedWindowBatch):

    def get_title(self):
        return _("Import match ADN")

    def run(self):
        self.MyHeritageMatchID="MyHeritageMatchID"
        self.GeneanetMatchID="GeneanetMatchID"
        self.GeneanetSourceTitle="Match from Geneanet files"
        self.MyHeritageSourceTitle="Match from MyHeritage files"
        self.GeneanetCitation=None
        self.MyHeritageCitation=None
        self.db = self.dbstate.get_database()
        self.People=defaultdict(str)
        self.myheritagelistefile=str(self.get_opt("myherlistefile"))
        self.myheritagesegmentfile = str(self.get_opt("myhersegmentfile"))
        self.myher = self.get_opt("myher")
        self.geneanetlistefile=str(self.get_opt("geneanetlistefile"))
        self.geneanetsegmentfile = str(self.get_opt("geneanetsegmentfile"))
        self.geneanet = self.get_opt("geneanet")
        self.db.disable_signals()
        self.People=self.init_people(self.db)
        self.SourceGeneanet,self.SourceMyHeritage=self.get_sources()
        self.pid = self.get_opt('pid')
        self.souche = self.db.get_person_from_gramps_id(self.pid)
        if self.souche is None:
            raise ReportError(_("Person %s is not in the Database") % pid)
        if self.myher:
            self.parsefile(filetype="MyHeritage")
        if self.geneanet:
            self.parsefile(filetype="Geneanet")
        self.db.enable_signals()
        self.db.request_rebuild()
        LOG.debug("ADMMATCH:" )

    def  get_sources(self):
        sourcesgeneanet=None
        sourcesmyheritage=None
        try:
            with DbTxn(_("Citation Creation"), self.db, batch=True) as self.trans:
                for handle in self.db.get_source_handles():
                    source=self.db.get_source_from_handle(handle)
                    if source.get_title() == self.GeneanetSourceTitle:
                        sourcesgeneanet = source
                    elif source.get_title() == self.MyHeritageSourceTitle:
                        sourcesmyheritage = source
                if not sourcesgeneanet:
                    source = Source()
                    source.set_title(self.GeneanetSourceTitle)
                    self.db.add_source(source, self.trans)
                    self.db.commit_source(source, self.trans)
                    sourcesgeneanet = source
                if not sourcesmyheritage:
                    source = Source()
                    source.set_title(self.MyHeritageSourceTitle)
                    self.db.add_source(source, self.trans)
                    self.db.commit_source(source, self.trans)
                    sourcesmyheritage = source
        except EnvironmentError as err:
            user.notify_error(_("%s could not be opened\n") % filename, str(err))
        return (sourcesgeneanet,sourcesmyheritage)


    def parsefile(self,filetype):
        MYLISTE=defaultdict(list)
        MYSEG=defaultdict(list)
        num  = 0
        if filetype == "MyHeritage":
            listefile = self.myheritagelistefile
            segmentfile = self.myheritagesegmentfile
            attribute=self.MyHeritageMatchID
            citationtype="MyHeritage"
            myherownid = "D-8EF78206-5831-4EE2-A1C1-4F0342B15546"
        elif filetype == "Geneanet":
            listefile = self.geneanetlistefile
            segmentfile = self.geneanetsegmentfile
            attribute=self.GeneanetMatchID
            citationtype="Geneanet"
        try:
            with DbTxn(_("ADNMatch import"), self.db, batch=True) as self.trans:
                
                with open(listefile, newline='') as myfile:
                    cor = csv.reader(myfile)
                    for L in cor:
                        if num:
                            if L:
                                if filetype == "MyHeritage":
                                    replaceid = myherownid + "-"
                                    ID=str(L[0].replace(replaceid,''))
                                elif filetype == "Geneanet": 
                                    ID=L[0]
                                MYLISTE[ID]=L
                        else:
                            num = 1
                num  = 0
                with open(segmentfile, newline='') as myfile2:
                    seg = csv.reader(myfile2)
                    for L in seg:
                        if num:
                            if L:
                                if filetype == "Geneanet":
                                    ID=str(L[0])
                                    chrom=str(L[3])
                                    deb=int(L[4])
                                    fin=int(L[5])
                                    longueur=float(L[7])
                                    numsnp=int(L[6])
                                elif filetype == "MyHeritage":
                                    replaceid = myherownid + "-"
                                    ID=str(L[0].replace(replaceid,''))
                                    chrom=str(L[3])
                                    deb=int(L[4])
                                    fin=int(L[5])
                                    longueur=float(L[8])
                                    numsnp=int(L[9])
                                MYSEG[ID].append((chrom,deb,fin,longueur,numsnp))
                        else:
                            num = 1
                for ID in MYLISTE.keys():
                    if ID in self.People.keys():
                        self.person=self.People[ID]
                    else:
                        self.person=self.create_people(self.db,ID,MYLISTE,attribute=attribute)
                    self.create_or_update_attrs(self.person,self.db,ID,MYLISTE)
                    assoc=False
                    for ref in self.souche.get_person_ref_list():
                        person = self.db.get_person_from_handle(ref.ref)
                        if person == self.person:
                            result = ref.get_relation()
                            if result == "DNA":
                                assoc=True
                    if not assoc:
                        handle=self.person.get_handle()
                        self.personref = PersonRef()
                        self.personref.ref = handle
                        self.personref.rel = "DNA"
                        texte="" 
                        for segment in MYSEG[ID]:
                            (chrom,deb,fin,longueur,numsnp)=segment
                            texto=",".join(str(e) for e in segment) 
                            if texte:
                                texte = texte + "\n" + texto
                            else:
                                texte = texto
                        note=Note()
                        note.set(texte)
                        note.type.set(NoteType.ASSOCIATION)
                        self.db.add_note(note, self.trans)
                        self.db.commit_note(note, self.trans)
                        handle=note.get_handle()
                        self.personref.add_note(handle)
                        if citationtype == "Geneanet":
                            self.GeneanetCitation=self.get_or_create_citation(citationtype=citationtype)
                            handle=self.GeneanetCitation.get_handle()
                        elif citationtype == "MyHeritage":
                            self.MyHeritageCitation=self.get_or_create_citation(citationtype=citationtype)
                            handle=self.MyHeritageCitation.get_handle()
                        self.personref.add_citation(handle)
                        self.souche.add_person_ref(self.personref)
                        self.db.commit_person(self.souche,self.trans)

        except EnvironmentError as err:
            user.notify_error(_("%s could not be opened\n") % filename, str(err))
        return

    def get_or_create_citation(self,citationtype):
        citation = None
        if citationtype == "Geneanet":
            if self.GeneanetCitation:
                citation = self.GeneanetCitation
            else:
                citation=Citation()
                citation.set_reference_handle(self.SourceGeneanet.get_handle())
                self.db.add_citation(citation, self.trans)
                self.db.commit_citation(citation, self.trans)
        elif citationtype == "MyHeritage":
            if self.MyHeritageCitation:
                citation = self.MyHeritageCitation
            else:
                citation=Citation()
                citation.set_reference_handle(self.SourceMyHeritage.get_handle())
                self.db.add_citation(citation, self.trans)
                self.db.commit_citation(citation, self.trans)
        return citation

    def parsemyheritage(self):
        MYHERLISTE=defaultdict(list)
        MYHERSEG=defaultdict(list)
        num  = 0
        myherownid="D-8EF78206-5831-4EE2-A1C1-4F0342B15546"
        try:
            with DbTxn(_("ADNMatch import"), self.db, batch=True) as self.trans:
                self.souche=self.db.get_person_from_gramps_id('I0000')
                if not self.souche:
                    self.souche=self.create_souche(self.db)
                with open(self.myherlistefile, newline='') as myfile:
                    cor = csv.reader(myfile)
                    for L in cor:
                        if num:
                            if L:
                                replaceid = myherownid + "-"
                                ID=str(L[0].replace(replaceid,''))
                                MYHERLISTE[ID]=L
                        else:
                            num = 1
                num  = 0
                with open(self.myhersegmentfile, newline='') as myfile2:
                    seg = csv.reader(myfile2)
                    for L in seg:
                        if num:
                            if L:
                                replaceid = myherownid + "-"
                                ID=str(L[0].replace(replaceid,''))
                                chrom=str(L[3])
                                deb=int(L[4])
                                fin=int(L[5])
                                longueur=float(L[8])
                                numsnp=int(L[9])
                                MYHERSEG[ID].append((chrom,deb,fin,longueur,numsnp))
                        else:
                            num = 1
                for ID in MYHERLISTE.keys():
                    if ID in self.People.keys():
                        self.person=self.People[ID]
                    else:
                        self.person=self.create_people(self.db,ID,MYHERLISTE,attribute=self.MyHeritageMatchID)
                    self.create_or_update_attrs(self.person,self.db,ID,MYHERLISTE)
                    assoc=False
                    for ref in self.souche.get_person_ref_list():
                        person = self.db.get_person_from_handle(ref.ref)
                        if person == self.person:
                            result = ref.get_relation()
                            if result == "DNA":
                                assoc=True
                    if not assoc:
                        handle=self.person.get_handle()
                        self.personref = PersonRef()
                        self.personref.ref = handle
                        self.personref.rel = "DNA"
                        texte="" 
                        for segment in MYHERSEG[ID]:
                            (chrom,deb,fin,longueur,numsnp)=segment
                            texto=",".join(str(e) for e in segment) 
                            if texte:
                                texte = texte + "\n" + texto
                            else:
                                texte = texto
                        note=Note()
                        note.set(texte)
                        note.type.set(NoteType.ASSOCIATION)
                        self.db.add_note(note, self.trans)
                        self.db.commit_note(note, self.trans)
                        handle=note.get_handle()
                        self.personref.add_note(handle)
                        self.MyHeritageCitation=self.get_or_create_citation(citationtype="MyHeritage")
                        handle=self.MyHeritageCitation.get_handle()
                        self.personref.add_citation(handle)
                        self.souche.add_person_ref(self.personref)
                        self.db.commit_person(self.souche,self.trans)

        except EnvironmentError as err:
            user.notify_error(_("%s could not be opened\n") % filename, str(err))
        return

    def get_opt(self, name):
        """Get the options value for further processing.

        :param name: Name of the menu option
        :param name: string
        :returns: Value of the option
        :rtype: True, False or integer
        """
        menu = self.options.menu
        opt = menu.get_option_by_name(name).get_value()
        return opt


    def init_people(self,database):
        PERSON={}
        for person in database.iter_people():
            myheritageid = ""
            for attr in person.get_attribute_list():
                if attr.get_type() == self.MyHeritageMatchID or attr.get_type() == self.GeneanetMatchID:
                    idvalue = attr.get_value()
                    PERSON[idvalue]=person
        return PERSON
     
    def create_people(self,database,ID,MYHERLISTE,attribute):
        nom=MYHERLISTE[ID][1]
        self.name = Name()
        self.name.set_type(NameType(NameType.BIRTH))
        N=nom.split()
        surname=N[-1]
        N.pop()
        separator = ' '
        firstname=separator.join(N)
        self.name.set_first_name(firstname)
        surname_obj = Surname()
        surname_obj.set_surname(surname)
        self.name.add_surname(surname_obj)
        self.name.get_primary_surname().set_surname(surname)
        self.person = Person()
        attr = Attribute()
        attr.set_type(attribute)
        attr.set_value(ID)
        self.person.set_primary_name(self.name)
        database.add_person(self.person,self.trans)
        self.person.add_attribute(attr)
        database.commit_person(self.person,self.trans)
        self.People[ID]=self.person
        return self.person

    def create_souche(self,database):
        self.name = Name()
        self.name.set_type(NameType(NameType.BIRTH))
        surname="Doutreleau"
        firstname="Eric"
        self.name.set_first_name(firstname)
        surname_obj = Surname()
        surname_obj.set_surname(surname)
        self.name.add_surname(surname_obj)
        self.name.get_primary_surname().set_surname(surname)
        self.person = Person()
        self.person.set_primary_name(self.name)
        database.add_person(self.person,self.trans)
        database.commit_person(self.person, self.trans)
        return self.person

    def create_or_update_attrs(self,person,database,ID,MYHERLISTE):
        return

# ----------------------------------------------------------------------------
#
# Option Class
#
# ----------------------------------------------------------------------------

class ImportADNMatchOptions(MenuToolOptions):
    """ Set Attribute options  """
    def __init__(self, name, person_id=None, dbstate=None):
        MenuToolOptions.__init__(self, name, person_id, dbstate)
    
    def add_menu_options(self, menu):
        
        """ Add the options """
        category_name = _("Person")

        self.__pid = PersonOption(_("Center Person"))
        self.__pid.set_help(_("The Person who own the match files"))
        menu.add_option(category_name, "pid", self.__pid)
        category_name = _("MyHeritage")
        fname="liste"
        self.myher = BooleanOption("Ficher myheritage",False)
        menu.add_option(category_name, "myher", self.myher)
        self.myherlistefile = DestinationOption("Liste des correspondances",fname)
        self.myherlistefile.set_directory_entry(False)
        self.myherlistefile.set_extension('.csv')
        menu.add_option(category_name, "myherlistefile", self.myherlistefile)
        #self.myhersegmentfile = DestinationOption("Liste des segmentss")
        fname="segment"
        self.myhersegmentfile = DestinationOption("Liste des segments",fname)
        self.myhersegmentfile.set_directory_entry(False)
        self.myhersegmentfile.set_extension('.csv')
        menu.add_option(category_name, "myhersegmentfile", self.myhersegmentfile)
        category_name = _("Geneanet")
        fname="liste"
        self.geneanet = BooleanOption("Ficher Geneanet",False)
        menu.add_option(category_name, "geneanet", self.geneanet)
        self.geneanetlistefile = DestinationOption("Liste des correspondances",fname)
        self.geneanetlistefile.set_directory_entry(False)
        self.geneanetlistefile.set_extension('.csv')
        menu.add_option(category_name, "geneanetlistefile", self.geneanetlistefile)
        #self.geneanetsegmentfile = DestinationOption("Liste des segmentss")
        fname="segment"
        self.geneanetsegmentfile = DestinationOption("Liste des segments",fname)
        self.geneanetsegmentfile.set_directory_entry(False)
        self.geneanetsegmentfile.set_extension('.csv')
        menu.add_option(category_name, "geneanetsegmentfile", self.geneanetsegmentfile)
        

