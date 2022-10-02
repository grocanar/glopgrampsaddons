#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
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

#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gramps.gen.datehandler import parser
from gramps.gen.lib.eventroletype import EventRoleType
from gramps.gen.lib.eventtype import EventType
from gramps.gen.filters.rules import Rule
from gramps.gen.relationship import get_relationship_calculator
import logging
LOG = logging.getLogger(".debug")



#-------------------------------------------------------------------------
#
# HasDeath
#
#-------------------------------------------------------------------------
class IsFilleul(Rule):
    """Rule that match a person with several birth or death"""

    name        = _('People match filleul ')
    description = _("Matches people filleul")
    category    = _('Person filters')
    
    def apply(self,db,person):
       result = False
       relation = [ "Filleul"  , "Filleule" ]
       relationship = get_relationship_calculator()
       refs = person.get_person_ref_list()
       if refs:
          for ref in person.serialize()[-1]:
              (a, b, c, two, value) = ref
              if value in relation:
                  result=True
       return result
