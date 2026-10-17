"""A squad written before the host key existed drifts on every system skill pointer, with the
exit code unchanged; one ``sq sync`` rewrites them and ``sq check`` is clean after it."""

import pytest

from _invocable_squad import build_squad, drifted

pytestmark = pytest.mark.anyio

LINE = "user-invocable: false\n"


async def test_check_warns_on_each_system_pointer_until_sync_then_is_clean(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    clean_exit = (await invoke(["check"])).exit_code
    pointers = sorted((paths.root / ".claude" / "skills").glob("*/SKILL.md"))
    system = [p for p in pointers if LINE in p.read_text(encoding="utf-8")]
    authored = {"onboarding", "sq-onboarding"}
    assert {p.parent.name for p in system}.isdisjoint(authored)
    assert len(system) > len(authored)
    for pointer in system:  # the squad as an earlier release wrote it
        pointer.write_text(pointer.read_text(encoding="utf-8").replace(LINE, ""), encoding="utf-8")

    assert await drifted(invoke) == [f".claude/skills/{p.parent.name}/SKILL.md" for p in system]
    assert (await invoke(["check"])).exit_code == clean_exit

    assert (await invoke(["sync"])).exit_code == 0

    assert await drifted(invoke) == []
    assert (await invoke(["check"])).exit_code == clean_exit
    assert all(LINE in p.read_text(encoding="utf-8") for p in system)
