"""The parse guards behind the CLI-layer clean-failure behaviour: `_sections.split_frontmatter`
on intact-but-malformed YAML, and `_paths.load_config` on a malformed `.squads.toml`. The
CLI-layer tests pin what a user sees; these pin the primitives directly, including the
no-source-given degrade path and the "well-formed input is unaffected" guarantee.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._paths import load_config
from squads._sections import replace_frontmatter, split_frontmatter

_MERGE_CONFLICTED = """---
id: TASK-1
<<<<<<< HEAD
title: A
=======
title: B
>>>>>>> other
---
body
"""

_WELL_FORMED = """---
id: TASK-1
title: A
---
body
"""


def test_malformed_frontmatter_raises_squads_error_not_the_underlying_yaml_error():
    with pytest.raises(SquadsError):
        split_frontmatter(_MERGE_CONFLICTED)


def test_malformed_frontmatter_error_names_the_source_when_given():
    with pytest.raises(SquadsError, match=r"item\.md"):
        split_frontmatter(_MERGE_CONFLICTED, source="item.md")


def test_malformed_frontmatter_error_still_raises_with_no_source_given():
    """A caller with no path in scope gets a degraded message (no filename) -- not silence."""
    with pytest.raises(SquadsError):
        split_frontmatter(_MERGE_CONFLICTED)


def test_replace_frontmatter_propagates_the_same_guard():
    """The write-path mutation core inherits this for free through one guarded parse --
    a corrupt file refuses a rewrite instead of silently discarding it."""
    with pytest.raises(SquadsError):
        replace_frontmatter(_MERGE_CONFLICTED, {"id": "TASK-1"})


def test_read_frontmatter_names_the_path_it_was_given(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_text(_MERGE_CONFLICTED, encoding="utf-8")

    with pytest.raises(SquadsError, match=str(path)):
        read_frontmatter(path=path)


def test_a_well_formed_file_parses_exactly_as_before():
    data, body = split_frontmatter(_WELL_FORMED)
    assert data == {"id": "TASK-1", "title": "A"}
    assert body == "body\n"


def test_load_config_raises_squads_error_on_a_malformed_toml(tmp_path: Path):
    config_path = tmp_path / ".squads.toml"
    config_path.write_text("squad_dir = [unterminated\n", encoding="utf-8")

    with pytest.raises(SquadsError, match=str(config_path)):
        load_config(config_path)


def test_load_config_reads_a_well_formed_file_exactly_as_before(tmp_path: Path):
    config_path = tmp_path / ".squads.toml"
    config_path.write_text('squad_dir = "squads"\n', encoding="utf-8")

    config = load_config(config_path)
    assert config.squad_dir == "squads"
