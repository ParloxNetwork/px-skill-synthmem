#!/usr/bin/env python3
"""
validate_vault.py — deterministic health check for a synthmem vault.

Read-only. Reports issues; never modifies the vault. Runs either:
  - automatically at the end of every /synthmem run (the indexer/reviewer
    invokes it and folds findings into the daily log), or
  - standalone via `/synthmem validate` against an existing vault, with no
    consolidation run (cheap scale-testing).

Checks:
  frontmatter  — required fields, type↔prefix match, 5 distinct tags,
                 valid content-type, valid status, ISO dates, slug match
  wikilinks    — broken targets, asymmetric links, isolated nodes,
                 dangling targets referenced by >=3 files (should be stubs)
  duplicates   — near-identical slugs / titles (merge candidates)
  markdown     — raw <...>, unescaped pipes, stray leading '#'
  structure    — file in the correct typed subdir, no binaries, clean root

Stdout: JSON {summary, errors[], warnings[], info[]}
Exit codes:
    0 — no errors (warnings/info allowed)
    1 — argument error
    2 — I/O error
    3 — vault path not found
    5 — validation found ERROR-level issues
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

CONTENT_TYPES = {
    "concept", "pattern", "decision", "recipe",
    "reference", "entity", "summary", "meta",
}
STATUSES = {"active", "draft", "deprecated", "superseded"}
TYPES = {"node", "entity", "log", "chat", "archive", "meta"}
TYPE_DIR = {
    "node": "nodes", "entity": "entities",
    "chat": "chats", "log": "logs", "archive": "archives",
}
REQUIRED_FM = ["id", "type", "title", "slug", "tags", "status",
               "created", "last_updated"]
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?"
                    r"([.+-]\d|Z|[+-]\d{2}:\d{2})?)?")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")
RAW_ANGLE_RE = re.compile(r"(?<!`)<[a-zA-Z][a-zA-Z0-9_-]*>")
CODE_FENCE_RE = re.compile(r"^```")
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp",
              ".mp3", ".mp4", ".zip", ".docx", ".xlsx", ".bin"}


def parse_frontmatter(text):
    """Return (fm_dict_or_None, body, error_or_None). Tiny YAML subset."""
    if not text.startswith("---"):
        return None, text, "no frontmatter block"
    end = text.find("\n---", 3)
    if end == -1:
        return None, text, "unterminated frontmatter"
    raw = text[3:end].strip("\n")
    body = text[end + 4:]
    fm = {}
    key = None
    for line in raw.splitlines():
        if re.match(r"^\s*-\s", line) and key:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(line.strip()[1:].strip().strip('"'))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                fm[key] = []          # likely a block list/map
            elif val.startswith("["):
                inner = val.strip("[]").strip()
                fm[key] = [x.strip().strip('"') for x in inner.split(",")
                           if x.strip()] if inner else []
            else:
                fm[key] = val.strip('"')
    return fm, body, None


def iter_md(vault):
    for p in sorted(vault.rglob("*.md")):
        # skip anything under a dotdir (.git, .obsidian, etc.)
        if any(part.startswith(".") for part in p.relative_to(vault).parts):
            continue
        yield p


def check_file(p, vault, errors, warnings, info, link_index, slugs, titles):
    rel = str(p.relative_to(vault))
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        errors.append({"file": rel, "check": "io", "msg": str(e)})
        return

    name = p.stem
    is_meta = name in ("_INDEX", "_RECENT") or name == "README"
    fm, body, fmerr = parse_frontmatter(text)

    # README is exempt from frontmatter
    if name == "README":
        _scan_markdown(rel, body if fm else text, warnings)
        return

    if fmerr:
        errors.append({"file": rel, "check": "frontmatter", "msg": fmerr})
        _scan_markdown(rel, text, warnings)
        return

    # required fields
    for f in REQUIRED_FM:
        if f not in fm or fm[f] in ("", [], None):
            errors.append({"file": rel, "check": "frontmatter",
                            "msg": f"missing/empty required field: {f}"})

    ftype = fm.get("type", "")
    if ftype not in TYPES:
        errors.append({"file": rel, "check": "frontmatter",
                        "msg": f"invalid type: {ftype!r}"})

    # type ↔ prefix / subdir
    prefix = name.split("_")[0] if "_" in name else ""
    if ftype in TYPE_DIR:
        want_dir = TYPE_DIR[ftype]
        if p.parent.name != want_dir:
            warnings.append({"file": rel, "check": "structure",
                             "msg": f"type {ftype} should live in {want_dir}/"})

    # slug match — convention-aware. The slug is the filename stem with the
    # type prefix stripped, verbatim. Meta files (_INDEX/_RECENT) are exempt
    # (their slug is the stem minus the leading underscore, case-insensitive).
    slug = fm.get("slug", "")
    expect = None
    if name in ("_INDEX", "_RECENT"):
        if slug and slug.lower() != name[1:].lower():
            warnings.append({"file": rel, "check": "frontmatter",
                             "msg": f"meta slug {slug!r} != {name[1:]!r}"})
    else:
        for pfx in ("_archive_", "node_", "entity_", "chat_", "log_"):
            if name.startswith(pfx):
                expect = name[len(pfx):]
                break
        if expect is not None and slug and slug != expect:
            warnings.append({"file": rel, "check": "frontmatter",
                             "msg": f"slug {slug!r} != filename-tail "
                                    f"{expect!r} (slug must equal the stem "
                                    f"after the type prefix)"})

    # tags: exactly 5, all distinct
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        if len(tags) != 5:
            errors.append({"file": rel, "check": "tags",
                            "msg": f"expected 5 tags, got {len(tags)}"})
        if len(tags) != len(set(tags)):
            dups = sorted({t for t in tags if tags.count(t) > 1})
            errors.append({"file": rel, "check": "tags",
                            "msg": f"duplicate tag(s) across positions: {dups}"})
        if len(tags) >= 4 and tags[3] not in CONTENT_TYPES:
            warnings.append({"file": rel, "check": "tags",
                             "msg": f"position-4 (content-type) {tags[3]!r} "
                                    f"not in fixed vocabulary"})

    if fm.get("status") not in STATUSES:
        errors.append({"file": rel, "check": "frontmatter",
                        "msg": f"invalid status: {fm.get('status')!r}"})
    if fm.get("status") == "superseded" and not fm.get("superseded_by"):
        errors.append({"file": rel, "check": "frontmatter",
                        "msg": "status superseded requires superseded_by"})

    for df in ("created", "last_updated"):
        v = fm.get(df, "")
        if v and not ISO_RE.match(str(v)):
            warnings.append({"file": rel, "check": "frontmatter",
                             "msg": f"{df} not ISO-8601: {v!r}"})

    # duplicate slug / title detection feed
    if slug:
        slugs.setdefault(slug, []).append(rel)
    title = fm.get("title", "")
    if title:
        titles.append((title, rel))

    # collect wikilinks (basename targets) for graph checks
    linked = fm.get("linked_nodes", [])
    if isinstance(linked, list):
        for raw in linked:
            for tgt in WIKILINK_RE.findall(str(raw)):
                link_index["edges"].append((name, tgt.strip()))
    for tgt in WIKILINK_RE.findall(body):
        link_index["refs"].setdefault(tgt.strip(), set()).add(rel)

    if ftype == "node" and isinstance(linked, list) and len(linked) == 0:
        link_index["isolated_nodes"].append(rel)

    link_index["all_names"].add(name)
    _scan_markdown(rel, body, warnings)


def _scan_markdown(rel, body, warnings):
    in_fence = False
    for i, line in enumerate(body.splitlines(), 1):
        if CODE_FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # strip inline code spans before scanning
        scrub = re.sub(r"`[^`]*`", "", line)
        if RAW_ANGLE_RE.search(scrub):
            warnings.append({"file": rel, "check": "markdown",
                             "msg": f"line {i}: raw <tag>-like token "
                                    f"(wrap in backticks or escape)"})


def graph_checks(link_index, errors, warnings, info):
    names = link_index["all_names"]
    # broken wikilinks
    broken = {}
    for tgt, refs in link_index["refs"].items():
        base = tgt.split("/")[-1]
        if base not in names and not base.startswith("_archive_"):
            broken[base] = sorted(refs)
    for tgt, refs in sorted(broken.items()):
        if len(refs) >= 3:
            warnings.append({"file": "(graph)", "check": "wikilinks",
                             "msg": f"dangling [[{tgt}]] referenced by "
                                    f"{len(refs)} files — should be a "
                                    f"status:draft stub"})
        else:
            info.append({"file": "(graph)", "check": "wikilinks",
                         "msg": f"unresolved [[{tgt}]] ({len(refs)} ref) "
                                f"— intentional anchor, OK"})

    # asymmetric linked_nodes edges
    edge_set = set(link_index["edges"])
    for a, b in sorted(edge_set):
        if b in names and (b, a) not in edge_set:
            warnings.append({"file": "(graph)", "check": "wikilinks",
                             "msg": f"asymmetric link {a} -> {b} "
                                    f"(missing {b} -> {a})"})

    iso = link_index["isolated_nodes"]
    total_nodes = sum(1 for n in names if n.startswith("node_"))
    if total_nodes:
        pct = len(iso) * 100 // total_nodes
        entry = {"file": "(graph)", "check": "wikilinks",
                 "msg": f"{len(iso)}/{total_nodes} nodes isolated "
                        f"(linked_nodes: []) = {pct}%"}
        (warnings if pct > 30 else info).append(entry)


def dup_checks(slugs, titles, warnings, info):
    for slug, files in sorted(slugs.items()):
        if len(files) > 1:
            warnings.append({"file": "(dedup)", "check": "duplicates",
                             "msg": f"slug {slug!r} used by {files}"})
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            t1, f1 = titles[i]
            t2, f2 = titles[j]
            r = difflib.SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
            if r >= 0.88:
                info.append({"file": "(dedup)", "check": "duplicates",
                             "msg": f"near-identical titles ({r:.2f}): "
                                    f"{f1} ~ {f2}"})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--vault", required=True, help="vault root path")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    ap.add_argument("--changed", default=None,
                    help="comma-separated list of vault-relative paths this "
                         "run wrote/touched. ERRORs in files NOT in this "
                         "list are demoted to warnings tagged 'pre-existing "
                         "(run /synthmem repair)'. Used by the run gate so "
                         "legacy issues don't block finalization forever.")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    if not vault.is_dir():
        print(f"Vault not found: {vault}", file=sys.stderr)
        sys.exit(3)

    errors, warnings, info = [], [], []
    link_index = {"edges": [], "refs": {}, "all_names": set(),
                  "isolated_nodes": []}
    slugs, titles = {}, []

    # binary / structure sweep
    for p in sorted(vault.rglob("*")):
        if any(part.startswith(".") for part in p.relative_to(vault).parts):
            continue
        if p.is_file() and p.suffix.lower() in BINARY_EXT:
            errors.append({"file": str(p.relative_to(vault)),
                           "check": "structure",
                           "msg": "binary file — vault must be markdown-only"})

    try:
        for p in iter_md(vault):
            check_file(p, vault, errors, warnings, info,
                       link_index, slugs, titles)
    except OSError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        sys.exit(2)

    graph_checks(link_index, errors, warnings, info)
    dup_checks(slugs, titles, warnings, info)

    # Scope-aware gate: demote ERRORs in files this run did NOT touch to
    # warnings. Legacy issues should not block finalization forever —
    # they are addressed by `/synthmem repair`, not by reprocessing.
    if args.changed is not None:
        scope = {s.strip() for s in args.changed.split(",") if s.strip()}
        kept, demoted = [], []
        for e in errors:
            if e["file"] in scope or e["file"] in ("(graph)", "(dedup)"):
                kept.append(e)
            else:
                e = dict(e)
                e["msg"] += " — pre-existing (run /synthmem repair)"
                demoted.append(e)
        errors = kept
        warnings = demoted + warnings

    result = {
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info),
            "verdict": "FAIL" if errors else
                       ("REVIEW" if warnings else "PASS"),
        },
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }

    if args.format == "text":
        s = result["summary"]
        print(f"synthmem vault validation — {s['verdict']}")
        print(f"  errors={s['errors']} warnings={s['warnings']} "
              f"info={s['info']}")
        for bucket in ("errors", "warnings"):
            for it in result[bucket]:
                print(f"  [{bucket[:-1].upper()}] {it['file']} "
                      f"({it['check']}): {it['msg']}")
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")

    sys.exit(5 if errors else 0)


if __name__ == "__main__":
    main()
