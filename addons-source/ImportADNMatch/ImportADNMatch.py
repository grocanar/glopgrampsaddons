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
from gramps.gen.plug.menu import StringOption, PersonOption, \
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
        self.FTDNAMatchID="FTDNAMatchID"
        self.GeneanetSourceTitle="Match from Geneanet files"
        self.MyHeritageSourceTitle="Match from MyHeritage files"
        self.FTDNASourceTitle="Match from FTDNA files"
        self.GeneanetCitation=None
        self.MyHeritageCitation=None
        self.FTDNACitation=None
        self.db = self.dbstate.get_database()
        self.People=defaultdict(str)
        self.myheritagelistefile=str(self.get_opt("myherlistefile"))
        self.myheritagesegmentfile = str(self.get_opt("myhersegmentfile"))
        self.myher = self.get_opt("myher")
        self.myhermatchid = self.get_opt("myhermatchid")
        self.mincM = float(str(self.get_opt("mincM")))
        self.geneanetlistefile=str(self.get_opt("geneanetlistefile"))
        self.geneanetsegmentfile = str(self.get_opt("geneanetsegmentfile"))
        self.geneanet = self.get_opt("geneanet")
        self.FTDNAlistefile=str(self.get_opt("FTDNAlistefile"))
        self.FTDNAsegmentfile = str(self.get_opt("FTDNAsegmentfile"))
        self.FTDNA = self.get_opt("FTDNA")
        self.db.disable_signals()
        self.People=self.init_people(self.db)
        self.SourceGeneanet,self.SourceMyHeritage,self.SourceFTDNA=self.get_sources()
        self.pid = self.get_opt('pid')
        self.souche = self.db.get_person_from_gramps_id(self.pid)
        if self.souche is None:
            raise ReportError(_("Person %s is not in the Database") % pid)
        if self.myher:
            self.parsefile(filetype="MyHeritage")
        if self.geneanet:
            self.parsefile(filetype="Geneanet")
        if self.FTDNA:
            self.parsefile(filetype="FTDNA")
        self.db.enable_signals()
        self.db.enable_signals()
        self.db.request_rebuild()
        LOG.debug("ADMMATCH:" )

    def  get_sources(self):
        sourcesgeneanet=None
        sourcesmyheritage=None
        sourcesFTDNA=None
        try:
            with DbTxn(_("Citation Creation"), self.db, batch=True) as self.trans:
                for handle in self.db.get_source_handles():
                    source=self.db.get_source_from_handle(handle)
                    if source.get_title() == self.GeneanetSourceTitle:
                        sourcesgeneanet = source
                    elif source.get_title() == self.MyHeritageSourceTitle:
                        sourcesmyheritage = source
                    elif source.get_title() == self.FTDNASourceTitle:
                        sourcesFTDNA = source
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
                if not sourcesFTDNA:
                    source = Source()
                    source.set_title(self.FTDNASourceTitle)
                    self.db.add_source(source, self.trans)
                    self.db.commit_source(source, self.trans)
                    sourcesFTDNA = source
        except EnvironmentError as err:
            user.notify_error(_("%s could not be opened\n") % filename, str(err))
        return (sourcesgeneanet,sourcesmyheritage,sourcesFTDNA)


    def nbline(self,fichier):
        with open (fichier,'r') as mon_fichier:
            num=len(mon_fichier.readlines())
        return num

     
    def parsefile(self,filetype):
        MYLISTE=defaultdict(list)
        MYSEG=defaultdict(list)
        num  = 0
        if filetype == "MyHeritage":
            listefile = self.myheritagelistefile
            numlistefile=self.nbline(self.myheritagelistefile)
            segmentfile = self.myheritagesegmentfile
            numsegmentfile=self.nbline(self.myheritagesegmentfile)
            attribute=self.MyHeritageMatchID
            citationtype="MyHeritage"
            myherownid = self.myhermatchid
        elif filetype == "Geneanet":
            listefile = self.geneanetlistefile
            numlistefile=self.nbline(self.geneanetlistefile)
            segmentfile = self.geneanetsegmentfile
            numsegmentfile=self.nbline(self.geneanetsegmentfile)
            attribute=self.GeneanetMatchID
            citationtype="Geneanet"
        elif filetype == "FTDNA":
            listefile = self.FTDNAlistefile
            numlistefile=self.nbline(self.FTDNAlistefile)
            segmentfile = self.FTDNAsegmentfile
            numsegmentfile=self.nbline(self.FTDNAsegmentfile)
            attribute=self.FTDNAMatchID
            citationtype="FTDNA"
        try:
            numline=0
            with DbTxn(_("ADNMatch import"), self.db, batch=True) as self.trans:
                
                with open(listefile, newline='') as myfile:
                    message = "Read " + filetype + " List File"
                    progress = ProgressMeter(_( message ), can_cancel=False)
                    length = numlistefile
                    progress.set_pass(_(message),length)
                    cor = csv.reader(myfile)
                    for L in cor:
                        progress.step()
                        if num:
                            if L:
                                long=0.0
                                if filetype == "MyHeritage":
                                    replaceid = myherownid + "-"
                                    ID=str(L[0].replace(replaceid,''))
                                    lon=str(L[9])
                                    long=float(lon.replace(',','.'))
                                elif filetype == "Geneanet": 
                                    ID=L[0]
                                    long=float(L[9])
                                elif filetype == "FTDNA": 
                                    ID=L[0]
                                    long=float(L[6])
                                if long > self.mincM:
                                    if ID in self.People.keys():
                                        self.person=self.People[ID]
                                    else:
                                        self.person=self.create_people(self.db,ID,L,filetype)
                                        self.addpersonassoc(self.person,ID,L,filetype)
                                        self.People[ID]=self.person
                                    MYLISTE[ID]=L
                        else:
                            num = 1
                    progress.close()
                num  = 0
                with open(segmentfile, newline='') as myfile2:
                    seg = csv.reader(myfile2)
                    message = "Read " + filetype + " Segment File"
                    progress = ProgressMeter(_( message ), can_cancel=False)
                    length = numsegmentfile
                    progress.set_pass(_(message),length)
                    for L in seg:
                        progress.step()
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
                                elif filetype == "FTDNA":
                                    ID=str(L[0])
                                    chrom=str(L[1])
                                    deb=int(L[2])
                                    fin=int(L[3])
                                    longueur=float(L[4])
                                    numsnp=int(L[5])
                                MYSEG[ID].append((chrom,deb,fin,longueur,numsnp))
                        else:
                            num = 1
                    progress.close()
                message = "Importing " + filetype + " Data"
                progress = ProgressMeter(_( message ), can_cancel=False)
                length = len(MYLISTE.keys())
                progress.set_pass(_(message),length)
                for ID in MYLISTE.keys():
                    progress.step
                    self.person=self.People[ID]
                    self.create_or_update_attrs(self.person,self.db,ID,MYLISTE)
                    assoc=False
                    for ref in self.souche.get_person_ref_list():
                        person = self.db.get_person_from_handle(ref.ref)
                        if person == self.person:
                            result = ref.get_relation()
                            if result == "DNA":
                                assoc=True
                    if not assoc:
                        assocvalue="DNA"
                        texte="" 
                        for segment in MYSEG[ID]:
                            (chrom,deb,fin,longueur,numsnp)=segment
                            texto=",".join(str(e) for e in segment) 
                            if texte:
                                texte = texte + "\n" + texto
                            else:
                                texte = texto
                        self.add_assoc(self.person,assocvalue,ID,citationtype,texte)
                        self.db.commit_person(self.person,self.trans)
                progress.close()

        except EnvironmentError as err:
            user.notify_error(_("%s could not be opened\n") % filename, str(err))
        return

    def add_assoc(self,person,assocvalue,ID,citationtype,notevalue):

        handle=self.person.get_handle()
        handle2=self.souche.get_handle()
        personref = PersonRef()
        personref2 = PersonRef()
        personref.ref = handle
        personref2.ref = handle2
        personref.rel = assocvalue
        personref2.rel = assocvalue
        note=Note()
        note.set(notevalue)
        note.type.set(NoteType.ASSOCIATION)
        self.db.add_note(note, self.trans)
        self.db.commit_note(note, self.trans)
        handle=note.get_handle()
        personref.add_note(handle)
        personref2.add_note(handle)
        if citationtype == "Geneanet":
            GeneanetCitation=self.get_or_create_citation(citationtype=citationtype)
            handle=GeneanetCitation.get_handle()
        elif citationtype == "MyHeritage":
            MyHeritageCitation=self.get_or_create_citation(citationtype=citationtype)
            handle=MyHeritageCitation.get_handle()
        elif citationtype == "FTDNA":
            FTDNACitation=self.get_or_create_citation(citationtype=citationtype)
            handle=FTDNACitation.get_handle()
        personref.add_citation(handle)
        personref2.add_citation(handle)
        self.souche.add_person_ref(personref)
        self.person.add_person_ref(personref2)
        self.db.commit_person(self.souche,self.trans)
        self.db.commit_person(person,self.trans)

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
        elif citationtype == "FTDNA":
            if self.FTDNACitation:
                citation = self.FTDNACitation
            else:
                citation=Citation()
                citation.set_reference_handle(self.SourceFTDNA.get_handle())
                self.db.add_citation(citation, self.trans)
                self.db.commit_citation(citation, self.trans)
        return citation

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
     
    def addpersonassoc(self,person,ID,MYLISTE,filetype):
        if filetype == "Geneanet":
            citationtype="Geneanet"
            assocvalue="cM"
            texte=MYLISTE[9]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
            assocvalue=_("Number of Segment")
            texte=MYLISTE[10]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
            assocvalue=_("Longest Segment")
            texte=MYLISTE[11]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
        elif filetype == "MyHeritage":
            citationtype="MyHeritage"
            assocvalue="cM"
            texte=MYLISTE[9]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
            assocvalue=_("Number of Segment")
            texte=MYLISTE[11]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
            assocvalue=_("Longest Segment")
            texte=MYLISTE[12]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
        elif filetype == "FTDNA":
            citationtype="FTDNA"
            assocvalue="cM"
            texte=MYLISTE[6]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)
            assocvalue=_("Longest Segment")
            texte=MYLISTE[7]
            self.add_assoc(person,assocvalue,ID,citationtype,texte)

    def create_people(self,database,ID,MYLISTE,filetype):
        nom = MYLISTE[1]
        self.name = Name()
        self.name.set_type(NameType(NameType.BIRTH))
        person = Person()
        database.add_person(person,self.trans)
        if filetype == "Geneanet" or filetype == "MyHeritage":
            N=nom.split()
            surname=N[-1]
            N.pop()
            separator = ' '
            firstname=separator.join(N)
        elif filetype == "FTDNA":
            surname=MYLISTE[3]
            firstname = MYLISTE[1] + " " + MYLISTE[2]
        if filetype == "Geneanet":
            sexe=MYLISTE[2]
            if sexe == "Homme":
                person.set_gender(Person.MALE)
            elif sexe == "Femme":
                person.set_gender(Person.FEMALE)
            identifiant = MYLISTE[3]
            attr="GeneanetId"
            self.add_attribute(person,attr,identifiant)
            attr=self.GeneanetMatchID
            self.add_attribute(person,attr,ID)
        elif filetype == "MyHeritage":
            attr=self.MyHeritageMatchID
            self.add_attribute(person,attr,ID)
        elif filetype == "FTDNA":
            attr=self.FTDNAMatchID
            self.add_attribute(person,attr,ID)
        self.name.set_first_name(firstname)
        surname_obj = Surname()
        surname_obj.set_surname(surname)
        self.name.add_surname(surname_obj)
        self.name.get_primary_surname().set_surname(surname)
        person.set_primary_name(self.name)
        database.commit_person(person,self.trans)
        return person

    def add_attribute(self,person,attrtypevalue,value):
        attr = Attribute()
        attrtype=AttributeType()
        attrtype.set(attrtypevalue)
        attr.set_type(attrtype)
        attr.set_value(value)
        person.add_attribute(attr)

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
        self.mincM = StringOption(_("Minimum share segment"),"12.0")
        menu.add_option(category_name, "mincM", self.mincM)
        category_name = _("MyHeritage")
        fname="liste"
        self.myher = BooleanOption("Ficher myheritage",False)
        menu.add_option(category_name, "myher", self.myher)
        self.myherlistefile = DestinationOption(_("Matching List"),fname)
        self.myherlistefile.set_directory_entry(False)
        self.myherlistefile.set_extension('.csv')
        menu.add_option(category_name, "myherlistefile", self.myherlistefile)
        #self.myhersegmentfile = DestinationOption("Liste des segmentss")
        fname="segment"
        self.myhersegmentfile = DestinationOption(_("Segment List"),fname)
        self.myhersegmentfile.set_directory_entry(False)
        self.myhersegmentfile.set_extension('.csv')
        menu.add_option(category_name, "myhersegmentfile", self.myhersegmentfile)
        self.myhermatchid = StringOption(_("Unique Key for user"),"")
        menu.add_option(category_name, "myhermatchid", self.myhermatchid)
        category_name = _("Geneanet")
        self.geneanet = BooleanOption("Ficher Geneanet",False)
        menu.add_option(category_name, "geneanet", self.geneanet)
        fname="liste"
        self.geneanetlistefile = DestinationOption(_("Matching List"),fname)
        self.geneanetlistefile.set_directory_entry(False)
        self.geneanetlistefile.set_extension('.csv')
        menu.add_option(category_name, "geneanetlistefile", self.geneanetlistefile)
        #self.geneanetsegmentfile = DestinationOption("Liste des segmentss")
        fname="segment"
        self.geneanetsegmentfile = DestinationOption(_("Segment List"),fname)
        self.geneanetsegmentfile.set_directory_entry(False)
        self.geneanetsegmentfile.set_extension('.csv')
        menu.add_option(category_name, "geneanetsegmentfile", self.geneanetsegmentfile)
        self.FTDNA = BooleanOption("Ficher FamilytreeDNA",False)
        category_name = _("FTDNA")
        menu.add_option(category_name, "FTDNA", self.FTDNA)
        fname="liste"
        self.FTDNAlistefile = DestinationOption(_("Matching List"),fname)
        self.FTDNAlistefile.set_directory_entry(False)
        self.FTDNAlistefile.set_extension('.csv')
        menu.add_option(category_name, "FTDNAlistefile", self.FTDNAlistefile)
        fname="segment"
        self.FTDNAsegmentfile = DestinationOption(_("Segment List"),fname)
        self.FTDNAsegmentfile.set_directory_entry(False)
        self.FTDNAsegmentfile.set_extension('.csv')
        menu.add_option(category_name, "FTDNAsegmentfile", self.FTDNAsegmentfile)
        

