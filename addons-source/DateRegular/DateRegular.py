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
from gramps.gen.filters.rules import Rule
import logging
LOG = logging.getLogger(".debug")



#-------------------------------------------------------------------------
#
# HasDeath
#
#-------------------------------------------------------------------------
class DateRegular(Rule):
    """Rule that match an event with a regular date """

    name        = _('Event with regular date')
    description = _("Match Event with regular date")
    category    = _('Event filters')
    
    def apply(self,db,event):
        
        evt=event.get_date_object()
        if evt:
            if evt.is_regular():	
                return True
            else:
                return False
        else:
            return False

