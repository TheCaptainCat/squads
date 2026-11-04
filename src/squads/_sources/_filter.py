"""The source filter language: one boolean expression per side of an issue, parsed when
``sources.toml`` loads and evaluated against the values an issue has on that side.

``not`` binds tightest, then ``and``, then ``or``, and ``and`` and ``or`` group from the left. A
value is a bare word (ASCII letters, digits and ``:-_.``) or a double-quoted string in which only
``\\"`` and ``\\\\`` are escapes. The keywords are lowercase.
"""

from abc import ABC, abstractmethod
from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum, auto
from unicodedata import category

_BARE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:-_.")
_KEYWORDS = ("or", "and", "not")
_BLANKS = " \t\n"
#: How deep parentheses and ``not`` may nest; deeper is refused at load.
MAX_DEPTH = 64


class FilterSyntaxError(ValueError):
    """A malformed expression, with the 1-based line and column of the character at fault."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} (line {line}, column {column})")
        self.message = message
        self.line = line
        self.column = column


class Expression(ABC):
    """A parsed boolean expression."""

    @abstractmethod
    def matches(self, values: Collection[str]) -> bool:
        """Whether the expression is true for an issue holding *values* on the side."""


@dataclass(frozen=True)
class Word(Expression):
    """A value: true when it is one of the issue's values on the side."""

    value: str

    def matches(self, values: Collection[str]) -> bool:
        """Whether *values* hold this value, spelled exactly."""
        return self.value in values


@dataclass(frozen=True)
class Negation(Expression):
    """``not`` and its operand."""

    operand: Expression

    def matches(self, values: Collection[str]) -> bool:
        """Whether the operand is false."""
        return not self.operand.matches(values)


@dataclass(frozen=True)
class Conjunction(Expression):
    """Operands joined by ``and``."""

    operands: tuple[Expression, ...]

    def matches(self, values: Collection[str]) -> bool:
        """Whether every operand is true."""
        return all(operand.matches(values) for operand in self.operands)


@dataclass(frozen=True)
class Disjunction(Expression):
    """Operands joined by ``or``."""

    operands: tuple[Expression, ...]

    def matches(self, values: Collection[str]) -> bool:
        """Whether some operand is true."""
        return any(operand.matches(values) for operand in self.operands)


def words(expression: Expression) -> tuple[str, ...]:
    """Every value *expression* names, in the order it names them."""
    if isinstance(expression, Word):
        return (expression.value,)
    if isinstance(expression, Negation):
        return words(expression.operand)
    if isinstance(expression, Conjunction | Disjunction):
        return tuple(w for operand in expression.operands for w in words(operand))
    return ()


class _Kind(Enum):
    VALUE = auto()
    OR = auto()
    AND = auto()
    NOT = auto()
    OPEN = auto()
    CLOSE = auto()
    END = auto()


@dataclass(frozen=True)
class _Token:
    kind: _Kind
    text: str
    line: int
    column: int

    def shown(self) -> str:
        """The token as a message names it."""
        if self.kind is _Kind.END:
            return "the end of the expression"
        if self.kind is _Kind.VALUE:
            return f"the value {self.text!r}"
        return f"{self.text!r}"


def _is_control(char: str) -> bool:
    """Whether *char* is a Unicode control character (category Cc)."""
    return category(char) == "Cc"


class _Lexer:
    """Cuts an expression into tokens, tracking the line and column of each character."""

    def __init__(self, source: str) -> None:
        self._source = source
        self._at = 0
        self._line = 1
        self._column = 1

    def _step(self) -> None:
        if self._source[self._at] == "\n":
            self._line += 1
            self._column = 1
        else:
            self._column += 1
        self._at += 1

    def _peek(self, offset: int = 0) -> str:
        at = self._at + offset
        return self._source[at] if at < len(self._source) else ""

    def tokens(self) -> list[_Token]:
        """Every token of the source, then the end marker."""
        found: list[_Token] = []
        while True:
            self._skip_blanks()
            if self._at >= len(self._source):
                found.append(_Token(_Kind.END, "", self._line, self._column))
                return found
            found.append(self._next())

    def _skip_blanks(self) -> None:
        while True:
            while self._peek() in _BLANKS and self._peek() != "":
                self._step()
            if self._peek() != "\r":
                return
            if self._peek(1) != "\n":
                raise FilterSyntaxError(
                    "a carriage return outside a CRLF line break", self._line, self._column
                )
            self._step()

    def _next(self) -> _Token:
        char = self._peek()
        line, column = self._line, self._column
        if char in "()":
            self._step()
            return _Token(_Kind.OPEN if char == "(" else _Kind.CLOSE, char, line, column)
        if char == '"':
            return _Token(_Kind.VALUE, self._quoted(), line, column)
        if char in _BARE:
            return self._bare(line, column)
        if _is_control(char):
            raise FilterSyntaxError(
                f"the control character U+{ord(char):04X} is not allowed in an expression",
                line,
                column,
            )
        shown = f"U+{ord(char):04X}" if not char.isprintable() else repr(char)
        raise FilterSyntaxError(
            f"the character {shown} is not allowed outside quotes; quote the value", line, column
        )

    def _bare(self, line: int, column: int) -> _Token:
        start = self._at
        while self._peek() != "" and self._peek() in _BARE:
            self._step()
        word = self._source[start : self._at]
        if word in _KEYWORDS:
            return _Token(_Kind[word.upper()], word, line, column)
        if word.lower() in _KEYWORDS:
            raise FilterSyntaxError(
                f"keywords are lowercase: write {word.lower()!r}, or quote the value "
                f'("{word}") to match it',
                line,
                column,
            )
        return _Token(_Kind.VALUE, word, line, column)

    def _quoted(self) -> str:
        opened = (self._line, self._column)
        self._step()
        chars: list[str] = []
        while True:
            char = self._peek()
            if char == "":
                raise FilterSyntaxError("a quoted value is not closed", *opened)
            if char == '"':
                break
            if char == "\\":
                following = self._peek(1)
                if following not in ('"', "\\"):
                    raise FilterSyntaxError(
                        'a backslash must be followed by " or \\ inside quotes',
                        self._line,
                        self._column,
                    )
                self._step()
                chars.append(following)
            elif _is_control(char):
                raise FilterSyntaxError(
                    "a control character or line break inside a quoted value",
                    self._line,
                    self._column,
                )
            else:
                chars.append(char)
            self._step()
        self._step()
        if not chars:
            raise FilterSyntaxError("a quoted value is empty", *opened)
        return "".join(chars)


def _spacing_hint(token: _Token) -> str:
    """The advice that goes with a value found where an operator was due."""
    return "; quote a value that holds a space" if token.kind is _Kind.VALUE else ""


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._at = 0
        self._depth = 0

    def _nested(self, token: _Token) -> None:
        """Count one more level of nesting at *token*, refusing past :data:`MAX_DEPTH`."""
        self._depth += 1
        if self._depth > MAX_DEPTH:
            raise FilterSyntaxError(
                f"nested more than {MAX_DEPTH} levels deep with 'not' or '('",
                token.line,
                token.column,
            )

    def _current(self) -> _Token:
        return self._tokens[self._at]

    def _advance(self) -> _Token:
        token = self._tokens[self._at]
        self._at += 1
        return token

    def parse(self) -> Expression:
        """The whole expression; anything left after it is a fault."""
        expression = self._disjunction()
        token = self._current()
        if token.kind is _Kind.CLOSE:
            raise FilterSyntaxError("')' closes no '('", token.line, token.column)
        if token.kind is not _Kind.END:
            raise FilterSyntaxError(
                f"expected 'and', 'or' or the end of the expression, found {token.shown()}"
                f"{_spacing_hint(token)}",
                token.line,
                token.column,
            )
        return expression

    def _disjunction(self) -> Expression:
        operands = [self._conjunction()]
        while self._current().kind is _Kind.OR:
            self._advance()
            operands.append(self._conjunction())
        return operands[0] if len(operands) == 1 else Disjunction(tuple(operands))

    def _conjunction(self) -> Expression:
        operands = [self._negation()]
        while self._current().kind is _Kind.AND:
            self._advance()
            operands.append(self._negation())
        return operands[0] if len(operands) == 1 else Conjunction(tuple(operands))

    def _negation(self) -> Expression:
        if self._current().kind is _Kind.NOT:
            self._nested(self._advance())
            operand = self._negation()
            self._depth -= 1
            return Negation(operand)
        return self._primary()

    def _primary(self) -> Expression:
        token = self._advance()
        if token.kind is _Kind.VALUE:
            return Word(token.text)
        if token.kind is _Kind.OPEN:
            self._nested(token)
            inner = self._disjunction()
            self._depth -= 1
            closing = self._current()
            if closing.kind is _Kind.CLOSE:
                self._advance()
                return inner
            if closing.kind is _Kind.END:
                raise FilterSyntaxError("'(' is not closed", token.line, token.column)
            raise FilterSyntaxError(
                f"expected 'and', 'or' or ')', found {closing.shown()}{_spacing_hint(closing)}",
                closing.line,
                closing.column,
            )
        raise FilterSyntaxError(
            f"expected a value or '(', found {token.shown()}", token.line, token.column
        )


def parse_expression(source: str) -> Expression:
    """The expression *source* writes; a malformed or empty one raises ``FilterSyntaxError``."""
    if not source.strip(" \t\r\n"):
        raise FilterSyntaxError("the expression is empty", 1, 1)
    return _Parser(_Lexer(source).tokens()).parse()
