#!/usr/bin/env python3
"""
Anomaly Studio v0.1.0-alpha — CLI .db0 Archive Tool (List, Extract, Pack)
=========================================================================
Author / Credits: EternalPain
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STUDIO_ROOT / "backend"))

from db0_vfs import read_db0_toc, extract_db0_entry, pack_directory_to_db0


def cmd_list(args: argparse.Namespace) -> int:
    entries = read_db0_toc(args.archive)
    for e in entries[: args.limit]:
        print(f"{e.size_real:10d}  {e.vfs_path}")
    print(f"Total entries in {args.archive}: {len(entries)}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    entries = read_db0_toc(args.archive)
    out_dir = Path(args.output).resolve()
    count = 0
    for e in entries:
        if args.filter and args.filter.lower() not in e.vfs_path.lower():
            continue
        dest = out_dir / e.vfs_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(extract_db0_entry(e))
        count += 1
    print(f"Extracted {count} files to {out_dir}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    res = pack_directory_to_db0(Path(args.source), Path(args.output), header_prefix=args.prefix or "")
    print(json.dumps(res, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Anomaly 1.5.3 .db0 Archive Tool (EternalPain)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List entries in a .db0 archive")
    p_list.add_argument("archive", help="Path to .db0 file")
    p_list.add_argument("--limit", type=int, default=100, help="Max entries to display")
    p_list.set_defaults(func=cmd_list)

    p_ext = sub.add_parser("extract", help="Extract entries from a .db0 archive")
    p_ext.add_argument("archive", help="Path to .db0 file")
    p_ext.add_argument("-o", "--output", required=True, help="Output directory")
    p_ext.add_argument("-f", "--filter", default="", help="Substring filter")
    p_ext.set_defaults(func=cmd_extract)

    p_pack = sub.add_parser("pack", help="Pack a directory/gamedata folder into a .db0 archive")
    p_pack.add_argument("source", help="Source directory or gamedata folder")
    p_pack.add_argument("-o", "--output", required=True, help="Output .db0 path")
    p_pack.add_argument("--prefix", default="", help="Optional header prefix")
    p_pack.set_defaults(func=cmd_pack)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
