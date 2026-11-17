#!/usr/bin/env python3
"""
Find where the game stores a piece of TEXT (item names, descriptions, menu text...).

Usage:
    python3 find_text.py "<extracted game folder>" "Crumpled Paper" "Cow Bell" "Chicken Bowl"
    python3 find_text.py "<game folder>/data_archive.oaf" "Crumpled Paper"      (search the big archive file itself)
    (with no strings given it searches for a few item names)

Also tries UTF-8 with the words split by spaces/underscores removed, and the ASCII form with '_' for ' '.

For every match it prints the file, the offset, the text around it, and the 16 bytes BEFORE the match in hex.
Those bytes usually hold the entry's ID and length, which is exactly what we need to edit a name safely.
Searches ASCII and UTF-16 (the two usual encodings), case-insensitively. Audio, textures and movies are skipped.
"""
import mmap, os, re, sys

SKIP_EXT = {".gfx", ".dds", ".tga", ".wem", ".bnk", ".bik", ".usm", ".png", ".jpg", ".jpeg", ".wav", ".ogg"}
DEFAULT = ["Crumpled Paper", "Head of the Powell Statue", "Cow Bell"]
MAX_PER_FILE = 4


def show(rel, data, s, e, enc, n):
    ctx = bytes(data[max(0, s - 40): e + 40])
    txt = ctx.decode("utf-16-le", "replace") if enc == "utf-16-le" else ctx.decode("latin1")
    txt = re.sub(r"[^ -~]", ".", txt)
    before = bytes(data[max(0, s - 16): s]).hex(" ", 4)
    print(f"{rel} @0x{s:X} [{enc}] '{n}'\n    text:   {txt}\n    before: {before}")


def variants(n):
    """The same text in the forms a game might store it."""
    forms = {f.lower() for f in (n, n.replace(" ", "_"), n.replace(" ", ""))}      # the regex is case-insensitive
    for f in forms:
        for enc in ("ascii", "utf-16-le"):
            yield n, enc, re.compile(re.escape(f.encode(enc)), re.I)


def main(root, needles):
    pats = [p for n in needles for p in variants(n)]
    total = 0
    if os.path.isfile(root):                                   # one big file (e.g. data_archive.oaf): use mmap
        with open(root, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for n, enc, rx in pats:
                for k, m in enumerate(rx.finditer(mm)):
                    if k >= 6:
                        break
                    show(os.path.basename(root), mm, m.start(), m.end(), enc, n)
                    total += 1
        print(f"\n{total} match(es).")
        return
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            path = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(path) > 300 * 1024 * 1024:
                    continue
                data = open(path, "rb").read()
            except OSError:
                continue
            for n, enc, rx in pats:
                for k, m in enumerate(rx.finditer(data)):
                    if k >= MAX_PER_FILE:
                        break
                    show(os.path.relpath(path, root), data, m.start(), m.end(), enc, n)
                    total += 1
    print(f"\n{total} match(es).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2:] or DEFAULT)