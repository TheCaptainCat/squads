"""`sq ref add/rm` and `sq refs` — the cross-linking graph."""

import json

import typer
from rich.table import Table

from squads.cli import app
from squads.cli.common import console, get_service, handle_errors

ref_app = typer.Typer(no_args_is_help=True, help="Manage forward reference edges.")


@ref_app.command("add")
@handle_errors
def ref_add(
    from_id: str = typer.Argument(...),
    to_id: str = typer.Argument(...),
    kind: str = typer.Option("related", "--kind", help="related | blocks | implements"),
):
    """Add a forward reference FROM_ID → TO_ID."""
    get_service().add_ref(from_id, to_id, kind=kind)
    console.print(f"{from_id} → {to_id} ([dim]{kind}[/dim])")


@ref_app.command("rm")
@handle_errors
def ref_rm(from_id: str = typer.Argument(...), to_id: str = typer.Argument(...)):
    """Remove a forward reference FROM_ID → TO_ID."""
    get_service().rm_ref(from_id, to_id)
    console.print(f"removed {from_id} → {to_id}")


@app.command()
@handle_errors
def refs(
    item_id: str = typer.Argument(...),
    out: bool = typer.Option(False, "--out", help="Forward refs (default)."),
    incoming: bool = typer.Option(False, "--in", help="Backrefs (computed)."),
    all_: bool = typer.Option(False, "--all", help="Both directions."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Show an item's references (forward edges stored; backrefs computed by inversion)."""
    svc = get_service()
    show_out = out or all_ or not (incoming or all_)
    show_in = incoming or all_
    data: dict[str, list[dict[str, str]]] = {}
    if show_out:
        data["out"] = [{"id": i, "kind": k} for i, k in svc.refs_out(item_id)]
    if show_in:
        data["in"] = [{"id": i, "kind": k} for i, k in svc.refs_in(item_id)]
    if json_out:
        console.print_json(json.dumps(data))
        return
    for direction, label in (("out", "→ refs"), ("in", "← backrefs")):
        if direction not in data:
            continue
        if not data[direction]:
            console.print(f"[dim]{label}: none[/dim]")
            continue
        table = Table(title=label, box=None, pad_edge=False, title_justify="left")
        table.add_column("ID")
        table.add_column("Kind")
        for row in data[direction]:
            table.add_row(row["id"], row["kind"])
        console.print(table)
