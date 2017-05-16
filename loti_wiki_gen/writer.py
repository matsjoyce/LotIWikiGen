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

import shlex
import re

from . import utils


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
    url = index.query_ability("WEAPON_SPECIAL_" + name)
    if url:
        return "[[LotI_Abilities#{}|{}]]".format(url, x)
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
    url = index.query_ability("ABILITY_" + name)
    if url:
        return "[[LotI_Abilities#{}|{}]]".format(url, x)
    return x


def writer(file):
    def write(*a, **kw):
        k = {"file": file, "end": "<br/>\n"}
        k.update(kw)
        return print(*a, **k)
    return write


def write_item(name, tag, file, index):
    write = writer(file)
    sort = tag.keys["sort"].any
    keys = tag.keys
    write("===", name, "&ndash;", format_values(keys["sort"], "{}", sort=True), "===", end="\n")
    if "flavour" in keys:
        write("<span style='color:#808080'><i>{}</i></span>".format(keys["flavour"].any))
    if "defence" in keys:
        write(format_values(keys["defence"],
                            "<span style='color:#60A0FF'>Increases physical resistances by {}</span>",
                            "<span style='color:#60A0FF'>Decreases physical resistances by {}</span>",
                            percent=True))
    for t in damage_ranges:
        e = " ({} attacks only)".format(t.replace("_", "")) if t else t
        if "damage" + t in keys:
            write(format_values(keys["damage" + t],
                                "<span style='color:green'>Damage increased by {{}}{}</span>".format(e),
                                "<span style='color:green'>Damage decreased by {{}}{}</span>".format(e),
                                percent=True))
        if "damage" + t + "_plus" in keys:
            write(format_values(keys["damage" + t + "_plus"],
                                "<span style='color:green'>Damage increased by {{}}{}</span>".format(e),
                                "<span style='color:green'>Damage decreased by {{}}{}</span>".format(e)))
    if "attacks" in keys:
        write(format_values(keys["attacks"],
                            "<span style='color:green'>{} more attacks</span>",
                            "<span style='color:green'>{} fewer attacks</span>",
                            percent=sort in weapon_sorts))
    if "merge" in keys:
        write("<span style='color:green'>Merges attacks</span>")
    if "damage_type" in keys:
        write(format_values(keys["damage_type"],
                            "<span style='color:green'>Sets damage type to {}</span>"))
    if "suck" in keys:
        write(format_values(keys["suck"],
                            "<span style='color:#60A0FF'>Sucks {} health from targets with each hit</span>"))
    if "spell_suck" in keys:
        write(format_values(keys["spell_suck"],
                            "<span style='color:#60A0FF'>Spells suck {} health from targets with each hit</span>"))
    if "devastating_blow" in keys:
        write(format_values(keys["devastating_blow"],
                            "<span style='color:#60A0FF'>{} chance to strike a devastating blow</span>",
                            percent=True))
    for t in damage_types:
        if t + "_penetrate" in keys:
            write(format_values(keys[t + "_penetrate"],
                                "<span style='color:green'>Enemy resistances to {} decreased by {{}}</span>".format(t),
                                percent=True))
    for t in damage_ranges:
        e = " ({} attacks only)".format(t.replace("_", "")) if t else t
        for specials in tag.tags["specials" + t]:
            for special in specials.macros:
                name, *args = shlex.split(special)
                real_name = special_name(index, name.replace("WEAPON_SPECIAL_", ""), args)
                write("<span style='color:green'>New weapon special: {}{}</span>".format(real_name, e))
    if "magic" in keys:
        write(format_values(keys["magic"],
                            "<span style='color:green'>Increases all magical damages by {}</span>",
                            percent=True))
    if "dodge" in keys:
        write(format_values(keys["dodge"],
                            "<span style='color:#60A0FF'>Chance to get hit decreased by {}</span>",
                            percent=True))
    for t in damage_types:
        if t + "_resist" in keys:
            write(format_values(keys[t + "_resist"],
                                "<span style='color:#60A0FF'>Resistance to {} increased by {{}}</span>".format(t),
                                "<span style='color:#60A0FF'>Resistance to {} decreased by {{}}</span>".format(t),
                                percent=True))
    for effect in tag.tags["effect"]:
        if effect.keys["apply_to"].any == "new_ability":
            for specials in effect.tags["abilities"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = ability_name(index, name.replace("ABILITY_", ""), args)
                    write("<span style='color:#60A0FF'>New ability: {}</span>".format(real_name))
        elif effect.keys["apply_to"].any == "movement":
            write(format_values(effect.keys["increase"],
                                "<span style='color:#60A0FF'>{} more movement points</span>",
                                "<span style='color:#60A0FF'>{} fewer movement points</span>"))
        elif effect.keys["apply_to"].any == "vision":
            write(format_values(effect.keys["vision"],
                                "<span style='color:#60A0FF'>Increases vision range by {}</span>",
                                "<span style='color:#60A0FF'>Decreases vision range by {}</span>"))
        elif effect.keys["apply_to"].any == "hitpoints":
            times = " per level" if "times" in effect.keys and effect.keys["times"].any == "per level" else ""
            if "increase_total" in effect.keys:
                write(format_values(effect.keys["increase_total"],
                                    "<span style='color:#60A0FF'>{{}} more hitpoints per level{}</span>".format(times),
                                    "<span style='color:#60A0FF'>{{}} fewer hitpoints per level{}</span>".format(times)))
            if "heal_full" in effect.keys and effect.keys["heal_full"].any == "yes":
                write("<span style='color=#60A0FF'>Full heal</span>")
        elif effect.keys["apply_to"].any == "defence":
            for defence in effect.tags["defence"]:
                for m, h in defence_types:
                    if m in defence.keys:
                        write(format_values(defence.keys[m],
                                            "<span style='color:#60A0FF'>Chance to get hit {} increased by {{}}</span>".format(h),
                                            "<span style='color:#60A0FF'>Chance to get hit {} reduced by {{}}</span>".format(h),
                                            percent=True))
        elif effect.keys["apply_to"].any == "movement_costs":
            for movement in effect.tags["movement_costs"]:
                for m, h in movement_costs:
                    if m in movement.keys:
                        write(format_values(movement.keys[m],
                                            "<span style='color:#60A0FF'>Movement costs {} set to {{}}</span>".format(h)))
        elif effect.keys["apply_to"].any == "alignment":
            write(format_values(effect.keys["alignment"],
                                "<span style='color:#60A0FF'>Sets alignment to {}</span>"))
        elif effect.keys["apply_to"].any == "status" and effect.keys["add"].any == "not_living":
            write("<span style='color:#60A0FF'>Unlife (immunity to poison, plague and drain)</span>")
        elif effect.keys["apply_to"].any == "new_attack":
            write("<span style='color:green'>New attack: {} ({} - {})</span>".format(effect.keys["name"].any,
                                                                                     effect.keys["damage"].any,
                                                                                     effect.keys["number"].any))
        elif effect.keys["apply_to"].any == "new_advancement":
            write("<span style='color:yellow'>New advancements: {}</span>".format(effect.keys["description"].any))
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
                    real_name = special_name(index, name.replace("WEAPON_SPECIAL_", ""), args)
                    write("<span style='color:green'>New weapon special{}{}: {}</span>".format(wname, rt, real_name))
            if "remove_specials" in effect.keys:
                write(format_values(effect.keys["remove_specials"],
                                    "<span style='color:green'>Remove weapon special{}{}: {{}}</span>".format(wname, rt)))
            if "increase_damage" in effect.keys:
                write(format_values(effect.keys["increase_damage"],
                                    "<span style='color:green'>Damage increased by {{}}{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>Damage decreased by {{}}{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "increase_attacks" in effect.keys:
                write(format_values(effect.keys["increase_attacks"],
                                    "<span style='color:green'>{{}} more attacks{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>{{}} fewer attacks{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "set_type" in effect.keys:
                write(format_values(effect.keys["set_type"],
                                    "<span style='color:green'>Sets damage type to {{}}{}{}</span>".format(wname, rt)))

    for latent in tag.tags["latent"]:
        value = re.sub("\(requires ([^)]+)\)",
                       lambda m: "(requires [[#{}|{}]])".format(index.query_item(m.group(1).lower()), m.group(1)),
                       latent.keys["desc"].any)
        write(re.sub("color='([^']+)'", "style='color:\\1'", value))
    if "description" in keys:
        v = re.sub("color='([^']+)'", "style='color:\\1'", keys["description"].any)
        if "<" not in v:
            v = "<span style='color:#808080'><i>{}</i></span>".format(v)
        write(v)
    write()


def write_advancement(section, name, tag, file, index):
    write = writer(file)
    keys = tag.keys
    write("===", keys["description"].any, "&ndash;", name, "===", end="\n")
    if "max_times" in keys:
        write("<span style='color:#808080'><i>This advancement can be taken {}</i></span>".format(keys["max_times"].any + " times" if keys["max_times"].any != "1" else "once"))
    if "require_amla" in keys and keys["require_amla"].any not in ["{LEGACY}", ""]:
        amlas = [n.strip() for n in keys["require_amla"].any.split(",")]
        amlas = utils.english_join("[[#{}|{}]]".format(index.query_advancement(section, n), n) if index.query_advancement(section, n) else n for n in amlas)
        write("<span style='color:#808080'><i>This advancement requires the advancement{} to be achieved first</i></span>".format(amlas))
    for effect in tag.tags["effect"]:
        if effect.keys["apply_to"].any == "new_ability":
            for specials in effect.tags["abilities"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = ability_name(index, name.replace("ABILITY_", ""), args)
                    write("<span style='color:#60A0FF'>New ability: {}</span>".format(real_name))
        elif effect.keys["apply_to"].any == "remove_ability":
            for specials in effect.tags["abilities"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = ability_name(index, name.replace("ABILITY_", ""), args)
                    write("<span style='color:#60A0FF'>Remove ability: {}</span>".format(real_name))
        elif effect.keys["apply_to"].any == "movement":
            write(format_values(effect.keys["increase"],
                                "<span style='color:#60A0FF'>{} more movement points</span>",
                                "<span style='color:#60A0FF'>{} fewer movement points</span>"))
        elif effect.keys["apply_to"].any == "vision":
            write(format_values(effect.keys["vision"],
                                "<span style='color:#60A0FF'>Increases vision range by {}</span>",
                                "<span style='color:#60A0FF'>Decreases vision range by {}</span>"))
        elif effect.keys["apply_to"].any == "hitpoints":
            times = " per level" if "times" in effect.keys and effect.keys["times"].any == "per level" else ""
            if "increase_total" in effect.keys:
                write(format_values(effect.keys["increase_total"],
                                    "<span style='color:#60A0FF'>{{}} more hitpoints per level{}</span>".format(times),
                                    "<span style='color:#60A0FF'>{{}} fewer hitpoints per level{}</span>".format(times)))
            if "heal_full" in effect.keys and effect.keys["heal_full"].any == "yes":
                write("<span style='color=#60A0FF'>Full heal</span>")
        elif effect.keys["apply_to"].any == "defence":
            for defence in effect.tags["defence"]:
                for m, h in defence_types:
                    if m in defence.keys:
                        write(format_values(defence.keys[m],
                                            "<span style='color:#60A0FF'>Chance to get hit {} increased by {{}}</span>".format(h),
                                            "<span style='color:#60A0FF'>Chance to get hit {} reduced by {{}}</span>".format(h),
                                            percent=True))
        elif effect.keys["apply_to"].any == "movement_costs":
            for movement in effect.tags["movement_costs"]:
                for m, h in movement_costs:
                    if m in movement.keys:
                        write(format_values(movement.keys[m],
                                            "<span style='color:#60A0FF'>Movement costs {} set to {{}}</span>".format(h)))
        elif effect.keys["apply_to"].any == "alignment":
            write(format_values(effect.keys["alignment"],
                                "<span style='color:#60A0FF'>Sets alignment to {}</span>"))
        elif effect.keys["apply_to"].any == "status" and effect.keys["add"].any == "not_living":
            write("<span style='color:#60A0FF'>Unlife (immunity to poison, plague and drain)</span>")
        elif effect.keys["apply_to"].any == "new_attack":
            write("<span style='color:green'>New attack: {} ({} - {})</span>".format(effect.keys["name"].any,
                                                                                     effect.keys["damage"].any,
                                                                                     effect.keys["number"].any))
            wname = format_values(effect.keys["name"], " for the {} attack")
            for specials in effect.tags["specials"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = special_name(index, name.replace("WEAPON_SPECIAL_", ""), args)
                    write("<span style='color:green'>New weapon special{}: {}</span>".format(wname, real_name))
        elif effect.keys["apply_to"].any == "new_advancement":
            write("<span style='color:yellow'>New advancements: {}</span>".format(effect.keys["description"].any))
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
                    real_name = special_name(index, name.replace("WEAPON_SPECIAL_", ""), args)
                    write("<span style='color:green'>New weapon special{}{}: {}</span>".format(wname, rt, real_name))
            if "remove_specials" in effect.keys:
                write(format_values(effect.keys["remove_specials"],
                                    "<span style='color:green'>Remove weapon special{}{}: {{}}</span>".format(wname, rt)))
            if "increase_damage" in effect.keys:
                write(format_values(effect.keys["increase_damage"],
                                    "<span style='color:green'>Damage increased by {{}}{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>Damage decreased by {{}}{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "increase_attacks" in effect.keys:
                write(format_values(effect.keys["increase_attacks"],
                                    "<span style='color:green'>{{}} more attacks{}{}</span>".format(wname, rt),
                                    "<span style='color:green'>{{}} fewer attacks{}{}</span>".format(wname, rt),
                                    percent=bonus))
            if "set_type" in effect.keys:
                write(format_values(effect.keys["set_type"],
                                    "<span style='color:green'>Sets damage type to {{}}{}{}</span>".format(wname, rt)))
        elif effect.keys["apply_to"].any == "resistance":
            for resistances in effect.tags["resistance"]:
                for t in damage_types:
                    if t in resistances.keys:
                        write(format_values(resistances.keys[t],
                                            "<span style='color:#60A0FF'>Resistance to {} decreased by {{}}</span>".format(t),
                                            "<span style='color:#60A0FF'>Resistance to {} increased by {{}}</span>".format(t),
                                            percent=True, invert=True))
        elif effect.keys["apply_to"].any == "defense":
            for defence in effect.tags["defense"]:
                for m, h in defence_types:
                    if m in defence.keys:
                        write(format_values(defence.keys[m],
                                            "<span style='color:#60A0FF'>Chance to get hit {} increased by {{}}</span>".format(h),
                                            "<span style='color:#60A0FF'>Chance to get hit {} reduced by {{}}</span>".format(h),
                                            percent=True))
        elif effect.keys["apply_to"].any == "bonus_attack":
            write("<span style='color:green'>New bonus attack: {} ({}% - {}% {} {})</span>".format(effect.keys["name"].any,
                                                                                                   effect.keys["damage"].any,
                                                                                                   effect.keys["number"].any,
                                                                                                   effect.keys["range"].any,
                                                                                                   effect.keys["type"].any))
            wname = format_values(effect.keys["name"], " for the {} attack")
            for specials in effect.tags["specials"]:
                for special in specials.macros:
                    name, *args = shlex.split(special)
                    real_name = special_name(index, name.replace("WEAPON_SPECIAL_", ""), args)
                    write("<span style='color:green'>New weapon special{}: {}</span>".format(wname, real_name))
    write()


def write_ability(section, name, type, macro_name, tag, file, index):
    write = writer(file)
    keys = tag.keys
    write("===", keys["name"].any, "&ndash;", type, "===", end="\n")
    write(re.sub("([^\n]+)", "<span style='color:#808080'><i>\\1</i></span>", keys["description"].any))
    write()


def write_scenario(chapter, name, tag, file):
    write = writer(file)
    write("===", name, "===", end="\n")
    drops = []
    for macro in tag.macros:
        if macro.startswith("DROPS"):
            drops.append(macro.split()[1:])
    if drops:
        assert len(drops) == 1
        chance, chance_gem, weapons, bosses, enemies = drops[0]
        weapons = weapons.replace("(", "").replace(")", "").split(",")
        write("<span style='color:green'>Chance of a dying enemy on the side" + utils.english_join(enemies.split(",")), "dropping a weapon is {}%</span>".format(chance))
        write("<span style='color:green'>Chance of a dying enemy on the side" + utils.english_join(enemies.split(",")), "dropping a gem is {}%</span>".format(chance_gem))
        if bosses != "yes":
            write("<span style='color:#B81413'>Enemy bosses do not always drop</span>")
        for weapon_type in set(weapons):
            write("<span style='color:#60A0FF'>Chance of a {} dropping is {:.0%}</span>".format(weapon_type, weapons.count(weapon_type) / len(weapons)))
    else:
        write("<span style='color:#808080'><i>No drop information found</i></span>")
    write()
