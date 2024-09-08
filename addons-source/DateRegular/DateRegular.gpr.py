#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2017       Dave Scheipers
# Copyright (C) 2017       Paul Culley
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

"""
Filter rule to match Event with a Regular date
"""
register(RULE,
  id    = 'DateRegular',
  name  = _("Event with regular date"),
  description = _("Match Event with Regular Date"),
<<<<<<< HEAD
  version = '1.0.6',
=======
  version = '1.0.7',
>>>>>>> a64f97d49698b0e632e5a486446674f623b12c66
  authors = ["Eric Doutreleau"],
  authors_email = ["eric@doutreleau.fr"],
  gramps_target_version  = '5.2',
  status = STABLE,
  fname = "DateRegular.py",
  ruleclass = 'DateRegular',  # must be rule class name
  namespace = 'Event',  # one of the primary object classes
  )
