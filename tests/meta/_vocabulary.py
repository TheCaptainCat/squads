"""What the bundled spec declares and how the vocabulary guards find it in the source tree.

Every name comes from a `WorkflowSpec`; nothing here lists a word. A name the engine itself defines
with the same spelling (a colour intent, a role capability) is not vocabulary and is left out by
reading those closed sets from the engine.
"""

import ast
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from squads._roles._models import REVIEW_CAPABILITY
from squads._workflow._models import COLOR_INTENTS, WorkflowSpec

#: The directories of the spec layer and of the released runners; the scan stops at them.
SPEC_LAYER_DIRS: frozenset[str] = frozenset({"_specs", "_migrations"})

type Vocabulary = dict[str, frozenset[str]]

#: The vocabulary categories, as the guards name them.
REF = "ref kind"
STATUS = "status"
KIND = "sub-entity kind"
TYPE = "item type"
FIELD = "field"


def _declared(spec: WorkflowSpec) -> Iterator[tuple[str, str]]:
    """Every `(name, category)` pair *spec* declares, the reserved roster types aside."""
    for type_name, item in spec.items.items():
        if spec.item_is_roster(type_name):
            continue
        yield type_name, TYPE
        yield item.prefix, TYPE
        yield from ((alias, TYPE) for alias in item.aliases)
        yield from ((declared.code, FIELD) for declared in item.fields)
    for kind, kind_spec in spec.subentity_kinds.items():
        yield kind, KIND
        yield kind_spec.plural, KIND
        yield kind_spec.local_prefix, KIND
        yield from ((declared.code, FIELD) for declared in kind_spec.fields)
    for name, collection in spec.collections.items():
        yield name, FIELD
        yield from ((badge.code, FIELD) for badge in collection.badges)
    yield from ((name, REF) for name in spec.ref_kinds)
    for machine in spec.lifecycles.values():
        yield from ((state, STATUS) for state in machine.states)


def vocabulary(spec: WorkflowSpec, *categories: str) -> Vocabulary:
    """Every name *spec* declares in the given *categories*, mapped to the categories naming it.

    The reserved roster types are not vocabulary: no override drops them.
    """
    found: dict[str, set[str]] = {}
    for name, category in _declared(spec):
        if name and category in categories:
            found.setdefault(name, set()).add(category)
    return {name: frozenset(owners) for name, owners in found.items()}


def dropped(bundled: Vocabulary, kept: Vocabulary) -> Vocabulary:
    """The names of *bundled* that a squad with the vocabulary *kept* no longer declares."""
    return {name: owners for name, owners in bundled.items() if name not in kept}


#: The constants through which the engine names a word of its own, by the name they are assigned
#: to: the assignment that defines one is the only place its spelling is allowed.
ENGINE_CONSTANTS: dict[str, str] = {"REVIEW_CAPABILITY": REVIEW_CAPABILITY}


def engine_words() -> frozenset[str]:
    """Words the engine defines for itself wherever it spells them: the colour intents."""
    return COLOR_INTENTS


@dataclass(frozen=True)
class Hit:
    path: str
    lineno: int
    name: str
    owners: frozenset[str]

    def __str__(self) -> str:
        return f"{self.path}:{self.lineno}: {self.name!r} ({', '.join(sorted(self.owners))})"


def source_files(root: Path, *suffixes: str) -> Iterator[Path]:
    """Every file under `src/squads` of *root* with one of *suffixes*, the spec layer excluded."""
    base = root / "src" / "squads"
    if not base.is_dir():
        return
    for path in sorted(base.rglob("*")):
        if (
            path.is_file()
            and path.suffix in suffixes
            and "__pycache__" not in path.parts
            and not SPEC_LAYER_DIRS & set(path.relative_to(base).parts)
        ):
            yield path


def _registered_names(tree: ast.AST) -> set[str]:
    """The names of functions registered as `app.command("x")(fn)`, bare or wrapped."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Call)
            and isinstance(node.func.func, ast.Attribute)
            and node.func.func.attr in ("command", "callback")
        ):
            for argument in node.args:
                inner = argument
                while isinstance(inner, ast.Call) and inner.args:
                    inner = inner.args[0]
                if isinstance(inner, ast.Name):
                    names.add(inner.id)
    return names


def _is_command(node: ast.AST, registered: set[str]) -> bool:
    """Whether *node* is a function registered as a command or group callback, whose docstring
    Typer prints as `--help`: decorated, or applied to the result of `app.command(...)`."""
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    return node.name in registered or any(
        isinstance(d, ast.Call)
        and isinstance(d.func, ast.Attribute)
        and d.func.attr in ("command", "callback")
        for d in node.decorator_list
    )


def _docstring_ids(tree: ast.AST) -> set[int]:
    """The docstrings that are developer prose: every one but those of commands."""
    registered = _registered_names(tree)
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and not _is_command(node, registered)
            ):
                ids.add(id(first.value))
    return ids


def _engine_definition_ids(tree: ast.AST) -> set[int]:
    """The string constants that define an engine constant (`NAME = "word"`)."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign) and isinstance(node.value, ast.Constant):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if any(ENGINE_CONSTANTS.get(n) == node.value.value for n in names):
                ids.add(id(node.value))
    return ids


def string_constants(tree: ast.AST) -> Iterator[ast.Constant]:
    """Every string constant of *tree* that is not a docstring or an engine constant's definition
    (implicit concatenations are one)."""
    docstrings = _docstring_ids(tree) | _engine_definition_ids(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            yield node


def string_units(tree: ast.AST) -> Iterator[tuple[int, str]]:
    """Every string of *tree* that is not a docstring as `(line, text)`, an f-string as one text
    with `{}` for each expression, so a code span split across its pieces stays whole."""
    inside: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            inside |= {id(part) for part in ast.walk(node) if part is not node}
            yield (
                node.lineno,
                "".join(
                    part.value
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                    else "{}"
                    for part in node.values
                ),
            )
    for node in string_constants(tree):
        if id(node) not in inside:
            assert isinstance(node.value, str)
            yield node.lineno, node.value


_AFFIXES = ("--min-", "--no-", "--", "add-")


_ID_HEAD_RE = re.compile(r"([A-Z]+)-(?:$|[^A-Za-z])")


def _stem(value: str) -> str:
    """*value* without a flag or verb prefix, so `--priority` and `add-story` read as the name; an
    ID written with its prefix and dash (`TASK-`, `TASK-%d`) reads as the prefix."""
    for affix in _AFFIXES:
        if value.startswith(affix):
            return value.removeprefix(affix)
    head = _ID_HEAD_RE.match(value)
    return head.group(1) if head else value


def literal_hits(root: Path, names: Vocabulary, *, ignore: Iterable[str] = ()) -> list[Hit]:
    """String constants of the source equal to one of *names*, bare or as a flag or verb of it.

    A one-character name is read only inside a code span (`span_hits`): alone it is
    indistinguishable from a format character.
    """
    skipped = frozenset(ignore)
    wanted = {n: o for n, o in names.items() if len(n) > 1 and n not in skipped}
    hits: list[Hit] = []
    for path in source_files(root, ".py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(root).as_posix()
        for node in string_constants(tree):
            stem = _stem(str(node.value))
            if stem in wanted:
                hits.append(Hit(rel, node.lineno, stem, wanted[stem]))
    return hits


_SPAN_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_FENCE = "```"
_JINJA_TAG_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
_JINJA_LITERAL_RE = re.compile(r"'([^'\n]*)'|\"([^\"\n]*)\"")
_JINJA_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


def code_spans(text: str) -> Iterator[tuple[int, str]]:
    """The code spans of *text* as `(line number, span text)`: inline backtick spans, every line
    of a fenced block, and a line that is a command (`sq ...`)."""
    fenced = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(_FENCE):
            fenced = not fenced
            continue
        if fenced or stripped.startswith("sq "):
            yield lineno, line
            continue
        for match in _SPAN_RE.finditer(line):
            yield lineno, match.group(1)


def names_pattern(names: Iterable[str]) -> re.Pattern[str]:
    """A pattern for any of *names* as a whole token (a flag or a verb prefix may touch it).

    A one-character name (an alias such as `f`) is read only as the word after `sq`.
    """
    long = sorted((n for n in names if len(n) > 1), key=len, reverse=True)
    short = sorted(n for n in names if len(n) == 1)
    long_alt = "|".join(map(re.escape, long)) or "(?!)"
    short_alt = "|".join(map(re.escape, short)) or "(?!)"
    return re.compile(
        rf"(?<![A-Za-z0-9_])(?P<long>{long_alt})(?![A-Za-z0-9_])"
        rf"|\bsq\s+(?P<short>{short_alt})(?![\w-])"
    )


def span_hits_in(
    text: str, path: str, names: Vocabulary, *, line_offset: int = 0, ignore: Iterable[str] = ()
) -> list[Hit]:
    """The names of *names* that appear inside a code span of *text*."""
    skipped = frozenset(ignore)
    wanted = {n: o for n, o in names.items() if n not in skipped}
    if not wanted:
        return []
    pattern = names_pattern(wanted)
    return [
        Hit(path, lineno + line_offset, name, wanted[name])
        for lineno, span in code_spans(text)
        for match in pattern.finditer(span)
        for name in [match.group("long") or match.group("short")]
    ]


def span_hits(root: Path, names: Vocabulary, *, ignore: Iterable[str] = ()) -> list[Hit]:
    """Names inside a code span of a source string constant or a template of the source tree."""
    hits: list[Hit] = []
    for path in source_files(root, ".py", ".j2"):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".j2":
            generated = _JINJA_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
            hits.extend(span_hits_in(generated, rel, names, ignore=ignore))
            continue
        for lineno, unit in string_units(ast.parse(text)):
            hits.extend(span_hits_in(unit, rel, names, line_offset=lineno - 1, ignore=ignore))
    return hits


def template_literal_hits(
    root: Path, names: Vocabulary, *, ignore: Iterable[str] = ()
) -> list[Hit]:
    """Quoted literals equal to one of *names* inside the `{{ }}` and `{% %}` tags of a template."""
    skipped = frozenset(ignore)
    wanted = {n: o for n, o in names.items() if len(n) > 1 and n not in skipped}
    hits: list[Hit] = []
    for path in source_files(root, ".j2"):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for tag in _JINJA_TAG_RE.finditer(text):
            lineno = text.count("\n", 0, tag.start()) + 1
            for literal in _JINJA_LITERAL_RE.finditer(tag.group(0)):
                value = literal.group(1) if literal.group(1) is not None else literal.group(2)
                if value in wanted:
                    hits.append(Hit(rel, lineno, value, wanted[value]))
    return hits


def tree_hits(root: Path, spec: WorkflowSpec, *categories: str) -> list[Hit]:
    """Every place the source tree of *root* spells a name *spec* declares in *categories*: a bare
    string, a flag or verb of it, a code span of a string or template, a quoted template literal."""
    names = vocabulary(spec, *categories)
    ignore = engine_words()
    return [
        *literal_hits(root, names, ignore=ignore),
        *span_hits(root, names),
        *template_literal_hits(root, names, ignore=ignore),
    ]


def report(hits: list[Hit]) -> str:
    """The hits as one line each, for an assertion message."""
    return "\n".join(f"  {hit}" for hit in hits)
