"""Every check finding under ``src`` is built with a ``rule`` that is a validator-catalog name or a
registered binding rule, so a finding is always matchable by its rule rather than by its message
text."""

import ast
from dataclasses import dataclass, field
from pathlib import Path

from squads._services._check_rules import BINDING_RULES, is_registered
from squads._workflow._validator_names import SQUAD_GLOBAL_VALIDATOR_NAMES, VALIDATOR_NAMES

_SRC = Path(__file__).resolve().parents[2] / "src"
_CATALOG_NAMES = VALIDATOR_NAMES | SQUAD_GLOBAL_VALIDATOR_NAMES
_RULE_INDEX = 3  # level, item, message, rule
_RULE_CHECK_RULES_MODULE = "squads/_services/_check_rules.py"

#: Helpers outside the catalog members that build a member's findings, and the member's name.
_HELPERS = {
    "on_disk_not_indexed": "index_reconciled",
    "not_on_disk": "index_reconciled",
    "backend_entry_missing": "backend_reconciled",
    "backend_entry_drift": "backend_reconciled",
}

#: The one construction that forwards a rule read from the override service's findings: a
#: comprehension over ``check_override_issues(...)`` in this function.
_FORWARDING_SITE = ("squads/_services/_check.py", "check")
_FORWARDING_SOURCE = "check_override_issues"

#: Every construction outside the catalog members: (module, function) -> the rules it files
#: under, in source order. A new site, or a site moved to another rule, fails here until the
#: row says so; the per-source ``--json`` table then needs a row that drives it.
_SITES: dict[tuple[str, str], tuple[str, ...]] = {
    ("squads/_overrides/_service.py", "_roles_catalog_invalid_issue"): ("override_loads",),
    ("squads/_overrides/_service.py", "_stamp_issue"): ("override_stamped", "override_current"),
    ("squads/_overrides/_service.py", "_check_template_override_issues"): (
        "override_loads",
        "view_tag_in_region",
        "override_loads",
        "override_loads",
        "override_stamped",
        "override_current",
    ),
    ("squads/_overrides/_service.py", "_check_role_toml_override_issues"): (
        "override_loads",
        "override_stamped",
        "override_current",
    ),
    ("squads/_overrides/_service.py", "_check_role_override_resolves"): (
        "override_loads",
        "override_loads",
    ),
    ("squads/_services/_check.py", "_missing_timestamp_issues"): ("timestamps_present",),
    ("squads/_services/_check.py", "_value_skew_issue"): ("frontmatter_matches_index",),
    ("squads/_services/_check.py", "check"): ("ids_unique", "numbers_unique"),
    ("squads/_services/_check.py", "_orphaned_skill_issues"): ("skill_type_declared",),
    ("squads/_services/_check.py", "_scan_for_check"): (
        "file_readable",
        "markers_balanced",
        "view_target_resolves",
        "view_tag_in_region",
        "seeded_view_resolves",
        "body_regions_present",
        "block_in_container",
        "frontmatter_parses",
        "id_present",
        "id_well_formed",
        "fields_valid",
    ),
    ("squads/_services/_squad_ops.py", "_check_refusal"): ("playbook_loads", "workflow_loads"),
    ("squads/_services/_squad_ops.py", "check_squad"): ("corpus_scans",),
    ("squads/_services/_validators.py", "on_disk_not_indexed"): ("index_reconciled",),
    ("squads/_services/_validators.py", "not_on_disk"): ("index_reconciled",),
    ("squads/_services/_validators.py", "backend_entry_missing"): ("backend_reconciled",),
    ("squads/_services/_validators.py", "backend_entry_drift"): ("backend_reconciled",),
}


@dataclass
class _Scan:
    problems: list[str] = field(default_factory=list)
    rules: set[str] = field(default_factory=set)
    sites: list[tuple[str, str, str]] = field(default_factory=list)


def _literals(node: ast.expr | None) -> list[str] | None:
    """The string literal(s) *node* can evaluate to, or ``None`` when it is anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        body, orelse = _literals(node.body), _literals(node.orelse)
        return body + orelse if body is not None and orelse is not None else None
    return None


def _rule_node(call: ast.Call) -> ast.expr | None:
    if len(call.args) > _RULE_INDEX:
        return call.args[_RULE_INDEX]
    return next((kw.value for kw in call.keywords if kw.arg == "rule"), None)


def _called_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


class _Visitor(ast.NodeVisitor):
    def __init__(self, where: str, aliases: set[str], scan: _Scan) -> None:
        self.where = where
        self.aliases = aliases
        self.scan = scan
        self.functions: list[str] = []
        self.forwarding = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # pyright: ignore[reportAssignmentType]

    def _member(self) -> str:
        return self.functions[0].removeprefix("_") if self.functions else ""

    def _rule_problem(self, rule: str) -> str | None:
        member = self._member()
        outer = self.functions[0] if self.functions else ""
        if not is_registered(rule):
            return f"{rule!r} is not registered"
        if member in _CATALOG_NAMES and rule != member:
            return f"{rule!r} inside catalog member {member!r}"
        if member not in _CATALOG_NAMES and rule in _CATALOG_NAMES and _HELPERS.get(outer) != rule:
            return f"{rule!r} filed by unlisted helper {outer!r}"
        return None

    def _construction(self, node: ast.Call, name: str) -> None:
        site = f"{self.where}:{node.lineno}"
        rule_node = _rule_node(node)
        if rule_node is None and name == "replace":
            return  # a replace that leaves the rule alone restamps nothing
        literals = _literals(rule_node)
        outer = self.functions[0] if self.functions else ""
        forwarded = (
            isinstance(rule_node, ast.Name)
            and self.forwarding
            and (self.where, outer) == _FORWARDING_SITE
        )
        if literals is None and forwarded:
            return
        if literals is None:
            self.scan.problems.append(f"{site}: rule is missing or not a string literal")
            return
        for rule in literals:
            self.scan.rules.add(rule)
            if self._member() not in _CATALOG_NAMES:
                self.scan.sites.append((self.where, outer, rule))
            problem = self._rule_problem(rule)
            if problem:
                self.scan.problems.append(f"{site}: {problem}")

    def _helper_call_problem(self, node: ast.Call, name: str) -> None:
        if self._member() in _CATALOG_NAMES and _HELPERS[name] != self._member():
            self.scan.problems.append(
                f"{self.where}:{node.lineno}: {name!r} files under {_HELPERS[name]!r}, "
                f"called from member {self._member()!r}"
            )

    def visit_ListComp(self, node: ast.ListComp) -> None:
        source = node.generators[0].iter if node.generators else None
        self.forwarding = isinstance(source, ast.Call) and _called_name(source.func) == (
            _FORWARDING_SOURCE
        )
        self.generic_visit(node)
        self.forwarding = False

    def visit_Assign(self, node: ast.Assign) -> None:
        if _called_name(node.value) in self.aliases:  # pyright: ignore[reportArgumentType]
            self.scan.problems.append(f"{self.where}:{node.lineno}: CheckIssue is rebound")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _called_name(node.func) or ""
        if name == "__class__" or (
            isinstance(node.func, ast.Call) and _called_name(node.func.func) == "type"
        ):
            self.scan.problems.append(
                f"{self.where}:{node.lineno}: a finding is built from another's class"
            )
        restamps = name == "replace" and any(kw.arg == "rule" for kw in node.keywords)
        if name in self.aliases or name == "_issue" or restamps:
            self._construction(node, name)
        elif name == "partial" and any(_called_name(a) in self.aliases for a in node.args):
            self.scan.problems.append(f"{self.where}:{node.lineno}: partial(CheckIssue) hides it")
        elif name in _HELPERS:
            self._helper_call_problem(node, name)
        self.generic_visit(node)


def _scan(source: str, where: str) -> _Scan:
    tree = ast.parse(source)
    aliases = {"CheckIssue"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            aliases |= {a.asname for a in node.names if a.name == "CheckIssue" and a.asname}
    scan = _Scan()
    _Visitor(where, aliases, scan).visit(tree)
    return scan


def _scan_src() -> _Scan:
    total = _Scan()
    for path in sorted((_SRC / "squads").rglob("*.py")):
        rel = path.relative_to(_SRC).as_posix()
        if rel == _RULE_CHECK_RULES_MODULE:
            continue
        found = _scan(path.read_text(encoding="utf-8"), rel)
        total.problems += found.problems
        total.rules |= found.rules
        total.sites += found.sites
    return total


def test_every_construction_site_files_under_its_pinned_rule() -> None:
    found: dict[tuple[str, str], list[str]] = {}
    for where, function, rule in _scan_src().sites:
        found.setdefault((where, function), []).append(rule)
    assert {k: tuple(v) for k, v in found.items()} == _SITES


def test_every_check_finding_names_a_registered_rule() -> None:
    assert not _scan_src().problems, "\n".join(_scan_src().problems)


_BAD = {
    "unregistered": 'CheckIssue("error", "x", "m", "no_such_rule")',
    "missing": 'CheckIssue("error", "x", "m")',
    "variable": 'CheckIssue("error", "x", "m", rule=name)',
    "starred": "CheckIssue(*parts)",
    "attribute": '_results.CheckIssue("error", "x", "m", "no_such_rule")',
    "aliased": (
        "from squads._services._results import CheckIssue as CI\n"
        'CI("error", "x", "m", "no_such_rule")'
    ),
    "replace": 'dataclasses.replace(issue, rule="no_such_rule")',
    "replace_variable": "replace(issue, rule=other)",
    "partial": 'functools.partial(CheckIssue, rule="markers_balanced")',
    "member_mismatch": (
        'def _parent_in(ctx):\n    return CheckIssue("warn", "x", "m", "dangling_ref")'
    ),
    "unlisted_helper": 'def helper():\n    return CheckIssue("warn", "x", "m", "parent_in")',
    "helper_wrong_rule": (
        'def not_on_disk():\n    return CheckIssue("warn", "x", "m", "backend_reconciled")'
    ),
    "helper_from_sibling": ('def _dangling_ref(ctx):\n    return not_on_disk(1, level="warn")'),
    "rebound": "CI = CheckIssue",
    "rebound_attribute": "CI = results.CheckIssue",
    "type_of_instance": 'type(issue)("error", "x", "m", "markers_balanced")',
    "dunder_class": 'issue.__class__("error", "x", "m", "markers_balanced")',
    "forwarded_elsewhere": (
        "def check(self):\n    return [CheckIssue(a, b, c, rule) for a, b, c, rule in other()]"
    ),
    "issue_helper": '_issue("error", "d", "m", "no_such_rule")',
}

_GOOD = {
    "literal": 'CheckIssue("error", "x", "m", "markers_balanced")',
    "keyword": 'CheckIssue("error", "x", "m", rule="markers_balanced")',
    "member": 'def _parent_in(ctx):\n    return CheckIssue("warn", "x", "m", "parent_in")',
    "listed_helper": (
        'def not_on_disk():\n    return CheckIssue("warn", "x", "m", "index_reconciled")'
    ),
    "helper_from_own_member": "def _index_reconciled(ctx):\n    return not_on_disk(1)",
    "conditional": '_issue("e", "d", "m", "override_stamped" if x else "override_current")',
    "override_forwarding": (
        "def check(self):\n"
        "    return [CheckIssue(a, b, c, rule) for a, b, c, rule in check_override_issues()]"
    ),
    "replace_without_rule": "replace(issue, level='warn')",
}


def _where(case: str) -> str:
    """The module path a probe pretends to live in: the forwarding cases need the real one."""
    return _FORWARDING_SITE[0] if "forward" in case else "probe"


def test_the_guard_fails_on_every_shape_it_exists_to_catch() -> None:
    missed = [name for name, src in _BAD.items() if not _scan(src, _where(name)).problems]
    assert not missed, f"the guard let these shapes through: {missed}"


def test_the_guard_accepts_the_legitimate_shapes() -> None:
    refused = {name: _scan(src, _where(name)).problems for name, src in _GOOD.items()}
    assert not any(refused.values()), refused


def test_every_binding_rule_is_filed_by_some_construction() -> None:
    """Counts only the rule argument of real construction sites, not the registry's own keys."""
    assert set(BINDING_RULES) <= _scan_src().rules, set(BINDING_RULES) - _scan_src().rules
