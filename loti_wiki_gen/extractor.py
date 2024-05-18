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
import string

from . import utils, wml_parser

BUG_DETECT = False


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


def special_notes_sub(str):
    for name, note in sorted(
        special_notes_translation.items(), key=lambda kv: -1 * len(kv[0])
    ):
        # substitute the names in reverse length order since some names may be substrings of another name
        str = str.replace(name, note)
    return (
        str.replace("SPECIAL_NOTES", "\nSpecial Notes:").strip().replace("\n\n", "\n")
    )


def extract_abilities(start):
    global special_notes_translation
    fname = start / "utils" / "abilities.cfg"
    stuff = wml_parser.parse(fname.open(encoding="utf-8").read(), fname, 1)
    for name, (macro,) in stuff.tags.items():
        if name.startswith("ABILITY"):
            section = "Abilities"
        elif name.startswith("WEAPON_SPECIAL"):
            section = "Weapon Specials"
        else:
            if name.startswith("SPECIAL_NOTES"):
                special_notes_translation[name] = macro.tags["text"][0]
            continue
        for tag_type, tags in macro.tags.items():
            tags = [t for t in tags if t.keys["name"].any]
            if not tags:
                continue
            elif len(tags) == 1:
                (tag,) = tags
                yield section, tag.keys["name"].any.replace("{", "").replace(
                    "}", ""
                ), tag_type, name, tag
            elif len(tags) == 2:
                a, b = tags
                a.keys["name"].all = a.keys["name"].any + " and " + b.keys["name"].any
                a.keys["description"].all = (
                    a.keys["description"].any + " " + b.keys["description"].any
                )
                yield section, a.keys["name"].any.replace("{", "").replace(
                    "}", ""
                ), tag_type, name, a
            else:
                raise RuntimeError("Cannot merge 3+ tags yet, implement!")


def extract_items(start):
    fname = start / "utils" / "item_list.cfg"
    data = wml_parser.parse(fname.open(encoding="utf-8").read(), fname, 1)
    for tag in data.tags["ITEM_LIST"][0].tags["object"]:
        if "name" in tag.keys and "filter" not in tag.tags:
            yield tag.keys["name"].any, tag


def extract_unit_advancements(start):
    for item in start.iterdir():
        if item.is_dir():
            yield from extract_unit_advancements(item)
        elif item.suffix == ".cfg":
            data = item.open(encoding="utf-8").read()
            if "GENERIC_AMLA" in data:
                amla_mode = "\nThis unit also has generic AMLA advancements"
            elif "SOUL_EATER_AMLA" in data:
                amla_mode = "\nThis unit also has soul eater AMLA advancements"
            elif "AMLA_GOD" in data:
                amla_mode = "\nThis unit also has god AMLA advancements"
            else:
                amla_mode = ""
            data = re.sub(
                "{(?:GENERIC_AMLA|SOUL_EATER_AMLA|AMLA_GOD) [^(]+\((.*)\)[^}]+}",
                "\\1[/unit_type]",
                data,
                0,
                re.DOTALL,
            )
            stuff = wml_parser.parse(data, item, 1)
            fmt_fname = utils.english_title(
                item.stem.replace("_", " ").lstrip(" " + string.digits)
            )
            for unit in stuff.tags["unit_type"]:
                if not unit.keys["name"].any:
                    name = fmt_fname
                elif fmt_fname not in unit.keys["name"].any:
                    name = "{} ({})".format(unit.keys["name"].any, fmt_fname)
                else:
                    name = unit.keys["name"].any
                name = utils.english_title(name.replace("female^", ""))
                desc = special_notes_sub(unit.keys["description"].any) + amla_mode
                for adv in unit.tags["advancement"]:
                    if "id" not in adv.keys:
                        print(adv.keys.keys())
                    adv.keys["description"].all = utils.english_title(
                        adv.keys["description"].any
                    )
                    yield name, adv.keys["id"].any, adv, desc
                for var in unit.tags["variation"]:
                    for adv in var.tags["advancement"]:
                        if "id" not in adv.keys:
                            print(adv.keys.keys())
                        adv.keys["description"].all = utils.english_title(
                            adv.keys["description"].any
                        )
                        yield name, adv.keys["id"].any, adv, desc


def extract_standard_advancements(fname):
    x = wml_parser.parse(fname.open(encoding="utf-8").read(), fname, 1)
    for name, tags in x.tags.items():
        if name.endswith("ADVANCEMENTS") or name in [
            "ADDITIONAL_AMLA",
            "LEGACY_DISCOVERY",
        ]:
            if name == "LEGACY_DISCOVERY":
                name = "GENERIC_AMLA_ADVANCEMENTS"
            for adv in tags[0].tags["advancement"]:
                adv.keys["description"].all = utils.english_title(
                    adv.keys["description"].any
                )
                yield name, utils.english_title(
                    adv.keys["id"].any.removesuffix("_dummy")
                ), adv


def extract_scenarios(start):
    for chapter in start.glob("scenarios*"):
        for fname in chapter.glob("*.cfg"):
            x = wml_parser.parse(fname.open(encoding="utf-8").read(), fname, 1)
            for scenario in x.tags["scenario"]:
                yield (
                    int(chapter.name.replace("scenarios", "")),
                    "{} &ndash; {}".format(
                        fname.name.split("_")[0], scenario.keys["name"].any
                    ),
                    scenario,
                )
