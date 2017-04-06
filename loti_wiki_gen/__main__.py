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
import itertools
import time
import subprocess

from . import wml_parser, extractor, writer, utils, index, config

__version__ = "0.3.5"

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


def auto_upload():
    import requests
    import getpass
    import bs4

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    s = requests.Session()
    r = s.get("https://wiki.wesnoth.org/index.php?title=Special:UserLogin")
    if r.status_code != 200:
        print("Login request failed")
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    token = soup.find("form").find("input", type="hidden")["value"]
    r = s.post("https://wiki.wesnoth.org/index.php?title=Special:UserLogin&action=submitlogin&type=login",
               data={"wpName": username,
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
            ("LotI Standard Advancements", "standard_advancements.wiki"),
            ("LotI Unit Advancements", "unit_advancements.wiki")
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

    conf = config.Config()
    parser = argparse.ArgumentParser(prog="loti_wiki_gen", description="Generate the wiki for LotI")
    parser.add_argument("--version", nargs=1, default=None, help="Override version")
    parser.add_argument("--autoupload", action="store_true", help="Upload to the wiki after generation has finished")

    args = parser.parse_args()

    start = pathlib.Path(conf.get_dir())
    print("LotI Scraper version", __version__, "loading from directory", start)

    if args.version is None:
        print("Scanning info...")
        if (start / "_info.cfg").exists():
            info = wml_parser.parse((start / "_info.cfg").open().read())
            version = info.tags["info"][0].keys["version"].any
        else:
            version = "git-" + subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(start)).decode().strip()
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

    def sort_by_all_but_not_last(x):
        return list(map(str.lower, x[:-1]))

    def sort_by_first2(x):
        return x[0].lower()

    print("Scanning standard advancements...")
    standard_advancements = list(extractor.extract_standard_advancements(start / "utils" / "amla.cfg"))
    standard_advancements.sort(key=sort_by_first)

    print("Scanning unit advancements...")
    unit_advancements = list(extractor.extract_unit_advancements(start / "units"))
    unit_advancements.sort(key=sort_by_first2)

    print("Scanning abilities...")
    abilities = list(extractor.extract_abilities(start))
    abilities.sort(key=sort_by_all_but_not_last)

    print("Scanning items...")
    items = list(extractor.extract_items(start))
    items.sort(key=sort_by_all_but_not_last)

    print("Found", len(abilities), "abilities,", len(standard_advancements), "standard advancements,",
          len(unit_advancements), "unit advancements and", len(items), "items")

    print("Creating index...")
    idx = index.Index(unit_advancements, standard_advancements, abilities, items)

    print("Writing item information to items.wiki")
    with open("items.wiki", "w") as items_file:
        print(header.format("all the items", "", version), file=items_file)

        for item in items:
            writer.write_item(*item, items_file, idx)

    print("Writing ability information to abilities.wiki")
    with open("abilities.wiki", "w") as ability_file:
        print(header.format("all the abilities and weapon specials", "", version), file=ability_file)

        for section, abilities in itertools.groupby(abilities, sort_by_first2):
            abilities = list(abilities)
            print("==", abilities[0][0], "==", file=ability_file)
            for ab in abilities:
                writer.write_ability(*ab, ability_file, idx)

    print("Writing standard advancement information to standard_advancements.wiki")
    with open("standard_advancements.wiki", "w") as adv_standard_file:
        print(header.format("all the advancements avalible for catagories of units",
                            "See https://wiki.wesnoth.org/LotI_Unit_Advancements for unit specific advancements.",
                            version), file=adv_standard_file)

        for section, advs in itertools.groupby(standard_advancements, sort_by_first):
            section = section[1:]
            if section == "GENERIC_AMLA_ADVANCEMENTS":
                section = "Legacies and Books"
            elif section == "ADDITIONAL_AMLA":
                section = "Soul Eater and God Advancements"
            else:
                section = utils.english_title(section.replace("_", " ").replace("AMLA ", ""))
            print("==", utils.english_title(section), "==", file=adv_standard_file)
            print(file=adv_standard_file)
            for adv in advs:
                writer.write_advancement(*adv, adv_standard_file, idx)
            print(file=adv_standard_file)

    print("Writing unit advancement information to unit_advancements.wiki")
    with open("unit_advancements.wiki", "w") as adv_units_file:
        print(header.format("all the advancements that are unit specific",
                            "See https://wiki.wesnoth.org/LotI_Standard_Advancements for general advancements such as legacies and books.",
                            version), file=adv_units_file)

        for section, advs in itertools.groupby(unit_advancements, sort_by_first2):
            advs = list(advs)
            print("==", advs[0][0], "==", file=adv_units_file)
            print("<span style='color:#808080'><i>{}</i></span>".format(advs[0][-1].replace("\n", "<br/>\n")), file=adv_units_file)
            print(file=adv_units_file)
            for adv in advs:
                writer.write_advancement(*adv[:-1], adv_units_file, idx)
            print(file=adv_units_file)

    if args.autoupload:
        auto_upload()

    print("All done!")


if __name__ == "__main__":
    main()
