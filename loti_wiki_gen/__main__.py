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
import configparser

from . import wml_parser, extractor, writer, utils, index

__version__ = "0.3.5.1"

header = """
This is an auto-generated wiki page listing {{}} currently available in the campaign "Legend of the Invincibles". {{}}
This was generated at {} using version {{}} of LotI and version {} of the generation script.
As this is auto-generated, DO NOT EDIT THIS PAGE.
Instead, create a new issue at [https://github.com/matsjoyce/LotIWikiGen/issues/new the tracker] and the script will be adjusted.

Other LotI-related wiki pages:

* [[LotI Items]] &ndash; items, such as weapons and books
* [[LotI Standard Advancements]] &ndash; general advancements such as legacies and books
* [[LotI Unit Advancements]] &ndash; unit-specific advancements
* [[LotI Abilities]] &ndash; abilities and weapon specials
* [[LotI Scenarios]] &ndash; scenario information
* [[DeadlyUnitsFromLotI]]
""".lstrip().format(time.ctime(), __version__)


def auto_upload(config):
    import requests
    import getpass
    import bs4

    if config.get("username", None):
        username = config.get("username", None)
        print("Using username", username)
    else:
        username = input("Username: ")

    if config.get("password", None):
        password = config.get("password", None)
        print("Using stored password")
    else:
        password = getpass.getpass("Password: ")

    s = requests.Session()
    r = s.get("https://wiki.wesnoth.org/index.php?title=Special:UserLogin")
    if r.status_code != 200:
        print("Login request failed")
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    token = soup.find("input", {"name": "wpLoginToken"})["value"]
    r = s.post("https://wiki.wesnoth.org/index.php?title=Special:UserLogin&action=submitlogin&type=login",
               data={"wpName": username.title(),
                     "wpPassword": password,
                     "wploginattempt": "Log in",
                     "wpLoginToken": token,
                     "authAction": "login",
                     "title": "Special:UserLogin",
                     "wpEditToken": "+/",
                     "force": ""
                     },
               allow_redirects=False)
    if r.status_code != 302:
        print("Login submit failed")
        return
    print("Logging in successful")

    # save action
    for title, fname in [
            ("LotI Items", "items.wiki"),
            ("LotI Abilities", "abilities.wiki"),
            ("LotI Standard Advancements", "standard_advancements.wiki"),
            ("LotI Unit Advancements", "unit_advancements.wiki"),
            ("LotI Scenarios", "scenarios.wiki")
            ]:
        print("Updating", title + "...")
        r = s.get("https://wiki.wesnoth.org/index.php?title=" + title + "&action=edit")
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        form = soup.find("form", id="editform")
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

    all_config = configparser.ConfigParser()
    all_config.read(["config.ini", "setup.cfg"])

    if "lotigen" in all_config:
        print("Configuration found")
        config = all_config["lotigen"]
    else:
        print("Configuration not found")
        config = {}

    parser = argparse.ArgumentParser(prog="loti_wiki_gen", description="Generate the wiki for LotI")
    if config.get("dir", None):
        kw = {"default": config.get("dir"), "nargs": "?"}
    else:
        kw = {}
    parser.add_argument("dir", help="Path the the root of LotI. ~/.local/share/wesnoth/1.12/data/add-ons/Legend_of_the_Invincibles/ on unix", **kw)
    parser.add_argument("--version", nargs=1, default=None, help="Override version")
    parser.add_argument("--autoupload", action="store_true", help="Upload to the wiki after generation has finished")
    parser.add_argument("--noupdate", action="store_true", help="Do not update <dir> when it is a git repository")
    parser.add_argument("--bug-detect", action="store_true", help="Print information that may be the result of LotI bugs")

    args = parser.parse_args()

    wml_parser.BUG_DETECT = extractor.BUG_DETECT = writer.BUG_DETECT = args.bug_detect

    start = pathlib.Path(args.dir).expanduser().resolve()
    print("LotI Scraper version", __version__, "loading from directory", start)

    if args.version is None:
        print("Scanning info...")
        if (start / "_info.cfg").exists():
            info = wml_parser.parse((start / "_info.cfg").open().read())
            version = info.tags["info"][0].keys["version"].any
        else:
            if not args.noupdate:
                try:
                    subprocess.check_call(["git", "checkout", "master"], cwd=str(start))
                    subprocess.check_call(["git", "pull", "https://github.com/Dugy/Legend_of_the_Invincibles.git", "master"], cwd=str(start))
                except IOError:
                    print("Update of LotI directory failed. If this is not a git repository, provide the version using the --version flag")
                    return
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

    def sort_by_first2(x):
        return x[0].lower()

    def sort_by_type(item):
        type = item[1].keys["sort"].any
        if type in writer.sort_translations:
            type = writer.sort_translations[type]
        return type

    def sort_ability_type(ability):
        type = ability[2]
        if (type == "dummy"):
            type = "Other"
        return type

    print("Scanning standard advancements...")
    standard_advancements = list(extractor.extract_standard_advancements(start / "utils" / "amla.cfg"))
    standard_advancements.sort(key=sort_by_first)

    #extract abilities before unit advancements because some special notes are defined in the ability file
    print("Scanning abilities...")
    abilities = list(extractor.extract_abilities(start))
    abilities.sort(key=sort_by_first2)

    print("Scanning unit advancements...")
    unit_advancements = list(extractor.extract_unit_advancements(start / "units"))
    unit_advancements.sort(key=sort_by_first2)

    print("Scanning items...")
    items = list(extractor.extract_items(start))
    items.sort(key=sort_by_type)

    print("Scanning scenarios...")
    scenarios = list(extractor.extract_scenarios(start))
    scenarios.sort(key=lambda x: x[:2])

    print("Found", len(abilities), "abilities,", len(standard_advancements), "standard advancements,",
          len(unit_advancements), "unit advancements,", len(items), "items and", len(scenarios), "scenarios")

    print("Creating index...")
    idx = index.Index(unit_advancements, standard_advancements, abilities, items, verbose=args.bug_detect)

    print("Writing item information to items.wiki")
    with open("items.wiki", "w", encoding="utf-8") as items_file:
        print(header.format("all the items", "", version), file=items_file)

        for type, items in itertools.groupby(items, sort_by_type):
            print("==", type, "==", file=items_file)
            items = list(items)
            items.sort(key=sort_by_first2)
            for item in items:
                writer.write_item(*item, items_file, idx)


    print("Writing ability information to abilities.wiki")
    with open("abilities.wiki", "w", encoding="utf-8") as ability_file:
        print(header.format("all the abilities and weapon specials", "", version), file=ability_file)

        for section, abilities in itertools.groupby(abilities, sort_by_first2):
            abilities = list(abilities)
            abilities.sort(key = sort_ability_type)
            print("==", abilities[0][0], "==", file=ability_file)
            for type, abs in itertools.groupby(abilities, sort_ability_type):
                print("===", utils.english_title(type.replace("_", " ")), "===", file=ability_file)
                abs = list(abs)
                abs.sort(key = lambda x: x[1])
                for ab in abs:
                    writer.write_ability(*ab, ability_file, idx)

    print("Writing standard advancement information to standard_advancements.wiki")
    with open("standard_advancements.wiki", "w", encoding="utf-8") as adv_standard_file:
        print(header.format("all the advancements available for categories of units",
                            "See [[LotI Standard Advancements]] for unit-specific advancements.",
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
    with open("unit_advancements.wiki", "w", encoding="utf-8") as adv_units_file:
        print(header.format("all the advancements that are unit specific",
                            "See [[LotI Standard Advancements]] for general advancements such as legacies and books.",
                            version), file=adv_units_file)

        for section, advs in itertools.groupby(unit_advancements, sort_by_first2):
            advs = list(advs)
            if advs[0][0] == "Data Loaders":
                continue
            print("==", advs[0][0], "==", file=adv_units_file)
            print("<span style='color:#808080'><i>{}</i></span>".format(advs[0][-1].replace("\n", "<br/>\n")), file=adv_units_file)
            print(file=adv_units_file)
            for adv in advs:
                writer.write_advancement(*adv[:-1], adv_units_file, idx)
            print(file=adv_units_file)

    print("Writing scenario information to scenarios.wiki")
    with open("scenarios.wiki", "w", encoding="utf-8") as scenarios_file:
        print(header.format("all the scenarios",
                            "",
                            version), file=scenarios_file)

        for _, scenarios in itertools.groupby(scenarios, lambda x: x[0]):
            scenarios = list(scenarios)
            print("== Chapter {} ==".format(scenarios[0][0]), file=scenarios_file)
            print(file=scenarios_file)
            for scenario in scenarios:
                if (scenario[1].startswith("test")):
                    continue
                writer.write_scenario(*scenario, scenarios_file)
            print(file=scenarios_file)

    if args.autoupload:
        auto_upload(config)

    print("All done!")


if __name__ == "__main__":
    main()
