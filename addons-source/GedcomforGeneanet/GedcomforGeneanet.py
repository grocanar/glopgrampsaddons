#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2012  Bastien Jacquet
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
Extends GedcomWriter to include common non-compliant GEDCOM additions.
"""
#-------------------------------------------------------------------------
#
# Standard Python Modules
#
#-------------------------------------------------------------------------
import os
import time
import io
import re
from collections import defaultdict

#------------------------------------------------------------------------
#
# GTK modules
#
#------------------------------------------------------------------------
from gi.repository import Gtk

import gramps.plugins.lib.libgedcom as libgedcom
from gramps.plugins.export import exportgedcom
from gramps.gui.plug.export import WriterOptionBox
from gramps.gen.errors import DatabaseError
from gramps.gen.lib.date import Today
from gramps.gen.lib import (EventRoleType, FamilyRelType, Citation, EventType,Date, \
 PlaceType,Person, AttributeType, NameType, NoteType, ChildRefType)
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.utils.file import media_path_full, media_path, relative_path
from gramps.gen.utils.location import get_location_list
from gramps.gen.relationship import get_relationship_calculator
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.utils import ProgressMeter
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
import zipfile
import logging
import datetime
from gramps.version import VERSION
from gramps.gen.config import config
from gramps.gen.display.place import displayer as _pd
from gramps.gen.utils.location import get_main_location
from gramps.gen.utils.place import conv_lat_lon
from gramps.gen.display import place

LOG = logging.getLogger("gedcomforgeneanet")


MIME2GED = {
    "image/bmp"   : "bmp",
    "image/gif"   : "gif",
    "image/jpeg"  : "jpeg",
    "image/x-pcx" : "pcx",
    "image/tiff"  : "tiff",
    "audio/x-wav" : "wav"
    }

LANGUAGES = {
    'cs' : 'Czech', 'da' : 'Danish','nl' : 'Dutch',
    'en' : 'English','eo' : 'Esperanto', 'fi' : 'Finnish',
    'fr' : 'French', 'de' : 'German', 'hu' : 'Hungarian',
    'it' : 'Italian', 'lt' : 'Latvian', 'lv' : 'Lithuanian',
    'no' : 'Norwegian', 'po' : 'Polish', 'pt' : 'Portuguese',
    'ro' : 'Romanian', 'sk' : 'Slovak', 'es' : 'Spanish',
    'sv' : 'Swedish', 'ru' : 'Russian',
    }

QUALITY_MAP = {
    Citation.CONF_VERY_HIGH : "3",
    Citation.CONF_HIGH      : "2",
    Citation.CONF_NORMAL    : "1",
    Citation.CONF_LOW       : "0",
    Citation.CONF_VERY_LOW  : "0",
}
PEDIGREE_TYPES = {
    ChildRefType.BIRTH    : 'birth',
    ChildRefType.STEPCHILD: 'Step',
    ChildRefType.ADOPTED  : 'Adopted',
    ChildRefType.FOSTER   : 'Foster',
}

NEEDS_PARAMETER = set(
    ["CAST", "DSCR", "EDUC", "IDNO", "NATI", "NCHI",
     "NMR", "OCCU", "PROP", "RELI", "SSN", "TITL"])

GRAMPLET_CONFIG_NAME = "gedcomforgeneanet"
CONFIG = config.register_manager("gedcomforgeneanet")

CONFIG.register("preferences.include_witnesses", True)
CONFIG.register("preferences.include_media", False)
CONFIG.register("preferences.include_depot" , True)
CONFIG.register("preferences.extended_role" , False)
CONFIG.register("preferences.relativepath" , True)
CONFIG.register("preferences.quaynote", True)
CONFIG.register("preferences.zip", False)
CONFIG.register("preferences.namegen" , True)
CONFIG.register("preferences.nameus" , False)
CONFIG.register("preferences.anychar", True)
CONFIG.register("preferences.citattr", True)
CONFIG.register("preferences.inccensus", True)
CONFIG.register("preferences.urlshort", True)
CONFIG.register("preferences.parentsrc", True)
CONFIG.register("preferences.altname", True)
CONFIG.register("preferences.placegeneanet", True)
CONFIG.register("preferences.ancplacename", True)
CONFIG.register("preferences.extendedtitle", True)
CONFIG.load()

#-------------------------------------------------------------------------
#
# sort_handles_by_id
#
#-------------------------------------------------------------------------
def sort_handles_by_id(handle_list, handle_to_object):
    """
    Sort a list of handles by the Gramps ID.
    
    The function that returns the object from the handle needs to be supplied
    so that we get the right object.
    
    """
    sorted_list = []
    for handle in handle_list:
        obj = handle_to_object(handle)
        if obj:
            data = (obj.get_gramps_id(), handle)
            sorted_list.append(data)
    sorted_list.sort()
    return sorted_list

def event_has_subordinate_data(event, event_ref):
    """ determine if event is empty or not """
    if event and event_ref:
        return (event.get_description().strip() or
                not event.get_date_object().is_empty() or
                event.get_place_handle() or
                event.get_attribute_list() or
                event_ref.get_attribute_list() or
                event.get_note_list() or
                event.get_citation_list() or
                event.get_media_list())
    else:
        return False



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


class GedcomWriterforGeneanet(exportgedcom.GedcomWriter):
    """
    GedcomWriter forGeneanets.
    """
    def __init__(self, database, user, option_box=None):
        self.database = database
        super(GedcomWriterforGeneanet, self).__init__(database, user, option_box)
        self.GENEWEBNAME = defaultdict(str)
        self.GENEWEBURL = defaultdict(str)
        self.GENEWEBPARURL = defaultdict(str)
        if option_box:
            # Already parsed in GedcomWriter
            LOG.debug("dans OPTION %s")
            self.include_witnesses = option_box.include_witnesses
            self.include_media = option_box.include_media
            self.relativepath = option_box.relativepath
            self.include_depot = option_box.include_depot
            self.extended_role = option_box.extended_role
            self.quaynote = option_box.quaynote
            self.zip = option_box.zip
            self.namegen = option_box.namegen
            self.nameus = option_box.nameus
            self.anychar = option_box.anychar
            self.citattr = option_box.citattr
            self.inccensus = option_box.inccensus
            self.urlshort = option_box.urlshort
            self.parentsrc = option_box.parentsrc
            self.altname = option_box.altname
            self.placegeneanet = option_box.placegeneanet
            self.ancplacename = option_box.ancplacename
            self.extendedtitle = option_box.extendedtitle
            CONFIG.save()
        else:
            LOG.debug("pas dans OPTION %s")
            self.include_witnesses = 1
            self.include_media = 1
            self.include_depot = 1
            self.extended_role = 0
            self.relativepath = 0
            self.quaynote = 0
            self.zip = 0
            self.namegen = 0
            self.nameus = 1
            self.anychar = 1
            self.citattr = 1
            self.inccensus = 1
            self.urlshort = 1
            self.parentsrc = 1
            self.altname = 0
            self.placegeneanet = 0
            self.ancplacename = 0
            self.extendedtitle = 0
        self.zipfile = None

    def get_filtered_database(self, dbase, progress=None, preview=False):
        """
        dbase - the database
        progress - instance that has:
           .reset() method
           .set_total() method
           .update() method
           .progress_cnt integer representing N of total done
        """
        # Increment the progress count for each filter type chosen
        if self.private and progress:
            progress.progress_cnt += 1

        if self.restrict_num > 0 and progress:
            progress.progress_cnt += 1

        if (self.cfilter != None and (not self.cfilter.is_empty())) and progress:
            progress.progress_cnt += 1

        if (self.nfilter != None and (not self.nfilter.is_empty())) and progress:
            progress.progress_cnt += 1

        if self.reference_num > 0 and progress:
            progress.progress_cnt += 1
        if progress:
            progress.set_total(progress.progress_cnt)
            progress.progress_cnt = 0

        if self.preview_dbase:
            if progress:
                progress.progress_cnt += 5
            return self.preview_dbase

        self.proxy_dbase.clear()
        for proxy_name in self.get_proxy_names():
          #  LOG.debug("proxy %s" % proxy_name)
            dbase = self.apply_proxy(proxy_name, dbase, progress)
            if preview:
                self.proxy_dbase[proxy_name] = dbase
                self.preview_proxy_button[proxy_name].set_sensitive(1)
                people_count = len(dbase.get_person_handles())
                self.preview_proxy_button[proxy_name].set_label(
                    # translators: leave all/any {...} untranslated
                    ngettext("{number_of} Person",
                             "{number_of} People", people_count
                            ).format(number_of=people_count) )
        return dbase

    def _place(self, place, dateobj, level , ancplacename):
        """
        PLACE_STRUCTURE:=
            n PLAC <PLACE_NAME> {1:1}
            +1 FORM <PLACE_HIERARCHY> {0:1}
            +1 FONE <PLACE_PHONETIC_VARIATION> {0:M}  # not used
            +2 TYPE <PHONETIC_TYPE> {1:1}
            +1 ROMN <PLACE_ROMANIZED_VARIATION> {0:M} # not used
            +2 TYPE <ROMANIZED_TYPE> {1:1}
            +1 MAP {0:1}
            +2 LATI <PLACE_LATITUDE> {1:1}
            +2 LONG <PLACE_LONGITUDE> {1:1}
            +1 <<NOTE_STRUCTURE>> {0:M}
        """
        if place is None:
            return
       
        if self.placegeneanet:
            displayer=PlaceDisplayGeneanet()
            dateobj2=Today()
            place_name = displayer.display(self.dbase, place, dateobj2)
        else:
            place_name = _pd.display(self.dbase, place, dateobj)
        self._writeln(level, "PLAC", place_name.replace('\r', ' '), limit=120)
        longitude = place.get_longitude()
        latitude = place.get_latitude()
        if longitude and latitude:
            (latitude, longitude) = conv_lat_lon(latitude, longitude, "GEDCOM")
    
        if longitude and latitude:
            self._writeln(level + 1, "MAP")
            self._writeln(level + 2, 'LATI', latitude)
            self._writeln(level + 2, 'LONG', longitude)

        # The Gedcom standard shows that an optional address structure can
        # be written out in the event detail.
        # http://homepages.rootsweb.com/~pmcbride/gedcom/55gcch2.htm#EVENT_DETAIL
        location = get_main_location(self.dbase, place)
        street = location.get(PlaceType.STREET)
        locality = location.get(PlaceType.LOCALITY)
        city = location.get(PlaceType.CITY)
        state = location.get(PlaceType.STATE)
        country = location.get(PlaceType.COUNTRY)
        postal_code = place.get_code()

        if  street or locality or city or state or postal_code or country:
            self._writeln(level, "ADDR", street)
            if street:
                self._writeln(level + 1, 'ADR1', street)
            if locality:
                self._writeln(level + 1, 'ADR2', locality)
            if city:
                self._writeln(level + 1, 'CITY', city)
            if state:
                self._writeln(level + 1, 'STAE', state)
            if postal_code:
                self._writeln(level + 1, 'POST', postal_code)
            if country:
                self._writeln(level + 1, 'CTRY', country)
        if self.placegeneanet and self.ancplacename and ancplacename:
            anc_name = displayer.display(self.dbase, place, dateobj)
            if anc_name != place_name:
                place_name = _pd.display(self.dbase, place, dateobj)
                text = _("Place name at the time") + " : "  + place_name
                self._writeln(2, 'NOTE' , text )
        if self.altname and ancplacename:
            alt_names=self.display_alt_names(place)
            if len(alt_names) > 0:
                text = _("Alternate name for place") + ' \n'.join(alt_names)
                self._writeln(2, 'NOTE' , text )
        else:
            LOG.debug(" PAS PLACENOTE")
        if ancplacename:
            self._note_references(place.get_note_list(), level + 1)

    def display_alt_names(self, place):
        """
    Display alternative names for the place.
    """
        alt_names = ["%s (%s)" % (name.get_value(), name.get_language())
                 if name.get_language() else name.get_value()
                 for name in place.get_alternative_names()]
        return alt_names



    def _names(self, person):
        """
        Write the names associated with the person to the current level.

        Since nicknames in version < 3.3 are separate from the name structure,
        we search the attribute list to see if we can find a nickname.
        Because we do not know the mappings, we just take the first nickname
        we find, and add it to the primary name.
        If a nickname is present in the name structure, it has precedence

        """
        nicknames = [attr.get_value() for attr in person.get_attribute_list()
                     if int(attr.get_type()) == AttributeType.NICKNAME]
        if len(nicknames) > 0:
            nickname = nicknames[0]
        else:
            nickname = ""

        self._person_name(person.get_primary_name(), nickname)
        self.get_geneweb_name(person,person.get_primary_name())
            
        for name in person.get_alternate_names():
            self._person_altname(name, "")

    def _writeln(self, level, token, textlines="", limit=72):
        """
        Write a line of text to the output file in the form of:

            LEVEL TOKEN text

        If the line contains newlines, it is broken into multiple lines using
        the CONT token. If any line is greater than the limit, it will broken
        into multiple lines using CONC.

        """
        assert token
        if textlines:
            # break the line into multiple lines if a newline is found
            textlines = textlines.replace('\n\r', '\n')
            textlines = textlines.replace('\r', '\n')
          #  LOG.debug("anychar %d" % self.anychar)
            if self.anychar:
                if not textlines.startswith('@'):  # avoid xrefs
                    textlines = textlines.replace('@', '@@')
            textlist = textlines.split('\n')
            token_level = level
            for text in textlist:
                # make it unicode so that breakup below does the right thin.
                text = str(text)
                if limit:
                    prefix = "\n%d CONC " % (level + 1)
                    txt = prefix.join(self.breakup(text, limit))
                else:
                    txt = text
                self.gedcom_file.write("%d %s %s\n" %
                                       (token_level, token, txt))
                token_level = level + 1
                token = "CONT"
        else:
            self.gedcom_file.write("%d %s\n" % (level, token))

    def breakup(self,txt, limit):
        """
        Break a line of text into a list of strings that conform to the
        maximum length specified, while breaking words in the middle of a word
        to avoid issues with spaces.
        """
        if limit < 1:
            raise ValueError("breakup: unexpected limit: %r" % limit)
        data = []
        while len(txt) > limit:
            # look for non-space pair to break between
            # do not break within a UTF-8 byte sequence, i. e. first char >127
            idx = limit
            while (idx > 0 and (txt[idx - 1].isspace() or txt[idx].isspace() or
                            ord(txt[idx - 1]) > 127)):
                idx -= 1
            if idx == 0:
                #no words to break on, just break at limit anyway
                idx = limit
            data.append(txt[:idx])
            txt = txt[idx:]
        if len(txt) > 0:
            data.append(txt)
        return data
 
    def get_usuel_first_name(self,name):
        """
        Returns a GEDCOM-formatted usuel name.
        """

     #   LOG.debug("on rentre dans usged")
        call = name.get_call_name()
        if call:
     #       LOG.debug("on a trouve un call dans GEDCOM")
            firstname = ""
            listeprenom = name.first_name.split()
            for pren in listeprenom:
                if pren == call:
                    pren = '"' + pren + '"'
                if firstname:
                    firstname = firstname + " " + pren
                else:
                    firstname = pren
        else:
            firstname = name.first_name.strip()
        return firstname

    
    def _person_name(self, name, attr_nick):
        """
        n NAME <NAME_PERSONAL> {1:1}
        +1 NPFX <NAME_PIECE_PREFIX> {0:1}
        +1 GIVN <NAME_PIECE_GIVEN> {0:1}
        +1 NICK <NAME_PIECE_NICKNAME> {0:1}
        +1 SPFX <NAME_PIECE_SURNAME_PREFIX {0:1}
        +1 SURN <NAME_PIECE_SURNAME> {0:1}
        +1 NSFX <NAME_PIECE_SUFFIX> {0:1}
        +1 <<SOURCE_CITATION>> {0:M}
        +1 <<NOTE_STRUCTURE>> {0:M}
        """
        gedcom_name = self.get_gedcom_name(name)

        if self.nameus:
            firstname = self.get_usuel_first_name(name)
        else:
            firstname = name.get_first_name().strip()
        surns = []
        surprefs = []
        for surn in name.get_surname_list():
            surns.append(surn.get_surname().replace('/', '?'))
            if surn.get_connector():
                #we store connector with the surname
                surns[-1] = surns[-1] + ' ' + surn.get_connector()
            surprefs.append(surn.get_prefix().replace('/', '?'))
        surname = ', '.join(surns)
        surprefix = ', '.join(surprefs)
        suffix = name.get_suffix()
        title = name.get_title()
        nick = name.get_nick_name()
        if nick.strip() == '':
            nick = attr_nick

        self._writeln(1, 'NAME', gedcom_name)
        if int(name.get_type()) == NameType.BIRTH:
            pass
        elif int(name.get_type()) == NameType.MARRIED:
            self._writeln(2, 'TYPE', 'married')
        elif int(name.get_type()) == NameType.AKA:
            self._writeln(2, 'TYPE', 'aka')
        else:
            self._writeln(2, 'TYPE', name.get_type().xml_str())

        if firstname:
            self._writeln(2, 'GIVN', firstname)
        if surprefix:
            self._writeln(2, 'SPFX', surprefix)
        if surname:
            self._writeln(2, 'SURN', surname)
        if name.get_suffix():
            self._writeln(2, 'NSFX', suffix)
        if name.get_title():
            self._writeln(2, 'NPFX', title)
        if nick:
            self._writeln(2, 'NICK', nick)

        self._source_references(name.get_citation_list(), 2)
        self._note_references(name.get_note_list(), 2)
    
    def _person_altname(self, name, attr_nick):
        """
        n NAME <NAME_PERSONAL> {1:1}
        +1 NPFX <NAME_PIECE_PREFIX> {0:1}
        +1 GIVN <NAME_PIECE_GIVEN> {0:1}
        +1 NICK <NAME_PIECE_NICKNAME> {0:1}
        +1 SPFX <NAME_PIECE_SURNAME_PREFIX {0:1}
        +1 SURN <NAME_PIECE_SURNAME> {0:1}
        +1 NSFX <NAME_PIECE_SUFFIX> {0:1}
        +1 <<SOURCE_CITATION>> {0:M}
        +1 <<NOTE_STRUCTURE>> {0:M}
        """
        if self.namegen:
            gedcom_name = self.get_genegedcom_name(name)
        else:
            gedcom_name = self.get_gedcom_name(name)

        firstname = name.get_first_name().strip()
        surns = []
        surprefs = []
        for surn in name.get_surname_list():
            surns.append(surn.get_surname().replace('/', '?'))
            if surn.get_connector():
                #we store connector with the surname
                surns[-1] = surns[-1] + ' ' + surn.get_connector()
            surprefs.append(surn.get_prefix().replace('/', '?'))
        surname = ', '.join(surns)
        surprefix = ', '.join(surprefs)
        suffix = name.get_suffix()
        title = name.get_title()
        nick = name.get_nick_name()
        if nick.strip() == '':
            nick = attr_nick

        self._writeln(1, 'NAME', gedcom_name)
        if int(name.get_type()) == NameType.BIRTH:
            pass
        elif int(name.get_type()) == NameType.MARRIED:
            self._writeln(2, 'TYPE', 'married')
        elif int(name.get_type()) == NameType.AKA:
            self._writeln(2, 'TYPE', 'aka')
        else:
            self._writeln(2, 'TYPE', name.get_type().xml_str())

        if firstname:
            self._writeln(2, 'GIVN', firstname)
        if surprefix:
            self._writeln(2, 'SPFX', surprefix)
        if surname:
            self._writeln(2, 'SURN', surname)
        if name.get_suffix():
            self._writeln(2, 'NSFX', suffix)
        if name.get_title():
            self._writeln(2, 'NPFX', title)
        if nick:
            self._writeln(2, 'NICK', nick)

        self._source_references(name.get_citation_list(), 2)
        self._note_references(name.get_note_list(), 2)


    def get_genegedcom_name(self,name):
        """
        Returns a GEDCOM-formatted name.
        """
        firstname = name.first_name.strip()
        surname = name.get_surname().replace('/', '?')
        suffix = name.suffix
        if suffix == "":
            return '%s %s' % (firstname, surname)
        return '%s %s %s' % (firstname, surname, suffix)

    def get_gedcom_name(self,name):
        """
        Returns a GEDCOM-formatted name.
        """
        if self.nameus:
           firstname = self.get_usuel_first_name(name)
        else:
           firstname = name.first_name.strip()
        surname = name.get_surname().replace('/', '?')
        suffix = name.suffix
        if suffix == "":
            return '%s /%s/' % (firstname, surname)
        return '%s /%s/ %s' % (firstname, surname, suffix)

    def get_geneweb_name(self,person,name):
        """
        Returns a GEDCOM-formatted name.
        """
        num  = 0
        NotTrouve = True
        if self.nameus:
           firstname = self.get_usuel_first_name(name)
        else:
           firstname = name.first_name.strip()
        firstnam = self.rem_spaces(firstname)
        firstnameurl = self.plus_spaces(firstname)
        surname = self.rem_spaces(name . get_surname())
        surnameurl = self.plus_spaces(name . get_surname())
        suffix = name.get_suffix()
        handle = person.get_handle()
        urlbase="https://gw.geneanet.org/glopglop?lang=fr"
        urlparbase="https://gw.geneanet.org/glopglop?lang=fr&pz=eric+christophe&nz=doutreleau&p=eric+christophe&n=doutreleau&m=A&t=D&"
        if suffix == "":
            while NotTrouve:
                genewebname = '%s %s.%d' % (surname, firstnam , num) 
                geneweburl = urlbase + '&p=%s&n=%s&oc=%d' % (firstnameurl , surnameurl ,num) 
                genewebparurl = urlparbase + 'p1=%s&n1=%s&oc1=%d' % (firstnameurl , surnameurl ,num) + "&l=20"
                if self.GENEWEBNAME[genewebname]:
                    num = num + 1
                else:
                    LOG.debug(genewebname)
                    LOG.debug(firstname," ",name . get_surname())
                    NotTrouve = False
                    self.GENEWEBNAME[genewebname] = 1
                    self.GENEWEBURL[handle] = geneweburl
                    self.GENEWEBPARURL[handle] = genewebparurl
            return genewebname

        while NotTrouve:
            genewebname = '%s %s_%s.%d' % (surname, firstnam , suffix , num) 
            geneweburl = urlbase + '&p=%s+%s&n=%s&oc=%d' % (firstnameurl , suffix , surnameurl ,num) 
            genewebparurl = urlparbase + 'p1=%s+%s&n1=%s&oc1=%d' % (firstnameurl ,  suffix, surnameurl ,num) + "&l=20"
            if self.GENEWEBNAME[genewebname]:
                num = num + 1
            else:
                LOG.debug(genewebname)
                LOG.debug(firstname," ",name . get_surname())
                self.GENEWEBNAME[genewebname] = 1
                self.GENEWEBURL[handle] = geneweburl
                self.GENEWEBPARURL[handle] = genewebparurl
                NotTrouve = False
        return genewebname

    def rem_spaces(self,str):
        str = re.sub(r'^"','_"',str)
        str = re.sub(r'^\(','_(',str)
        char_remov = [ 'à', 'â' , 'ä']
        for char in char_remov:
            str = str.replace(char, "a")
        char_remov = [ 'é' , 'è' , 'ê' , 'ë' ]
        for char in char_remov:
            str = str.replace(char, "e")
        char_remov = [ 'î' , 'ï' ]
        for char in char_remov:
            str = str.replace(char, "i")
        char_remov = [ 'ô' , 'ö' ]
        for char in char_remov:
            str = str.replace(char, "o")
        char_remov = [ 'ù' , 'û' , 'ü' ]
        for char in char_remov:
            str = str.replace(char, "u")
        char_remov = [ 'ÿ' ]
        for char in char_remov:
            str = str.replace(char, "y")
        char_remov = [ 'ç' ]
        for char in char_remov:
            str = str.replace(char, "c")
        str = str.replace('-','_')
        str = str.replace("'",'')
        return str.replace(' ','_')

    def plus_spaces(self,str):
        str = str.replace(' ','+')
        return str.replace('-','+')

    def _photo(self, photo, level):
        """
        Overloaded media-handling method to skip over media
        if not included.
        """
#        LOG.debug("deb photo %d" % self.relativepath)
        if self.include_media:
            photo_obj_id = photo.get_reference_handle()
            photo_obj = self.dbase.get_media_from_handle(photo_obj_id)
            if photo_obj:
                mime = photo_obj.get_mime_type()
                form = MIME2GED.get(mime, mime)
                if self.relativepath:
                    fullpath = media_path_full(self.dbase, photo_obj.get_path())
                    if not os.path.isfile(fullpath):
                        return
                    base = media_path(self.dbase)
                    path = relative_path(fullpath,base)
                else:
                    path = media_path_full(self.dbase, photo_obj.get_path())
                    if not os.path.isfile(path):
                        return
                self._writeln(level, 'OBJE')
                if form:
                    self._writeln(level+1, 'FORM', form)
                self._writeln(level+1, 'TITL', photo_obj.get_description())
                self._writeln(level+1, 'FILE', path, limit=255)
                self._note_references(photo_obj.get_note_list(), level+1)
                if self.zip:
                    self._packzip(path)
 
 
    def _packzip(self, path ):
        if path:
            self.zipfile.write(path)

    def _family_events(self, family):
        for event_ref in family.get_event_ref_list():
            event = self.dbase.get_event_from_handle(event_ref.ref)
            if event is None:
                continue
            self._process_family_event(event, event_ref)
            self._dump_event_stats(event, event_ref,True)

        level = 1
#        self._writeln(level,"TEST")
        if (int(family.get_relationship()) == FamilyRelType.UNMARRIED or int(family.get_relationship()) == FamilyRelType.UNKNOWN):
            self._writeln(level, "_UST", "COHABITATION")
    
# Workaround pour geneanet upload
#    def _url_list(self, obj, level):
#        if self.include_persurl:
#            for url in obj.get_url_list():
#                self._writeln(level, 'OBJE')
#                self._writeln(level+1, 'FORM', 'URL')
#                if url.get_description():
#                    self._writeln(level+1, 'TITL', url.get_description())
#                if url.get_path():
#                    self._writeln(level+1, 'FILE', url.get_path(), limit=255)
#        else:
#            return

    

    def _child_families(self, person):
        """
        Write the Gramps ID as the XREF for each family in which the person
        is listed as a child.
        """

        # get the list of familes from the handle list
        family_list = [self.dbase.get_family_from_handle(hndl)
                       for hndl in person.get_parent_family_handle_list()]

        for family in family_list:
            if family:
                self._writeln(1, 'FAMC', '@%s@' % family.get_gramps_id())
                for child in family.get_child_ref_list():
                    if child.get_reference_handle() == person.get_handle():
                        if child.frel == ChildRefType.ADOPTED and \
                                child.mrel == ChildRefType.ADOPTED:
                            self._writeln(2, 'PEDI adopted')
                        elif child.frel == ChildRefType.BIRTH and \
                                child.mrel == ChildRefType.BIRTH:
                            self._writeln(2, 'PEDI birth')
                        elif child.frel == ChildRefType.STEPCHILD and \
                                child.mrel == ChildRefType.STEPCHILD:
                            self._writeln(2, 'PEDI stepchild')
                        elif child.frel == ChildRefType.FOSTER and \
                                child.mrel == ChildRefType.FOSTER:
                            self._writeln(2, 'PEDI foster')
                        elif child.frel == child.mrel:
                            self._writeln(2, 'PEDI %s' % child.frel.xml_str())
                        else:
                            self._writeln(
                                2, '_FREL %s' % PEDIGREE_TYPES.get(
                                    child.frel.value, child.frel.xml_str()))
                            self._writeln(
                                2, '_MREL %s' % PEDIGREE_TYPES.get(
                                    child.mrel.value, child.mrel.xml_str()))
                        if self.parentsrc:
                            result = "<BR>"
                            for citation_hdl in child.get_citation_list():
                                result = "<B>" + _("Source Filiation") + " :</B><BR> "
                                citation = self.dbase.get_citation_from_handle(citation_hdl)
                                src_handle = citation.get_reference_handle()
                                if src_handle is None:
                                    continue
                                src = self.dbase.get_source_from_handle(src_handle)
                                if src is None:
                                    continue
                                if src.get_title():
                                    result = result + "<I>" + _("Title") + "</I> " + src.get_title() + "<BR>"
                                if src.get_author():
                                    result = result + "<I>" + _("Author") + "</I> " + src.get_author() + "<BR>"
                                if src.get_publication_info():
                                    result = result + "<I>" + _("Publication Info") + "</I> " + src.get_publication_info() + "<BR>"
                                if citation.get_page() != "":
                                    result = result + "<I>" + _("Page") + "</I> : " + citation.get_page()[0:248] 
                                result = result + "<BR>"
                                self._writeln(1, 'NOTE %s' % result)



    def _process_family_event(self, event, event_ref):
        """
        Write the witnesses associated with the family event.
        based on http://www.geneanet.org/forum/index.php?topic=432352.0&lang=fr
        """
        super(GedcomWriterforGeneanet, self)._process_family_event(event,\
                                                                 event_ref)

        if self.include_witnesses:
            for (objclass, handle) in self.dbase.find_backlink_handles(
                event.handle, ['Person']):
                person = self.dbase.get_person_from_handle(handle)
                if person:
                    for ref in person.get_event_ref_list():
                        if ref.ref == event.handle:
                            role=int(ref.get_role())
                            if role in [EventRoleType.CELEBRANT,  EventRoleType.CLERGY, EventRoleType.AIDE, EventRoleType.FAMILY, EventRoleType.CUSTOM]:
                                level = 2

                                rol = role + 1
                                if str(ref.role) == "Mentionnée" or str(ref.role) == "Mentionné":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Mentioned")
                                elif str(ref.role) == "Présence":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Attending")
                                elif str(ref.role) == "Parrain":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "GodFather")
                                elif str(ref.role) == "Marraine":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "GodMother")
                                else:
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Other")
                                    if self.extended_role:
                                        if role:
                                            self._writeln(level+1, "NOTE", '\xA0%s' % EventRoleType._DATAMAP[rol][1])
                                        else:
                                            self._writeln(level+1, "NOTE", '\xA0%s' % str(ref.role))
                                self.get_geneweb_name(person,person.get_primary_name())
                                self._note_references(ref.get_note_list(), level+1)
                            elif role in [EventRoleType.INFORMANT]:
                                level = 2
                                rol = role + 1
                                self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                self._writeln(level+1, "TYPE", "INDI")
                                self._writeln(level+1, "RELA", "Informant")
                                self.get_geneweb_name(person,person.get_primary_name())
                            elif role in [EventRoleType.WITNESS]:
                                level = 2
                                rol = role + 1
                                self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                self._writeln(level+1, "TYPE", "INDI")
                                self._writeln(level+1, "RELA", "Witness")
                                self.get_geneweb_name(person,person.get_primary_name())


    def _sources(self):
        """
        Write out the list of sources, sorting by Gramps ID.
        """
        self.reset(_("Writing sources"))
        self.progress_cnt += 1
        self.update(self.progress_cnt)
        sorted_list = sort_handles_by_id(self.dbase.get_source_handles(),
                                         self.dbase.get_source_from_handle)

        for (source_id, handle) in sorted_list:
            source = self.dbase.get_source_from_handle(handle)
            if source is None: continue
            self._writeln(0, '@%s@' % source_id, 'SOUR')
            if source.get_title():
                self._writeln(1, 'TITL', source.get_title())

            if source.get_author():
                self._writeln(1, "AUTH", source.get_author())

            if source.get_publication_info():
                self._writeln(1, "PUBL", source.get_publication_info())

            if source.get_abbreviation():
                self._writeln(1, 'ABBR', source.get_abbreviation())

            for srcattr in source.get_attribute_list():
                level = 1
                if self.urlshort:
                    url_pattern = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
                    link = re.match(url_pattern, srcattr.value)
                    if link:
                        url=link.group()
                        text = "<A HREF=\"" + str(url) + "\" title=\"" + str(url) + "\">" + str(srcattr.type) + "</A>"
                        self._writeln(level + 1,"DATA" , text)
                    else:
                        self._writeln(level + 1,"DATA", str(srcattr.type))
                        self._writeln(level + 2,"TEXT", srcattr.value)

                else:
                    self._writeln(level + 1,"DATA", str(srcattr.type))
                    self._writeln(level + 2, "TEXT", srcattr.value)
            self._photos(source.get_media_list(), 1)

            if self.include_depot:
                for reporef in source.get_reporef_list():
                    self._reporef(reporef, 1)

            self._note_references(source.get_note_list(), 1)
            self._change(source.get_change_time(), 1)

 
    def _person_event_ref(self, key, event_ref):
        """
        Write the witnesses associated with the birth and death event. 
        based on http://www.geneanet.org/forum/index.php?topic=432352.0&lang=fr
        """
        if event_ref:
            event = self.dbase.get_event_from_handle(event_ref.ref)
            if event_has_subordinate_data(event, event_ref):
                self._writeln(1, key)
            else:
                self._writeln(1, key, 'Y')
            if event.get_description().strip() != "":
                self._writeln(2, 'TYPE', event.get_description())
            self._dump_event_stats(event, event_ref,True)

        if self.include_witnesses and event_ref:
            role = int(event_ref.get_role())
            if role != EventRoleType.PRIMARY:
                return
            event = self.dbase.get_event_from_handle(event_ref.ref)
            etype = int(event.get_type())
            devel = 2
            for (objclass, handle) in self.dbase.find_backlink_handles(
                event.handle, ['Person']):
                person = self.dbase.get_person_from_handle(handle)
                if person:
                    for ref in person.get_event_ref_list():
                        devel = 2
                        if (ref.ref == event.handle): 
                            role = int(ref.get_role())
                            if int(ref.get_role()) in [EventRoleType.CELEBRANT, EventRoleType.AIDE ,EventRoleType.CLERGY, EventRoleType.AIDE,EventRoleType.FAMILY,EventRoleType.CUSTOM]:
                                level = 2
                                rol = role + 1
                                if str(ref.role) == "Mentionnée" or str(ref.role) == "Mentionné":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Mentioned")
                                elif str(ref.role) == "Présence":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Attending")
                                elif str(ref.role) == "Parrain":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "GodFather")
                                elif str(ref.role) == "Marraine":
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "GodMother")
                                else:
                                    self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Other")
                                    if self.extended_role:
                                        if role:
                                            self._writeln(level+1, "NOTE", '\xA0%s' % EventRoleType._DATAMAP[rol][1])
                                        else:
                                            self._writeln(level+1, "NOTE", '\xA0%s' % str(ref.role))
                                self._note_references(ref.get_note_list(), level+1)
                            elif role in [EventRoleType.INFORMANT]:
                                level = 2
                                rol = role + 1
                                self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                self._writeln(level+1, "TYPE", "INDI")
                                self._writeln(level+1, "RELA", "Informant")
                            elif role in [EventRoleType.WITNESS]:
                                level = 2
                                rol = role + 1
                                self._writeln(level, "ASSO", "@%s@" % person.get_gramps_id())
                                self._writeln(level+1, "TYPE", "INDI")
                                self._writeln(level+1, "RELA", "Witness")

    def _remaining_events(self, person):
        """
        Output all events associated with the person that are not BIRTH or
        DEATH events.

        Because all we have are event references, we have to
        extract the real event to discover the event type.

        """
        global adop_written
        # adop_written is only shared between this function and
        # _process_person_event. This is rather ugly code, but it is difficult
        # to support an Adoption event without an Adopted relationship from the
        # parent(s), an Adopted relationship from the parent(s) without an
        # event, and both an event and a relationship. All these need to be
        # supported without duplicating the output of the ADOP GEDCOM tag. See
        # bug report 2370.
        adop_written = False
        for event_ref in person.get_event_ref_list():
            event = self.dbase.get_event_from_handle(event_ref.ref)
            if not event:
                continue
            self._process_person_event(person, event, event_ref)
        if not adop_written:
            self._adoption_records(person, adop_written)

    def _process_person_event(self, person ,event ,event_ref):
        """
        Write the witnesses associated with other personnal event.
        """
        global adop_written
        etype = int(event.get_type())
        # if the event is a birth or death, skip it.
        if etype in (EventType.BIRTH, EventType.DEATH, EventType.MARRIAGE):
            return
        role = int(event_ref.get_role())
        if role != EventRoleType.PRIMARY:
            return
        devel = 2
        val = libgedcom.PERSONALCONSTANTEVENTS.get(etype, "").strip()
        if val and val.strip() and not val == "ADOP" :
            if val in NEEDS_PARAMETER:
                if event.get_description().strip():
                    self._writeln(1, val, event.get_description())
                else:
                    self._writeln(1, val)
            else:
                if event_has_subordinate_data(event, event_ref):
                    self._writeln(1, val)
                else:
                    self._writeln(1, val, 'Y')
                if event.get_description().strip():
                    self._writeln(2, 'TYPE', event.get_description())
        else:
            descr = event.get_description()
            if descr:
                self._writeln(1, 'EVEN', descr)
            else:
                self._writeln(1, 'EVEN')
            if val.strip() and not val == "ADOP":
                self._writeln(2, 'TYPE', val)
            else:
                self._writeln(2, 'TYPE', _(event.get_type().xml_str()))

        etype = int(event.get_type())
        if etype == EventType.NOB_TITLE:
            self._dump_event_stats(event, event_ref,False)
        else:
            self._dump_event_stats(event, event_ref,True)
        if etype == EventType.ADOPT and not adop_written:
            adop_written = True
            self._adoption_records(person, adop_written)

        if self.include_witnesses:
            if etype in (EventType.BAPTISM, EventType.CHRISTEN):
                for (objclass, handle) in self.dbase.find_backlink_handles(
                    event.handle, ['Person']):
                    person2 = self.dbase.get_person_from_handle(handle)
                    if person2 and person2 != person:
                        for ref in person2.get_event_ref_list():
                            if (ref.ref == event.handle):
                                if (int(ref.get_role()) == EventRoleType.CUSTOM):
                                    level = 1
                                    if str(ref.role) == "Mentionnée" or str(ref.role) == "Mentionné":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "Mentioned")
                                    elif str(ref.role) == "Présence":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "Attending")
                                    elif str(ref.role) == "Parrain":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "GodFather")
                                    elif str(ref.role) == "Marraine":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "GodMother")
                                    else:
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        if person2.get_gender() == Person.MALE:
                                            self._writeln(level+1, "RELA", "Godfather")
                                        elif person2.get_gender() == Person.FEMALE:
                                            self._writeln(level+1, "RELA", "Godmother")
                                        else:
                                            self._writeln(level+1, "RELA", "Unknown")

                                    self._note_references(ref.get_note_list(), level+1)
                                else:
                                    level = 2
                                    self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Witness")
                                    self._note_references(ref.get_note_list(), level+1)
            else:
                devel = 2
                for (objclass, handle) in self.dbase.find_backlink_handles(
                    event.handle, ['Person']):
                    person2 = self.dbase.get_person_from_handle(handle)
                    if person2 and person != person2:
                        for ref in person2.get_event_ref_list():
                            if (ref.ref == event.handle):  
                                role=int(ref.get_role())
                                if int(ref.get_role()) in [EventRoleType.CELEBRANT, EventRoleType.AIDE, EventRoleType.CLERGY, EventRoleType.AIDE, EventRoleType.FAMILY, EventRoleType.CUSTOM]:
                                    level = 2
#pylint: disable=maybe-no-member
                                    rol = role + 1
                                    if str(ref.role) == "Mentionnée" or str(ref.role) == "Mentionné":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "Mentioned")
                                    elif str(ref.role) == "Présence":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "Attending")
                                    elif str(ref.role) == "Parrain":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "GodFather")
                                    elif str(ref.role) == "Marraine":
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "GodMother")
                                    else:
                                        self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                        self._writeln(level+1, "TYPE", "INDI")
                                        self._writeln(level+1, "RELA", "Other")
                                        if self.extended_role:
                                            if role:
                                                self._writeln(level+1, "NOTE", '\xA0%s' % EventRoleType._DATAMAP[rol][1])
                                            else:
                                                self._writeln(level+1, "NOTE", '\xA0%s' % str(ref.role))
                                    self._note_references(ref.get_note_list(), level+1)
                                elif role in [EventRoleType.INFORMANT]:
                                    level = 2
                                    rol = role + 1
                                    self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Informant")
                                elif role in [EventRoleType.WITNESS]:
                                    level = 2
                                    rol = role + 1
                                    self._writeln(level, "ASSO", "@%s@" % person2.get_gramps_id())
                                    self._writeln(level+1, "TYPE", "INDI")
                                    self._writeln(level+1, "RELA", "Witness")

        if val == "TITL" and self.extendedtitle:
            descr = event.get_description()
            if descr:
                self._writeln(1, 'EVEN', descr)
            else:
                self._writeln(1, 'EVEN')
            self._writeln(2, 'TYPE', 'Titre')
            self._dump_event_stats(event, event_ref,True)

    def _dump_event_stats(self, event, event_ref,ancplace):
        """
        Write the event details for the event, using the event and event
        reference information.

        GEDCOM does not make a distinction between the two.

        """
        dateobj = event.get_date_object()
        self._date(2, dateobj)
        if self._datewritten:
            # write out TIME if present
            times = [attr.get_value() for attr in event.get_attribute_list()
                     if int(attr.get_type()) == AttributeType.TIME]
            # Not legal, but inserted by PhpGedView
            if len(times) > 0:
                self._writeln(3, 'TIME', times[0])

        place = None

        if event.get_place_handle():
            place = self.dbase.get_place_from_handle(event.get_place_handle())
            self._place(place, dateobj, 2, ancplace)

        for attr in event.get_attribute_list():
            attr_type = attr.get_type()
            if attr_type == AttributeType.CAUSE:
                self._writeln(2, 'CAUS', attr.get_value())
            elif attr_type == AttributeType.AGENCY:
                self._writeln(2, 'AGNC', attr.get_value())
            elif attr_type == _("Phone"):
                self._writeln(2, 'PHON', attr.get_value())
            elif attr_type == _("FAX"):
                self._writeln(2, 'FAX', attr.get_value())
            elif attr_type == _("EMAIL"):
                self._writeln(2, 'EMAIL', attr.get_value())
            elif attr_type == _("WWW"):
                self._writeln(2, 'WWW', attr.get_value())
            elif attr_type == AttributeType.TIME:
                toto = 0
            else:
                self._writeln(2, 'NOTE', str(attr_type) + ": " + attr.get_value())

        resultstring = ""
        etype = int(event.get_type())
        if etype == EventType.CENSUS:
            if self.inccensus:
                attrs = event_ref.get_attribute_list()
                if len(attrs):
                    self._writeln(2, 'NOTE' )
                    for attr in attrs:
                        typ = str(attr.get_type())
                        val = str(attr.get_value())
                        LOG.debug("TYPE %s VAL %s" % ( typ , val))
                        text = typ + " : " + val
                        self._writeln(3,'CONT', text )
        else:
            for attr in event_ref.get_attribute_list():
                attr_type = attr.get_type()
                if attr_type == AttributeType.AGE:
                    self._writeln(2, 'AGE', attr.get_value())
                elif attr_type == AttributeType.FATHER_AGE:
                    self._writeln(2, 'HUSB')
                    self._writeln(3, 'AGE', attr.get_value())
                elif attr_type == AttributeType.MOTHER_AGE:
                    self._writeln(2, 'WIFE')
                    self._writeln(3, 'AGE', attr.get_value())
                else:  
                    self._writeln(2, 'NOTE' )
                    typ = str(attr.get_type())
                    val = str(attr.get_value())
                    text = typ + " : " + val
                    self._writeln(3,'DATA', text )
            
        if ancplace:
            self._note_references(event.get_note_list(), 2)
            self._source_references(event.get_citation_list(), 2)

            self._photos(event.get_media_list(), 2)
            if place:
                self._photos(place.get_media_list(), 2)
    

    def _attributes(self, person):
        """
        Write out the attributes to the GEDCOM file.
        
        Since we have already looked at nicknames when we generated the names,
        we filter them out here.

        We use the GEDCOM 5.5.1 FACT command to write out attributes not
        built in to GEDCOM.

        """

        if person.get_privacy():
            self._writeln(1, 'RESN confidential')
            
        # filter out the nicknames
        attr_list = [attr for attr in person.get_attribute_list()
                     if attr.get_type() != AttributeType.NICKNAME]

        for attr in attr_list:

            attr_type = int(attr.get_type())
            name = libgedcom.PERSONALCONSTANTATTRIBUTES.get(attr_type)
            key = str(attr.get_type())
            value = attr.get_value().strip().replace('\r', ' ')

            if key in ("AFN", "RFN", "REFN", "_UID", "_FSFTID"):
#pylint: disable=maybe-no-member
                self._writeln(1, key, value)
                continue

            if key == "RESN":
                self._writeln(1, 'RESN')
                continue

            if name and name.strip():
                self._writeln(1, name, value)
            elif value:
                if key != "ID Gramps fusionné":
#pylint: disable=maybe-no-member
                    self._writeln(1, 'FACT', value)
                    self._writeln(2, 'TYPE', key)
            else:
                continue
            self._note_references(attr.get_note_list(), 2)
            self._source_references(attr.get_citation_list(), 2)

    def _header(self, filename):
        """
        Write the GEDCOM header.

            HEADER:=
            n HEAD {1:1}
            +1 SOUR <APPROVED_SYSTEM_ID> {1:1}
            +2 VERS <VERSION_NUMBER> {0:1}
            +2 NAME <NAME_OF_PRODUCT> {0:1}
            +2 CORP <NAME_OF_BUSINESS> {0:1}           # Not used
            +3 <<ADDRESS_STRUCTURE>> {0:1}             # Not used
            +2 DATA <NAME_OF_SOURCE_DATA> {0:1}        # Not used
            +3 DATE <PUBLICATION_DATE> {0:1}           # Not used
            +3 COPR <COPYRIGHT_SOURCE_DATA> {0:1}      # Not used
            +1 DEST <RECEIVING_SYSTEM_NAME> {0:1*}     # Not used
            +1 DATE <TRANSMISSION_DATE> {0:1}
            +2 TIME <TIME_VALUE> {0:1}
            +1 SUBM @XREF:SUBM@ {1:1}
            +1 SUBN @XREF:SUBN@ {0:1}
            +1 FILE <FILE_NAME> {0:1}
            +1 COPR <COPYRIGHT_GEDCOM_FILE> {0:1}
            +1 GEDC {1:1}
            +2 VERS <VERSION_NUMBER> {1:1}
            +2 FORM <GEDCOM_FORM> {1:1}
            +1 CHAR <CHARACTER_SET> {1:1}
            +2 VERS <VERSION_NUMBER> {0:1}
            +1 LANG <LANGUAGE_OF_TEXT> {0:1}
            +1 PLAC {0:1}
            +2 FORM <PLACE_HIERARCHY> {1:1}
            +1 NOTE <GEDCOM_CONTENT_DESCRIPTION> {0:1}
            +2 [CONT|CONC] <GEDCOM_CONTENT_DESCRIPTION> {0:M}

        """
        local_time = time.localtime(time.time())
        (year, mon, day, hour, minutes, sec) = local_time[0:6]
        date_str = "%d %s %d" % (day, libgedcom.MONTH[mon], year)
        time_str = "%02d:%02d:%02d" % (hour, minutes, sec)
        rname = self.dbase.get_researcher().get_name()
        LOG.debug("deb header %d" % self.relativepath)
        VERS2 = VERSION + "-GedcomforGeneanet-2.0.12"
        self._writeln(0, "HEAD")
        self._writeln(1, "SOUR", "Gramps" )
        self._writeln(2, "VERS", VERS2)
        self._writeln(2, "NAME", "Gramps")
        self._writeln(1, "DATE", date_str)
        self._writeln(2, "TIME", time_str)
        self._writeln(1, "SUBM", "@SUBM@")
        if self.relativepath:
            filenam = os.path.basename(filename)
            self._writeln(1, "FILE2", filenam, limit=255)
        else:
            self._writeln(1, "FILE", filename, limit=255)
        self._writeln(1, "COPR", 'Copyright (c) %d %s.' % (year, rname))
        self._writeln(1, "GEDC")
        self._writeln(2, "VERS", "5.5.1")
        self._writeln(2, "FORM", 'LINEAGE-LINKED')
        self._writeln(1, "CHAR", "UTF-8")

        # write the language string if the current LANG variable 
        # matches something we know about.

        lang = glocale.language[0]
        if lang and len(lang) >= 2:
            lang_code = LANGUAGES.get(lang[0:2])
            if lang_code:
                self._writeln(1, 'LANG', lang_code)

    def _source_ref_record(self, level, citation_handle):

        citation = self.dbase.get_citation_from_handle(citation_handle)

        src_handle = citation.get_reference_handle()
        if src_handle is None:
            return

        src = self.dbase.get_source_from_handle(src_handle)
        if src is None:
            return

        # Reference to the source
        self._writeln(level, "SOUR", "@%s@" % src.get_gramps_id())
        if citation.get_page() != "":
            # PAGE <WHERE_WITHIN_SOURCE> can not have CONC lines.
            # WHERE_WITHIN_SOURCE:= {Size=1:248}
            # Maximize line to 248 and set limit to 248, for no line split
            self._writeln(level + 1, 'PAGE', citation.get_page()[0:248],
                          limit=248)

        conf = min(citation.get_confidence_level(),
                   Citation.CONF_VERY_HIGH)
         
        if self.quaynote:
            if conf == Citation.CONF_VERY_HIGH:
                self._writeln(level +1, "DATA")
                self._writeln(level +2, "NOTE", _("Very High Quality Source"))
            elif conf == Citation.CONF_HIGH:
                self._writeln(level +1, "DATA")
                self._writeln(level +2, "NOTE", _("High Quality Source"))
            elif conf == Citation.CONF_NORMAL:
                self._writeln(level +1, "DATA")
                self._writeln(level +2, "NOTE", _("Normal Quality Source"))
            elif conf == Citation.CONF_LOW:
                self._writeln(level +1, "DATA")
                self._writeln(level +2, "NOTE", _("Low Quality Source"))
            elif conf == Citation.CONF_VERY_LOW:
                self._writeln(level +1, "DATA")
                self._writeln(level +2, "NOTE", _("Very Low Quality Source"))
        if  conf != -1:
            self._writeln(level + 1, "QUAY", QUALITY_MAP[conf])

        if not citation.get_date_object().is_empty():
            self._writeln(level + 1, 'DATA')
            self._date(level + 2, citation.get_date_object())

        if len(citation.get_note_list()) > 0:

            note_list = [self.dbase.get_note_from_handle(h)
                         for h in citation.get_note_list()]
            note_list = [n for n in note_list
                         if n.get_type() == NoteType.SOURCE_TEXT]

            if note_list:
                ref_text = note_list[0].get()
            else:
                ref_text = ""

            if ref_text != "" and citation.get_date_object().is_empty():
                self._writeln(level + 1, 'DATA')
            if ref_text != "":
                self._writeln(level + 2, "TEXT", ref_text)

            note_list = [self.dbase.get_note_from_handle(h)
                         for h in citation.get_note_list()]
            note_list = [n.handle for n in note_list
                         if n and n.get_type() != NoteType.SOURCE_TEXT]
            self._note_references(note_list, level + 1)

        self._photos(citation.get_media_list(), level + 1)

        even = None
        for srcattr in citation.get_attribute_list():
            if str(srcattr.type) == "EVEN":
                even = srcattr.value
                self._writeln(level + 1, "EVEN", even)
                break
        if even:
            for srcattr in citation.get_attribute_list():
                if str(srcattr.type) == "EVEN:ROLE":
                    self._writeln(level + 2, "ROLE", srcattr.value)
                    break
        if self.citattr:
            for citattr in citation.get_attribute_list():
                if self.urlshort:
                    url_pattern = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
                    link = re.match(url_pattern, citattr.value)
                    if link:
                        url=link.group()
                        LOG.debug("deb write gedcom %s : %s  :" % ( str(url) , citattr.value ))
                        text = "<A HREF=\"" + str(url) + "\" title=\"" + str(url) + "\" target=_blank>" + str(citattr.type) + "</A>"
                        self._writeln(level + 1, "DATA" , text) 
                    else:
                        self._writeln(level + 1, "DATA", str(citattr.type))
                        self._writeln(level + 2, "TEXT", citattr.value)
                else:
                    self._writeln(level + 1, "DATA", str(citattr.type))
                    self._writeln(level + 2, "TEXT", citattr.value)
                
    def write_gedcom_file(self, filename):
        """
        Write the actual GEDCOM file to the specified filename.
        """

        self.dirname = os.path.dirname (filename)
        self.gedcom_file = io.open(filename, "w", encoding='utf-8')
        if self.zip:
            zipf = filename + ".zip"
            self.zipfile = zipfile.ZipFile(zipf,'w')
            if not self.zipfile:
                raise Exception('fichier zip %s non ouvert' % zipf)
        
        LOG.debug("deb write gedcom %d" % self.relativepath)
        self._header(filename)
        self._submitter()
        self._individuals()
        self._families()
        self._sources()
        self._repos()
        self._notes()
        self._writeln(0, "TRLR")
        self.gedcom_file.close()
        if self.zip:
            self.zipfile.close()
        return True

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

    def _recheader(self):
        msg = "= Recensement 1946=\n<BR><BR>\n"
        self.rec_file.write(msg)
        msg = "Cette page donne le recensement pour la commune de Plouguerneau en 1946 et le pourcentage de parenté avec moi meme\n<BR>\n"
        self.rec_file.write(msg)

    def _recwrite(self,nametag):

        RES=defaultdict(lambda : defaultdict(str))
        self.PARENTY= defaultdict(str)
        self.LEN= defaultdict(str)
        self.REL= defaultdict(str)
        self.TIMS= defaultdict(str)
        self.rel_class = get_relationship_calculator(glocale)
        self.home_person = self.database.get_default_person()
        p2 = self.home_person.get_primary_name().get_name()
        parentypers=0
        couleur1="7FD5CE"
        couleur2="D5C17F"
        couleur=couleur1
        progress = ProgressMeter(_('Export Census 1946'), can_cancel=True)
        length = self.database.get_number_of_people()
        progress.set_pass('recploug1946',length)
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
                        LOG.debug("TAG trouve %s" % tname)
                        LOG.debug("calcul rerlationship ",p1)
                        common, self.msg_list = self.rel_class.get_relationship_distance_new(
                              self.database, self.person, self.home_person,
                        all_families=True,
                        all_dist=True,
                        only_birth=False)
                        LOG.debug"calcul parenty ")
                        LOG.debug(common)
                        (parenty,rel) = self.get_parenty(common)
                        LOG.debug("parenty2 ",parenty)
                        numlinks=len(common)
                        if nametag == 'recploug1946':
                            for event_ref in person.get_event_ref_list():
                                event = self.database.get_event_from_handle(event_ref.ref)
                                if not event:
                                    continue
                                if event.get_type() == EventType.CENSUS:
                                    for tag_handle in event.get_tag_list():
                                        tag = self.database.get_tag_from_handle(tag_handle)
                                        name = tag.get_name()
                                        if name == 'recploug1946':
                                            result=""
                                            ehandle=int(float.fromhex(event.handle[0:11]))
                                            timst=event.gramps_id
                                            timst=timst.replace('E','')
                                            attrs = event_ref.get_attribute_list()
                                            if len(attrs):
                                                for attribute in attrs:
                                                    attr_type = attribute.get_type()
                                                    attr_val  = attribute.get_value()
                                                    if attr_type == "Rang":
                                                        clas=str(ehandle) + "." + str (attr_val)
                                                        self.TIMS[phandle]=float(clas)
                                                    else:
                                                        if result:
                                                            result = result + "</TD><TD>" + str(attr_val)
                                                        else:
                                                            result = "<TD>" + str(attr_val)
                                                result= result + "</TD>"
                            RES[phandle]['recploug1946']=result
                        if parenty > 0.0:
                            parentypers=parentypers + 1
                            attributes = self.person.get_attribute_list()
                            attributes.sort(key=lambda a: a.get_type().value)
                            result=""
                            self.PARENTY[phandle]=parenty
                            self.LEN[phandle]=numlinks
                            self.REL[phandle]=rel
                        else:
                            self.PARENTY[phandle]=0
                            self.LEN[phandle]=0
                            self.REL[phandle]=""
        num=parentypers
        progress.close()
        num2=len(self.TIMS.keys())
        if nametag == "recploug1946":
            msg =  "<BR>Nombre total de personnes dans le recensement : " + str(num2)  + "<BR>Nombre total de personnes apparentés : " + str(num)  + "<BR><BR>\n"
            self.rec_file.write(msg)
            pct = 100.0 * num / num2
            msg = "<b>" + str(format(pct, '.2f')) + "%</b> de personnes apparentées<BR><BR><BR>\n"
            self.rec_file.write(msg)
            msg = "<TABLE class=\"tabwiki\"><TR><TH>Nom</TH><TH>Nom Recensement</TH><TH>Adresse</TH><TH>Relation</TH><TH>Date Naissance</TH><TH>Nationalité</TH><TH>Profession</TH><TH>% parenté</TH><TH>Relation la plus proche</TH><TH>Nombre de liens</TH></tr>\n"
            self.rec_file.write(msg)
            num = 1
            sortedDict = sorted(self.TIMS.items(), reverse=False,key=lambda kv: float(kv[1]))
            LOG.debug(sortedDict)
            preval=""
            couleur= couleur1
            for k,val in sortedDict:
                valstr=str(val)
                (ehandl,reste)=valstr.split('.')
                if ehandl != preval:
                    if couleur == couleur1:
                        couleur = couleur2
                    else:
                        couleur = couleur1
                preval = ehandl
                if k not in self.PARENTY:
                    value = 0
                else:
                    value=self.PARENTY[k]
                person = self.database.get_person_from_handle(k)
                p1 = person.get_primary_name().get_name()
                phandle=k
                if self.GENEWEBURL[phandle]:
                    msg = "<TR bgcolor=" + couleur +"><TD>" + "<A HREF=\""+ self.GENEWEBURL[phandle] + "\">" + p1 + "</A>" + RES[k]['recploug1946'] + "<TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                else:
                    msg = "<TR bgcolor=" + couleur + "><TD>" + p1 + RES[k]['recploug1946'] + "<TD>" + str(format(value, '.10f')) + "</TD><TD>" + str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) + "</TD>\n"
                LOG.debug("NUM %d Nom %s REL %s" % (num,p1,str(self.REL[k])))
                num = num + 1
                msg = msg + "</TR>\n"
                self.rec_file.write(msg)
            msg = "</TABLE>\n"
            self.rec_file.write(msg)
            msg = "Nombre " + str(num) + "\n"
            self.rec_file.write(msg)


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
        progress = ProgressMeter(_('Export Star'), can_cancel=True)
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
                        (parenty,rel) = self.get_parenty(common)
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
            url = self.GENEWEBURL[k]
            msg = msg + "<TD> <A HREF=\"" + url + "\">Lien</A></TD>" + "<TD>" + str(format(val, '.10f')) +  "</TD><TD>" +str(self.REL[k]) + "</TD><TD>" + str(self.LEN[k]) +"</TD></TR>\n"
            self.star_file.write(msg)
        msg = msg + "</TABLE>"
        self.star_file.write(msg)
        config.set('behavior.generation-depth',self.olddepth)
        config.save


    def _couswrite(self,nametag):
#
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
        p2 = self.home_person.get_primary_name().get_name()
        parentypers=0
        progress = ProgressMeter(_('Export Star'), can_cancel=True)
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
                        for relation in common:
                            handle=relation[1]
                            self.HANDL[self.person.handle].add(handle)
                        (parenty,rel) = self.get_parenty(common)
                        numlinks=len(common)
                        if parenty > 0.0:
                            parentypers=parentypers + 1
                            attributes = self.person.get_attribute_list()
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
                        url = self.GENEWEBURL[hdl]
                        parurl = self.GENEWEBPARURL[hdl]
                        person2 = self.database.get_person_from_handle(hdl)
                        p2 = person2.get_primary_name().get_name()
                        msg = "<TR><TD> <A HREF=\"" + url + "\">" + p2 + "</A></TD><TD><A HREF=\"" + parurl + "\">Lien de parenté</TD></TR>\n"
                        self.cous_file.write(msg)
        msg =  "</TABLE>"
        self.cous_file.write(msg)


    def write_rec_file(self, filename):
        """
        Write the actual GEDCOM file to the specified filename.
        """

        self.dirname = os.path.dirname (filename)
        self.rec_file = io.open(filename, "w", encoding='utf-8')
        self._recheader()
        nametag="recploug1946"
        self._recwrite(nametag=nametag)
        self.rec_file.close()

    def write_star_file(self, filename):
        """
        Write the actual GEDCOM file to the specified filename.
        """

        self.dirname = os.path.dirname (filename)
        self.star_file = io.open(filename, "w", encoding='utf-8')
        nametag="star"
        self._starwrite(nametag=nametag)
        self.star_file.close()

    def write_cous_file(self, filename):
        """
        Write the actual GEDCOM file to the specified filename.
        """

        self.dirname = os.path.dirname (filename)
        self.cous_file = io.open(filename, "w", encoding='utf-8')
        nametag="cousingen"
        self._couswrite(nametag=nametag)
        self.cous_file.close()

#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
#
# GedcomWriter Options
#
#-------------------------------------------------------------------------
class GedcomWriterOptionBox(WriterOptionBox):
    """
    Create a VBox with the option widgets and define methods to retrieve
    the options.
    """
    def __init__(self, person, dbstate, uistate , track=None, window=None):
        """
        Initialize the local options.
        """
        super(GedcomWriterOptionBox, self).__init__(person, dbstate, uistate)
        self.include_witnesses = CONFIG.get("preferences.include_witnesses")
        self.include_witnesses_check = None
        self.include_media = CONFIG.get("preferences.include_media")
        self.include_media_check = None
        self.include_depot = CONFIG.get("preferences.include_depot")
        self.include_depot_check = None
        self.extended_role = CONFIG.get("preferences.extended_role")
        self.extended_role_check = None
        self.relativepath = CONFIG.get("preferences.relativepath")
        self.relativepath_check = None
        self.quaynote = CONFIG.get("preferences.quaynote")
        self.quaynote_check = None
        self.zip = CONFIG.get("preferences.zip")
        self.zip_check = None
        self.namegen = CONFIG.get("preferences.namegen")
        self.namegen_check = None
        self.nameus = CONFIG.get("preferences.nameus")
        self.nameus_check = None
        self.anychar = CONFIG.get("preferences.anychar")
        self.anychar_check = None
        self.citattr = CONFIG.get("preferences.citattr")
        self.citattr_check = None
        self.altname = CONFIG.get("preferences.altname")
        self.altname_check = None
        self.placegeneanet = CONFIG.get("preferences.placegeneanet")
        self.placegeneanet_check = None
        self.ancplacename = CONFIG.get("preferences.ancplacename")
        self.ancplacename_check = None
        self.extendedtitle = CONFIG.get("preferences.extendedtitle")
        self.extendedtitle_check = None
        self.inccensus = CONFIG.get("preferences.inccensus")
        self.inccensus_check = None
        self.urlshort = CONFIG.get("preferences.urlshort")
        self.urlshort_check = None
        self.parentsrc = CONFIG.get("preferences.parentsrc")
        self.parentsrc_check = None

    def get_option_box(self):
        option_box = super(GedcomWriterOptionBox, self).get_option_box()
        # Make options:
        self.include_witnesses_check = Gtk.CheckButton(_("Include witnesses"))
        self.include_media_check = Gtk.CheckButton(_("Include media"))
        self.relativepath_check = Gtk.CheckButton(_("Relative path for media"))
        self.include_depot_check = Gtk.CheckButton(_("Include depot in sources"))
        self.extended_role_check = Gtk.CheckButton(_("Role Display for Events"))
        self.quaynote_check = Gtk.CheckButton(_("Export Source Quality"))
        self.zip_check = Gtk.CheckButton(_("Create a zip of medias"))
        self.namegen_check = Gtk.CheckButton(_("Geneanet name beautify"))
        self.nameus_check = Gtk.CheckButton(_("Support for call name"))
        self.anychar_check = Gtk.CheckButton(_("Implementation of anychar"))
        self.citattr_check = Gtk.CheckButton(_("Export of attributes of citation"))
        self.inccensus_check = Gtk.CheckButton(_("Include Census information for people"))
        self.urlshort_check = Gtk.CheckButton(_("Title instead of url for links"))
        self.parentsrc_check = Gtk.CheckButton(_("Include Parental Source as Notes"))
        self.altname_check = Gtk.CheckButton(_("Display alternative name for place"))
        self.placegeneanet_check = Gtk.CheckButton(_("Geneanet format place"))
        self.ancplacename_check = Gtk.CheckButton(_("Display place name at the time"))
        self.extendedtitle_check = Gtk.CheckButton(_("Display Extended Title"))
        #self.include_witnesses_check.set_active(1)
        self.include_witnesses_check.set_active(CONFIG.get("preferences.include_witnesses"))
        self.include_media_check.set_active(CONFIG.get("preferences.include_media"))
        self.include_depot_check.set_active(CONFIG.get("preferences.include_depot"))
        self.relativepath_check.set_active(CONFIG.get("preferences.relativepath"))
        self.extended_role_check.set_active(CONFIG.get("preferences.extended_role"))
        self.quaynote_check.set_active(CONFIG.get("preferences.quaynote"))
        self.zip_check.set_active(CONFIG.get("preferences.zip"))
        self.namegen_check.set_active(CONFIG.get("preferences.namegen"))
        self.nameus_check.set_active(CONFIG.get("preferences.nameus"))
        self.anychar_check.set_active(CONFIG.get("preferences.anychar"))
        self.citattr_check.set_active(CONFIG.get("preferences.citattr"))
        self.inccensus_check.set_active(CONFIG.get("preferences.inccensus"))
        self.urlshort_check.set_active(CONFIG.get("preferences.urlshort"))
        self.parentsrc_check.set_active(CONFIG.get("preferences.parentsrc"))
        self.altname_check.set_active(CONFIG.get("preferences.altname"))
        self.placegeneanet_check.set_active(CONFIG.get("preferences.placegeneanet"))
        self.ancplacename_check.set_active(CONFIG.get("preferences.ancplacename"))
        self.extendedtitle_check.set_active(CONFIG.get("preferences.extendedtitle"))

        # Add to gui:
        option_box.pack_start(self.include_witnesses_check, False, False, 0)
        option_box.pack_start(self.include_media_check, False, False, 0)
        option_box.pack_start(self.include_depot_check, False, False, 0)
        option_box.pack_start(self.relativepath_check, False, False, 0)
        option_box.pack_start(self.extended_role_check, False, False, 0)
        option_box.pack_start(self.quaynote_check, False, False, 0)
        option_box.pack_start(self.zip_check, False, False, 0)
        option_box.pack_start(self.namegen_check, False, False, 0)
        option_box.pack_start(self.nameus_check, False, False, 0)
        option_box.pack_start(self.anychar_check, False, False, 0)
        option_box.pack_start(self.citattr_check, False, False, 0)
        option_box.pack_start(self.inccensus_check, False, False, 0)
        option_box.pack_start(self.urlshort_check, False, False, 0)
        option_box.pack_start(self.parentsrc_check, False, False, 0)
        option_box.pack_start(self.altname_check, False, False, 0)
        option_box.pack_start(self.placegeneanet_check, False, False, 0)
        option_box.pack_start(self.ancplacename_check, False, False, 0)
        option_box.pack_start(self.extendedtitle_check, False, False, 0)
        return option_box

    def parse_options(self):
        """
        Get the options and store locally.
        """
        super(GedcomWriterOptionBox, self).parse_options()
        if self.include_witnesses_check:
            self.include_witnesses = self.include_witnesses_check.get_active()
        if self.include_media_check:
            self.include_media = self.include_media_check.get_active()
        if self.include_depot_check:
            self.include_depot = self.include_depot_check.get_active()
        if self.extended_role_check:
            self.extended_role = self.extended_role_check.get_active()
        if self.relativepath_check:
            self.relativepath = self.relativepath_check.get_active()
        if self.quaynote_check:
            self.quaynote = self.quaynote_check.get_active()
        if self.zip_check:
            self.zip = self.zip_check.get_active()
        if self.namegen_check:
            self.namegen = self.namegen_check.get_active()
        if self.nameus_check:
            self.nameus = self.nameus_check.get_active()
        if self.anychar_check:
            self.anychar = self.anychar_check.get_active()
        if self.citattr_check:
            self.citattr = self.citattr_check.get_active()
        if self.inccensus_check:
            self.inccensus = self.inccensus_check.get_active()
        if self.urlshort_check:
            self.urlshort = self.urlshort_check.get_active()
        if self.parentsrc_check:
            self.parentsrc = self.parentsrc_check.get_active()
        if self.altname_check:
            self.altname = self.altname_check.get_active()
        if self.placegeneanet_check:
            self.placegeneanet = self.placegeneanet_check.get_active()
        if self.ancplacename_check:
            self.ancplacename = self.ancplacename_check.get_active()
        if self.extendedtitle_check:
            self.extendedtitle = self.extendedtitle_check.get_active()
        CONFIG.set("preferences.include_witnesses" , self.include_witnesses )
        CONFIG.set("preferences.include_witnesses" , self.include_witnesses )
        CONFIG.set("preferences.include_media" , self.include_media)
        CONFIG.set("preferences.include_depot" , self.include_depot)
        CONFIG.set("preferences.extended_role" , self.extended_role)
        CONFIG.set("preferences.relativepath" , self.relativepath)
        CONFIG.set("preferences.quaynote" , self.quaynote)
        CONFIG.set("preferences.zip" , self.zip)
        CONFIG.set("preferences.namegen" , self.namegen)
        CONFIG.set("preferences.nameus" , self.nameus)
        CONFIG.set("preferences.anychar" , self.anychar)
        CONFIG.set("preferences.citattr" , self.citattr)
        CONFIG.set("preferences.inccensus" , self.inccensus)
        CONFIG.set("preferences.urlshort" , self.urlshort)
        CONFIG.set("preferences.parentsrc" , self.parentsrc)
        CONFIG.set("preferences.altname" , self.altname)
        CONFIG.set("preferences.placegeneanet" , self.placegeneanet)
        CONFIG.set("preferences.ancplacename" , self.ancplacename)
        CONFIG.set("preferences.extendedtitle" , self.extendedtitle)
        CONFIG.save()

def export_data(database, filename, user, option_box=None):
    """
    External interface used to register with the plugin system.
    """
    ret = False
    try:
        ged_write = GedcomWriterforGeneanet(database, user, option_box)
#pylint: disable=maybe-no-member
        ret = ged_write.write_gedcom_file(filename)
    except IOError as msg:
        msg2 = _("Could not create %s") % filename
        user.notify_error(msg2, msg)
    except DatabaseError as msg:
        user.notify_db_error(_("Export failed"), msg)
    return ret
