"""cli-anything-handwrite — agent-usable CLI for the HandWrite Plain Text generator.

Click-based, stateful, with both one-shot subcommands and an interactive REPL
(default when no subcommand given). Every command supports ``--json`` for
machine consumption. Rendering is delegated to the REAL Node pipeline — never
reimplemented.
"""
from __future__ import annotations

import json as _json
import os
import shlex
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from cli_anything.handwrite import __version__
from cli_anything.handwrite.core import model as model_mod
from cli_anything.handwrite.core import params as params_mod
from cli_anything.handwrite.core import project as project_mod
from cli_anything.handwrite.core import render as render_mod
from cli_anything.handwrite.core.session import Session, SESSION_SUFFIX
from cli_anything.handwrite.utils import handwrite_backend
from cli_anything.handwrite.utils.repl_skin import ReplSkin

# ── module-level session + mode flags ──────────────────────────────────
_session: Optional[Session] = None
_repl_mode: bool = False


def get_session() -> Session:
    global _session
    if _session is None:
        _session = Session()
    return _session


def _skin() -> ReplSkin:
    # Construction walks the filesystem for the skill path; cache one instance.
    return _cached_skin(__version__)


@lru_cache(maxsize=1)
def _cached_skin(version: str) -> ReplSkin:
    return ReplSkin("handwrite", version=version)


def _emit(ctx: click.Context, record: Dict[str, Any]) -> None:
    """Emit a result record as JSON or nothing (human output handled by caller)."""
    if ctx.obj.get("json"):
        click.echo(_json.dumps(record, ensure_ascii=False))


def _err(ctx: click.Context, message: str, code: int = 1) -> None:
    if ctx.obj.get("json"):
        click.echo(_json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        _skin().error(message)
    ctx.exit(code)


def _ok(ctx: click.Context, record: Dict[str, Any]) -> None:
    if ctx.obj.get("json"):
        click.echo(_json.dumps({"ok": True, **record}, ensure_ascii=False))


# ── root group ─────────────────────────────────────────────────────────
@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output all results as JSON.")
@click.option("--project", "project_path", type=str, default=None,
              help="Load a .toml project file (GUI-native format) into the session.")
@click.option("--session", "session_path", type=str, default=None,
              help="Load a .hwsess.json session file.")
@click.option("--dry-run", "dry_run", is_flag=True, default=False,
              help="Run command without auto-saving changes to disk.")
@click.option("--output-dir", "output_dir", type=str, default=None,
              help="Default output directory for rendered PNGs.")
@click.option("--seed", "seed", type=int, default=None, help="Default RNG seed for renders.")
@click.version_option(__version__, prog_name="cli-anything-handwrite")
@click.pass_context
def cli(ctx: click.Context, use_json: bool, project_path: Optional[str],
        session_path: Optional[str], dry_run: bool, output_dir: Optional[str],
        seed: Optional[int]) -> None:
    """Agent-usable CLI for the HandWrite Plain Text generator.

    Renders plain text as handwritten PNGs using the REAL Node render pipeline.
    With no subcommand, enters the interactive REPL.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = use_json
    ctx.obj["dry_run"] = dry_run

    sess = get_session()
    if session_path:
        try:
            global _session
            _session = Session.load_session(session_path)
            sess = _session
        except Exception as e:
            _err(ctx, f"failed to load session {session_path}: {e}")
    if project_path:
        try:
            m = project_mod.open_project(project_path)
            sess.set_model(m, project_path=project_path)
        except Exception as e:
            _err(ctx, f"failed to open project {project_path}: {e}")
    if output_dir:
        sess.output_dir = output_dir
    if seed is not None:
        sess.seed = seed

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.result_callback()
def _auto_save(result, use_json, project_path, session_path, dry_run, output_dir, seed, **kwargs):
    """Auto-save after one-shot mutations (skipped in REPL / with --dry-run)."""
    if _repl_mode or dry_run:
        return
    sess = get_session()
    if not sess._modified:
        return
    try:
        if sess.project_path:
            project_mod.save_project(sess.model, sess.project_path)
        if sess.session_path:
            sess.save_session()
    except Exception as e:
        click.echo(f"Warning: auto-save failed: {e}", err=True)


# ── project ────────────────────────────────────────────────────────────
@cli.group()
def project() -> None:
    """Project (DocumentModel) lifecycle: new / open / save / info."""


@project.command("new")
@click.option("--font", "font_path", type=str, default=None, help="TTF font path.")
@click.option("--text", "text", type=str, default="", help="Initial text.")
@click.option("-o", "--out", "out", type=str, default=None, help="Save as .toml project file.")
@click.pass_context
def project_new(ctx, font_path, text, out):
    """Create a fresh handwritten-text project."""
    sess = get_session()
    fp = font_path or ""
    m = project_mod.new_project(fp, text=text)
    sess.set_model(m, project_path=out)
    if out:
        project_mod.save_project(m, out)
        sess._modified = False
    rec = project_mod.project_info(m, out)
    _ok(ctx, {"project": rec})
    if not ctx.obj.get("json"):
        _skin().success(f"New project created ({len(text)} chars)" + (f" -> {out}" if out else ""))


@project.command("open")
@click.argument("toml_path", type=str)
@click.pass_context
def project_open(ctx, toml_path):
    """Open a .toml project file (GUI-native)."""
    sess = get_session()
    try:
        m = project_mod.open_project(toml_path)
    except Exception as e:
        _err(ctx, str(e))
        return
    sess.set_model(m, project_path=toml_path)
    rec = project_mod.project_info(m, toml_path)
    _ok(ctx, {"project": rec})
    if not ctx.obj.get("json"):
        _skin().success(f"Opened {toml_path}")


@project.command("save")
@click.argument("toml_path", type=str, required=False)
@click.pass_context
def project_save(ctx, toml_path):
    """Save the project as a GUI-native .toml file (via the real persistence layer)."""
    sess = get_session()
    target = toml_path or sess.project_path
    if not target:
        _err(ctx, "no project path; pass a TOML path or open a project first")
        return
    try:
        path = project_mod.save_project(sess.model, target)
    except Exception as e:
        _err(ctx, str(e))
        return
    sess.project_path = path
    sess._modified = False
    _ok(ctx, {"path": path})
    if not ctx.obj.get("json"):
        _skin().success(f"Saved -> {path}")


@project.command("info")
@click.pass_context
def project_info(ctx):
    """Show project summary."""
    sess = get_session()
    if not sess.has_project():
        _err(ctx, "no project open")
        return
    rec = project_mod.project_info(sess.model, sess.project_path)
    _ok(ctx, {"project": rec})
    if not ctx.obj.get("json"):
        s = _skin()
        s.status_block({
            "text length": str(rec["text_length"]),
            "lines": str(rec["text_lines"]),
            "overrides": str(rec["overrides"]),
            "font": Path(rec["font_path"]).name if rec["font_path"] else "(unset)",
            "paper": f"{rec['paper'][0]}x{rec['paper'][1]}",
            "font_size": str(rec["font_size"]),
            "rate": str(rec["rate"]),
        }, title="project")


@project.command("close")
@click.pass_context
def project_close(ctx):
    """Close the current project (keep session)."""
    sess = get_session()
    sess.model = model_mod.create_document_model()
    sess.project_path = None
    sess._modified = True
    _ok(ctx, {"closed": True})
    if not ctx.obj.get("json"):
        _skin().success("Project closed")


# ── text ───────────────────────────────────────────────────────────────
@cli.group()
def text() -> None:
    """Text content: set / append / show."""


@text.command("set")
@click.argument("content", type=str, required=False)
@click.option("--file", "file", type=str, default=None, help="Read text from a file.")
@click.pass_context
def text_set(ctx, content, file):
    """Set the document text."""
    sess = get_session()
    if file:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
    if content is None:
        _err(ctx, "provide text or --file")
        return
    sess.snapshot()
    sess.model["text"] = content
    model_mod.DocumentModelOps.trim_to_text(sess.model)
    sess.mark_modified()
    _ok(ctx, {"text_length": len(content)})
    if not ctx.obj.get("json"):
        _skin().success(f"Text set ({len(content)} chars)")


@text.command("append")
@click.argument("content", type=str)
@click.pass_context
def text_append(ctx, content):
    """Append text to the document."""
    sess = get_session()
    sess.snapshot()
    sess.model["text"] += content
    sess.mark_modified()
    _ok(ctx, {"text_length": len(sess.model["text"])})
    if not ctx.obj.get("json"):
        _skin().success(f"Appended ({len(content)} chars)")


@text.command("show")
@click.option("--head", "head", type=int, default=None, help="Show first N chars.")
@click.pass_context
def text_show(ctx, head):
    """Show the document text."""
    sess = get_session()
    t = sess.model["text"]
    if head is not None:
        t = t[:head]
    _ok(ctx, {"text": t, "length": len(sess.model["text"])})
    if not ctx.obj.get("json"):
        click.echo(t)


# ── param (global) ─────────────────────────────────────────────────────
@cli.group()
def param() -> None:
    """Global render parameters: set / get / list / reset / preset."""


@param.command("set")
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.pass_context
def param_set(ctx, key, value):
    """Set a global param, e.g. `param set font_size 40`."""
    sess = get_session()
    nk = params_mod.normalize_key(key)
    if nk not in model_mod.GLOBAL_PARAM_KEYS:
        _err(ctx, f"unknown param '{key}'. keys: {', '.join(model_mod.GLOBAL_PARAM_KEYS)}")
        return
    try:
        coerced = params_mod.coerce_value(nk, value)
    except ValueError as e:
        _err(ctx, str(e))
        return
    sess.snapshot()
    sess.model["global_params"][nk] = coerced
    try:
        params_mod.validate_params(sess.model["global_params"])
    except ValueError as e:
        # roll back
        sess.undo()
        _err(ctx, f"validation failed: {e}")
        return
    sess.mark_modified()
    _ok(ctx, {"key": nk, "value": coerced})
    if not ctx.obj.get("json"):
        _skin().status(nk, str(coerced))


@param.command("get")
@click.argument("key", type=str)
@click.pass_context
def param_get(ctx, key):
    """Get a global param value."""
    sess = get_session()
    nk = params_mod.normalize_key(key)
    v = sess.model["global_params"].get(nk)
    _ok(ctx, {"key": nk, "value": v})
    if not ctx.obj.get("json"):
        click.echo(f"{nk} = {v}")


@param.command("list")
@click.pass_context
def param_list(ctx):
    """List all global params."""
    sess = get_session()
    gp = sess.model["global_params"]
    _ok(ctx, {"params": gp})
    if not ctx.obj.get("json"):
        rows = [[k, str(gp.get(k))] for k in model_mod.GLOBAL_PARAM_KEYS]
        _skin().table(["param", "value"], rows)


@param.command("reset")
@click.argument("key", type=str, required=False)
@click.pass_context
def param_reset(ctx, key):
    """Reset one param (or all) to defaults."""
    sess = get_session()
    sess.snapshot()
    defaults = model_mod.default_global_params(sess.model["global_params"].get("font_path", ""))
    if key:
        nk = params_mod.normalize_key(key)
        sess.model["global_params"][nk] = defaults[nk]
    else:
        sess.model["global_params"] = defaults
    sess.mark_modified()
    _ok(ctx, {"reset": key or "all"})
    if not ctx.obj.get("json"):
        _skin().success(f"Reset {key or 'all params'}")


@param.command("preset")
@click.argument("name", type=str)
@click.pass_context
def param_preset(ctx, name):
    """Apply a paper preset: default / a4 / b5 / letter."""
    sess = get_session()
    sess.snapshot()
    try:
        sess.model["global_params"] = params_mod.apply_preset(sess.model["global_params"], name)
    except ValueError as e:
        _err(ctx, str(e))
        return
    sess.mark_modified()
    _ok(ctx, {"preset": name, "params": sess.model["global_params"]})
    if not ctx.obj.get("json"):
        _skin().success(f"Applied preset '{name}'")


# ── override (range-level) ─────────────────────────────────────────────
@cli.group()
def override() -> None:
    """Range-level overrides (mirror GUI selection overrides)."""


def _parse_override_pairs(pairs: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for p in pairs:
        if "=" not in p:
            raise ValueError(f"expected KEY=VALUE, got '{p}'")
        k, v = p.split("=", 1)
        nk = params_mod.normalize_key(k)
        if nk not in model_mod.ADJUSTABLE_KEYS:
            raise ValueError(f"'{k}' is not an adjustable key. options: {', '.join(model_mod.ADJUSTABLE_KEYS)}")
        if nk == "fill":
            out[nk] = list(params_mod.parse_color(v))
        elif nk == "alignment":
            out[nk] = v.strip().lower()
        elif nk == "underline":
            out[nk] = params_mod.coerce_value("underline", v)
        else:
            out[nk] = float(v) if "." in v else int(v)
    return out


@override.command("set")
@click.argument("start", type=int)
@click.argument("end", type=int)
@click.argument("pairs", nargs=-1, required=True)
@click.pass_context
def override_set(ctx, start, end, pairs):
    """Set overrides on [start,end), e.g. `override set 0 5 font_size=50 fill=red`."""
    sess = get_session()
    try:
        params = _parse_override_pairs(list(pairs))
    except ValueError as e:
        _err(ctx, str(e))
        return
    sess.snapshot()
    model_mod.DocumentModelOps.set_range(sess.model, start, end, params)
    sess.mark_modified()
    _ok(ctx, {"start": start, "end": end, "params": params,
              "overrides": len(sess.model["overrides"])})
    if not ctx.obj.get("json"):
        _skin().success(f"Override set on [{start},{end})")


@override.command("clear")
@click.argument("start", type=int)
@click.argument("end", type=int)
@click.pass_context
def override_clear(ctx, start, end):
    """Clear overrides on [start,end)."""
    sess = get_session()
    sess.snapshot()
    model_mod.DocumentModelOps.clear_range(sess.model, start, end)
    sess.mark_modified()
    _ok(ctx, {"start": start, "end": end, "overrides": len(sess.model["overrides"])})
    if not ctx.obj.get("json"):
        _skin().success(f"Cleared overrides on [{start},{end})")


@override.command("list")
@click.pass_context
def override_list(ctx):
    """List all override ranges."""
    sess = get_session()
    ov = sess.model["overrides"]
    _ok(ctx, {"overrides": [{"start": o["start"], "end": o["end"], "params": o["params"]} for o in ov]})
    if not ctx.obj.get("json"):
        if not ov:
            _skin().info("No overrides")
            return
        rows = [[str(o["start"]), str(o["end"]), _json.dumps(o["params"], ensure_ascii=False)] for o in ov]
        _skin().table(["start", "end", "params"], rows)


@override.command("show")
@click.argument("index", type=int)
@click.pass_context
def override_show(ctx, index):
    """Show effective params at a character index."""
    sess = get_session()
    eff = model_mod.DocumentModelOps.effective_params(sess.model, index)
    seg = model_mod.DocumentModelOps.override_at(sess.model, index)
    _ok(ctx, {"index": index, "effective": eff, "override": seg})
    if not ctx.obj.get("json"):
        rows = [[k, str(v)] for k, v in eff.items()]
        _skin().table(["param", "effective"], rows)


# ── font ───────────────────────────────────────────────────────────────
@cli.group()
def font() -> None:
    """Font management (ttf_library)."""


@font.command("list")
@click.pass_context
def font_list(ctx):
    """List available .ttf fonts in ttf_library."""
    try:
        fonts = handwrite_backend.list_fonts()
    except Exception as e:
        _err(ctx, str(e))
        return
    _ok(ctx, {"fonts": fonts})
    if not ctx.obj.get("json"):
        if not fonts:
            _skin().warning("No .ttf fonts in ttf_library/")
            return
        rows = [[str(i), f["name"], f["path"]] for i, f in enumerate(fonts)]
        _skin().table(["#", "name", "path"], rows)


@font.command("set")
@click.argument("selector", type=str)
@click.pass_context
def font_set(ctx, selector):
    """Set the active font by name or index."""
    sess = get_session()
    try:
        fonts = handwrite_backend.list_fonts()
    except Exception as e:
        _err(ctx, str(e))
        return
    if not fonts:
        _err(ctx, "no fonts available in ttf_library/")
        return
    chosen = None
    if selector.isdigit():
        idx = int(selector)
        if 0 <= idx < len(fonts):
            chosen = fonts[idx]
    if not chosen:
        for f in fonts:
            if f["name"] == selector or f["path"] == selector:
                chosen = f
                break
    if not chosen:
        _err(ctx, f"no font matching '{selector}'")
        return
    sess.snapshot()
    sess.model["global_params"]["font_path"] = chosen["path"]
    sess.mark_modified()
    _ok(ctx, {"font": chosen})
    if not ctx.obj.get("json"):
        _skin().success(f"Font set: {chosen['name']}")


# ── render ─────────────────────────────────────────────────────────────
@cli.group()
def render() -> None:
    """Render to PNGs via the real Node pipeline / inspect outputs."""


@render.command("run")
@click.option("--seed", "seed", type=int, default=None, help="RNG seed (default: session seed / random).")
@click.option("--output-dir", "output_dir", type=str, default=None, help="Output directory.")
@click.option("--verify/--no-verify", default=True, help="Verify PNG outputs (magic bytes, size).")
@click.pass_context
def render_run(ctx, seed, output_dir, verify):
    """Render the current project to paginated PNGs."""
    sess = get_session()
    if not sess.has_project():
        _err(ctx, "no project open")
        return
    outdir = output_dir or sess.output_dir
    use_seed = seed if seed is not None else sess.seed
    try:
        result = render_mod.render_model(sess.model, outdir, seed=use_seed)
    except Exception as e:
        _err(ctx, str(e))
        return
    sess.seed = result.get("seed")
    sess.last_outputs = result.get("outputs", [])
    # Render does NOT mark the model modified (text/params unchanged).
    verification = render_mod.verify_render_result(result) if verify else None
    rec = {
        "seed": result.get("seed"),
        "page_count": result.get("page_count"),
        "outputs": result.get("outputs"),
        "pages": result.get("pages"),
    }
    if verification is not None:
        rec["verification"] = verification
    _ok(ctx, rec)
    if not ctx.obj.get("json"):
        s = _skin()
        s.success(f"Rendered {result.get('page_count')} page(s) (seed={result.get('seed')})")
        for p in result.get("pages", []):
            s.status(f"  page {p.get('index')}", f"{p['width']}x{p['height']}  {p['bytes']:,}B  {p['path']}")
        if verification and not verification["ok"]:
            s.warning("Output verification FAILED — see JSON for details")


@render.command("last")
@click.pass_context
def render_last(ctx):
    """Show paths from the last render."""
    sess = get_session()
    _ok(ctx, {"outputs": sess.last_outputs, "seed": sess.seed})
    if not ctx.obj.get("json"):
        if not sess.last_outputs:
            _skin().info("No render yet")
            return
        for p in sess.last_outputs:
            click.echo(p)


@render.command("open")
@click.pass_context
def render_open(ctx):
    """Open the output directory (mirrors the GUI button)."""
    sess = get_session()
    res = render_mod.open_output_dir(sess.output_dir)
    _ok(ctx, res)
    if not ctx.obj.get("json"):
        if res["ok"]:
            _skin().success(f"Opened {res['opened']}")
        else:
            _skin().error(res.get("error", "failed"))


# ── session ────────────────────────────────────────────────────────────
@cli.group()
def session() -> None:
    """Session state: status / save / load / undo / redo / history."""


@session.command("status")
@click.pass_context
def session_status(ctx):
    sess = get_session()
    rec = sess.status()
    _ok(ctx, {"status": rec})
    if not ctx.obj.get("json"):
        s = _skin()
        s.status_block({k: str(v) for k, v in rec.items()}, title="session")


@session.command("save")
@click.argument("path", type=str, required=False)
@click.pass_context
def session_save(ctx, path):
    sess = get_session()
    target = path or sess.session_path
    if not target:
        target = "handwrite" + SESSION_SUFFIX
    try:
        p = sess.save_session(target)
    except Exception as e:
        _err(ctx, str(e))
        return
    _ok(ctx, {"path": p})
    if not ctx.obj.get("json"):
        _skin().success(f"Session saved -> {p}")


@session.command("load")
@click.argument("path", type=str)
@click.pass_context
def session_load(ctx, path):
    global _session
    try:
        _session = Session.load_session(path)
    except Exception as e:
        _err(ctx, str(e))
        return
    _ok(ctx, {"status": _session.status()})
    if not ctx.obj.get("json"):
        _skin().success(f"Session loaded from {path}")


@session.command("undo")
@click.pass_context
def session_undo(ctx):
    sess = get_session()
    ok = sess.undo()
    _ok(ctx, {"undone": ok, **sess.history()})
    if not ctx.obj.get("json"):
        _skin().success("Undo" if ok else "Nothing to undo")


@session.command("redo")
@click.pass_context
def session_redo(ctx):
    sess = get_session()
    ok = sess.redo()
    _ok(ctx, {"redone": ok, **sess.history()})
    if not ctx.obj.get("json"):
        _skin().success("Redo" if ok else "Nothing to redo")


@session.command("history")
@click.pass_context
def session_history(ctx):
    sess = get_session()
    rec = sess.history()
    _ok(ctx, {"history": rec})
    if not ctx.obj.get("json"):
        _skin().status_block({k: str(v) for k, v in rec.items()}, title="history")


# ── repl ───────────────────────────────────────────────────────────────
REPL_COMMANDS: Dict[str, str] = {
    "project": "new / open / save / info / close",
    "text": "set / append / show",
    "param": "set / get / list / reset / preset",
    "override": "set / clear / list / show",
    "font": "list / set",
    "render": "run / last / open",
    "session": "status / save / load / undo / redo / history",
    "help": "show this help",
    "exit": "leave the REPL",
}


@cli.command()
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Enter the interactive REPL (default when no subcommand is given)."""
    global _repl_mode
    _repl_mode = True
    skin = _skin()
    skin.print_banner()
    try:
        pt = skin.create_prompt_session()
    except Exception:
        # No real console (piped stdin, non-TTY, MSYS bash on Windows, etc.) —
        # prompt_toolkit can't initialize. Fall back to plain input().
        pt = None
    sess = get_session()
    while True:
        try:
            line = skin.get_input(pt, project_name=_project_label(sess), modified=sess._modified)
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        low = line.strip().lower()
        if low in ("exit", "quit", "q"):
            break
        if low in ("help", "?"):
            skin.help(REPL_COMMANDS)
            continue
        try:
            args = shlex.split(line)
        except ValueError as e:
            skin.error(f"parse error: {e}")
            continue
        try:
            cli.main(args, prog_name="cli-anything-handwrite", standalone_mode=False)
        except click.exceptions.UsageError as e:
            e.show()
        except click.exceptions.Abort:
            pass
        except SystemExit:
            pass
        except click.ClickException as e:
            e.show()
        except Exception as e:
            skin.error(str(e))
    skin.print_goodbye()


def _project_label(sess: Session) -> str:
    if sess.project_path:
        return Path(sess.project_path).name
    if sess.has_project():
        return "untitled"
    return ""


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
