"""The corpus-wide and squad-creation DTOs: what a repair, renumber, migration, repad, bulk
rename, import, init and adopt did, each as one report.

``unreadable`` holds one sentence per file a rebuild could not read, as the command prints it
after ``error:``; ``notice`` is the announcement that a rebuild rewrote item content, ``None``
when it rewrote nothing."""

from squads._api._dto._base import DTO


class RepairRequest(DTO):
    """Rebuild the index from the item files; *renumber* first gives a shared number a new one."""

    renumber: bool = False


class RepairReport(DTO):
    """The rebuilt index's size and counter, the indexed items whose file is gone, the files it
    could not read, the renumbering it did, and whether refs are left to check by hand."""

    indexed: int
    counter: int
    notice: str | None
    missing: list[str]
    unreadable: list[str]
    renumbered: list[str]
    references_left: bool


class RenumberRequest(DTO):
    """Move every item numbered *from_seq* or above past *onto*, or up by *by*."""

    from_seq: int
    onto: int | None = None
    by: int | None = None


class Renumbered(DTO):
    """One moved item: its id before and after."""

    old: str
    new: str


class RenumberReport(DTO):
    """The items moved, in the order of their new id, the counter, and the caution a move by an
    offset carries."""

    moved: list[Renumbered]
    counter: int
    warning: str | None
    notice: str | None


class MigrateRequest(DTO):
    """Run the migrations this squad is behind on."""


class Reconciled(DTO):
    """What the index rebuild before the first migration changed: the ids it indexed and the ones
    it dropped because no file backs them."""

    indexed: list[str]
    missing: list[str]


class AppliedMigration(DTO):
    """One migration run: its release and schema step, its summary, how many items it changed,
    its report lines, the items it skipped and whether it leaves manual steps."""

    version: str
    from_schema: str
    to_schema: str
    summary: str
    changed: int
    reports: list[str]
    skipped: list[str]
    manual: bool


class MigrationReport(DTO):
    """The migrations run, oldest first, and the schema the squad is now at. ``manual_span`` is
    the ``sq migrate chlog`` range holding their manual steps, ``None`` when none has any."""

    schema_version: str
    applied: list[AppliedMigration]
    reconciled: Reconciled | None
    config_dropped: list[str]
    notice: str | None
    unreadable: list[str]
    manual_span: str | None


class RepadRequest(DTO):
    """Widen the zero padding of item numbers to *width* digits."""

    width: int


class RepadReport(DTO):
    """The padding before and after, and how many files were renamed."""

    previous: int
    width: int
    renamed: int


class RenameTypeRequest(DTO):
    """Move every item of *old_type* to *new_type*."""

    old_type: str
    new_type: str


class RenameStatusRequest(DTO):
    """Relabel *old_status* as *new_status* on every item of *type*."""

    type: str
    old_status: str
    new_status: str


class RenamedId(DTO):
    """One item a type rename moved: its id before and after."""

    old: str
    new: str


class RenameTypeReport(DTO):
    """The two types, how many items moved and each one's ids."""

    old_type: str
    new_type: str
    renamed: int
    ids: list[RenamedId]


class RenameStatusReport(DTO):
    """The type, the two statuses and how many items were relabelled."""

    type: str
    old_status: str
    new_status: str
    renamed: int


class ImportRequest(DTO):
    """Apply the JSONL *text*; *dry_run* checks it and writes nothing, *default_as* attributes an
    event with no actor of its own."""

    text: str
    dry_run: bool = False
    default_as: str | None = None


class ImportIssueRow(DTO):
    """A pre-pass problem: the line it is on and what is wrong."""

    line: int
    message: str


class ImportFindingRow(DTO):
    """A finding on an item the applied import touched: its level, the item, the message and the
    rule."""

    level: str
    item: str
    message: str
    rule: str


class ImportReport(DTO):
    """The plan of a refused or dry run, or the outcome of an applied one. ``issues`` holds the
    pre-pass problems of a refused run, or every finding on an item an applied run touched;
    ``ok`` is false when the pre-pass refused or a finding is an error, which exits 3."""

    op_counts: dict[str, int]
    handle_to_id: dict[str, str]
    handle_to_sub: dict[str, list[str]]
    issues: list[ImportIssueRow | ImportFindingRow]
    ok: bool
    applied: bool
    dry_run: bool
    created_ids: list[str]
    warnings: list[str]


class InitRequest(DTO):
    """Create a squad in the request's directory: its folder, the agent backends to write files
    for, the roles to activate and the names to give them. *force* overwrites an existing
    configuration; *seed_skills* stamps the bundled skill files as items."""

    squad_dir: str
    backends: list[str]
    roles: str
    no_claude: bool
    force: bool
    names: dict[str, str]
    seed_skills: bool


class InitReport(DTO):
    """The squad created: its folder, its index, the roles activated, the agent backends, and the
    notices about files the scaffolding left alone."""

    squad: str
    index: str
    roles: list[str]
    backends: list[str]
    warnings: list[str]


class AdoptRequest(DTO):
    """Bring the squad folder in the request's directory under squads; *squad_dir* applies when
    no configuration names one. *renumber* gives files that share a number new ones first."""

    squad_dir: str
    backends: list[str]
    roles: str
    no_claude: bool
    renumber: bool


class AdoptReport(DTO):
    """The squad adopted: its folder, how many items it held, the roles newly activated, the
    rebuild's content notice and unreadable files, and the scaffolding notices."""

    squad: str
    imported: int
    roles: list[str]
    notice: str | None
    unreadable: list[str]
    warnings: list[str]
