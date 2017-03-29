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

import argparse
import pathlib
import re
import collections
import itertools
import builtins
import time
import sys
import shlex
import string
import subprocess

__version__ = "0.3.5"

wml_regexes = [("key", r"([\w{}]+)\s*=\s*_?\s*\"([^\"]*)\""),
               ("key", r"([\w{}]+)\s*=\s*([^\n]+)"),
               ("keys", r"([\w,]+)\s*=\s*([^\n]+)"),
               ("open", r"\[([\w{}]+)\]"),
               ("close", r"\[/([\w{}]+)\]"),
               ("macro_open", r"(\{[^{}]+)"),
               ("pre", r"#(define|ifdef|else|endif|enddef) ?([^\n]*)"),
               ("whitespace", r"(\s+)"),
               ("comment", r"#[^\n]*")]

wml_regexes = [(n, re.compile(r, re.DOTALL)) for n, r in wml_regexes]

levels = ["EASY", "MEDIUM", "HARD"]

sort_translations = {"weaponword": "craftable as any weapon",
                     "armourword": "craftable as any armour",
                     }

weapon_sorts = ["sword", "axe", "bow", "mace", "xbow", "spear", "dagger", "knife", "staff",
                "weaponword", "polearm", "sling", "thunderstick", "claws", "essence", "exotic"]

damage_ranges = ["", "_melee", "_ranged"]
damage_types = ["blade", "impact", "pierce", "fire", "cold", "arcane"]

defence_types = [("forest", "in forests"),
                 ("frozen", "on frozen places"),
                 ("flat", "on flat terrains"),
                 ("cave", "in caves"),
                 ("fungus", "in mushroom groves"),
                 ("village", "in villages"),
                 ("castle", "in castles"),
                 ("shallow_water", "in shallow waters"),
                 ("reef", "on coastal reefs"),
                 ("deep_water", "in deep water"),
                 ("swamp_water", "in swamps"),
                 ("hills", "on hills"),
                 ("mountains", "on mountains"),
                 ("sand", "on sands"),
                 ("unwalkable", "above unwalkable places"),
                 ("impassable", "inside impassable walls")]

movement_costs = [("forest", "through forests"),
                  ("frozen", "on frozen lands"),
                  ("flat", "on flat terrains"),
                  ("cave", "through dark caves"),
                  ("fungus", "through mushroom groves"),
                  ("village", "through villages"),
                  ("castle", "through castles"),
                  ("shallow_water", "in shallow waters"),
                  ("reef", "on coastal reefs"),
                  ("deep_water", "in deep waters"),
                  ("swamp_water", "through swampy places"),
                  ("hills", "on hills"),
                  ("mountains", "on mountains"),
                  ("sand", "across sands"),
                  ("unwalkable", "above unwalkable places"),
                  ("impassable", "through impassable walls")]

special_translation = {"NOSFERATU_GORGE": "nosferatu's gorge",
                       "RAIJERS_SALOON": "Raijer's saloon"
                       }

ability_translation = {"BERSERK_LEADERSHIP": "radiating insanity",
                       "CHARGE_LEADERSHIP": "warlord's rule",
                       "POISON_LEADERSHIP": "radiation",
                       "FIRSTSTRIKE_LEADERSHIP": "zeal aura",
                       "BACKSTAB_LEADERSHIP": "murderous presence",
                       "MARKSMAN_LEADERSHIP": "cantor",
                       "DRAIN_LEADERSHIP": "aura of hunger",
                       "REGENERATES_LESSER": "regenerates slightly",
                       "PENETRATE_LEADERSHIP": "push",
                       "DARKENS_IMPROVED": "darkens badly",
                       "DARKENS_GREAT": "darkens severely",
                       "ILLUMINATES_IMPROVED": "improved illumination",
                       "ILLUMINATES_GREAT": "great illumination",
                       "LEADERSHIP_LEVEL_6": "leadership",
                       "WEAK_AMBUSH": "lesser ambush",
                       "IMMUNE_TO_SLOW": "resistant to slow",
                       "PENETRATE": "penetrates",
                       "TOXIC_AURA": "dark aura",
                       "FEEDING_EASY": "feeding",
                       }

special_notes_translation = {
    "SPECIAL_NOTES_SPIRIT": " Spirits have very unusual resistances to damage, and move quite slowly over open water.",
    "SPECIAL_NOTES_ARCANE": " This unit’s arcane attack deals tremendous damage to magical creatures, and even some to mundane creatures.",
    "SPECIAL_NOTES_HEALS": " This unit is capable of basic healing.",
    "SPECIAL_NOTES_EXTRA_HEAL": " This unit is capable of rapid healing.",
    "SPECIAL_NOTES_CURES": " This unit is capable of healing those around it, and curing them of poison.",
    "SPECIAL_NOTES_UNPOISON": " This unit is capable of neutralizing the effects of poison in units around it.",
    "SPECIAL_NOTES_REGENERATES": " This unit regenerates, which allows it to heal as though always stationed in a village.",
    "SPECIAL_NOTES_STEADFAST": " The steadiness of this unit reduces damage from some attacks, but only while defending.",
    "SPECIAL_NOTES_LEADERSHIP": " The leadership of this unit enables adjacent units of the same side to deal more damage in combat, though this only applies to units of lower level.",
    "SPECIAL_NOTES_SKIRMISHER": " This unit’s skill at skirmishing allows it to ignore enemies’ zones of control and thus move unhindered around them.",
    "SPECIAL_NOTES_ILLUMINATES": " Illumination increases the lighting level in adjacent areas.",
    "SPECIAL_NOTES_TELEPORT": " This unit can use one move to teleport between any two empty villages controlled by its side.",
    "SPECIAL_NOTES_AMBUSH": " In woodlands, this unit’s ambush skill renders it invisible to enemies unless it is immediately adjacent or has revealed itself by attacking.",
    "SPECIAL_NOTES_NIGHTSTALK": " This unit is able to hide at night, leaving no trace of its presence.",
    "SPECIAL_NOTES_CONCEALMENT": " This unit can hide in villages (with the exception of water villages), and remain undetected by its enemies, except by those standing next to it.",
    "SPECIAL_NOTES_SUBMERGE": " This unit can move unseen in deep water, requiring no air from the surface.",
    "SPECIAL_NOTES_FEEDING": " This unit gains 1 hitpoint added to its maximum whenever it kills a living unit.",
    "SPECIAL_NOTES_BERSERK": " Whenever its berserk attack is used, this unit continues to push the attack until either it or its enemy lies dead.",
    "SPECIAL_NOTES_BACKSTAB": " If there is an enemy of the target on the opposite side of the target while attacking it, this unit may backstab, inflicting double damage by creeping around behind that enemy.",
    "SPECIAL_NOTES_PLAGUE": " Foes who lose their life to the plague will rise again in unlife, unless they are standing on a village.",
    "SPECIAL_NOTES_SLOW": " This unit is able to slow its enemies, halving their movement speed and attack damage until they end a turn.",
    "SPECIAL_NOTES_PETRIFY": " The ability to turn the living to stone makes this unit extremely dangerous.",
    "SPECIAL_NOTES_MARKSMAN": " This unit’s marksmanship gives it a high chance of hitting targeted enemies, but only on the attack.",
    "SPECIAL_NOTES_MAGICAL": " This unit has magical attacks, which always have a high chance of hitting an opponent.",
    "SPECIAL_NOTES_SWARM": " The swarming attacks of this unit become less deadly whenever its members are wounded.",
    "SPECIAL_NOTES_CHARGE": " Using a charging attack doubles both damage dealt and received; this does not affect defensive retaliation.",
    "SPECIAL_NOTES_DRAIN": " During battle, this unit can drain life from victims to renew its own health.",
    "SPECIAL_NOTES_FIRSTSTRIKE": " The length of this unit’s weapon allows it to strike first in melee, even in defense.",
    "SPECIAL_NOTES_POISON": " The victims of this unit’s poison will continually take damage until they can be cured in town or by a unit which cures.",
    }

header = """
This is an auto-generated wiki page listing {{}} currently avalible in the campaign "Legend of the Invincibles". {{}}
This was generated at {} using version {{}} of LotI and version {} of the generation script.
As this is auto-generated, DO NOT EDIT THIS PAGE.
Instead, create a new issule at https://github.com/matsjoyce/LotIWikiGen/issues/new and the script will be adjusted.

Other LotI-related wiki pages:

* https://wiki.wesnoth.org/LotI_Items &ndash; items, such as weapons and books
* https://wiki.wesnoth.org/LotI_Standard_Advancements &ndash; general advancements such as legacies and books
* https://wiki.wesnoth.org/LotI_Unit_Advancements &ndash; unit specific advancements
* https://wiki.wesnoth.org/LotI_Abilities &ndash; abilities and weapon specials
* https://wiki.wesnoth.org/DeadlyUnitsFromLotI
""".lstrip().format(time.ctime(), __version__)


WMLTag = collections.namedtuple("WMLTag", ("keys", "tags", "annotation", "macros"))


class WMLValue:
    def __init__(self):
        self.EASY = self.MEDIUM = self.HARD = ""

    @property
    def any(self):
        return self.EASY or self.MEDIUM or self.HARD

    @property
    def all(self):
        return self.EASY == self.MEDIUM == self.HARD

    @all.setter
    def all(self, value):
        self.EASY = self.MEDIUM = self.HARD = value

    def iter(self):
        yield "EASY", self.EASY
        yield "MEDIUM", self.MEDIUM
        yield "HARD", self.HARD

    def __repr__(self):
        return "WMLValue({!r}, {!r}, {!r})".format(self.EASY, self.MEDIUM, self.HARD)


def tokenize(str):
    macro_transforms = [(r"\"\s*\+\s*\{([^}]*)\}\s*\+\s*_?\s*\"", "\\1"),
                        (r"\{([^}]*)\}\s*\+\s*_?\s*\"", "\"\\1"),
                        (r"\"\s*\+\s*\{([^}]*)\}", "\\1\""),
                        (r"\"\s*\+\s*_?\s*\"", "")
                        ]
    for regex, sub in macro_transforms:
        regex = re.compile(regex)
        while regex.search(str):
            str = regex.sub(sub, str)
    #print(str)
    while str:
        for type, regex in wml_regexes:
            m = regex.match(str)
            if m:
                groups = m.groups()
                str = str[m.end():]
                if type in ("whitespace", "comment"):
                    pass
                elif type == "keys":
                    yield from (("key", x) for x in zip(groups[0].split(","),
                                                        groups[1].split(",")))
                elif type == "macro_open":
                    contents = groups[0]
                    count = 1
                    while count:
                        c = str[0]
                        if c == "{":
                            count += 1
                        if c == "}":
                            count -= 1
                        contents += c
                        str = str[1:]
                    yield "macro", (contents[1:-1],)
                else:
                    yield type, groups
                break
        else:
            raise RuntimeError("Can't parse {}".format(repr(str[:100])))


def parse_wml(tokens, tag_ann="all"):
    keys = collections.defaultdict(WMLValue)
    tags = collections.defaultdict(list)
    macros = []
    annotation = levels
    tokens = iter(tokens)
    for type, value in tokens:
        if type == "key":
            name, value = value
            if name == "increse_attacks":
                name = "increase_attacks"
            for l in annotation:
                setattr(keys[name], l, value)
        if type == "open":
            subtokens = []
            nt = next(tokens)
            count = 0
            while count or nt != ("close", (value[0],)):
                if nt == ("open", (value[0],)):
                    count += 1
                if nt == ("close", (value[0],)):
                    count -= 1
                subtokens.append(nt)
                nt = next(tokens)
            try:
                tag = parse_wml(subtokens, annotation)
            except Exception as e:
                print(e.__class__)
                raise
            else:
                tags[value[0]].append(tag)
        if type == "close":
            pass
        if type == "macro":
            if value[0].startswith("QUANTITY "):
                _, name, easy, medium, hard = value[0].split()
                keys[name].EASY = easy
                keys[name].MEDIUM = medium
                keys[name].HARD = hard
            else:
                macros.append(value[0])
        if type == "pre":
            if value[0] == "ifdef":
                annotation = {value[1]}
            elif value[0] == "else":
                annotation = set(levels) - set(annotation)
            elif value[0] == "endif":
                annotation = levels
            elif value[0] == "define":
                name = value[1].split()[0]
                subtokens = []
                nt = next(tokens)
                while nt != ("pre", ("enddef", "")):
                    subtokens.append(nt)
                    nt = next(tokens)
                tag = parse_wml(subtokens, annotation)
                tags[name].append(tag)
    return WMLTag(keys, tags, tag_ann, macros)


def format_parsed(tag, level=0):
    stuff = []
    for key, values in tag.keys.items():
        if values.all():
            stuff.append("    " * level + key + " = " + values.any)
        else:
            for name, value in values.iter():
                stuff.append("    " * level + key + " = " + value + " # " + name)
    for name, tags in tag.tags.items():
        for tag in tags:
            if tag.annotation != "all":
                stuff.append("    " * level + "# " + tag.annotation)
            stuff.append("    " * level + "[{}]".format(name))
            stuff.append(format_parsed(tag, level=level + 1))
            stuff.append("    " * level + "[/{}]".format(name))
    return "\n".join(stuff)


def special_notes_sub(str):
    for name, note in special_notes_translation.items():
        str = str.replace(name, note)
    return str.replace("SPECIAL_NOTES", "\nSpecial Notes:").strip().replace("\n\n", "\n")


def extract_abilities(start):
    data = (start / "utils" / "abilities.cfg").open().read()
    for type, obj in re.findall(r"#define ((?:ABILITY|WEAPON_SPECIAL)\S+)[^\n]*(.*?)#enddef", data, re.DOTALL):
        try:
            stuff = parse_wml(tokenize(obj))
        except RuntimeError as e:
            print(obj, "X" * 50, obj, "X" * 50, e, type(e))
            raise e
        if type.startswith("ABILITY"):
            section = "Abilities"
        else:
            section = "Weapon Specials"
        for tag_type, tags in stuff.tags.items():
            tags = [t for t in tags if t.keys["name"].any]
            if not tags:
                continue
            elif len(tags) == 1:
                tag, = tags
                yield section, tag.keys["name"].any, tag_type, type, tag
            elif len(tags) == 2:
                a, b = tags
                a.keys["name"].all = a.keys["name"].any + " and " + b.keys["name"].any
                a.keys["description"].all = a.keys["description"].any + " " + b.keys["description"].any
                yield section, a.keys["name"].any, tag_type, type, a
            else:
                raise RuntimeError("Cannot merge 3+ tags yet, implement!")



def extract_items(start):
    data = (start / "utils" / "item_list.cfg").open().read()
    for obj in re.findall(r"\[object\].*?\[/object\]", data, re.DOTALL):
        try:
            stuff = parse_wml(tokenize(obj))
        except RuntimeError as e:
            print(f, "X" * 50, obj, "X" * 50, e, type(e))
            raise e
        stuff = stuff.tags["object"][0]
        if "name" in stuff.keys and "filter" not in stuff.tags:
            yield stuff.keys["name"].any, stuff


def extract_advancements(start):
    for item in start.iterdir():
        if item.is_dir():
            yield from extract_advancements(item)
        elif item.suffix == ".cfg":
            data = item.open().read()
            if "GENERIC_AMLA" in data:
                amla_mode = "\nThis unit also has generic AMLA advancements"
            elif "SOUL_EATER_AMLA" in data:
                amla_mode = "\nThis unit also has soul eater AMLA advancements"
            elif "AMLA_GOD" in data:
                amla_mode = "\nThis unit also has god AMLA advancements"
            else:
                amla_mode = ""
            data = re.sub("{(?:GENERIC_AMLA|SOUL_EATER_AMLA|AMLA_GOD) [^(]+\((.*)\)[^}]+}", "\\1[/unit_type]", data, 0, re.DOTALL)
            fmt_fname = english_title(item.stem.replace("_", " ").lstrip(" " + string.digits))
            for unit in re.findall(r"\[unit_type\].*?\[/unit_type\]", data, re.DOTALL):
                try:
                    stuff = parse_wml(tokenize(unit))
                except RuntimeError as e:
                    print(f, "X" * 50, adv, "X" * 50, e, type(e))
                    raise e
                unit = stuff.tags["unit_type"][0]
                if not unit.keys["name"].any:
                    name = fmt_fname
                elif fmt_fname not in unit.keys["name"].any:
                    name = "{} ({})".format(unit.keys["name"].any.replace("female^", ""), fmt_fname)
                else:
                    name = unit.keys["name"].any.replace("female^", "")
                name = english_title(name)
                desc = special_notes_sub(unit.keys["description"].any) + amla_mode
                for adv in unit.tags["advancement"]:
                    if "id" not in adv.keys:
                        print(adv.keys.keys())
                    adv.keys["description"].all = english_title(adv.keys["description"].any)
                    yield name, adv.keys["id"].any, adv, desc
                for var in unit.tags["variation"]:
                    for adv in var.tags["advancement"]:
                        if "id" not in adv.keys:
                            print(adv.keys.keys())
                        adv.keys["description"].all = english_title(adv.keys["description"].any)
                        yield name, adv.keys["id"].any, adv, desc


def extract_utils_amla_advancements(fname):
    x = parse_wml(tokenize(fname.open().read()))
    for name, tags in x.tags.items():
        if name.endswith("ADVANCEMENTS") or name in ["ADDITIONAL_AMLA",
                                                     "LEGACY_DISCOVERY"]:
            if name == "LEGACY_DISCOVERY":
                name = "GENERIC_AMLA_ADVANCEMENTS"
            for adv in tags[0].tags["advancement"]:
                adv.keys["description"].all = english_title(adv.keys["description"].any)
                yield name, english_title(adv.keys["id"].any), adv


def format_values(values, positive, negative="",
                  percent=False, sort=False, invert=False):
    s = ""
    reverse = (all(i in "1234567890-" for n, v in values.iter() for i in v)
               and values.any and (int(values.any) < 0 or invert))
    for name, value in ([("", values.any)] if values.all else values.iter()):
        if not value:
            continue
        if s:
            s += ", "
        if sort and value in sort_translations:
            s += str(sort_translations[value])
        elif reverse:
            s += str(-int(value))
        else:
            s += str(value)
        if percent:
            s += "%"
        if not values.all:
            s += " (in {} difficulty)".format(name)
    if reverse:
        return negative.format(s)
    return positive.format(s)


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


def item_key_sort(kv):
    key, values = kv
    if key == "sort":
        return 0
    if key == "damage":
        return 1
    if key == "attacks":
        return 2
    if key == "defence":
        return 3
    if key.endswith("resist"):
        return 9
    if key.endswith("penetrate"):
        return 10
    else:
        return 11


def special_name(index, name, args):
    if name in special_translation:
        x = special_translation[name]
    elif name == "PLAGUE_TYPE_LOTI":
        x = "plague ({})".format(args[0])
    elif name == "LESSER_BERSERK":
        x = "lesser berserk ({})".format(args[0])
    elif name == "EXTRA_5_IMPACT_DAMAGE":
        x = "extra damage (+5; impact)"
    elif name == "CHARGING":
        x = "charge ({})".format(args[0])
    else:
        assert not args
        x = name.replace("_", " ").lower()
    if "WEAPON_SPECIAL_" + name in index:
        return "[[LotI_Abilities#{}|{}]]".format(index["WEAPON_SPECIAL_" + name], x)
    return x


def ability_name(index, name, args):
    args = [i.replace("_", "") for i in args]
    if name in ability_translation:
        x = ability_translation[name]
    elif name.startswith("ABSORB"):
        x = "absorbs ({})".format(name.replace("ABSORB_", ""))
    elif name == "INCREASE_RESISTANCE_AURA":
        x = "{} ({})".format(*args)
    elif name == "EXTRA_DAMAGE_AURA":
        x = "{} ({})".format(*args)
    elif name == "BURNING_AURA":
        x = "burns foes ({})".format(args[0])
    elif name == "REGENERATES_OTHER":
        x = "regenerates ({})".format(args[0])
    elif name == "HEALS_OTHER":
        x = "heals ({})".format(args[0])
    elif name in ("SHIELD", "DESPAIR", "CONVICTION", "FRAIL_TIDE", "UNHOLYBANE", "DEATHAURA", "CAREFUL"):
        x = "{} ({})".format(name.replace("_", " ").lower(), args[0])
    else:
        assert not args, name
        x = name.replace("_", " ").lower()
    if "ABILITY_" + name in index:
        return "[[LotI_Abilities#{}|{}]]".format(index["ABILITY_" + name], x)
    return x


class make_adv_index:
    def __init__(self, advs):
        self.index = {}
        self.refs = set()
        for section, name, tag, *_ in advs:
            iname = name
            ref = "{}_.E2.80.93_{}".format(tag.keys["description"].any.replace(" ", "_"),
                                           iname.replace(" ", "_"))
            i = 2
            while ref in self.refs:
                iname = "{}_{}".format(name, i)
                ref = "{}_.E2.80.93_{}".format(tag.keys["description"].any.replace(" ", "_"),
                                               iname.replace(" ", "_"))
                i += 1
            self.refs.add(ref)
            self.index[section + name] = ref
            if name in self.index:
                self.index[name] = ""
            else:
                self.index[name] = ref

    def get(self, section, id):
        if id in self.index and self.index[id]:
            return self.index[id]
        if section + id in self.index:
            return self.index[section + id]
        return ""


def make_item_index(items):
    index = {}
    for name, tag in items:
        index[name.lower()] = "{}_.E2.80.93_{}".format(name, format_values(tag.keys["sort"],
                                                                           "{}", sort=True))
    index["dark sword of desctruction"] = index["dark sword of destruction"]
    index["dark helm of desctruction"] = index["dark helm of destruction"]
    return index


def make_ability_index(items):
    index = {}
    for section, name, type, macro_name, tag in items:
        index[macro_name] = "{}_.E2.80.93_{}".format(name, type)
    return index


def write_item(name, tag, file, index):
    def print(*a, **kw):
        k = {"file": file, "end": "<br/>\n"}
        k.update(kw)
        return builtins.print(*a, **k)
    sort = tag.keys["sort"].any
    keys = tag.keys
    print("===", name, "&ndash;", format_values(keys["sort"], "{}", sort=True), "===", end="\n")
    if "flavour" in keys:
        print("<span style='color:#808080'><i>{}</i></span>".format(keys["flavour"].any))
    if "defence" in keys:
        print(format_values(keys["defence"],
                            "<span style='color:#60A0FF'>Increases physical resistances by {}</span>",
                            "<span style='color:#60A0FF'>Decreases physical resistances by {}</span>",
                            percent=True))
    for t in damage_ranges:
        e = " ({} attacks only)".format(t.replace("_", "")) if t else t
        if "damage" + t in keys:
            print(format_values(keys["damage" + t],
                                "<span style='color:green'>Damage increased by {{}}{}</span>".format(e),
                                "<span style='color:green'>Damage decreased by {{}}{}</span>".format(e),
                                percent=True))
        if "damage" + t + "_plus" in keys:
            print(format_values(keys["damage" + t + "_plus"],
                                "<span style='color:green'>Damage increased by {{}}{}</span>".format(e),
                                "<span style='color:green'>Damage decreased by {{}}{}</span>".format(e)))
    if "attacks" in keys:
        print(format_values(keys["attacks"],
                            "<span style='color:green'>{}% more attacks</span>",
                            "<span style='color:green'>{}% fewer attacks</span>",
                            percent=sort in weapon_sorts))
    if "merge" in keys:
        print("<span style='color:green'>Merges attacks</span>")
    if "damage_type" in keys:
        print(format_values(keys["damage_type"],
                            "<span style='color:green'>Sets damage type to {}</span>"))
    if "suck" in keys:
        print(format_values(keys["suck"],
                            "<span style='color:#60A0FF'>Sucks {} health from targets with each hit</span>"))
    if "spell_suck" in keys:
        print(format_values(keys["spell_suck"],
                            "<span style='color:#60A0FF'>Spells suck {} health from targets with each hit</span>"))
    if "devastating_blow" in keys:
        print(format_values(keys["devastating_blow"],
                            "<span style='color:#60A0FF'>{} chance to strike a devastating blow</span>",
                            percent=True))
    for t in damage_types:
        if t + "_penetrate" in keys:
            print(format_values(keys[t + "_penetrate"],
                                "<span style='color:green'>Enemy resistances to {} decreased by {{}}</span>".format(t),
                                percent=True))
    for t in damage_ranges:
        e = " ({} attacks only)".format(t.replace("_", "")) if t else t
        for specials in tag.tags["specials" + t]:
            for special in specials.macros:
                name, *args = shlex.split(special)
                real_name = special_name(name.replace("WEAPON_SPECIAL_", ""), args)
                print("<span style='color:green'>New weapon special: {}{}</span>".format(real_name, e))
    if "magic" in keys:
        print(format_values(keys["magic"],
                            "<span style='color:green'>Increases all magical damages by {}</span>",
                            percent=True))
    if "dodge" in keys:
        print(format_values(keys["dodge"],
                            "<span style='color:#60A0FF'>Chance to get hit decreased by {}</span>",
                            percent=True))
    for t in damage_types:
        if t + "_resist" in keys:
            print(format_values(keys[t + "_resist"],
                                "<span style='color:#60A0FF'>Resistance to {} increased by {{}}</span>".format(t),
                                "<span style='color:#60A0FF'>Resistance to {} decreased by {{}}</span>".format(t),
                                percent=True))
    for effect in tag.tags["effect"]:
        if effect.keys["apply_to"].any == "new_ability":
            for specials in effect.tags["abilities"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = ability_name(name.replace("ABILITY_", ""), args)
                    print("<span style='color:#60A0FF'>New ability: {}</span>".format(real_name))
        elif effect.keys["apply_to"].any == "movement":
            print(format_values(effect.keys["increase"],
                                "<span style='color:#60A0FF'>{} more movement points</span>",
                                "<span style='color:#60A0FF'>{} fewer movement points</span>"))
        elif effect.keys["apply_to"].any == "vision":
            print(format_values(effect.keys["vision"],
                                "<span style='color:#60A0FF'>Increases vision range by {}</span>",
                                "<span style='color:#60A0FF'>Decreases vision range by {}</span>"))
        elif effect.keys["apply_to"].any == "hitpoints":
            times = " per level" if "times" in effect.keys and effect.keys["times"].any == "per level" else ""
            if "increase_total" in effect.keys:
                print(format_values(effect.keys["increase_total"],
                                    "<span style='color:#60A0FF'>{{}} more hitpoints per level{}</span>".format(times),
                                    "<span style='color:#60A0FF'>{{}} fewer hitpoints per level{}</span>".format(times)))
            if "heal_full" in effect.keys and effect.keys["heal_full"].any == "yes":
                print("<span style='color=#60A0FF'>Full heal</span>")
        elif effect.keys["apply_to"].any == "defence":
            for defence in effect.tags["defence"]:
                for m, h in defence_types:
                    if m in defence.keys:
                        print(format_values(defence.keys[m],
                                            "<span style='color:#60A0FF'>Chance to get hit {} increased by {{}}</span>".format(h),
                                            "<span style='color:#60A0FF'>Chance to get hit {} reduced by {{}}</span>".format(h),
                                            percent=True))
        elif effect.keys["apply_to"].any == "movement_costs":
            for movement in effect.tags["movement_costs"]:
                for m, h in movement_costs:
                    if m in movement.keys:
                        print(format_values(movement.keys[m],
                                            "<span style='color:#60A0FF'>Movement costs {} set to {{}}</span>".format(h)))
        elif effect.keys["apply_to"].any == "alignment":
            print(format_values(effect.keys["alignment"],
                                "<span style='color:#60A0FF'>Sets alignment to {}</span>"))
        elif effect.keys["apply_to"].any == "status" and effect.keys["add"].any == "not_living":
            print("<span style='color:#60A0FF'>Unlife (immunity to poison, plague and drain)</span>")
        elif effect.keys["apply_to"].any == "new_attack":
            print("<span style='color:green'>New attack: {} ({} - {})</span>".format(effect.keys["name"].any,
                                                                                     effect.keys["damage"].any,
                                                                                     effect.keys["number"].any))
        elif effect.keys["apply_to"].any == "new_advancement":
            print("<span style='color:yellow'>New advancements: {}</span>".format(effect.keys["description"].any))
        elif effect.keys["apply_to"].any in ["attack", "improve_bonus_attack"]:
            bonus = effect.keys["apply_to"].any == "improve_bonus_attack"
            range = wname = wtype = rt = ""
            if "range" in effect.keys:
                range = format_values(effect.keys["range"], "{}")
            if "type" in effect.keys:
                wtype = format_values(effect.keys["type"], "{}")
            if range or wtype:
                rt = " ({}{}{} attacks only)".format(range, " " if range and wtype else "", wtype)
            if "name" in effect.keys:
                wname = format_values(effect.keys["name"], " for the {} attack")
            for specials in effect.tags["set_specials"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = special_name(name.replace("WEAPON_SPECIAL_", ""), args)
                    print("<span style='color:green'>New weapon special{}{}: {}</span>".format(wname, rt, real_name))
            if "remove_specials" in effect.keys:
                print(format_values(effect.keys["remove_specials"],
                                    "<span style='color:green'>Remove weapon special{}{}: {{}}</span>".format(wname, rt)))
            if "increase_damage" in effect.keys:
                print(format_values(effect.keys["increase_damage"],
                                    "<span style='color:green'>Damage increased by {{}}{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>Damage decreased by {{}}{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "increase_attacks" in effect.keys:
                print(format_values(effect.keys["increase_attacks"],
                                    "<span style='color:green'>{{}} more attacks{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>{{}} fewer attacks{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "set_type" in effect.keys:
                print(format_values(effect.keys["set_type"],
                                    "<span style='color:green'>Sets damage type to {{}}{}{}</span>".format(wname, rt)))

    for latent in tag.tags["latent"]:
        value = re.sub("\(requires ([^)]+)\)",
                       lambda m: "(requires [[#{}|{}]])".format(index[m.group(1).lower()], m.group(1)),
                       latent.keys["desc"].any)
        print(re.sub("color='([^']+)'", "style='color:\\1'", value))
    if "description" in keys:
        v = re.sub("color='([^']+)'", "style='color:\\1'", keys["description"].any)
        if "<" not in v:
            v = "<span style='color:#808080'><i>{}</i></span>".format(v)
        print(v)
    print()


def write_advancement(section, name, tag, file, index):
    def print(*a, **kw):
        k = {"file": file, "end": "<br/>\n"}
        k.update(kw)
        return builtins.print(*a, **k)
    keys = tag.keys
    print("===", keys["description"].any, "&ndash;", name, "===", end="\n")
    if "max_times" in keys:
        print("<span style='color:#808080'><i>This advancement can be taken {}</i></span>".format(keys["max_times"].any + " times" if keys["max_times"].any != "1" else "once"))
    if "require_amla" in keys and keys["require_amla"].any not in ["{LEGACY}", ""]:
        amlas = [n.strip() for n in keys["require_amla"].any.split(",")]
        amlas = english_join("[[#{}|{}]]".format(index.get(section, n), n) if index.get(section, n) != "" else n for n in amlas)
        print("<span style='color:#808080'><i>This advancement requires the advancement{} to be achieved first</i></span>".format(amlas))
    for effect in tag.tags["effect"]:
        if effect.keys["apply_to"].any == "new_ability":
            for specials in effect.tags["abilities"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = ability_name(name.replace("ABILITY_", ""), args)
                    print("<span style='color:#60A0FF'>New ability: {}</span>".format(real_name))
        elif effect.keys["apply_to"].any == "remove_ability":
            for specials in effect.tags["abilities"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = ability_name(name.replace("ABILITY_", ""), args)
                    print("<span style='color:#60A0FF'>Remove ability: {}</span>".format(real_name))
        elif effect.keys["apply_to"].any == "movement":
            print(format_values(effect.keys["increase"],
                                "<span style='color:#60A0FF'>{} more movement points</span>",
                                "<span style='color:#60A0FF'>{} fewer movement points</span>"))
        elif effect.keys["apply_to"].any == "vision":
            print(format_values(effect.keys["vision"],
                                "<span style='color:#60A0FF'>Increases vision range by {}</span>",
                                "<span style='color:#60A0FF'>Decreases vision range by {}</span>"))
        elif effect.keys["apply_to"].any == "hitpoints":
            times = " per level" if "times" in effect.keys and effect.keys["times"].any == "per level" else ""
            if "increase_total" in effect.keys:
                print(format_values(effect.keys["increase_total"],
                                    "<span style='color:#60A0FF'>{{}} more hitpoints per level{}</span>".format(times),
                                    "<span style='color:#60A0FF'>{{}} fewer hitpoints per level{}</span>".format(times)))
            if "heal_full" in effect.keys and effect.keys["heal_full"].any == "yes":
                print("<span style='color=#60A0FF'>Full heal</span>")
        elif effect.keys["apply_to"].any == "defence":
            for defence in effect.tags["defence"]:
                for m, h in defence_types:
                    if m in defence.keys:
                        print(format_values(defence.keys[m],
                                            "<span style='color:#60A0FF'>Chance to get hit {} increased by {{}}</span>".format(h),
                                            "<span style='color:#60A0FF'>Chance to get hit {} reduced by {{}}</span>".format(h),
                                            percent=True))
        elif effect.keys["apply_to"].any == "movement_costs":
            for movement in effect.tags["movement_costs"]:
                for m, h in movement_costs:
                    if m in movement.keys:
                        print(format_values(movement.keys[m],
                                            "<span style='color:#60A0FF'>Movement costs {} set to {{}}</span>".format(h)))
        elif effect.keys["apply_to"].any == "alignment":
            print(format_values(effect.keys["alignment"],
                                "<span style='color:#60A0FF'>Sets alignment to {}</span>"))
        elif effect.keys["apply_to"].any == "status" and effect.keys["add"].any == "not_living":
            print("<span style='color:#60A0FF'>Unlife (immunity to poison, plague and drain)</span>")
        elif effect.keys["apply_to"].any == "new_attack":
            print("<span style='color:green'>New attack: {} ({} - {})</span>".format(effect.keys["name"].any,
                                                                                     effect.keys["damage"].any,
                                                                                     effect.keys["number"].any))
            wname = format_values(effect.keys["name"], " for the {} attack")
            for specials in effect.tags["specials"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = special_name(name.replace("WEAPON_SPECIAL_", ""), args)
                    print("<span style='color:green'>New weapon special{}: {}</span>".format(wname, real_name))
        elif effect.keys["apply_to"].any == "new_advancement":
            print("<span style='color:yellow'>New advancements: {}</span>".format(effect.keys["description"].any))
        elif effect.keys["apply_to"].any in ["attack", "improve_bonus_attack"]:
            bonus = effect.keys["apply_to"].any == "improve_bonus_attack"
            range = wname = wtype = rt = ""
            if "range" in effect.keys:
                range = format_values(effect.keys["range"], "{}")
            if "type" in effect.keys:
                wtype = format_values(effect.keys["type"], "{}")
            if range or wtype:
                rt = " ({}{}{} attacks only)".format(range, " " if range and wtype else "", wtype)
            if "name" in effect.keys:
                wname = format_values(effect.keys["name"], " for the {} attack")
            for specials in effect.tags["set_specials"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = special_name(name.replace("WEAPON_SPECIAL_", ""), args)
                    print("<span style='color:green'>New weapon special{}{}: {}</span>".format(wname, rt, real_name))
            if "remove_specials" in effect.keys:
                print(format_values(effect.keys["remove_specials"],
                                    "<span style='color:green'>Remove weapon special{}{}: {{}}</span>".format(wname, rt)))
            if "increase_damage" in effect.keys:
                print(format_values(effect.keys["increase_damage"],
                                    "<span style='color:green'>Damage increased by {{}}{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>Damage decreased by {{}}{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "increase_attacks" in effect.keys:
                print(format_values(effect.keys["increase_attacks"],
                                    "<span style='color:green'>{{}} more attacks{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>{{}} fewer attacks{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "set_type" in effect.keys:
                print(format_values(effect.keys["set_type"],
                                    "<span style='color:green'>Sets damage type to {{}}{}{}</span>".format(wname, rt)))
        elif effect.keys["apply_to"].any == "resistance":
            for resistances in effect.tags["resistance"]:
                for t in damage_types:
                    if t in resistances.keys:
                        print(format_values(resistances.keys[t],
                                            "<span style='color:#60A0FF'>Resistance to {} decreased by {{}}</span>".format(t),
                                            "<span style='color:#60A0FF'>Resistance to {} increased by {{}}</span>".format(t),
                                            percent=True, invert=True))
        elif effect.keys["apply_to"].any == "defense":
            for defence in effect.tags["defense"]:
                for m, h in defence_types:
                    if m in defence.keys:
                        print(format_values(defence.keys[m],
                                            "<span style='color:#60A0FF'>Chance to get hit {} increased by {{}}</span>".format(h),
                                            "<span style='color:#60A0FF'>Chance to get hit {} reduced by {{}}</span>".format(h),
                                            percent=True))
        elif effect.keys["apply_to"].any == "bonus_attack":
            print("<span style='color:green'>New bonus attack: {} ({}% - {}% {} {})</span>".format(effect.keys["name"].any,
                                                                                                   effect.keys["damage"].any,
                                                                                                   effect.keys["number"].any,
                                                                                                   effect.keys["range"].any,
                                                                                                   effect.keys["type"].any))
            wname = format_values(effect.keys["name"], " for the {} attack")
            for specials in effect.tags["specials"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = special_name(name.replace("WEAPON_SPECIAL_", ""), args)
                    print("<span style='color:green'>New weapon special{}: {}</span>".format(wname, real_name))
    print()



def write_ability(section, name, type, macro_name, tag, file):
    def print(*a, **kw):
        k = {"file": file, "end": "<br/>\n"}
        k.update(kw)
        return builtins.print(*a, **k)
    keys = tag.keys
    print("===", keys["name"].any, "&ndash;", type, "===", end="\n")
    print(re.sub("([^\n]+)", "<span style='color:#808080'><i>\\1</i></span>", keys["description"].any))
    print()


def auto_upload():
    import requests, getpass, bs4

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    s = requests.Session()
    r = s.get("https://wiki.wesnoth.org/index.php?title=Special:UserLogin")
    if r.status_code != 200:
        print("Login request failed")
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    token = soup.find("form").find("input", type="hidden")["value"]
    r = s.post("https://wiki.wesnoth.org/index.php?title=Special:UserLogin&action=submitlogin&type=login", data={"wpName": username,
                                                                                                                 "wpPassword": password,
                                                                                                                 "wpLoginAttempt": "Log in",
                                                                                                                 "wpLoginToken": token
                                                                                                                 })
    if r.status_code != 200:
        print("Login submit failed")
    print("Logging in successful")

    # save action
    for title, fname in [
        ("LotI Items", "items.wiki"),
        ("LotI Abilities", "abilities.wiki"),
        ("LotI Standard Advancements", "advancements_standard.wiki"),
        ("LotI Unit Advancements", "advancements_units.wiki")
        ]:
        print("Updating", title + "...")
        r = s.get("https://wiki.wesnoth.org/index.php?title=" + title + "&action=edit")
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        form = soup.find("form")
        payload = {i["name"]: i.get("value") for i in form.find_all("input")}
        payload["wpSummary"] = "Automated update by " + username
        payload["wpScrolltop"] = "0"
        del payload["wpPreview"]
        del payload["wpDiff"]
        payload["wpTextbox1"] = open(fname).read()
        r = s.post("https://wiki.wesnoth.org/index.php?title=" + title + "&action=edit", data=payload, allow_redirects=False)
        if r.status_code != 302:
            print("Update of page", title, "failed")
        else:
            print("Update of", title, "successful")


def main():
    global ability_name, special_name

    parser = argparse.ArgumentParser()
    parser.add_argument("LoTIdir")
    parser.add_argument("--version", nargs=1, default=None)
    parser.add_argument("--autoupload", action="store_true")

    args = parser.parse_args()

    start = pathlib.Path(args.LoTIdir).resolve()
    print("LotI Scraper version", __version__, "loading from directory", start)

    if args.version is None:
        print("Scanning info...")
        if (start / "_info.cfg").exists():
            info = parse_wml(tokenize((start / "_info.cfg").open().read()))
            version = info.tags["info"][0].keys["version"].any
        else:
            version = "git-" + subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=start).decode().strip()
    else:
        version = args.version[0]

    print("LotI version is", version)

    def sort_by_first(x):
        if x[0] == "GENERIC_AMLA_ADVANCEMENTS":
            return "0" + x[0]
        if x[0] == "ADDITIONAL_AMLA":
            return "1" + x[0]
        if x[0][0] == "S":
            return "2" + x[0]
        return "3" + x[0]

    def sort_by_not_last(x):
        return list(map(str.lower, x[:-1]))

    print("Scanning standard advancements...")
    advancements_standard = list(extract_utils_amla_advancements(start / "utils" / "amla.cfg"))
    advancements_standard.sort(key=sort_by_first)

    print("Scanning unit advancements...")
    advancements_units = list(extract_advancements(start / "units"))
    advancements_units.sort(key=lambda x: x[0].lower())

    print("Scanning abilities...")
    abilities = list(extract_abilities(start))
    abilities.sort(key=sort_by_not_last)
    ability_index = make_ability_index(abilities)

    def ability_name(*args, old=ability_name):
        return old(ability_index, *args)


    def special_name(*args, old=special_name):
        return old(ability_index, *args)


    print("Scanning items...")
    items = list(extract_items(start))
    items.sort(key=sort_by_not_last)

    print("Found", len(abilities), "abilities,",len(advancements_standard), "standard advancements,",
          len(advancements_units), "unit advancements and", len(items), "items")

    print("Writing item information to items.wiki")
    with open("items.wiki", "w") as items_file:
        print(header.format("all the items", "", version), file=items_file)

        index = make_item_index(items)
        for item in items:
            write_item(*item, items_file, index)

    print("Writing ability information to abilities.wiki")
    with open("abilities.wiki", "w") as ability_file:
        print(header.format("all the abilities and weapon specials", "", version), file=ability_file)

        #index = make_item_index(items)
        for section, abilities in itertools.groupby(abilities, lambda x: x[0]):
            print("==", section, "==", file=ability_file)
            for ab in abilities:
                write_ability(*ab, ability_file)

    print("Writing standard advancement information to advancements_standard.wiki")
    with open("advancements_standard.wiki", "w") as adv_standard_file:
        print(header.format("all the advancements avalible for catagories of units",
                            "See https://wiki.wesnoth.org/LotI_Unit_Advancements for unit specific advancements.",
                            version), file=adv_standard_file)

        index = make_adv_index(advancements_standard)
        for section, advs in itertools.groupby(advancements_standard, sort_by_first):
            section = section[1:]
            if section == "GENERIC_AMLA_ADVANCEMENTS":
                section = "Legacies and Books"
            elif section == "ADDITIONAL_AMLA":
                section = "Soul Eater and God Advancements"
            else:
                section = english_title(section.replace("_", " ").replace("AMLA ", ""))
            print("==", english_title(section), "==", file=adv_standard_file)
            print(file=adv_standard_file)
            for adv in advs:
                write_advancement(*adv, adv_standard_file, index)
            print(file=adv_standard_file)

    print("Writing unit advancement information to advancements_units.wiki")
    with open("advancements_units.wiki", "w") as adv_units_file:
        print(header.format("all the advancements that are unit specific",
                            "See https://wiki.wesnoth.org/LotI_Standard_Advancements for general advancements such as legacies and books.",
                            version), file=adv_units_file)

        index = make_adv_index(advancements_units)
        for section, advs in itertools.groupby(advancements_units, lambda x: x[0]):
            print("==", section, "==", file=adv_units_file)
            advs = list(advs)
            print("<span style='color:#808080'><i>{}</i></span>".format(advs[0][-1].replace("\n", "<br/>\n")), file=adv_units_file)
            print(file=adv_units_file)
            for adv in advs:
                write_advancement(*adv[:-1], adv_units_file, index)
            print(file=adv_units_file)

    if args.autoupload:
        auto_upload()

    print("All done!")


if __name__ == "__main__":
    main()
