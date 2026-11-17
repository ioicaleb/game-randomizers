"""
Renaming the placeholder item ("Junk From Another World") by editing the game's text.

Player-facing text lives in the LOCALIZATION archive (data_localized_en.oaf), in string tables ("global\\strings\\*.std").
Layout, as decoded from your archive:

  index entry, 36 bytes :  [id][length][0][length][0][text offset][0][0][0]
  text pool             :  NUL-terminated strings; an entry's text is at  pool_base + text offset

An item record in the item table refers to its name and description by these ids (fields 5 and 6).

What we do: take ONE string nothing important uses (Chicken Bowl's description, 131 characters of room), rewrite its text
to the label, and make every placeholder item use that string as its NAME (with no description). A longer text would
overwrite the next string, so we only ever write text that fits, and we update the stored length.

Safety: the first run keeps data_localized_en.oaf.clean next to the archive; the edit is always applied to the
original bytes, and can be undone by turning the feature off (the original text is restored from the backup).
"""
import glob
import mmap
import os
import shutil
import struct
from typing import Callable, Optional, Tuple

DONOR_ID = 0x18E75                               # Chicken Bowl (#102): description string, 131 characters
DONOR_START = b"Overcooked, oversauced"          # first words of the original text (sanity check)
ANCHOR_ID = 0x2011C                              # "Crumpled Paper" (used only to find the text pool)
ANCHOR_TEXT = b"Crumpled Paper"
NO_DESCRIPTION = 0xFFFFFFFF
TOKEN_NAME = "Junk From Another World"
ENTRY = 36


def _find_entry(buf, string_id: int, start: int = 0) -> int:
    """Offset of the 36-byte index entry for string_id, or -1."""
    needle = struct.pack("<I", string_id)
    pos = buf.find(needle, start)
    while pos != -1:
        w = struct.unpack("<9I", buf[pos: pos + ENTRY]) if pos + ENTRY <= len(buf) else None
        if w and w[1] == w[3] and w[2] == 0 and w[4] == 0 and w[6] == 0 and w[7] == 0 and w[8] == 0 and 0 < w[1] < 4096:
            return pos
        pos = buf.find(needle, pos + 1)
    return -1


def locate_donor(buf) -> Optional[Tuple[int, int, int]]:
    """Returns (entry offset, text offset, text length) of the donor string in this archive, or None."""
    anchor = _find_entry(buf, ANCHOR_ID)
    if anchor < 0:
        return None
    a_len, a_off = struct.unpack_from("<I", buf, anchor + 4)[0], struct.unpack_from("<I", buf, anchor + 20)[0]
    a_text = buf.find(ANCHOR_TEXT + b"\0")
    while a_text != -1 and buf[a_text: a_text + a_len] != ANCHOR_TEXT:
        a_text = buf.find(ANCHOR_TEXT + b"\0", a_text + 1)
    if a_text == -1:
        return None
    base = a_text - a_off                                      # where the text pool starts in this archive
    entry = _find_entry(buf, DONOR_ID)
    if entry < 0:
        return None
    length = struct.unpack_from("<I", buf, entry + 4)[0]
    text_at = base + struct.unpack_from("<I", buf, entry + 20)[0]
    if buf[text_at: text_at + len(DONOR_START)] != DONOR_START or buf[text_at + length] != 0:
        return None                                            # not the text we expect: leave this archive alone
    return entry, text_at, length


def patch_localized(game_dir: str, enabled: bool = True, dry_run: bool = False,
                    log: Callable[[str], None] = print) -> Optional[Tuple[int, int]]:
    """
    Edit (or, if enabled=False, restore) the donor string in every data_localized_*.oaf.
    Returns (name id, description id) the placeholder items should use, or None if the label is unavailable.
    """
    result = None
    archives = [p for p in glob.glob(os.path.join(game_dir, "data_localized_*.oaf"))
                if not os.path.basename(p).endswith(".clean") and "_vo_" not in os.path.basename(p)]
    if not archives:
        log("[TEXT] No data_localized_*.oaf found: placeholders keep a vanilla junk name.")
        return None
    for live in sorted(archives):
        clean = live + ".clean"
        name = os.path.basename(live)
        if not os.path.isfile(clean):
            if dry_run:
                continue
            shutil.copyfile(live, clean)
            log(f"[TEXT] Made a pristine backup of {name}.")
        if os.path.getsize(live) != os.path.getsize(clean):
            log(f"[TEXT] {name} and its .clean backup differ in size (game updated?). Delete the .clean file and retry.")
            continue
        with open(clean, "rb") as cf, mmap.mmap(cf.fileno(), 0, access=mmap.ACCESS_READ) as cm:
            where = locate_donor(cm)
            if where is None:
                log(f"[TEXT] {name}: the expected text was not found (other language or game version); left unchanged.")
                continue
            entry, text_at, length = where
            original_text = bytes(cm[text_at: text_at + length])
            original_entry = bytes(cm[entry: entry + ENTRY])
        label = TOKEN_NAME.encode("latin1")[:length]
        if len(label) < 8:
            log(f"[TEXT] {name}: no room for the label; left unchanged.")
            continue
        if not dry_run:
            with open(live, "r+b") as lf:
                if enabled:
                    lf.seek(text_at)
                    lf.write(label + b"\0" * (length - len(label)))
                    entry_bytes = bytearray(original_entry)
                    struct.pack_into("<I", entry_bytes, 4, len(label))
                    struct.pack_into("<I", entry_bytes, 12, len(label))
                    lf.seek(entry)
                    lf.write(entry_bytes)
                else:                                          # restore the original text and entry
                    lf.seek(text_at)
                    lf.write(original_text)
                    lf.seek(entry)
                    lf.write(original_entry)
        if enabled:
            log(f"[TEXT] {name}: placeholder label set to '{label.decode('latin1')}'.")
            result = (DONOR_ID, NO_DESCRIPTION)
        else:
            log(f"[TEXT] {name}: original text restored.")
    return result
