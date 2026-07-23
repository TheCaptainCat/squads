"""Drift guard: every `sq …` invocation shown in the bundled docs (`docs/*.md`) must resolve
against the live Typer command tree, so a doc can never silently cite a verb/flag that no
longer exists.

**Extraction rule** (kept narrow and high-signal on purpose):

- Only ```sh``` / ```bash``` fenced blocks, plus inline `` `sq …` `` code spans in the
  surrounding prose, are scanned. Fenced blocks tagged anything else (plain ``` ``` ``` ASCII
  diagrams, rendered-table/error-output examples) are stripped out *before* the inline scan runs,
  so example program output that happens to contain literal backticks is never mistaken for a
  documented command.
- A full-line `#` comment is skipped outright; a trailing inline `# …` comment is stripped before
  matching. A single physical line may hold more than one invocation (two commands side by side
  in a cheatsheet) — each match of a standalone `sq` word starts a fresh invocation running to the
  next match or the end of the line, so both are checked independently.
- Each invocation is shlex-tokenized and walked against the real command tree
  (`typer.main.get_command`), token by token:
    - a **global option** the current group actually declares (e.g. `--at <value>` before the
      verb) is skipped, consuming its value only if it isn't a bare flag;
    - an **address token** — the item number after `task`/`feature`/…, the local id after a
      sub-entity kind, or a role/operator/skill slug/id — is skipped structurally: either the
      current group declares a required positional `Argument` on itself (so any next token is its
      address, whatever it looks like), or it routes through a hidden `_addr` subgroup. Neither
      case is decided by pattern-matching digits or slug shapes — both are real, introspectable
      properties of the command tree, so this handles every addressed type/kind generically with
      no hardcoded type list;
    - once the walk reaches a leaf command (no further subcommands), its remaining tokens ARE
      still validated (`_leaf_tokens_are_declared`): every `-`/`--`-prefixed token must be one
      of that leaf's declared options, and a bare token is only legitimate if the leaf declares
      a positional `Argument` at all — this is what catches a `--status` flag `create` never
      had, `role list --available` after the flag was removed, or `sq dev add python` (no
      positional there; the technology is `--tech`, required). A legitimate positional's own
      *shape* (a title's wording, a status name, a target id) is still never inspected — only
      "is a positional expected here" and "is this flag real."
  If a token is none of the above, the invocation fails to resolve — *unless* it (or a later
  token) is a bracket placeholder standing in for the command name itself (`<type>`, `<kind>`,
  `<command>`, …, but not the address placeholders `<n>`/`<k>`) or an elision marker (`…`, `...`,
  `*`) — those mark the line as grammar/illustrative rather than a literal command, and the whole
  invocation is exempt.
- A tiny, explicitly commented allowlist (`_ILLUSTRATIVE_CUSTOM_TYPES` below) covers worked
  examples of a *hypothetical* custom item type a walkthrough teaches the reader to declare
  (`incident`/`inc`, `postmortem`) — real invocations, but only once *that reader's own*
  override declares the type, so they can't resolve against this process's bundled spec. The
  mechanism itself is proven end-to-end in
  tests/cli/test_custom_type_end_to_end.py.

A secondary, best-effort check (`test_no_documented_override_base_stamp_is_a_stale_version`)
flags a concrete `override-base:<x.y.z>` version literal left behind in the docs — the
`<version>`/`<current-squads-version>` placeholder forms used throughout are exempt by
construction (they're not digits).
"""

import re
import shlex
from pathlib import Path
from typing import Any

import typer.main

from squads import __version__, _docfiles
from squads._cli import app

#: A token that stands in for the whole command name/shape rather than one concrete argument
#: value — the line is grammar/illustrative, not a literal invocation. `<n>`/`<k>` are excluded:
#: those are real address placeholders and are handled structurally (see `_address_child`), not
#: exempted wholesale.
_ABSTRACT_PLACEHOLDER_RE = re.compile(r"^<.+>$")
_ADDRESS_PLACEHOLDER_RE = re.compile(r"^<[nk]>$", re.IGNORECASE)

#: A token meaning "…and so on" — the rest of the line is elided, not a literal argument list.
_ELISION_TOKENS = frozenset({"…", "...", "*"})

#: Hypothetical custom item types (`incident`/its `inc` alias, `postmortem`) that docs/workflow.md
#: and docs/overrides.md use as the worked example when teaching the reader to declare a custom
#: type — real once *that* override exists, never in the bundled spec these tests run against.
_ILLUSTRATIVE_CUSTOM_TYPES = frozenset({"incident", "inc", "postmortem"})

#: Same idea, one level down: flags for the hypothetical `impact` badge collection
#: docs/overrides.md's "Collections: custom badge axes" section teaches the reader to declare —
#: real once *that* override exists, never a flag on the bundled `task update` / `list`.
_ILLUSTRATIVE_CUSTOM_FLAGS = frozenset({"--impact", "--min-impact"})

#: Sentinel returned by `_resolve` for an exempt (abstract/elided/illustrative) invocation.
_ABSTRACT = "<abstract>"

#: Exact raw invocations that cite a *removed* verb/flag for contrast, not as a live example —
#: e.g. stability.md documenting that `--available` is gone. Checked verbatim (not structurally)
#: since the whole point is that these must NOT resolve; kept to one entry, commented.
_ALLOWLISTED_HISTORICAL_CITATIONS = frozenset({"sq role list --available"})

#: Shell composition, not part of the `sq` invocation itself (`sq check || exit 1`, a piped
#: `sq list --json | jq …`) — once one of these appears among a leaf's remaining tokens,
#: everything from there on is shell plumbing, not more of *this* command's own args.
_SHELL_METACHARACTERS = frozenset({"|", "||", "&&", ";", ">", ">>", "<"})

#: A bare flag shown as optional in prose (`[--purge]`) — the brackets are documentation
#: notation, not shell syntax; unwrap and validate the flag inside them the same way.
_BRACKETED_FLAG_RE = re.compile(r"^\[(-{1,2}[\w-]+)\]$")

_FENCE_RE = re.compile(r"^```([A-Za-z]*)[ \t]*\n(.*?)^```", re.DOTALL | re.MULTILINE)
_INLINE_RE = re.compile(r"`(sq [^`]+)`")
_SQ_WORD_RE = re.compile(r"(?<![\w./-])sq(?=\s)")
_OVERRIDE_BASE_VERSION_RE = re.compile(r"override-base:(\d+)\.(\d+)\.(\d+)")


def _repo_root() -> Path:
    return Path(_docfiles.__file__).resolve().parents[2]


def _own_option_arity(cmd: Any, token: str) -> int | None:
    """How many extra tokens *token* consumes if it's one of *cmd*'s own declared options
    (0 for a bare flag, 1 for a value option) — or None if it isn't one of *cmd*'s options."""
    for p in getattr(cmd, "params", []):
        if getattr(p, "param_type_name", None) == "option" and token in (p.opts or []):
            return 0 if getattr(p, "is_flag", False) else 1
    return None


def _has_positional_argument(cmd: Any) -> bool:
    """True when *cmd* itself declares a required positional `Argument`.

    Two distinct uses of the same underlying check: (1) as a *group*, every
    `sq <type> <n> …` group and sub-entity `<kind> <k> …` subgroup carries one — the address,
    consumed exactly once, immediately on freshly entering such a group (see `_resolve`) —
    never re-checked once we've already landed past it, which is what a naive "does the
    current group have an argument" re-check on every unmatched token would do (it would
    treat a genuinely bad verb right after the address as *one more* address to skip); (2) as
    a *leaf* command, whether it accepts a bare positional at all — `sq dev add` doesn't (only
    `--tech`/`--name`/`--model`), so a trailing bare token there is drift, not an opaque title
    (see `_leaf_tokens_are_declared`)."""
    return any(
        getattr(p, "param_type_name", None) == "argument" for p in getattr(cmd, "params", [])
    )


def _leaf_tokens_are_declared(cmd: Any, tokens: list[str], start: int) -> bool:
    """Once the verb path has resolved to a leaf command, validate *its own* remaining tokens
    instead of leaving them all unexamined:

    - every `-`/`--`-prefixed token must be one of *cmd*'s declared options (`_own_option_arity`)
      — this is the flag-drift class a path-only walk misses entirely, e.g. a `--status` flag
      `create` never had, or `role list --available` after the flag was removed;
    - a bare (non-flag) token is only legitimate if *cmd* declares a positional `Argument` at
      all — so `sq dev add python` (no positional on `dev add`; the technology is `--tech`,
      required) fails too, not just an unknown flag.

    A legitimate positional's own *shape* — a title's wording, a status name, a target id — is
    still never inspected; only "is a positional expected here at all" and "is this flag real"
    are, matching every other opaque-value spot in this walk. A shell metacharacter (`|`, `;`, …)
    ends the invocation outright — everything after it is shell plumbing, not this leaf's own
    args — and a bracket-wrapped optional flag (`[--purge]`) is unwrapped and checked the same
    way as a bare one.
    """
    i, n = start, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in _SHELL_METACHARACTERS:
            return True
        bracketed = _BRACKETED_FLAG_RE.match(tok)
        if bracketed is not None:
            tok = bracketed.group(1)
        if tok.startswith("-"):
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
    """True for a token that marks the whole invocation as grammar/illustrative rather than a
    literal command — an elision marker, a hypothetical-custom-vocabulary name/flag, or a
    bracket placeholder standing in for the command shape itself (`<n>`/`<k>` excluded — those
    are real address slots, handled structurally, not exempted wholesale)."""
    illustrative = _ELISION_TOKENS | _ILLUSTRATIVE_CUSTOM_TYPES | _ILLUSTRATIVE_CUSTOM_FLAGS
    if tok in illustrative:
        return True
    return bool(_ABSTRACT_PLACEHOLDER_RE.match(tok) and not _ADDRESS_PLACEHOLDER_RE.match(tok))


def _resolve(tokens: list[str]) -> str | None:
    """Walk *tokens* (an invocation with the leading ``sq`` already dropped) against the live
    command tree. Returns the normalized resolved path (e.g. ``"feature <n> add-story"``),
    `_ABSTRACT` if the invocation is exempt, or None if it doesn't resolve.
    """
    current: Any = typer.main.get_command(app)
    i, n = 0, len(tokens)
    path: list[str] = []
    while i < n and tokens[i].startswith("-"):
        arity = _own_option_arity(current, tokens[i])
        if arity is None:
            return None
        i += 1 + arity
    while i < n:
        tok = tokens[i]
        if _is_abstract_token(tok):
            return _ABSTRACT
        if not hasattr(current, "commands"):
            # A leaf command — validate its own remaining tokens (flags AND positionals)
            # rather than waving them through unexamined (see `_leaf_tokens_are_declared`).
            # Checked *before* the generic flag branch below, which is for a still-open
            # group's own options (e.g. the root `--at`) and must not swallow a leaf's.
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
            # Only a freshly-entered *group* (more subcommands ahead, e.g. task/feature/a
            # sub-entity kind) auto-consumes an address token here — a leaf's own positional
            # (a title, a target id) is handled generically in `_leaf_tokens_are_declared`
            # once the next iteration detects it has no `.commands` of its own.
            if hasattr(current, "commands") and _has_positional_argument(current) and i < n:
                i += 1  # the item number / sub-entity local id right after — skip unconditionally
                path.append("<n>")
            continue
        # Not a literal child of `current` — the one other addressing shape in this tree: an
        # unrecognized token routed through a hidden `_addr` subgroup (`role`/`operator`/
        # `skill`'s slug-or-id addressing, e.g. `sq role manager show`). `_addr`'s own required
        # argument is exactly the token we're consuming right here, so — unlike the branch
        # above — we deliberately do NOT re-run `_declares_own_address` after landing on it;
        # doing so would let a bogus verb right after the address (`sq role <n> update`, not a
        # real verb) be swallowed as a second "address" instead of failing to resolve.
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
            continue  # bare "sq" with nothing after it documents the tool name, not a command
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
    assert resolved  # non-empty: the extractor actually found and resolved something
    assert "role catalog" in resolved
    assert "feature <n> add-story" in resolved


def test_a_bogus_flag_on_a_resolved_leaf_command_fails_to_resolve() -> None:
    """Non-vacuity for the leaf-level check: a made-up flag on an otherwise-real verb path
    must not silently pass just because the verb itself resolves — the exact class of drift
    a verb-path-only walk would miss (a removed/renamed flag reappearing in a doc)."""
    assert _resolve(["role", "list", "--nonexistent-flag"]) is None
    assert _resolve(["create", "feature", "X", "--status", "Draft"]) is None  # no such flag


def test_an_unexpected_positional_on_a_flag_only_leaf_command_fails_to_resolve() -> None:
    """The other half of the same drift class: a bare positional where the leaf declares none
    at all (`dev add`'s technology is `--tech`, required — not a positional)."""
    assert _resolve(["dev", "add", "python"]) is None


def test_a_leaf_commands_real_flags_and_positionals_still_resolve() -> None:
    """The stricter leaf check must not false-positive on legitimate usage."""
    assert _resolve(["role", "list", "--json"]) == "role list"
    assert _resolve(["dev", "add", "--tech", "python"]) == "dev add"
    assert _resolve(["create", "feature", "Login", "--parent", "EPIC-1"]) == "create feature"


def test_no_documented_override_base_stamp_is_a_stale_version() -> None:
    """A concrete `override-base:<x.y.z>` literal in the docs must not be behind the installed
    version — the `<version>`/`<current-squads-version>` placeholder forms are exempt (they
    contain no digits, so the regex below never matches them)."""
    installed = tuple(int(part) for part in __version__.split(".")[:3])
    stale: list[str] = []
    for doc in sorted((_repo_root() / "docs").glob("*.md")):
        for m in _OVERRIDE_BASE_VERSION_RE.finditer(doc.read_text(encoding="utf-8")):
            cited = tuple(int(g) for g in m.groups())
            if cited < installed:
                stale.append(f"{doc.name}: {m.group(0)} behind installed {__version__}")
    assert not stale, "\n".join(stale)
