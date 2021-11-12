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
import logging
LOG = logging.getLogger(".debug")



#-------------------------------------------------------------------------
#
# HasDeath
#
#-------------------------------------------------------------------------
class HasSeveralEvent(Rule):
    """Rule that match a person with several individual unique event"""

    name        = _('People with several individual unique event')
    description = _("Matches people with several individual unique event")
    category    = _('Person filters')
    
    def apply(self,db,person):
        numdeath = 0
        numbirth = 0
        numburial = 0
        numbaptism = 0
        for event_ref in person.get_event_ref_list():
            if not event_ref:
                continue
            elif event_ref.role != EventRoleType.PRIMARY:
                # Only match primaries, no witnesses
                continue
            event = db.get_event_from_handle(event_ref.ref)
            if event.get_type() == EventType.DEATH:
                numdeath = numdeath + 1
                continue
            if event.get_type() == EventType.BIRTH:
                numbirth = numbirth + 1
                continue
            if event.get_type() == EventType.BURIAL:
                numburial = numburial + 1
                continue
            if event.get_type() == EventType.BAPTISM:
                numburial = numburial + 1
                continue
            # This event matched: exit positive
        # Nothing matched: exit negative
        LOG.debug("TAG BIRTH %d" % numbirth)
        LOG.debug("TAG DEATH %d" % numdeath)
        if numbirth > 1:
            return True
        if numdeath > 1:
            return True
        if numburial > 1:
            return True
        if numbaptism > 1:
            return True
        return False
