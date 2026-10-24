"""Loading, binding, calling and validating a view transform, driven through ``TransformLoader``."""

import re
import sys
from pathlib import Path

import pytest

from squads import _clock as clock
from squads._models._item import Item
from squads._transform import TransformLoader, ViewTransformError, check_view_transforms
from squads._workflow import bundled_spec
from squads._workflow._models import ViewTransform, view_transform_problems


def _item() -> Item:
    now = clock.now()
    return Item(
        sequence_id=7,
        type="task",
        title="Host",
        slug="host",
        status="Draft",
        path="tasks/x.md",
        created_at=now,
        updated_at=now,
        prefix="TASK",
    )


def _squad(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        target = tmp_path / ".overrides" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


def _run(squad: Path, function: str, source: object = None, path: str = "t.py") -> object:
    loader = TransformLoader(squad)
    transform = ViewTransform(path=path, function=function)
    return loader.run("v", transform, source or [], item=_item(), spec=bundled_spec())


def _symlinks_work(tmp_path: Path) -> None:
    try:
        (tmp_path / "probe").symlink_to(tmp_path)
    except OSError as exc:
        pytest.skip(f"cannot create symlinks here: {exc}")


@pytest.mark.parametrize(
    ("layout", "error"),
    [
        ("outward_symlink", "outside .overrides/"),
        ("missing", "is not a file"),
        ("directory", "is not a file"),
        ("inward_symlink", None),
        ("symlinked_overrides_dir", None),
    ],
)
def test_a_transform_path_must_resolve_to_a_file_inside_the_overrides_folder(
    tmp_path: Path, layout: str, error: str | None
) -> None:
    body = "def f(source):\n    return {'ok': True}\n"
    sentinel = tmp_path / "sentinel"
    squad = tmp_path / "squad"
    squad.mkdir()
    if layout == "outward_symlink":
        _symlinks_work(tmp_path)
        (tmp_path / "outside.py").write_text(f"open({str(sentinel)!r}, 'w')\n" + body)
        (squad / ".overrides").mkdir()
        (squad / ".overrides" / "t.py").symlink_to(tmp_path / "outside.py")
    elif layout == "directory":
        (squad / ".overrides" / "t.py").mkdir(parents=True)
    elif layout == "inward_symlink":
        _symlinks_work(tmp_path)
        _squad(squad, {"real.py": body})
        (squad / ".overrides" / "t.py").symlink_to(squad / ".overrides" / "real.py")
    elif layout == "symlinked_overrides_dir":
        _symlinks_work(tmp_path)
        _squad(tmp_path / "elsewhere", {"t.py": body})
        (squad / ".overrides").symlink_to(tmp_path / "elsewhere" / ".overrides")

    message = TransformLoader(squad).check("v", ViewTransform(path="t.py", function="f"))

    if error is None:
        assert message is None
    else:
        assert message is not None and error in message
    assert not sentinel.exists()


_BIND_FILE = """
def only_source(source): return {"item": False, "spec": False}
def with_item(source, *, item): return {"item": item.id}
def with_spec(source, *, spec): return {"spec": spec is not None}
def with_both(source, *, item, spec): return {"item": item.id, "spec": spec is not None}
def with_kwargs(source, **kwargs): return {"keys": sorted(kwargs)}
def with_default(source, extra=1): return {"extra": extra}
class Instance:
    def __call__(self, source): return {"called": True}
instance = Instance()
def no_params(): return {}
def keyword_only_first(*, source): return {}
def extra_required(source, extra): return {}
def unknown_keyword(source, *, other): return {}
async def coroutine(source): return {}
not_callable = 3
"""


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        ("only_source", {"item": False, "spec": False}),
        ("with_item", {"item": "TASK-7"}),
        ("with_spec", {"spec": True}),
        ("with_both", {"item": "TASK-7", "spec": True}),
        ("with_kwargs", {"keys": ["item", "spec"]}),
        ("with_default", {"extra": 1}),
        ("instance", {"called": True}),
    ],
)
def test_a_transform_receives_only_the_keywords_it_declares(
    tmp_path: Path, function: str, expected: object
) -> None:
    assert _run(_squad(tmp_path, {"t.py": _BIND_FILE}), function) == expected


@pytest.mark.parametrize(
    ("function", "reason"),
    [
        ("no_params", "first parameter"),
        ("keyword_only_first", "first parameter"),
        ("extra_required", "'extra'"),
        ("unknown_keyword", "'other'"),
        ("coroutine", "async"),
        ("not_callable", "not callable"),
        ("absent", "no attribute"),
    ],
)
def test_a_function_sq_cannot_call_is_refused_by_name(
    tmp_path: Path, function: str, reason: str
) -> None:
    with pytest.raises(ViewTransformError, match=reason):
        _run(_squad(tmp_path, {"t.py": _BIND_FILE}), function)


@pytest.mark.parametrize(
    ("expression", "json_path"),
    [
        ("'text'", "$"),
        ("None", "$"),
        ("(1, 2)", "$"),
        ("{1: 'x'}", "$"),
        ("{'a': float('nan')}", "$.a"),
        ("{'a': {1, 2}}", "$.a"),
        ("{'a': object()}", "$.a"),
        ("{'big': 10**5000}", "$.big"),
        ("{'rows': [1, 2, (3,)]}", "$.rows[2]"),
        (
            "{'delivered': [{}, {}, {}, {'when': __import__('datetime').date.today()}]}",
            "$.delivered[3].when",
        ),
    ],
)
def test_output_that_is_not_json_data_is_refused_with_the_path_of_the_first_offender(
    tmp_path: Path, expression: str, json_path: str
) -> None:
    squad = _squad(tmp_path, {"t.py": f"def f(source):\n    return {expression}\n"})
    with pytest.raises(ViewTransformError, match=re.escape(json_path)):
        _run(squad, "f")


def test_json_data_of_every_allowed_kind_is_returned_unchanged(tmp_path: Path) -> None:
    value = {"a": [1, 2.5, True, None, "s", {"b": []}], "c": {}}
    squad = _squad(tmp_path, {"t.py": f"def f(source):\n    return {value!r}\n"})
    assert _run(squad, "f") == value


def test_an_exception_in_a_transform_names_the_view_host_declaration_and_line(
    tmp_path: Path,
) -> None:
    squad = _squad(tmp_path, {"t.py": "def f(source):\n    raise KeyError('boom')\n"})
    with pytest.raises(ViewTransformError) as caught:
        _run(squad, "f")
    message = str(caught.value)
    assert "'v'" in message and "TASK-7" in message and "t.py:f" in message
    assert "KeyError" in message and "boom" in message
    assert f"{squad.resolve() / '.overrides' / 't.py'}:2" in message


@pytest.mark.parametrize(
    "source",
    ["def f(source):\n    raise SystemExit(0)\n", "import sys\nsys.exit(0)\ndef f(source): ...\n"],
)
def test_an_exit_in_a_transform_is_a_view_error_not_a_process_exit(
    tmp_path: Path, source: str
) -> None:
    with pytest.raises(ViewTransformError, match="SystemExit"):
        _run(_squad(tmp_path, {"t.py": source}), "f")


def test_an_interrupt_inside_a_transform_is_not_converted(tmp_path: Path) -> None:
    squad = _squad(tmp_path, {"t.py": "def f(source):\n    raise KeyboardInterrupt\n"})
    with pytest.raises(KeyboardInterrupt):
        _run(squad, "f")


def test_a_transform_gets_copies_loads_once_per_loader_and_leaves_no_module_behind(
    tmp_path: Path,
) -> None:
    counter = tmp_path / "counter"
    squad = _squad(
        tmp_path,
        {
            "t.py": f"open({str(counter)!r}, 'a').write('x')\n"
            "def f(source, *, item, spec):\n"
            "    source.append('mutated')\n"
            "    item.title = 'mutated'\n"
            "    spec.items.pop('bug')\n"
            "    return {}\n"
        },
    )
    original, host = ["a"], _item()
    loader = TransformLoader(squad)
    transform = ViewTransform(path="t.py", function="f")
    loader.run("v", transform, original, item=host, spec=bundled_spec())
    loader.run("v", transform, original, item=host, spec=bundled_spec())

    assert original == ["a"] and host.title == "Host" and "bug" in bundled_spec().items
    assert counter.read_text() == "x"
    assert not [name for name in sys.modules if name.startswith("_squads_view_transform_")]

    _run(squad, "f")
    assert counter.read_text() == "xx"


def test_an_edited_file_is_read_again_by_the_next_loader(tmp_path: Path) -> None:
    squad = _squad(tmp_path, {"t.py": "def f(source): return {'v': 1}\n"})
    assert _run(squad, "f") == {"v": 1}
    (squad / ".overrides" / "t.py").write_text("def f(source): return {'v': 2}\n")
    assert _run(squad, "f") == {"v": 2}


def test_checking_imports_the_file_but_never_calls_the_function(tmp_path: Path) -> None:
    called = tmp_path / "called"
    squad = _squad(
        tmp_path,
        {"t.py": f"def f(source):\n    open({str(called)!r}, 'w')\n    return {{}}\n"},
    )
    spec = bundled_spec().model_copy(
        update={
            "views": {
                "v": bundled_spec()
                .views["milestone_rollup"]
                .model_copy(update={"transform": ViewTransform(path="t.py", function="f")}),
                "w": bundled_spec()
                .views["milestone_rollup"]
                .model_copy(update={"transform": ViewTransform(path="t.py", function="missing")}),
            }
        }
    )
    found = check_view_transforms(spec, squad)
    assert [name for name, _ in found] == ["w"]
    assert not called.exists()


@pytest.mark.parametrize(
    ("transform", "problem"),
    [
        (ViewTransform(module="squads.x", path="t.py", function="f"), "exactly one"),
        (ViewTransform(function="f"), "exactly one"),
        (ViewTransform(module="os", function="f"), "under `squads.`"),
        (ViewTransform(path="t.py", function="class"), "not an identifier"),
        (ViewTransform(path="t.py", function="1x"), "not an identifier"),
        (ViewTransform(path="../t.py", function="f"), "`..`"),
        (ViewTransform(path="/abs/t.py", function="f"), "relative POSIX"),
        (ViewTransform(path="a\\t.py", function="f"), "relative POSIX"),
        (ViewTransform(path="t.txt", function="f"), "end in `.py`"),
        (ViewTransform(path="t\x00x.py", function="f"), "control characters"),
        (ViewTransform(path="t\x7fx.py", function="f"), "control characters"),
        (ViewTransform(path="a/t.py", function="f"), None),
        (ViewTransform(module="squads._view_transforms", function="f"), None),
    ],
)
def test_a_transform_declaration_is_checked_for_shape_alone(
    transform: ViewTransform, problem: str | None
) -> None:
    found = view_transform_problems(transform)
    if problem is None:
        assert found == []
    else:
        assert any(problem in p for p in found)
