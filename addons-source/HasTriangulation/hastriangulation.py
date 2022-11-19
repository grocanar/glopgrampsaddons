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
from gramps.gen.const import GRAMPS_LOCALE as glocale, USER_PLUGINS
from collections import defaultdict
from gramps.gen.relationship import get_relationship_calculator
import logging
import os
LOG = logging.getLogger(".debug")



#-------------------------------------------------------------------------
#
# HasTriangulation
#
#-------------------------------------------------------------------------
class HasTriangulation(Rule):
    """Rule that triangulate People with the home Person and  aspecific person"""

    labels = [ _('ID:') , _('Number of Centimorgan:') ]
    name        = _('Triangulation')
    description = _("Matches people which triangulate with home person and  aspecific person")
    category    = _('ADN filters')
    
    def findbase(self,base,chrom):
        baseprev=0
        baseinf=0
        basesup=0
        for bas in self.CHR[chrom].keys():
            if not baseprev:
                baseprev=bas
            else:
                if bas > base and not baseinf:
                    baseinf=baseprev
                    basesup=bas
                else:
                    baseprev=bas
        return baseinf,basesup

    def init_CHR(self):
        CHR = defaultdict(lambda : defaultdict(float))
        inputfile="data"
        centifile = os.path.join(USER_PLUGINS, "HasTriangulation", inputfile)
        print(" INPUT FILE  ", centifile)
        with open(centifile, newline='') as myfile:
            cor = myfile.readlines()
            for L in cor:
                H=L.split()
                chrom = H[0].replace('chr','')
                CHR[chrom][int(H[1])]=float(H[3])
        return CHR

    def get_centimorgan(self,chrom,base):
        centipos=self.CHR[chrom][base]
        if centipos == 0.0:
             (int1,int2)=self.findbase(base,chrom)
             centipos=self.CHR[chrom][int1]*(1-((base-int1)/(int2-int1))) + self.CHR[chrom][int2]*(1-((int2-base)/(int2-int1)))
        return centipos

    def prepare(self, db, user):
        # things we want to do just once, not for every handle
        self.souche = db.get_default_person()
        self.first = db.get_person_from_gramps_id(self.list[0])
        self.centimorgan = float(self.list[1]) 
        self.res = defaultdict(list)
        self.CHR = self.init_CHR()

        self.relationship = get_relationship_calculator(glocale)

        for ref in self.souche.get_person_ref_list():
            pers = db.get_person_from_handle(ref.ref)
            if pers == self.first:
                result = ref.get_relation()
                if result == "DNA":
                    data, msg = self.relationship.get_relationship_distance_new(db,self.souche,self.first,False, True, True)
                    notelist = ref.get_note_list()
                    for notehdl in notelist:
                        note = db.get_note_from_handle(notehdl)
                        LINE=note.get().splitlines()
                        for line in LINE:
                            L=line.split(',')
                            chr=L[0]
                            debut=int(L[1])
                            fin=int(L[2])
                            self.res[chr].append((debut,fin))


    def apply(self,db,people):
        resultat=False
        for ref in people.get_person_ref_list():
            pers = db.get_person_from_handle(ref.ref)
            if pers == self.souche:
                result = ref.get_relation()
                if result == "DNA":
                    notelist = ref.get_note_list()
                    data, msg = self.relationship.get_relationship_distance_new(db,self.souche,people,False, True, True)
                    notelist = ref.get_note_list()
                    for notehdl in notelist:
                        note = db.get_note_from_handle(notehdl)
                        LINE=note.get().splitlines()
                        for line in LINE:
                            L=line.split(',')
                            if len(L) > 3:
                                chro=L[0]
                                debut=int(L[1])
                                fin=int(L[2])
                                if chro in self.res.keys():
                                    LIS=self.res[chro]
                                    for (deb,fi) in LIS:
                                        if deb <= debut <= fi or deb <= fin <= fi:
                                            dnasegment=min([fi,fin]) - max([debut,deb])
                                            deb2=max([debut,deb])
                                            fin2=min([fi,fin])
                                            centideb=self.get_centimorgan(chro,deb2)
                                            centifin=self.get_centimorgan(chro,fin2)
                                            centi=centifin - centideb
                                            if centi > self.centimorgan:
                                                resultat = True
        return resultat

