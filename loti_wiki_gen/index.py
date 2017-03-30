#!/usr/bin/env python3
#
# Copyright 2016 Matthew Joyce
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from . import writer


class Index:
    def __init__(self, unit_advancements, standard_advancements, abilities, items):
        self.item_index = {}
        self.ability_index = {}
        self.advancement_index = {}
        self.advancement_urls = set()

        for name, tag in items:
            self.item_index[name.lower()] = "{}_.E2.80.93_{}".format(name, writer.sort_translations.get(tag.keys["sort"].any, tag.keys["sort"].any))

        for section, name, type, macro_name, tag in abilities:
            self.ability_index[macro_name] = "{}_.E2.80.93_{}".format(name, type)

        self.process_advancement(unit_advancements)
        self.process_advancement(standard_advancements)

    def process_advancement(self, advancements):
        for section, name, tag, *_ in advancements:
            iname = name
            ref = "{}_.E2.80.93_{}".format(tag.keys["description"].any.replace(" ", "_"),
                                           iname.replace(" ", "_"))
            i = 2
            while ref in self.advancement_urls:
                iname = "{}_{}".format(name, i)
                ref = "{}_.E2.80.93_{}".format(tag.keys["description"].any.replace(" ", "_"),
                                               iname.replace(" ", "_"))
                i += 1
            self.advancement_urls.add(ref)
            self.advancement_index[section + name] = ref

    def query_advancement(self, section, name):
        return self.advancement_index.get(section + name)

    def query_item(self, item_name):
        return self.item_index[item_name]

    def query_ability(self, ability_name):
        return self.ability_index.get(ability_name)
