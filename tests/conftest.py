"""The fixture harness: YAML 1.2 and strict JSON loading, the generated validators, `rules.json` and the fixture headers
(design §9)."""

import contextlib
import functools
import json
import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.composer import Composer, ComposerError
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError, SafeConstructor
from ruamel.yaml.error import YAMLError
from ruamel.yaml.events import AliasEvent, MappingStartEvent
from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode
from ruamel.yaml.parser import Parser, ParserError
from ruamel.yaml.reader import Reader, ReaderError
from ruamel.yaml.resolver import VersionedResolver
from ruamel.yaml.scanner import Scanner, ScannerError
from ruamel.yaml.tokens import (
    DocumentEndToken,
    FlowEntryToken,
    FlowMappingEndToken,
    FlowSequenceEndToken,
    ScalarToken,
    StreamEndToken,
    ValueToken,
)
from rules import json_pointer

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "src" / "astra" / "schema" / "generated"
DATA = REPO_ROOT / "tests" / "data"

_SCHEMA_NAMES = {"Analysis": "analysis", "ProvenanceRecord": "provenance"}
"""Each fixture root, with the name of its generated schema."""

_RULE_LINE = re.compile(r"# rule: ([A-Z][A-Z0-9_]*)")
_FAILS_AT_LINE = re.compile(r"# fails at: (\(root\)|parse|(/[^/]*)+)")
_ALSO_LINE = re.compile(r"# also: ([A-Z][A-Z0-9_]*) at (\(root\)|(/[^/]*)+)")

PARSE_CODES = {"INVALID_SYNTAX", "DUPLICATE_KEY"}
"""The parse-layer codes `parse_code` gives."""


class JSONError(ValueError):
    """A record's text that breaks a parse rule (spec §3), as `load_json` reads it."""


class DuplicateNameError(JSONError):
    """An object of a record with a name written twice (spec §3)."""


PARSE_ERRORS = (YAMLError, JSONError)
"""What the loaders raise for a file that breaks a parse rule: `load_document` a `YAMLError`, `load_json` a
`JSONError`."""


def parse_code(error: YAMLError | JSONError) -> str:
    """The parse-layer code of a loader error: `DUPLICATE_KEY` for a repeated key or name, `INVALID_SYNTAX` for any
    other."""
    return (
        "DUPLICATE_KEY"
        if isinstance(error, (DuplicateKeyError, DuplicateNameError))
        else "INVALID_SYNTAX"
    )


_TAG = "tag:yaml.org,2002:"

_CORE_SCALARS = {
    "null": re.compile(r"null|Null|NULL|~|"),
    "bool": re.compile(r"true|True|TRUE|false|False|FALSE"),
    "int": re.compile(r"[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+"),
    "float": re.compile(
        r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?|[-+]?\.(inf|Inf|INF)|\.(nan|NaN|NAN)"
    ),
}
"""The YAML 1.2 core schema's plain scalars other than strings (YAML 1.2.2 §10.3.2), in resolution order."""


_BREAKS = "\r\n"
"""YAML 1.2.2's line break characters, CR and LF (§5.4): the scanner reads a CR LF, a CR or an LF as a line break.

ruamel.yaml's scanner also reads NEL, LS and PS as line breaks, as YAML 1.1 did, but none of them reaches it: the reader
shows each as a stand-in (`_CoreSchemaReader`)."""

_END_OF_LINE = "\0" + _BREAKS
"""What ends a line: a line break, or the end of the text (`\\0`, which the reader adds)."""

_WHITE_OR_END = " \t" + _END_OF_LINE
"""White space, or what ends a line."""

_FLOW_INDICATORS = ",[]{}"
"""YAML 1.2.2's flow indicators ([23] `c-flow-indicator`)."""

_BEFORE_A_COMMENT = ("", " ", "\t", "\ufeff", *_BREAKS)
"""What a comment may follow: the start of the stream (`""`), white space, a byte order mark or a line break."""

_NON_BREAKS = "\x85\u2028\u2029"
"""NEL, LS and PS: ordinary characters in YAML 1.2 (YAML 1.2.2 §5.4), which ruamel.yaml's scanner reads as line
breaks."""

_CONTROLS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]")
"""What YAML 1.2.2 allows nowhere in a stream (§5.1, [1] `c-printable`): a C0 control other than tab, LF and CR, and a
surrogate, which isn't a character."""

_QUOTED_ONLY = re.compile("[\x7f-\x84\x86-\x9f\ufeff\ufffe\uffff]")
"""What YAML 1.2.2 allows in a quoted scalar but not in a plain scalar, a block scalar, a comment or a directive (§5.1,
[1] `c-printable`, [27] `nb-char`): DEL, a C1 control other than NEL, U+FEFF (a byte order mark), U+FFFE and U+FFFF.

ruamel.yaml reads a byte order mark anywhere but at the start of the text as the start of a plain scalar, so this also
refuses one at the start of a later document's prefix (`...` then U+FEFF), which YAML 1.2.2 §5.2 allows and spec §3,
by ASTRA's rule, doesn't."""

_STAND_INS = range(0xE000, 0xF900)
"""The code points the reader takes its stand-ins from: the private use area of the Basic Multilingual Plane."""


class _CoreSchemaReader(Reader):
    """ruamel.yaml's reader, reading a text by YAML 1.2.2's characters (§5.1, §5.4), and keeping the last character it
    read, for the scanner to look one back.

    It takes a text only: `load_document` decodes a file's bytes itself. It holds the whole text, which it never trims,
    so the scanner can read back to a line's start (`_CoreSchemaScanner._line_so_far`).

    ruamel.yaml's reader refuses DEL, the C1 controls, U+FFFE and U+FFFF anywhere, but YAML 1.2.2 allows every
    character but a C0 control (tab, LF and CR aside) inside a quoted scalar: this one refuses only those (`_CONTROLS`),
    and the scanner refuses the others outside a quoted scalar (`_QUOTED_ONLY`).

    ruamel.yaml's scanner reads NEL, LS and PS as line breaks, and its set of breaks is written out in about thirty
    places. So the reader shows each of the three to the scanner as a stand-in, a character of the private use area
    that the text doesn't hold, which the scanner reads as an ordinary character, as YAML 1.2 reads the three: `peek`
    gives the stand-in, and `prefix`, which the scanner reads a scalar's text by, gives the character itself. No value
    holds a stand-in: an escape (`"\\N"`, `"\\uE000"`) writes its own character.
    """

    last = ""
    """The last character read, or `""` at the start of the stream."""

    _originals: dict[int, str] = {}
    """The character each stand-in stands for, by the stand-in's code point, for `str.translate`."""

    @property
    def stream(self) -> Any:
        return Reader.stream.fget(self)

    @stream.setter
    def stream(self, val: Any) -> None:
        """Read the text `val`, each NEL, LS and PS in it shown as its stand-in."""
        if val is not None:
            if not isinstance(val, str):
                raise TypeError(
                    "the reader takes a text: a file's bytes are decoded first"
                )
            held = set(val)
            free = (c for c in map(chr, _STAND_INS) if c not in held)
            stand_ins = {ord(c): next(free) for c in _NON_BREAKS if c in held}
            self._originals = {ord(s): chr(c) for c, s in stand_ins.items()}
            val = val.translate(stand_ins)
        Reader.stream.fset(self, val)

    def check_printable(self, data: Any) -> None:
        """Refuse a C0 control other than tab, LF and CR, and a surrogate, anywhere in `data` (YAML 1.2.2 §5.1)."""
        found = _CONTROLS.search(data)
        if found is not None:
            raise ReaderError(
                self.name,
                found.start(),
                ord(found[0]),
                "unicode",
                "YAML allows no C0 control but tab, LF and CR, even quoted",
            )

    def prefix(self, length: int = 1) -> Any:
        return self.restore(super().prefix(length))

    def restore(self, text: str) -> str:
        """`text` with each stand-in replaced by the character it stands for."""
        return text.translate(self._originals) if self._originals else text

    def forward(self, length: int = 1) -> None:
        super().forward(length)
        if length:
            self.last = self.buffer[self.pointer - 1]


class _CoreSchemaScanner(Scanner):
    """ruamel.yaml's scanner, refusing a `%YAML` directive for any version but 1.2, reading tabs and the indicators of
    a flow collection as YAML 1.2.2 does, and refusing the text YAML 1.2.2 makes ill-formed that ruamel.yaml would
    read.

    The directive is ASTRA's rule, not YAML's (spec §3): YAML 1.2.2 §6.8.1 has a 1.2 processor accept `%YAML 1.1`,
    and process a later 1.x with a warning.

    ruamel.yaml takes a tab as white space only in a flow collection and a quoted scalar. YAML 1.2.2 takes one wherever
    white space separates (§6.2): after a token, at a line's end, on a line of white space only, before a comment,
    between the words of a plain scalar and after a continuation line's indentation, in a directive, in a block
    scalar's header, and in the block context after a line's indentation or a block indicator (`-`, `?`, `:`) before
    anything but a block collection. It refuses one in indentation (§6.1): before a token on a line with no more spaces
    than the block it is in, before a block collection (`-\\t-`, `?\\tkey:`), and in a block scalar's indentation
    (§8.1.1).

    In a flow collection (§7.4), ruamel.yaml takes every `?` as the explicit key indicator, `:` as the value indicator
    only before white space in a flow sequence but almost anywhere in a flow mapping (`{ :x}` is `{null: x}`, and
    `x: {a: :x}` is refused), and a `:` before a flow indicator into a plain scalar; it limits an implicit key of a
    flow mapping to one line of 1024 characters, takes `,`, `[` and `]` into a shorthand tag, and refuses a flow
    indicator right after a tag. YAML 1.2.2 takes `?` as the indicator only before white space or a line break, and
    otherwise as the start of a plain scalar before a safe character ([142], [126] `ns-plain-first`), so `{?x: y}`
    has the key `?x`. It takes `:` as the value indicator before white space, a line break or a flow indicator, after
    any key, which a plain scalar then doesn't hold ([147], [130] `ns-plain-char`), so `[x:]` is `[{x: null}]`; and
    after a JSON-like key (a quoted scalar or a flow collection) before anything too ([149], [153]), so `["x":y]` is
    `[{x: y}]`. Elsewhere, before a safe character, `:` starts a plain scalar, so `{ :x}` is `{":x": null}` and
    `{a: :x}` is `{a: ":x"}`. An implicit key of a flow mapping may span lines and be of any length ([145], [148]),
    unlike one in the block context or of a pair in a flow sequence ([154], [155]). A shorthand tag holds no flow
    indicator ([40] `ns-tag-char`), and one directly before `,`, `]` or `}` is on an empty node ([105] `e-scalar`), so
    `[!!str]` is `[""]`.

    The text YAML 1.2.2 makes ill-formed is: a comment with no white space before it (§6.6); a line of a flow
    collection or of a quoted scalar, its closing bracket or quote included, with no more indentation in spaces than
    the block collection it is in (§6.3, §8.2.3: under a block collection indented `n` spaces, a flow node is at
    `n+1`); `-` or `?` in a flow collection with a flow indicator after it, which starts no plain scalar and is no
    indicator (§7.3.3, as in `[-]` and `[?]`); a flow collection right after a `:` with no key before it ([147]:
    `{ :[b]}`, `{!!str :[b]}`); the verbatim tag `!<!>` (§6.9.1); a character of `_QUOTED_ONLY` in a plain scalar, a
    block scalar, a comment or a directive ([1], [27]); and a leading empty line of a block scalar with more spaces
    than its first non-empty line (§8.1.1.1; ruamel.yaml compares the empty lines with each other instead).
    """

    _quoted = False
    """True while a quoted scalar is scanned."""

    def reset_scanner(self) -> None:
        super().reset_scanner()
        self._after_tab: set[int] = set()
        """Where each token starts, by its index in the text, that follows a tab in the block context after a line's
        indentation or a block indicator: none of them may start a block collection."""
        self._indicator_end = -1
        """Where the last block indicator (`-`, `?` or `:` in the block context) ends, by its index in the text."""
        self._last_token: Any = None
        """The last token fetched, or None before the first. `tokens` may no longer hold it: the parser takes every
        token that no possible implicit key holds back, and in a flow collection no implicit key is possible after
        `?`."""

    def fetch_more_tokens(self) -> Any:
        found = super().fetch_more_tokens()
        self._last_token = self.tokens[-1]
        return found

    def _line_so_far(self) -> str:
        """The text of the reader's line before its position, without a byte order mark that starts the text."""
        buffer, pointer = self.reader.buffer, self.reader.pointer
        start = max(buffer.rfind("\n", 0, pointer), buffer.rfind("\r", 0, pointer)) + 1
        line = buffer[start:pointer]
        return line.removeprefix("\ufeff") if start == 0 else line

    def _refuse_quoted_only(self, text: str, mark: Any) -> None:
        """Raise `ScannerError` if `text`, a plain scalar, a block scalar, a comment or a directive as written, holds a
        character YAML 1.2.2 allows only in a quoted scalar (`_QUOTED_ONLY`)."""
        found = _QUOTED_ONLY.search(text)
        if found is not None:
            raise ScannerError(
                None,
                None,
                f"found U+{ord(found[0]):04X}, which YAML allows only in a quoted scalar",
                mark,
            )

    def scan_to_next_token(self) -> Any:
        """Skip the white space, comments and line breaks before the next token, refusing a comment glued to a token,
        a comment holding a character of `_QUOTED_ONLY`, and a tab in indentation (`_note_a_tab`)."""
        reader = self.reader
        peek, forward = reader.peek, reader.forward
        if peek() == "#" and reader.last not in _BEFORE_A_COMMENT:
            raise ScannerError(
                None,
                None,
                "found '#' right after a token: a comment needs white space before it",
                reader.get_mark(),
            )
        if reader.index == 0 and peek() == "\ufeff":
            forward()
        gap = reader.index
        while True:
            while peek() in " \t":
                forward()
            if peek() == "#":
                start, mark = reader.pointer, reader.get_mark()
                while peek() not in _END_OF_LINE:
                    forward()
                self._refuse_quoted_only(reader.buffer[start : reader.pointer], mark)
            if not self.scan_line_break():
                break
            if not self.flow_level:
                self.allow_simple_key = True
            gap = reader.index
        if not self.flow_level and peek() != "\0":
            self._note_a_tab(gap)
        return None

    def _note_a_tab(self, gap: int) -> None:
        """Before a token in the block context: refuse a tab in the line's indentation, and note the token in
        `_after_tab` if a tab comes before it after the indentation, or after a block indicator, `gap` being where the
        white space before the token starts on its line.

        The indentation is the spaces that start the line. With no more of them than the block collection it is in, the
        token would start an entry of that collection, or of one it is in, after the tab.
        """
        reader = self.reader
        line = self._line_so_far()
        if not line.strip(" \t"):
            if "\t" not in line:
                return
            if len(line) - len(line.lstrip(" ")) <= self.indent:
                raise ScannerError(
                    None,
                    None,
                    f"found a tab in indentation: no more spaces before it than the block it is in has "
                    f"({self.indent})",
                    reader.get_mark(),
                )
        elif (
            gap != self._indicator_end
            or "\t" not in reader.buffer[gap : reader.pointer]
        ):
            return
        self._after_tab.add(reader.index)

    def _refuse_after_a_tab(self, index: int, what: str, mark: Any) -> None:
        """Raise `ScannerError` if the token starting at `index` follows a tab after a line's indentation or a block
        indicator (`_after_tab`): `what` starts a block collection."""
        if index in self._after_tab:
            raise ScannerError(
                None,
                None,
                f"found {what} after a tab: a block collection starts after spaces only",
                mark,
            )

    def fetch_block_entry(self) -> None:
        block = not self.flow_level
        if block:
            self._refuse_after_a_tab(self.reader.index, "'-'", self.reader.get_mark())
        super().fetch_block_entry()
        if block:
            self._indicator_end = self.reader.index

    def fetch_key(self) -> None:
        block = not self.flow_level
        if block:
            self._refuse_after_a_tab(self.reader.index, "'?'", self.reader.get_mark())
        super().fetch_key()
        if block:
            self._indicator_end = self.reader.index

    def fetch_value(self) -> None:
        block = not self.flow_level
        if block:
            key = self.possible_simple_keys.get(self.flow_level)
            if key is None:
                self._refuse_after_a_tab(
                    self.reader.index, "':'", self.reader.get_mark()
                )
            else:
                self._refuse_after_a_tab(key.index, "a key", key.mark)
        super().fetch_value()
        if block:
            self._indicator_end = self.reader.index

    def scan_plain(self) -> Any:
        """A plain scalar, refused if it holds a character of `_QUOTED_ONLY`, and ending in a flow collection at a `:`
        before a flow indicator, which is then the value indicator ([130] `ns-plain-char`): ruamel.yaml, which ends one
        at a `:` only before white space, is shown the flow indicator as a space."""
        if self.flow_level:
            buffer = self.reader.buffer
            with self._shown_as_spaces(
                lambda index, ch: ch in _FLOW_INDICATORS and buffer[index - 1] == ":"
            ):
                token = super().scan_plain()
        else:
            token = super().scan_plain()
        start, end = token.start_mark, token.end_mark
        self._refuse_quoted_only(start.buffer[start.pointer : end.pointer], start)
        return token

    def scan_plain_spaces(self, indent: int, start_mark: Any) -> Any:
        """What follows a word of a plain scalar, as YAML 1.2.2 reads it (§6.3, §7.3.3): the white space before the
        next word on the line, the line breaks folded (`[" "]` for one, `["\\n", …]` for more), or `[]` or None (at a
        document marker) where the scalar ends.

        ruamel.yaml reads only spaces here. A tab is white space too: between two words it is content, and at a line's
        end it is folded away. A line after a break continues the scalar if it has `indent` spaces, then any white
        space ([69] `s-flow-line-prefix`), and is empty if it has fewer spaces and no tab, or only white space after
        `indent` spaces ([70] `l-empty`). A line with fewer spaces and then a tab ends the scalar after its spaces,
        leaving the tab to `scan_to_next_token`. In a flow collection, `_check_continuation` checks the spaces instead.
        """
        reader = self.reader
        peek, forward = reader.peek, reader.forward
        length = 0
        while peek(length) in " \t":
            length += 1
        white = reader.prefix(length)
        forward(length)
        if peek() not in _BREAKS:
            return [white] if white else []
        self.scan_line_break()
        self.allow_simple_key = True
        breaks: list[str] = []
        while True:
            if reader.prefix(3) in ("---", "...") and peek(3) in _END_OF_LINE + " \t":
                return None
            spaces = 0
            while peek(spaces) == " ":
                spaces += 1
            length = spaces
            if self.flow_level or spaces >= indent:
                while peek(length) in " \t":
                    length += 1
            if peek(length) not in _BREAKS:
                forward(spaces if peek(length) == "\t" else length)
                return breaks or [" "]
            forward(length)
            breaks.append(self.scan_line_break())

    def scan_block_scalar(self, style: Any, rt: Any = False) -> Any:
        token = super().scan_block_scalar(style, rt)
        start, end = token.start_mark, token.end_mark
        self._refuse_quoted_only(start.buffer[start.pointer : end.pointer], start)
        return token

    def scan_block_scalar_indicators(self, start_mark: Any) -> Any:
        """A block scalar's indicators, read with a tab as a space: white space may follow them ([162]
        `c-b-block-header`, [77] `s-b-comment`)."""
        with self._tabs_as_spaces():
            return super().scan_block_scalar_indicators(start_mark)

    def scan_block_scalar_ignored_line(self, start_mark: Any) -> Any:
        """The rest of a block scalar's header line, read with a tab as a space: white space, then a comment, may end
        it ([77] `s-b-comment`). `scan_block_scalar` checks the comment's characters."""
        with self._tabs_as_spaces():
            return super().scan_block_scalar_ignored_line(start_mark)

    def scan_block_scalar_indentation(self) -> Any:
        """`(breaks, indent, end_mark)` for a block scalar with no indentation indicator: its leading empty lines, and
        its indentation, the spaces of its first non-empty line (YAML 1.2.2 §8.1.1.1).

        A line whose spaces are followed by a tab isn't empty: it is the scalar's first line if it has at least the
        scalar's least indentation, the tab being content, and otherwise the tab is in the indentation, which YAML
        refuses. No leading empty line has more spaces than the first non-empty line. With no non-empty line, the
        indentation is the spaces of the longest line, as in ruamel.yaml.
        """
        reader = self.reader
        peek, forward = reader.peek, reader.forward
        least = self.indent + 1
        breaks, most, end_mark = [], 0, reader.get_mark()
        while peek() in " " + _BREAKS:
            if peek() == " ":
                forward()
            else:
                most = max(most, reader.column)
                breaks.append(self.scan_line_break())
                end_mark = reader.get_mark()
        if peek() == "\t" and reader.column < least:
            raise ScannerError(
                "while scanning a block scalar",
                None,
                f"found a tab in its indentation ({least} spaces at least)",
                reader.get_mark(),
            )
        if peek() != "\0" and reader.column >= least:
            if most > reader.column:
                raise ScannerError(
                    "while scanning a block scalar",
                    None,
                    "found a leading empty line with more spaces than the first non-empty line",
                    reader.get_mark(),
                )
            return breaks, reader.column, end_mark
        return breaks, max(most, reader.column), end_mark

    def scan_block_scalar_breaks(self, indent: int) -> Any:
        """ruamel.yaml's, refusing a line with fewer spaces than the scalar's indentation and then a tab: such a line is
        neither content nor empty ([170] `l-empty`), and can't follow a block scalar before a comment ([169]
        `l-trail-comments`), so the tab is in the indentation."""
        found = super().scan_block_scalar_breaks(indent)
        if self.reader.peek() == "\t" and self.reader.column < indent:
            raise ScannerError(
                "while scanning a block scalar",
                None,
                f"found a tab in its indentation ({indent} spaces)",
                self.reader.get_mark(),
            )
        return found

    def scan_line_break(self) -> Any:
        line_break = super().scan_line_break()
        if line_break and (self.flow_level or self._quoted):
            self._check_continuation()
        return line_break

    def _check_continuation(self) -> None:
        """Refuse the line just begun, in a flow collection or a quoted scalar, if it isn't indented past the block.

        A line of white space only, and in a flow collection a comment line, may have any indentation.
        """
        peek = self.reader.peek
        spaces = 0
        while peek(spaces) == " ":
            spaces += 1
        end = spaces
        while peek(end) in " \t":
            end += 1
        if peek(end) in ("\0", *_BREAKS) or (peek(end) == "#" and not self._quoted):
            return
        if spaces <= self.indent:
            raise ScannerError(
                "while scanning a quoted scalar"
                if self._quoted
                else "while scanning a flow collection",
                None,
                f"found a line indented {spaces} spaces: it must be indented more than the block it is in "
                f"({self.indent} spaces)",
                self.reader.get_mark(),
            )

    def scan_flow_scalar(self, style: Any) -> Any:
        self._quoted = True
        try:
            return super().scan_flow_scalar(style)
        finally:
            self._quoted = False

    def stale_possible_simple_keys(self) -> None:
        """ruamel.yaml's, which drops a possible implicit key once the scanner is past its line or 1024 characters
        after it, keeping each of a flow mapping, which may span lines and be of any length ([145], [148]): it stays
        possible until `,`, `}`, or the `:` that makes it a key."""
        kept = {
            level: key
            for level, key in self.possible_simple_keys.items()
            if level and self.flow_context[level - 1] == "{"
        }
        for level in kept:
            del self.possible_simple_keys[level]
        super().stale_possible_simple_keys()
        self.possible_simple_keys.update(kept)

    def check_key(self) -> Any:
        """`?` is the explicit key indicator only before white space or a line break ([142], [150]), in a flow
        collection too, where ruamel.yaml takes every `?` as one."""
        return self.reader.peek(1) in _WHITE_OR_END

    def check_value(self) -> Any:
        """In a flow collection, `:` is the value indicator before white space, a line break, `,`, `]` or `}`, after any
        key ([147] `c-ns-flow-map-separate-value`), and before anything after a JSON-like key, explicit or not ([149]
        `c-ns-flow-map-adjacent-value`, [153]): the last token fetched (`_last_token`) is then a quoted scalar or the
        end of a flow collection. Anywhere else, in a value too, it starts a plain scalar (`check_plain`), so `{a: :x}`
        is `{a: ":x"}`.

        After any other key, or none, white space separates the value from the `:` ([147]), so `{x:[y]}` and `{ :[y]}`
        are refused: the `:` is no value indicator here, and starts no plain scalar in `check_plain`."""
        if not self.flow_level:
            return super().check_value()
        if self.reader.peek(1) in _WHITE_OR_END + ",]}":
            return True
        last = self._last_token
        return isinstance(last, (FlowSequenceEndToken, FlowMappingEndToken)) or (
            isinstance(last, ScalarToken) and last.style in ("'", '"')
        )

    def check_plain(self) -> Any:
        """In a flow collection, `-`, `?` or `:` starts a plain scalar only before a safe character: not before white
        space, a line break or a flow indicator ([126] `ns-plain-first`). Elsewhere, ruamel.yaml's decides."""
        peek = self.reader.peek
        if self.flow_level and peek() in "-?:":
            return peek(1) not in _WHITE_OR_END + _FLOW_INDICATORS
        return super().check_plain()

    @contextlib.contextmanager
    def _shown_as_spaces(self, shown: Callable[[int, str], bool]) -> Any:
        """Show ruamel.yaml a space for each character `shown(index, character)` holds of, `index` being its place in
        the reader's text, where its scanner looks ahead (`peek`) and in the text it takes (`prefix`)."""
        reader = self.reader
        peek, prefix = reader.peek, reader.prefix

        def shown_peek(index: int = 0) -> str:
            ch = peek(index)
            return " " if shown(reader.pointer + index, ch) else ch

        def shown_prefix(length: int = 1) -> str:
            start = reader.pointer
            return "".join(
                " " if shown(start + i, ch) else ch
                for i, ch in enumerate(prefix(length))
            )

        reader.peek, reader.prefix = shown_peek, shown_prefix
        try:
            yield
        finally:
            del reader.peek, reader.prefix

    def _tabs_as_spaces(self) -> Any:
        """Show the reader's tabs to ruamel.yaml as spaces, where it takes only a space as white space and YAML 1.2.2
        takes a tab too (§6.2), and where neither is content: on a directive's line, after a tag, and on a block
        scalar's header line."""
        return self._shown_as_spaces(lambda index, ch: ch == "\t")

    def scan_tag(self) -> Any:
        """A tag, read with a tab as a space, and in a flow collection ending before `,`, `]` or `}`: anywhere in a
        shorthand tag or `!`, which holds none ([40] `ns-tag-char`), and after a verbatim tag's `>`. ruamel.yaml takes
        `,` and `]` into a shorthand tag, and refuses any of the three right after a tag, where YAML 1.2.2 reads the
        tag as on an empty node ([105] `e-scalar`): `[!!str]` is `[""]`."""
        reader = self.reader
        verbatim = reader.prefix(2) == "!<"
        end = reader.buffer.find(">", reader.pointer) if verbatim else -1
        flow = bool(self.flow_level)
        with self._shown_as_spaces(
            lambda index, ch: ch == "\t" or (flow and ch in ",]}" and index > end)
        ):
            token = super().scan_tag()
        if verbatim and token.value == (None, "!"):
            raise ScannerError(
                "while scanning a tag",
                token.start_mark,
                "found the verbatim tag !<!>, which YAML doesn't allow",
                token.end_mark,
            )
        return token

    def scan_directive(self) -> Any:
        """A directive, its line read with a tab as a space (YAML 1.2.2 §6.8: white space separates its parts and its
        comment), and refused if the line holds a character of `_QUOTED_ONLY` or is a `%YAML` for any version but
        1.2."""
        reader = self.reader
        start, mark = reader.pointer, reader.get_mark()
        with self._tabs_as_spaces():
            token = super().scan_directive()
        self._refuse_quoted_only(reader.buffer[start : reader.pointer], mark)
        if token.name == "YAML" and token.value != (1, 2):
            major, minor = token.value
            raise ScannerError(
                None,
                None,
                f"found %YAML {major}.{minor}: only 1.2 is read",
                token.start_mark,
            )
        return token


class _CoreSchemaParser(Parser):
    """ruamel.yaml's parser, reading two forms as YAML 1.2.2 does, where ruamel.yaml refuses or misreads them: a `...`
    with no document before it, which starts none, and a single pair with an empty key in a flow sequence, as in
    `[: x]` ([151], [146] `c-ns-flow-map-empty-key-entry`), whose key is null, so it is left out of its map, as any key
    that isn't a string is."""

    def parse_implicit_document_start(self) -> Any:
        """Skips each `...` at the start of the file or after another `...`: it ends no document, and starts none
        (YAML 1.2.2 [211] `l-yaml-stream`), where ruamel.yaml would start a document at it, refusing a file holding
        only `...`, and reading a second document after a `...` that follows one ending a document. As after a
        document, a `...` has nothing after it on its line but a comment ([205] `l-document-suffix`)."""
        scanner = self.scanner
        while scanner.check_token(DocumentEndToken):
            marker = scanner.get_token()
            following = scanner.peek_token()
            if (
                not isinstance(following, StreamEndToken)
                and following.start_mark.line == marker.end_mark.line
            ):
                raise ParserError(
                    None,
                    None,
                    "found content after a document end marker, on its line",
                    following.start_mark,
                )
        return super().parse_implicit_document_start()

    def parse_flow_sequence_entry(self, first: bool = False) -> Any:
        scanner = self.scanner
        if not first and scanner.check_token(FlowEntryToken):
            scanner.get_token()
            first = True
        if first and scanner.check_token(ValueToken):
            token = scanner.peek_token()
            self.state = self._parse_flow_sequence_entry_empty_key
            return MappingStartEvent(
                None, None, True, token.start_mark, token.end_mark, flow_style=True
            )
        return super().parse_flow_sequence_entry(first)

    def _parse_flow_sequence_entry_empty_key(self) -> Any:
        self.state = self.parse_flow_sequence_entry_mapping_value
        return self.process_empty_scalar(self.scanner.peek_token().start_mark)


_CORE_RESOLVERS: dict[Any, list] = {}
"""The core schema's resolvers, by the first character of the scalar (`""` for the empty one), as ruamel.yaml looks them up."""
for _name, _pattern in _CORE_SCALARS.items():
    _anchored = re.compile(rf"(?:{_pattern.pattern})\Z")
    for _first in ["", *"~nNtTfF-+0123456789."]:
        _CORE_RESOLVERS.setdefault(_first, []).append((_TAG + _name, _anchored))


class _CoreSchemaResolver(VersionedResolver):
    """Resolves a plain scalar by the core schema only: no timestamps, no merge key, no `_` in numbers."""

    @property
    def versioned_resolver(self) -> Any:
        return _CORE_RESOLVERS


class _CoreSchemaComposer(Composer):
    """ruamel.yaml's composer, refusing every anchor and alias (spec §3), and giving a scalar tagged `!` the tag
    `!!str`, as YAML 1.2.2 does (§6.9.1).

    An anchor or an alias raises `ComposerError`: a file uses neither, so an entry is written out in full. ruamel.yaml
    resolves a scalar tagged `!` as if it were plain, so that `! 12` would be 12.
    """

    def compose_node(self, parent: Any, index: Any) -> Any:
        event = self.parser.peek_event()
        if isinstance(event, AliasEvent):
            raise ComposerError(
                None,
                None,
                f"found the alias *{event.anchor}: a file uses no alias",
                event.start_mark,
            )
        if event.anchor is not None:
            raise ComposerError(
                None,
                None,
                f"found the anchor &{event.anchor}: a file uses no anchor",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def compose_scalar_node(self, anchor: Any) -> Any:
        event = self.parser.peek_event()
        if event.tag == "!":
            event.tag = _TAG + "str"
        return super().compose_scalar_node(anchor)


def _joined(value: str, mark: Any) -> str:
    """The string `value`, with each surrogate pair joined into the one character it encodes, as JSON joins `\\uD83D\\uDE00`
    into U+1F600; any other surrogate (U+D800-U+DFFF) raises `ConstructorError`, since a string holding one has no JSON
    form (spec §3).

    A surrogate can come only from an escape: YAML text can't hold one as a character.
    """
    try:
        return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    except UnicodeDecodeError as error:
        unit = int.from_bytes(error.object[error.start : error.start + 2], "little")
        raise ConstructorError(
            None,
            None,
            f"found the lone surrogate U+{unit:04X}: a string holding one has no JSON form",
            mark,
        ) from None


def _written(node: Any) -> str:
    """`node` as written in the text it was read from: from its first character (its tag's, if it has one) to its last."""
    start, end = node.start_mark, node.end_mark
    return start.buffer[start.pointer : start.pointer + end.index - start.index]


class _CoreSchemaConstructor(SafeConstructor):
    """Constructs the core schema's types only, each from its core form; any other tag is an error, and so is a value
    with no JSON form (spec §3): a float that isn't finite, an integer beyond a double's range, a string holding a lone
    surrogate.

    A map entry whose key isn't a string has no JSON form either, and is left out of its map. If the map is one of
    `map_pointers`, the maps of the document's JSON form, the key is recorded in `left_out`.
    """

    yaml_constructors: dict[Any, Any] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.map_pointers: dict[MappingNode, str] = {}
        """The JSON Pointer of each map node of the document's JSON form, by node (`_map_pointers`)."""
        self.left_out: list[tuple[int, str, str]] = []
        """`(index, pointer of the map, key as written)` for each key left out of a map of `map_pointers`, `index`
        being where the key starts in the text (maps are constructed out of document order)."""

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        """The map of `node`, whose keys must be distinct YAML nodes (YAML 1.2.2 §3.2.1.3); `<<` is an ordinary key.

        Two keys with the same tag and canonical form raise `DuplicateKeyError`, whatever their spelling and type: `a`
        and `"\\x61"`, `0x1f` and `31`, `true` and `True`. Keys of two tags are distinct, so `1`, `1.0`, `true` and
        `"1"` are four keys. An entry whose key isn't tagged `!!str` (a bool, a number, a null, a list or a map) isn't
        added: its key and value are still constructed, so that an error in them is raised, but it has no JSON form.
        If `node` is one of `map_pointers`, the key is recorded in `left_out`. A map inside a left-out entry isn't one
        of them, so a key left out of it is dropped with the entry.
        """
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None,
                None,
                f"expected a mapping node, but found {node.id}",
                node.start_mark,
            )
        canonical_keys = set()
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            canonical = self._canonical(key_node)
            if canonical in canonical_keys:
                raise DuplicateKeyError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a key equal to an earlier one: the same tag and canonical form",
                    key_node.start_mark,
                )
            canonical_keys.add(canonical)
            key = self.construct_object(key_node, deep=True)
            value = self.construct_object(value_node, deep=deep)
            if key_node.tag == _TAG + "str":
                mapping[key] = value
            elif node in self.map_pointers:
                self.left_out.append(
                    (
                        key_node.start_mark.index,
                        self.map_pointers[node],
                        self.loader.reader.restore(_written(key_node)),
                    )
                )
        return mapping

    def _canonical(self, node: Any) -> Any:
        """`node` as YAML compares nodes: its tag, and its canonical form (a scalar's value, a collection's nodes).

        With no alias, a node holds no node twice, so the recursion ends.
        """
        if isinstance(node, ScalarNode):
            return node.tag, self.construct_object(node, deep=True)
        if isinstance(node, SequenceNode):
            return node.tag, tuple(self._canonical(item) for item in node.value)
        return node.tag, frozenset(
            (self._canonical(key), self._canonical(value)) for key, value in node.value
        )

    def _core_scalar(self, node: Any, name: str) -> str:
        value = self.construct_scalar(node)
        if not _CORE_SCALARS[name].fullmatch(value):
            raise ConstructorError(
                None, None, f"{value!r} is not a core-schema {name}", node.start_mark
            )
        return value

    def construct_core_null(self, node: Any) -> None:
        self._core_scalar(node, "null")

    def construct_core_bool(self, node: Any) -> bool:
        return self._core_scalar(node, "bool").lower() == "true"

    def construct_core_int(self, node: Any) -> int:
        """An integer, read exactly; one beyond a double's range, which a double rounds to infinity, has no JSON form."""
        value = self._core_scalar(node, "int")
        if value.startswith(("0o", "0x")):
            number = int(value[2:], 8 if value[1] == "o" else 16)
        else:
            number = int(value)
        try:
            float(number)
        except OverflowError:
            raise ConstructorError(
                None,
                None,
                f"{value!r} is beyond a double's range: it has no JSON form",
                node.start_mark,
            ) from None
        return number

    def construct_core_float(self, node: Any) -> float:
        """A float; `.inf`, `-.inf`, `.nan` and a float beyond a double's range, which rounds to infinity, have no JSON
        form. One too small for a double rounds to 0."""
        value = self._core_scalar(node, "float")
        number = float(value.lower().replace(".inf", "inf").replace(".nan", "nan"))
        if not math.isfinite(number):
            raise ConstructorError(
                None,
                None,
                f"{value!r} isn't a finite number within a double's range: it has no JSON form",
                node.start_mark,
            )
        return number

    def construct_core_str(self, node: Any) -> str:
        """A string, a key's too, with each escaped surrogate pair joined into one character; a lone surrogate raises."""
        return _joined(self.construct_scalar(node), node.start_mark)


for _name in (*_CORE_SCALARS, "str"):
    _CoreSchemaConstructor.add_constructor(
        _TAG + _name, getattr(_CoreSchemaConstructor, f"construct_core_{_name}")
    )
for _name in ("seq", "map"):
    _CoreSchemaConstructor.add_constructor(
        _TAG + _name, getattr(SafeConstructor, f"construct_yaml_{_name}")
    )
_CoreSchemaConstructor.add_constructor(None, SafeConstructor.construct_undefined)


def _core_schema_yaml() -> YAML:
    """ruamel.yaml's pure safe loader, YAML 1.2, restricted to the core schema and held to YAML 1.2.2."""
    yaml = YAML(typ="safe", pure=True)
    yaml.Reader = _CoreSchemaReader
    yaml.Scanner = _CoreSchemaScanner
    yaml.Parser = _CoreSchemaParser
    yaml.Composer = _CoreSchemaComposer
    yaml.Resolver = _CoreSchemaResolver
    yaml.Constructor = _CoreSchemaConstructor
    return yaml


def _map_pointers(root: Any) -> dict[MappingNode, str]:
    """The JSON Pointer of each map node of the document's JSON form, by node, as `errors` writes it (`(root)` for the
    document): each map reached from `root` through list items and keys tagged `!!str`, and no other."""
    pointers: dict[MappingNode, str] = {}
    todo: list[tuple[Any, list[Any]]] = [(root, [])]
    while todo:
        node, path = todo.pop()
        if isinstance(node, MappingNode):
            pointers[node] = _pointer(path)
            todo.extend(
                (value, [*path, _joined(key.value, key.start_mark)])
                for key, value in node.value
                if key.tag == _TAG + "str" and isinstance(key, ScalarNode)
            )
        elif isinstance(node, SequenceNode):
            todo.extend((item, [*path, i]) for i, item in enumerate(node.value))
    return pointers


def load_document(source: Path | str) -> tuple[Any, list[tuple[str, str]]]:
    """`(document, left_out)`: the JSON form of the document in `source`, a file or a text, read as YAML 1.2.2 under
    the core schema only, and the keys left out of it; raises a `YAMLError` if it isn't such a document.

    A file's bytes are decoded as UTF-8, strictly (spec §3): bytes that aren't UTF-8 raise a `ReaderError`, so a UTF-16
    or UTF-32 file does too, though YAML 1.2.2 §5.2 reads them. A byte order mark that starts the text is kept, for the
    scanner to skip; one anywhere else outside a quoted scalar raises, though YAML 1.2.2 §5.2 allows one at the start
    of each document. The text is read by YAML 1.2.2's characters, tabs and line breaks (§5, §6.1, §6.2), where
    ruamel.yaml departs from them: a C0 control other than tab, LF and CR raises anywhere, and DEL, a C1 control other
    than NEL, U+FEFF, U+FFFE and U+FFFF raise outside a quoted scalar; NEL, LS and PS are ordinary characters, and a
    CR on its own ends a line; a tab separates wherever YAML 1.2.2 allows white space other than indentation (after a
    token, at a line's end, before a comment, inside a plain scalar, after an indentation's spaces before anything but
    a block collection), and raises in indentation, before a block collection after a block indicator (`-\\t-`), and in
    a block scalar's indentation.

    A plain scalar is a null, a bool, an int or a float only in its core-schema form, and a string otherwise (so
    timestamps and `1_000` are strings); a scalar tagged `!` is a string; `<<` is an ordinary key; a tag outside the
    core schema (`!!set`, `!!binary`, `!!omap`, `!!timestamp`, a local tag), a core tag on a node of another kind or
    a scalar of another form (`!!seq x`, `!!bool yes`) and a `%YAML` directive other than 1.2 are errors. An anchor,
    an alias and a second document raise `ComposerError`; a `...` with no document before it starts none, where
    ruamel.yaml would start one, so a file with no document (empty, or only comments and `...` lines) is None, and
    `...` lines before or after a document leave it the only one. Two keys of a map that are equal YAML nodes, with
    the same tag and canonical form, raise `DuplicateKeyError`, whatever their type. A flow collection's indicators
    are read as YAML 1.2.2 reads them, where ruamel.yaml would misread or refuse them: `?` is the explicit key
    indicator only before white space or a line break (`{?x: y}` has the key `?x`); `:` is the value indicator before
    white space, a line break or a flow indicator, and before anything after a JSON-like key (`[x:]` is
    `[{x: null}]`, `["x":y]` is `[{x: y}]`, and `{ :x}` is `{":x": null}`); a key of a flow mapping may span lines
    and be of any length; a single pair in a flow sequence may have an empty key (`[: x]`); and a tag may end an
    entry (`[!!str]` is `[""]`). Text YAML 1.2.2 makes ill-formed raises a `YAMLError` even where ruamel.yaml would
    read it: a comment glued to a token, an under-indented line of a flow collection or a quoted scalar, `[-]`,
    `[?]`, `{ :[b]}`, `!<!>`, and a `\\U` escape beyond U+10FFFF. A `RecursionError` (a document nested too deep)
    is left as it is.

    A value with no JSON form raises a `ConstructorError` (spec §3): `.inf`, `-.inf`, `.nan`, a number beyond a
    double's range (`1e400`, an integer of 400 digits), and a string holding a surrogate that isn't half of an
    escaped pair (`"\\uD800"`); an escaped pair is one character, so `"\\uD83D\\uDE00"` is U+1F600. A key that
    isn't a string (`true`, `1`, `~`, a list or a map) has no JSON form either, but it is left out rather than
    raised: its entry isn't in the document, and `left_out` holds `(pointer of the map, key as written)` for it, in
    document order, as `errors` writes a pointer, so that the rest of the document can be validated. A key inside a
    left-out entry is left out with it, and not listed. The document is composed first, so that each map's pointer
    is known, then constructed.
    """
    if isinstance(source, Path):
        data = source.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReaderError(
                str(source),
                error.start,
                data[error.start : error.start + 1],
                "utf-8",
                f"{error.reason}: an astra.yaml is UTF-8",
            ) from None
    else:
        text = source
    yaml = _core_schema_yaml()
    try:
        node = yaml.compose(text)
        if node is None:
            return None, []
        constructor = yaml.constructor
        constructor.map_pointers = _map_pointers(node)
        document = constructor.construct_document(node)
        return document, [(at, key) for _, at, key in sorted(constructor.left_out)]
    except (ValueError, OverflowError) as error:
        # ruamel.yaml turns a `\U` escape into a character without checking its range, so an escape beyond
        # U+10FFFF raises `ValueError` or `OverflowError`: it is raised as a `ScannerError`, from the original.
        raise ScannerError(
            None, None, f"found text YAML can't read as a value: {error}"
        ) from error


def _without_left_out_keys(loaded: tuple[Any, list[tuple[str, str]]]) -> Any:
    """The document of `load_document`'s result, or a `ValueError` naming the keys left out of it, if any."""
    document, left_out = loaded
    if left_out:
        raise ValueError(
            "keys that aren't strings, left out of the document's JSON form: "
            + ", ".join(f"{key!r} at {pointer}" for pointer, key in left_out)
        )
    return document


def load_yaml(path: Path) -> Any:
    """The JSON form of the document in `path`, its bytes decoded as strict UTF-8 and read as `load_document` reads
    them; raises a `YAMLError` if it isn't one, and a `ValueError` naming each key that isn't a string, if it has any.

    So a document that must be valid (a valid fixture, an example, a block of the specification) fails on such a key.
    """
    return _without_left_out_keys(load_document(path))


def load_yaml_text(text: str) -> Any:
    """The document `text`, read as `load_yaml` reads a file."""
    return _without_left_out_keys(load_document(text))


_DOUBLE_DIGITS = 309
"""The most digits an integer within a double's range can have: the greatest double is about 1.8 × 10^308."""


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """An object of a record, from its names and values in order; a name written twice raises `DuplicateNameError`."""
    found: dict[str, Any] = {}
    for name, value in pairs:
        if name in found:
            raise DuplicateNameError(
                f"found the name {name!r} twice in one object: a record's names are distinct"
            )
        found[name] = value
    return found


def _json_constant(text: str) -> Any:
    """`NaN`, `Infinity` or `-Infinity`, which `json.loads` reads but RFC 8259 has no form for: always raises."""
    raise JSONError(f"found {text}: RFC 8259 JSON has no such number")


def _json_float(text: str) -> float:
    """A number with a fraction or an exponent; one beyond a double's range, which rounds to infinity, raises."""
    number = float(text)
    if not math.isfinite(number):
        raise JSONError(
            f"{text!r} is beyond a double's range: it has no JSON form a record takes"
        )
    return number


def _json_int(text: str) -> int:
    """An integer, read exactly; one beyond a double's range, which a double rounds to infinity, raises.

    Its digits are counted first, since Python refuses to convert an integer of more than 4300 digits.
    """
    if len(text.lstrip("-")) <= _DOUBLE_DIGITS:
        number = int(text)
        try:
            float(number)
        except OverflowError:
            pass
        else:
            return number
    raise JSONError(
        f"{text[:20]}… is beyond a double's range: it has no JSON form a record takes"
    )


def _refuse_lone_surrogates(value: Any) -> None:
    """Raise `JSONError` if a string of `value`, a name included, holds a surrogate (U+D800-U+DFFF).

    `json.loads` joins an escaped surrogate pair into one character, so any surrogate left is a lone one, which has no
    JSON form (spec §3). Strict UTF-8 can't encode one, so raw text can't hold it: it comes only from an escape.
    """
    todo = [value]
    while todo:
        node = todo.pop()
        if isinstance(node, dict):
            todo.extend(node)
            todo.extend(node.values())
        elif isinstance(node, list):
            todo.extend(node)
        elif isinstance(node, str):
            try:
                node.encode("utf-8")
            except UnicodeEncodeError as error:
                raise JSONError(
                    f"found the lone surrogate U+{ord(node[error.start]):04X}: a string holding one has no JSON form"
                ) from None


def load_json(source: Path | str) -> Any:
    """The record in `source`, a file or a text, read as spec §3 reads a record: RFC 8259 JSON text in UTF-8 with no
    byte order mark, and with distinct names; raises a `JSONError` if it isn't one.

    A file's bytes are decoded as UTF-8, strictly, and a byte order mark at the start is refused, though RFC 8259 §8.1
    lets a parser ignore one. The text is read by `json.loads`, which takes only JSON's forms (no comment, trailing
    comma, single quote or YAML block form), except for what the hooks refuse: `NaN`, `Infinity` and `-Infinity`
    (`parse_constant`); a name written twice in one object, of which `json.loads` keeps the last, raises
    `DuplicateNameError` (`object_pairs_hook`), names being compared once their escapes are read, so `"a"` and
    `"\\u0061"` are one name; and a number beyond a double's range (`1e400`, an integer of 400 digits), which
    `json.loads` reads as an infinity or an exact integer (`parse_float`, `parse_int`). An escaped surrogate pair is
    one character, as `json.loads` reads it, so `"\\uD83D\\uDE00"` is U+1F600; any other surrogate (`"\\uD800"`) is
    refused by a walk over the value read, names included. A `RecursionError` (a record nested too deep) is left as it
    is.
    """
    data = source.read_bytes() if isinstance(source, Path) else source.encode("utf-8")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise JSONError(f"found bytes that aren't UTF-8: {error}") from None
    if text.startswith("\ufeff"):
        raise JSONError("found a byte order mark: a record starts without one")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_constant=_json_constant,
            parse_float=_json_float,
            parse_int=_json_int,
        )
    except json.JSONDecodeError as error:
        raise JSONError(f"found text that isn't RFC 8259 JSON: {error}") from None
    _refuse_lone_surrogates(value)
    return value


def load_fixture(path: Path) -> Any:
    """The document of the fixture at `path`: a record (`.json`) by `load_json`, an `astra.yaml` by `load_yaml`."""
    return load_json(path) if path.suffix == ".json" else load_yaml(path)


@functools.cache
def validator(root: str, *, closed: bool = True) -> Draft201909Validator:
    """A validator for documents rooted at `root`, from the committed schema (its open variant if not `closed`).

    Made once for each schema, so that each schema is read, and indexed for `absolute_keyword_location`, once.
    """
    suffix = ".schema.json" if closed else ".open.schema.json"
    schema = json.loads(
        (GENERATED / f"{_SCHEMA_NAMES[root]}{suffix}").read_text(encoding="utf-8")
    )
    Draft201909Validator.check_schema(schema)
    return Draft201909Validator(schema)


@functools.cache
def rules_catalogue() -> dict[str, Any]:
    """The committed `rules.json`: the rules of the specification's §9, and the error map of the JSON Schemas."""
    return json.loads((GENERATED / "rules.json").read_text(encoding="utf-8"))


def _pointer(path) -> str:
    """The JSON Pointer for a path of keys and indices, or `(root)` for the document."""
    return json_pointer(path) if path else "(root)"


_SUBSCHEMAS: dict[int, tuple[dict, dict[int, str]]] = {}
"""For each schema indexed, by `id`: the schema itself (kept, so that no other object takes its `id`), and the JSON
Pointer of every object in it, by `id`."""


def _subschema_pointers(schema: dict) -> dict[int, str]:
    """The JSON Pointer of every object in `schema`, by identity (`id`), indexed once per schema."""
    if id(schema) not in _SUBSCHEMAS:
        pointers: dict[int, str] = {}
        todo: list[tuple[Any, list[Any]]] = [(schema, [])]
        while todo:
            node, tokens = todo.pop()
            if isinstance(node, dict):
                pointers[id(node)] = json_pointer(tokens)
                todo.extend((child, [*tokens, key]) for key, child in node.items())
            elif isinstance(node, list):
                todo.extend((child, [*tokens, i]) for i, child in enumerate(node))
        _SUBSCHEMAS[id(schema)] = (schema, pointers)
    return _SUBSCHEMAS[id(schema)][1]


def absolute_keyword_location(v: Draft201909Validator, error: ValidationError) -> str:
    """The absolute keyword location of `error`: the URI of the schema resource, `#`, and the JSON Pointer to the keyword.

    That is the keyword's place once every `$ref` is resolved, as JSON Schema 2019-09 defines it and as `rules.json`
    keys its error map. `jsonschema`'s `absolute_schema_path` runs through `$ref`s without naming them, so it isn't
    that place (spec §10). But `error.schema` is the subschema that holds the failing keyword, and `error.validator`
    the keyword: the location is that subschema's JSON Pointer, found in the schema by identity, then the keyword. It
    is an error if the subschema isn't in the schema or doesn't hold the keyword.
    """
    pointer = _subschema_pointers(v.schema).get(id(error.schema))
    if (
        pointer is None
        or error.validator not in error.schema
        or error.absolute_schema_path[-1] != error.validator
    ):
        raise ValueError(
            f"{list(error.absolute_schema_path)}: the subschema that failed isn't found in the schema"
        )
    return v.schema["$id"] + "#" + pointer + json_pointer([error.validator])


def errors(v: Draft201909Validator, doc: Any) -> set[tuple[str, str, bool]]:
    """`(pointer, location, explains)` for every error `v` reports for `doc`, and for every error in each one's context.

    `location` is the error's absolute keyword location. `explains` is true for an error in the context of an error
    at the same pointer: it says why a branch of that combinator failed, rather than failing on its own.
    """
    found = set()
    for error in v.iter_errors(doc):
        outer = _pointer(error.absolute_path)
        found.add((outer, absolute_keyword_location(v, error), False))
        for e in error.context:
            pointer = _pointer(e.absolute_path)
            found.add((pointer, absolute_keyword_location(v, e), pointer == outer))
    return found


def error_pointers(v: Draft201909Validator, doc: Any) -> set[str]:
    """The JSON Pointer of every error `v` reports for `doc`, and of every error in each one's context."""
    return {pointer for pointer, _, _ in errors(v, doc)}


def header_file(path: Path) -> Path:
    """The file holding the header of the fixture at `path`: the fixture itself, or for a record (`.json`), which can't
    hold a comment, its sidecar `<stem>.header`."""
    return path.with_suffix(".header") if path.suffix == ".json" else path


def fixture_header(path: Path) -> tuple[str, str, tuple[str, str] | None]:
    """`(rule, fails_at, also)` from an invalid fixture's header, at the start of `header_file(path)`.

    The header is two comment lines, `# rule: <CODE>` and `# fails at: <location>`, then optionally a third,
    `# also: <CODE> at <pointer>`: a second error the fixture's one break brings. `also` is that line's
    `(code, pointer)`, or None. A third line that is a comment must be an `# also:` line.

    The lines are the first three that end in LF, read from the bytes as ASCII, so that a fixture that isn't UTF-8,
    or holds a CR on its own, has a header (a CR LF's CR is dropped).
    """
    header = header_file(path)
    if not header.is_file():
        raise ValueError(f"{path.name}: its header file {header.name} is missing")
    lines = [
        line.removesuffix(b"\r").decode("ascii", "replace")
        for line in header.read_bytes().split(b"\n")[:3]
    ]
    rule = _RULE_LINE.fullmatch(lines[0]) if lines else None
    fails_at = _FAILS_AT_LINE.fullmatch(lines[1]) if len(lines) > 1 else None
    if rule is None or fails_at is None:
        raise ValueError(
            f"{path.name}: lines 1-2 must be '# rule: <CODE>' and '# fails at: <location>'"
        )
    also = None
    if len(lines) > 2 and lines[2].startswith("#"):
        match = _ALSO_LINE.fullmatch(lines[2])
        if match is None:
            raise ValueError(
                f"{path.name}: a third comment line must be '# also: <CODE> at <pointer>'"
            )
        also = (match[1], match[2])
    return rule[1], fails_at[1], also


def fixtures(kind: str) -> list[Path]:
    """The fixtures of `kind` (`valid` or `invalid`), sorted: each `astra.yaml` (`.yaml`) and record (`.json`)."""
    return sorted([*(DATA / kind).glob("*.yaml"), *(DATA / kind).glob("*.json")])
