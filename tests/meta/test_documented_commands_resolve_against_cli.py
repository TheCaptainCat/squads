"""Drift guard: every `sq …` invocation shown in the bundled docs must resolve against the
live Typer command tree, token by token, so a doc can never silently cite a dead verb/flag."""

import re
import shlex
from pathlib import Path
from typing import Any

import typer.main

from squads import __version__, _docfiles
from squads._cli import app

#: A token standing in for the whole command shape rather than one concrete value.
#: `<n>`/`<k>` are excluded: those are real address placeholders, handled structurally.
_ABSTRACT_PLACEHOLDER_RE = re.compile(r"^<.+>$")
_ADDRESS_PLACEHOLDER_RE = re.compile(r"^<[nk]>$", re.IGNORECASE)

#: A token meaning "…and so on" — the rest of the line is elided.
_ELISION_TOKENS = frozenset({"…", "...", "*"})

#: Hypothetical custom item types the docs use as a worked example for declaring one.
_ILLUSTRATIVE_CUSTOM_TYPES = frozenset({"incident", "inc", "postmortem"})

#: Flags for the hypothetical `impact` badge collection the docs use as a worked example.
_ILLUSTRATIVE_CUSTOM_FLAGS = frozenset({"--impact", "--min-impact"})

#: Sentinel returned by `_resolve` for an exempt (abstract/elided/illustrative) invocation.
_ABSTRACT = "<abstract>"

#: Exact invocations citing a removed verb/flag for contrast, checked verbatim since they
#: must NOT resolve.
_ALLOWLISTED_HISTORICAL_CITATIONS = frozenset({"sq role list --available"})

#: Shell composition, not part of the `sq` invocation itself — everything from here on is
#: shell plumbing, not more of this command's own args.
_SHELL_METACHARACTERS = frozenset({"|", "||", "&&", ";", ">", ">>", "<"})

#: A bare flag shown as optional in prose (`[--purge]`); unwrap and validate as usual.
_BRACKETED_FLAG_RE = re.compile(r"^\[(-{1,2}[\w-]+)\]$")

_FENCE_RE = re.compile(r"^```([A-Za-z]*)[ \t]*\n(.*?)^```", re.DOTALL | re.MULTILINE)
_INLINE_RE = re.compile(r"`(sq [^`]+)`")
_SQ_WORD_RE = re.compile(r"(?<![\w./-])sq(?=\s)")
_OVERRIDE_BASE_VERSION_RE = re.compile(r"override-base:(\d+)\.(\d+)\.(\d+)")


def _repo_root() -> Path:
    return Path(_docfiles.__file__).resolve().parents[2]


def _own_option_arity(cmd: Any, token: str) -> int | None:
    """How many extra tokens *token* consumes if it's one of *cmd*'s own declared options
    (0 for a bare flag, 1 for a value option), or None if it isn't one. Also recognizes the
    Click-auto-added help option via ``get_help_option_names``, never a hardcoded string."""
    for p in getattr(cmd, "params", []):
        if getattr(p, "param_type_name", None) == "option" and token in (p.opts or []):
            return 0 if getattr(p, "is_flag", False) else 1
    if getattr(cmd, "add_help_option", False):
        ctx = cmd.make_context("sq", [], resilient_parsing=True)
        if token in cmd.get_help_option_names(ctx):
            return 0
    return None


def _has_positional_argument(cmd: Any) -> bool:
    """True when *cmd* itself declares a required positional `Argument` — used both for a
    group's own address token and for whether a leaf command accepts a bare positional."""
    return any(
        getattr(p, "param_type_name", None) == "argument" for p in getattr(cmd, "params", [])
    )


def _leaf_tokens_are_declared(cmd: Any, tokens: list[str], start: int) -> bool:
    """Once the walk lands on a leaf command, validate its own remaining tokens: every flag
    must be one of its declared options, and a bare token is legitimate only if it declares a
    positional argument. A shell metacharacter ends the invocation; a bracketed optional flag
    is unwrapped and checked the same way."""
    i, n = start, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in _SHELL_METACHARACTERS:
            return True
        bracketed = _BRACKETED_FLAG_RE.match(tok)
        if bracketed is not None:
            tok = bracketed.group(1)
        # A lone "-" (read from stdin) is a positional value, never an option.
        if tok.startswith("-") and tok != "-":
            arity = _own_option_arity(cmd, tok)
            if arity is None:
                return False
            i += 1 + arity
            continue
        if not _has_positional_argument(cmd):
            return False
        i += 1
    return True


def _is_abstract_token(tok: str) -> bool:
    """True for a token that marks the whole invocation as grammar/illustrative: an elision
    marker, an illustrative custom name/flag, or a command-shape bracket placeholder."""
    illustrative = _ELISION_TOKENS | _ILLUSTRATIVE_CUSTOM_TYPES | _ILLUSTRATIVE_CUSTOM_FLAGS
    if tok in illustrative:
        return True
    return bool(_ABSTRACT_PLACEHOLDER_RE.match(tok) and not _ADDRESS_PLACEHOLDER_RE.match(tok))


def _resolve(tokens: list[str]) -> str | None:
    """Walk *tokens* against the live command tree; return the resolved path, `_ABSTRACT` if
    exempt, or None if it doesn't resolve."""
    current: Any = typer.main.get_command(app)
    i, n = 0, len(tokens)
    path: list[str] = []
    while i < n and tokens[i].startswith("-"):
        arity = _own_option_arity(current, tokens[i])
        if arity is None:
            return None
        path.append(tokens[i])
        i += 1 + arity
    while i < n:
        tok = tokens[i]
        if _is_abstract_token(tok):
            return _ABSTRACT
        if not hasattr(current, "commands"):
            # A leaf command: validate its own remaining tokens rather than waving them through.
            if not _leaf_tokens_are_declared(current, tokens, i):
                return None
            break
        if tok.startswith("-"):
            arity = _own_option_arity(current, tok)
            if arity is None:
                break
            i += 1 + arity
            continue
        child = current.commands.get(tok)
        if child is not None:
            current = child
            path.append(tok)
            i += 1
            # Only a freshly-entered group auto-consumes an address token here.
            if hasattr(current, "commands") and _has_positional_argument(current) and i < n:
                i += 1
                path.append("<n>")
            continue
        # Not a literal child: try the hidden `_addr` subgroup (slug-or-id addressing).
        addr_group = getattr(current, "commands", {}).get("_addr")
        if addr_group is None:
            return None
        current = addr_group
        path.append("<n>")
        i += 1
    return " ".join(path) if path else None


def _split_invocations(block_text: str) -> list[str]:
    """One entry per standalone ``sq`` word in *block_text*, each running to the next such word
    or the end of its line — so a cheatsheet line holding two commands side by side yields two
    invocations. Full-`#`-comment lines are skipped; a trailing inline `# …` is stripped first."""
    invocations: list[str] = []
    for line in block_text.splitlines():
        if line.strip().startswith("#"):
            continue
        line = line.split(" #", 1)[0]
        starts = [m.start() for m in _SQ_WORD_RE.finditer(line)]
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(line)
            invocations.append(line[start:end].strip())
    return invocations


def _extract_invocations(text: str) -> list[str]:
    """Every ``sq …`` invocation documented in one file's raw markdown text."""
    invocations: list[str] = []
    prose_chunks: list[str] = []
    last_end = 0
    for m in _FENCE_RE.finditer(text):
        prose_chunks.append(text[last_end : m.start()])
        last_end = m.end()
        if m.group(1) in ("sh", "bash"):
            invocations.extend(_split_invocations(m.group(2)))
    prose_chunks.append(text[last_end:])
    for m in _INLINE_RE.finditer("".join(prose_chunks)):
        invocations.extend(_split_invocations(m.group(1)))
    return invocations


def _all_documented_invocations() -> list[tuple[str, str]]:
    """``(doc filename, raw invocation)`` for every documented ``sq …`` command, across every
    bundled doc — excluding `_ALLOWLISTED_HISTORICAL_CITATIONS`."""
    pairs: list[tuple[str, str]] = []
    for doc in sorted((_repo_root() / "docs").glob("*.md")):
        pairs.extend(
            (doc.name, invocation)
            for invocation in _extract_invocations(doc.read_text(encoding="utf-8"))
            if invocation not in _ALLOWLISTED_HISTORICAL_CITATIONS
        )
    return pairs


def test_documented_sq_invocations_resolve_against_the_live_command_tree() -> None:
    failures: list[str] = []
    for doc_name, invocation in _all_documented_invocations():
        tokens = shlex.split(invocation)
        if not tokens or tokens[0] != "sq" or len(tokens) == 1:
            continue
        outcome = _resolve(tokens[1:])
        if outcome is None:
            failures.append(f"{doc_name}: {invocation!r} does not resolve against the live CLI")
    assert not failures, "\n".join(failures)


def test_the_extractor_finds_known_anchor_commands() -> None:
    """A broken extractor that silently matches nothing must not pass vacuously."""
    resolved = {
        outcome
        for _, invocation in _all_documented_invocations()
        for tokens in [shlex.split(invocation)]
        if tokens and tokens[0] == "sq" and len(tokens) > 1
        for outcome in [_resolve(tokens[1:])]
        if outcome not in (None, _ABSTRACT)
    }
    assert resolved
    assert "role catalog" in resolved
    assert "feature <n> add-story" in resolved


def test_a_bogus_flag_on_a_resolved_leaf_command_fails_to_resolve() -> None:
    """A made-up flag on an otherwise-real verb path must not silently pass."""
    assert _resolve(["role", "list", "--nonexistent-flag"]) is None
    assert _resolve(["create", "feature", "X", "--status", "Draft"]) is None


def test_an_unexpected_positional_on_a_flag_only_leaf_command_fails_to_resolve() -> None:
    """A bare positional where the leaf declares none at all must not resolve."""
    assert _resolve(["dev", "add", "python"]) is None


def test_a_leaf_commands_real_flags_and_positionals_still_resolve() -> None:
    """The stricter leaf check must not false-positive on legitimate usage."""
    assert _resolve(["role", "list", "--json"]) == "role list"
    assert _resolve(["dev", "add", "--tech", "python"]) == "dev add"
    assert _resolve(["create", "feature", "Login", "--parent", "EPIC-1"]) == "create feature"


def test_a_bare_root_level_flag_resolves_instead_of_being_read_as_unresolved() -> None:
    """A bare root-level flag consuming the whole line resolves, for every flag this app
    actually declares."""
    assert _resolve(["--version"]) == "--version"
    assert _resolve(["--install-completion"]) == "--install-completion"
    assert _resolve(["--show-completion"]) == "--show-completion"


def test_the_auto_added_help_flag_resolves_at_root_group_and_leaf_level() -> None:
    """The Click-auto-added `--help` flag resolves at the root, a group, and a leaf."""
    assert _resolve(["--help"]) == "--help"
    assert _resolve(["role", "--help"]) == "role"
    assert _resolve(["role", "list", "--help"]) == "role list"


def test_a_flag_this_cli_never_declared_still_fails_to_resolve() -> None:
    """A flag this CLI never declared, including the short `-h` form, still fails to resolve."""
    assert _resolve(["-h"]) is None
    assert _resolve(["--totally-not-a-real-flag"]) is None


def test_no_documented_override_base_stamp_is_a_stale_version() -> None:
    """A concrete `override-base:<x.y.z>` literal in the docs must not be behind the installed
    version; the placeholder forms are exempt."""
    installed = tuple(int(part) for part in __version__.split(".")[:3])
    stale: list[str] = []
    for doc in sorted((_repo_root() / "docs").glob("*.md")):
        for m in _OVERRIDE_BASE_VERSION_RE.finditer(doc.read_text(encoding="utf-8")):
            cited = tuple(int(g) for g in m.groups())
            if cited < installed:
                stale.append(f"{doc.name}: {m.group(0)} behind installed {__version__}")
    assert not stale, "\n".join(stale)
