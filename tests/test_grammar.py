"""`docs/specification.md` §4's ABNF against the named types' patterns in the contract.

The grammar of ids, addresses, references, option references and conditions is written twice: as ABNF in §4, and as
the id setting and the structured patterns of `types.yaml`. D8 keeps one statement of each fact "so the two can't
drift", and this test ties the two. It reads §4's `abnf` fence, translates each rule to a regular expression, and
compares each rule named after a type (`-` read as `_`) with that type's pattern in `analysis.schema.json`, on every
string of up to `MAX_LENGTH` characters over `ALPHABET`.

The translator takes the subset of RFC 5234 that §4 uses: concatenation, `/`, `*( )`, `[ ]`, quoted strings
(case-insensitive, RFC 5234 §2.3), `%x` values and ranges, `DIGIT`, and the names of the block's own rules. It fails
on anything else.
"""

import functools
import itertools
import json
import re
from collections.abc import Callable, Iterator

import pytest
from markdown_it import MarkdownIt

from .conftest import GENERATED, REPO_ROOT, ecma_262, load_yaml

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
TYPES = REPO_ROOT / "src" / "astra" / "schema" / "types.yaml"
SECTION = "4. "
"""How §4's heading begins: the grammar is the one `abnf` fence under it."""

POINTERS = {
    "id": "/properties/outputs/propertyNames/pattern",
    "address": "/$defs/Output__identifier_optional/properties/decisions/items/pattern",
    "reference": "/$defs/Output__identifier_optional/properties/inputs/items/pattern",
    "option_reference": "/$defs/Option__identifier_optional/properties/requires/items/pattern",
    "condition": "/$defs/Output__identifier_optional/properties/when/items/pattern",
}
"""Where each named type's pattern is read in `analysis.schema.json`: a field of that type."""

ALPHABET = ["a", "z", "0", "9", "_", ".", "#", "~", "A", "-", "\n", " ", "é", "!"]
"""The characters of the strings compared: each one the grammar treats differently, and some it never takes."""

MAX_LENGTH = 5

CORE_RULES = {"digit": "[0-9]"}
"""The core rules of RFC 5234 (Appendix B.1) the translator knows, by name in lowercase."""


class GrammarError(ValueError):
    """ABNF the translator doesn't take."""


def grammar_text(markdown: str) -> str:
    """The text of the one `abnf` fence under §4's heading; an error if there is none, or more than one."""
    tokens = MarkdownIt("commonmark").parse(markdown)
    fences, section = [], ""
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            section = tokens[i + 1].content
        elif (
            token.type == "fence"
            and token.info.strip() == "abnf"
            and section.startswith(SECTION)
        ):
            fences.append(token.content)
    if len(fences) != 1:
        raise GrammarError(f"§4 has {len(fences)} `abnf` fences, not one")
    return fences[0]


_RULE = re.compile(r"([A-Za-z][A-Za-z0-9-]*)[ \t]*=[ \t]*(.*)")
"""A rule's first line, its comment left out: its name, then its elements."""

_TOKEN = re.compile(
    r"[ \t]+"
    r'|(?P<string>"[\x20\x21\x23-\x7e]*")'
    r"|(?P<value>%[xX][0-9A-Fa-f]+(?:-[0-9A-Fa-f]+)?)"
    r"|(?P<name>[A-Za-z][A-Za-z0-9-]*)"
    r"|(?P<punctuation>[()\[\]/*])"
)
"""A token of a rule's elements, or the white space between two."""


def _without_comment(line: str) -> str:
    """`line` without its comment, which runs from a `;` outside a quoted string to the end."""
    quoted = False
    for i, char in enumerate(line):
        if char == '"':
            quoted = not quoted
        elif char == ";" and not quoted:
            return line[:i]
    return line


def parse_rules(text: str) -> dict[str, str]:
    """The rules of the ABNF `text`, by name in lowercase (RFC 5234 §2.1), each its elements as written.

    Comments are left out, and a line that starts with white space continues the rule before it.
    """
    rules: dict[str, str] = {}
    name = None
    for line in text.splitlines():
        body = _without_comment(line).rstrip()
        if not body.strip():
            continue
        if body[0] in " \t":
            if name is None:
                raise GrammarError(
                    f"a continuation line with no rule before it: {line!r}"
                )
            rules[name] += " " + body.strip()
            continue
        match = _RULE.fullmatch(body)
        if not match:
            raise GrammarError(f"not a rule: {line!r}")
        name, elements = match.group(1).lower(), match.group(2)
        if elements.startswith("/"):
            raise GrammarError(f"an incremental alternative (`=/`): {line!r}")
        if name in rules:
            raise GrammarError(f"the rule {name} is defined twice")
        rules[name] = elements
    return rules


def _character(code: int) -> str:
    """The character `code` as a Python regular expression escape."""
    return f"\\U{code:08x}"


class _Rule:
    """The parser of one rule's elements, which translates them to a regular expression as it goes."""

    def __init__(self, name: str, elements: str, resolve: Callable[[str], str]):
        self.name = name
        self.resolve = resolve
        self.names: set[str] = set()
        """The rule names its elements refer to, in lowercase."""
        self.tokens: list[tuple[str, str]] = []
        position = 0
        while position < len(elements):
            match = _TOKEN.match(elements, position)
            if not match:
                raise GrammarError(
                    f"the rule {name} has {elements[position:]!r}, outside the subset"
                )
            if match.lastgroup:
                self.tokens.append((match.lastgroup, match.group()))
            position = match.end()
        self.position = 0

    def regex(self) -> str:
        regex = self.alternation()
        if self.peek() is not None:
            raise GrammarError(
                f"the rule {self.name} has an unexpected {self.peek()!r}"
            )
        return regex

    def peek(self) -> str | None:
        return (
            self.tokens[self.position][1] if self.position < len(self.tokens) else None
        )

    def take(self) -> tuple[str, str]:
        if self.position == len(self.tokens):
            raise GrammarError(f"the rule {self.name} ends too soon")
        self.position += 1
        return self.tokens[self.position - 1]

    def alternation(self) -> str:
        branches = [self.concatenation()]
        while self.peek() == "/":
            self.take()
            branches.append(self.concatenation())
        return branches[0] if len(branches) == 1 else "(?:" + "|".join(branches) + ")"

    def concatenation(self) -> str:
        parts = [self.repetition()]
        while self.peek() not in (None, "/", ")", "]"):
            parts.append(self.repetition())
        return "".join(parts)

    def repetition(self) -> str:
        if self.peek() != "*":
            return self.element()
        self.take()
        if self.peek() != "(":
            raise GrammarError(
                f"the rule {self.name} repeats something other than a group: only `*( )` is taken"
            )
        return self.element() + "*"

    def element(self) -> str:
        kind, text = self.take()
        if text in ("(", "["):
            inner = self.alternation()
            if self.take()[1] != {"(": ")", "[": "]"}[text]:
                raise GrammarError(f"the rule {self.name} doesn't close its {text!r}")
            return f"(?:{inner})" + ("?" if text == "[" else "")
        if kind == "string":
            return (
                "(?:"
                + "".join(
                    f"[{c.lower()}{c.upper()}]" if c.isalpha() else re.escape(c)
                    for c in text[1:-1]
                )
                + ")"
            )
        if kind == "value":
            low, _, high = text[2:].partition("-")
            low, high = int(low, 16), int(high or low, 16)
            if high < low:
                raise GrammarError(f"the rule {self.name} has an empty range, {text}")
            return f"[{_character(low)}-{_character(high)}]"
        if kind == "name":
            self.names.add(text.lower())
            return self.resolve(text.lower())
        raise GrammarError(f"the rule {self.name} has an unexpected {text!r}")


def translate(text: str) -> tuple[dict[str, str], dict[str, set[str]]]:
    """Each rule of the ABNF `text`, by name in lowercase, as a regular expression that matches what the rule does
    (anchored by the caller); and, for each rule, the rules of `text` it names."""
    rules = parse_rules(text)
    regexes: dict[str, str] = {}
    uses: dict[str, set[str]] = {}
    translating: list[str] = []

    def rule(name: str) -> str:
        if name not in regexes:
            if name in translating:
                raise GrammarError(
                    f"the rule {name} refers to itself, through {' → '.join(translating)}"
                )
            translating.append(name)
            parser = _Rule(name, rules[name], resolve)
            regexes[name] = f"(?:{parser.regex()})"
            uses[name] = parser.names & rules.keys()
            translating.pop()
        return regexes[name]

    def resolve(name: str) -> str:
        if name in rules:
            return rule(name)
        if name in CORE_RULES:
            return f"(?:{CORE_RULES[name]})"
        raise GrammarError(f"{name} is neither a rule of the grammar nor `DIGIT`")

    for name in rules:
        rule(name)
    return regexes, uses


@functools.cache
def grammar() -> tuple[dict[str, str], dict[str, set[str]]]:
    """§4's rules, translated, and the rules each one names."""
    return translate(grammar_text(SPECIFICATION.read_text(encoding="utf-8")))


def named_types() -> dict[str, dict]:
    """The named types of `types.yaml`, by name."""
    return load_yaml(TYPES)["types"]


def compared(rules: dict[str, str]) -> dict[str, str]:
    """The rules named after a named type, by the type's name (`-` read as `_`), each with its rule's name."""
    types = named_types()
    return {
        name.replace("-", "_"): name
        for name in rules
        if name.replace("-", "_") in types
    }


def schema_pattern(pointer: str) -> str:
    """The value at the JSON Pointer `pointer` of `analysis.schema.json`."""
    node = json.loads((GENERATED / "analysis.schema.json").read_text(encoding="utf-8"))
    for token in pointer.split("/")[1:]:
        node = node[token.replace("~1", "/").replace("~0", "~")]
    return node


def strings() -> Iterator[str]:
    """Every string of up to `MAX_LENGTH` characters over `ALPHABET`."""
    for length in range(MAX_LENGTH + 1):
        for characters in itertools.product(ALPHABET, repeat=length):
            yield "".join(characters)


def differences(abnf: str, pattern: str) -> list[str]:
    """The strings that the ABNF regular expression `abnf`, matched whole, and the JSON Schema `pattern` disagree on.

    A JSON Schema pattern isn't anchored (JSON Schema 2019-09 Validation §6.3.3), and is matched as ECMA-262 matches it
    (`ecma_262`), so both are run with `re.search`.
    """
    whole, schema = re.compile(rf"\A{abnf}\Z"), ecma_262(pattern)
    return [s for s in strings() if bool(whole.search(s)) != bool(schema.search(s))]


def test_the_translator_takes_the_subset():
    regexes, uses = translate(
        'a = b *( "x" / DIGIT ) [ "." b ] ; a comment\n'
        "b = %x61-63 %x2E ; a-c, then .\n"
        '   / "Q"         ; continued\n'
    )
    whole = re.compile(rf"\A{regexes['a']}\Z")
    taken = {"a.": True, "qx9X": True, "b.xx.q": True, "a": False, "d.": False}
    assert {s: bool(whole.search(s)) for s in taken} == taken
    assert uses == {"a": {"b"}, "b": set()}


@pytest.mark.parametrize(
    "text",
    [
        "a = ALPHA",
        "a = 1*( %x61 )",
        "a = *%x61",
        "a = %d97",
        "a = %x61.62",
        "a = <prose>",
        'a = "x"\na =/ "y"',
        'a = "x"\na = "y"',
        'a = ( "x"',
        'a = "x" )',
        "a = %x62-61",
        "a = b\nb = a",
        "  a = %x61",
        "a = ",
    ],
)
def test_the_translator_fails_outside_the_subset(text):
    with pytest.raises(GrammarError):
        translate(text)


def test_the_grammar_is_read_from_section_4_only():
    fence = "```abnf\na = %x61\n```\n"
    assert grammar_text(f"## 4. Names and grammars\n\n{fence}") == "a = %x61\n"
    for markdown in [
        "## 4. Names and grammars\n",
        f"## 5. Other\n\n{fence}",
        f"## 4. Names\n\n{fence}{fence}",
    ]:
        with pytest.raises(GrammarError):
            grammar_text(markdown)


def test_every_structured_type_has_a_rule():
    """Each type of `types.yaml` with a structured pattern (one built from the id grammar) has a rule in §4."""
    regexes, _ = grammar()
    structured = {
        name
        for name, definition in named_types().items()
        if "structured_pattern" in definition
    }
    assert sorted(structured - compared(regexes).keys()) == []


def test_every_compared_rule_has_a_pattern_to_compare():
    """A rule named after a type has a place in `POINTERS` to read that type's pattern from."""
    regexes, _ = grammar()
    assert sorted(compared(regexes).keys() - POINTERS.keys()) == []


def test_every_helper_rule_is_used():
    """A rule not named after a type is used by one that is, directly or through other rules."""
    regexes, uses = grammar()
    used, todo = set(), list(compared(regexes).values())
    while todo:
        name = todo.pop()
        if name not in used:
            used.add(name)
            todo.extend(uses[name])
    assert sorted(regexes.keys() - used) == []


@pytest.mark.parametrize("type_name", POINTERS)
def test_each_rule_matches_its_type(type_name):
    """The rule named after the type and the type's pattern in the contract take the same strings."""
    regexes, _ = grammar()
    rule = compared(regexes).get(type_name)
    assert rule is not None, f"§4 has no rule named after {type_name}"
    assert differences(regexes[rule], schema_pattern(POINTERS[type_name])) == []
