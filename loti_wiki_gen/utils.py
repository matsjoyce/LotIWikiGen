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

import re


def english_join(items):
    items = list(items)
    if len(items) == 1:
        return " " + items[0]
    else:
        before = ", ".join(items[:-1])
        return "s " + before + " and " + items[-1]


def english_title(str):
    def transform(match):
        x = match.group(0)
        if len(x) > 2 and x not in ["and", "that", "into", "the", "from", "with", "when", "per"]:
            return x[0].upper() + x[1:]
        else:
            return x
    subbed = re.sub("\w+", transform, str)
    if subbed:
        return subbed[0].upper() + subbed[1:]
    return ""
