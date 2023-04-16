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
import collections


BUG_DETECT = False


wml_regexes = [("key", r"([\w{}]+)\s*=\s*_?\s*\"([^\"]*)\""),
               ("key", r"([\w{}]+)\s*=\s*([^\n]+)\s*\n"),
               ("keys", r"([\w,]+)\s*=\s*([^\n]+)\s*\n"),
               ("open", r"\[\+?([\w{}]+)\]"),
               ("close", r"\[/([\w{}]+)\]"),
               ("macro_open", r"(\{[^{}]+)"),
               ("pre", r"#(define|ifdef|else|endif|enddef|ifver) ?([^\n]*)"),
               ("whitespace", r"(\s+)"),
               ("comment", r"#[^\n]*"),
               ("text", r"_?\s*\"(.*?)\"")]

levels = ["EASY", "MEDIUM", "HARD"]

wml_regexes = [(n, re.compile(r, re.DOTALL)) for n, r in wml_regexes]


WMLTag = collections.namedtuple("WMLTag", ("keys", "tags", "annotation", "macros", "filename"))


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

    def verify(self, name, filename, lineno):
        if BUG_DETECT:
            try:
                direction = name in ("experience", "village_gold")
                if any(i in filename for i in ["Uria", "Demon", "Lilith.", "Romero", "scenarios", "Beelzebub", "Ice_Dragon"]):
                    direction = not direction
                values = list(map(int, [self.EASY, self.MEDIUM, self.HARD]))
                if direction:
                    cond = values == sorted(values)
                else:
                    cond = list(reversed(values)) == sorted(values)
                if not cond:
                    print("BUG DETECT: Possibly inverted difficulty levels {}, {}, {} for key {} at {}:{}".format(*values, name, filename, lineno))
            except ValueError:
                pass


def tokenize(text, lineno, filename):
    macro_transforms = [(r"\"\s*\+\s*\{([^}]*)\}\s*\+\s*_?\s*\"", "\\1"),
                        (r"\{([^}]*)\}\s*\+\s*_?\s*\"", "\"\\1"),
                        (r"\"\s*\+\s*\{([^}]*)\}", "\\1\""),
                        (r"\"\s*\+\s*_?\s*\"", ""),
                        (r"\"\s*\+\s*\$(\S+)", "\\1\""),
                        (r"<<(.*?)>>+", "\"\1\"")
                        ]
    for regex, sub in macro_transforms:
        regex = re.compile(regex, re.MULTILINE + re.DOTALL)
        while regex.search(text):
            text = regex.sub(sub, text)
    while text:
        for type, regex in wml_regexes:
            m = regex.match(text)
            if m:
                groups = m.groups()
                text = text[m.end():]
                if type in ("whitespace", "comment"):
                    pass
                elif type == "keys":
                    yield from (("key", x, lineno)
                                for x in zip(groups[0].split(","), groups[1].split(",")))
                elif type == "macro_open":
                    contents = groups[0]
                    count = 1
                    while count:
                        c = text[0]
                        if c == "{":
                            count += 1
                        if c == "}":
                            count -= 1
                        contents += c
                        text = text[1:]
                    yield "macro", (contents[1:-1],), lineno
                else:
                    yield type, groups, lineno
                lineno += m.group(0).count("\n")
                break
        else:
            raise RuntimeError("Can't parse {} at {}:{}".format(repr(text[:100]), filename, lineno))


def preprocess(tokens):
    tokens = iter(tokens)
    for type, value, lineno in tokens:
        if type == "pre" and value[0] == "ifver":
            nt = next(tokens)
            while nt[:2] != ("pre", ("else", "")):
                yield nt
                nt = next(tokens)
            while nt[:2] != ("pre", ("endif", "")):
                nt = next(tokens)
        else:
            yield type, value, lineno


def subparse_wml(tokens, filename, first_lineno, tag_ann="all"):
    keys = collections.defaultdict(WMLValue)
    tags = collections.defaultdict(list)
    macros = []
    annotation = levels
    tokens = iter(tokens)
    for type, value, lineno in tokens:
        if type == "key":
            name, value = value
            if name == "increse_attacks":
                name = "increase_attacks"
            for l in annotation:
                setattr(keys[name], l, value)
            keys[name].verify(name, filename, lineno)
        if type == "open":
            subtokens = []
            nt = next(tokens)
            count = 0
            while count or nt[:2] != ("close", (value[0],)):
                if nt[:2] == ("open", (value[0],)):
                    count += 1
                if nt[:2] == ("close", (value[0],)):
                    count -= 1
                subtokens.append(nt)
                try:
                    nt = next(tokens)
                except StopIteration:
                    break
            try:
                tag = subparse_wml(subtokens, filename, lineno, annotation)
            except Exception as e:
                print(subtokens)
                print(filename, first_lineno)
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
                keys[name].verify(name, filename, lineno)
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
                while nt[:2] != ("pre", ("enddef", "")):
                    subtokens.append(nt)
                    try:
                        nt = next(tokens)
                    except StopIteration:
                        raise RuntimeError("EOF while parsing macro {}".format(name))
                tag = subparse_wml(subtokens, filename, lineno, annotation)
                tags[name].append(tag)
        if type == "text":
            # text translations for the special notes in the abilities file
            tags["text"] = value
    return WMLTag(keys, tags, tag_ann, macros, "{}:{}".format(filename, first_lineno))


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


def parse(text, filename, lineno):
    print(" -> Parsing", filename)
    return subparse_wml(preprocess(tokenize(text, lineno, filename)), str(filename), lineno)
