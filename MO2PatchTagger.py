# MO2 Patch Tagger - a Mod Organizer 2 tool that finds the mods that are patches and puts "[Patch] " in front of their names,
# so MO2 Custom Filters' Keywords tab lists them under [Patch] automatically.
#
# The owner, 2026-09-22: "make a mo2 plugin that can rename mods based on their content, what it overwrites and add a
# tag for patches which would appear automatically in the keyword area" - narrowed the same night to ONE tag: no
# content or overwrite tags in names ("only a single [Patch] tag"; overwrites: "there's no need"), a patch being a mod
# whose plugin lists another mod's plugin as a master, applied from a toolbar tool with a ticked preview. The tag
# is a PREFIX (the owner, 2026-09-22: "i want it to prefix the mods not sufix them").
#
# WHAT IS A PATCH. A mod that CALLS ITSELF one, in any of these places - each named in the window's "why" column:
#   * HEADER - a plugin's own description (the TES4 SNAM text its author wrote) says "patch";
#   * FILE NAME - a plugin file (.esp / .esm / .esl in the mod folder) is called ..._patch.esp or the like;
#   * MOD NAME - the mod's folder name says "patch" / "patches";
#   * CATEGORY - the mod sits in MO2's "Patches" category.
# What a plugin lists as its MASTERS is deliberately NOT a rule: the first build used it and it swept in every mod that
# merely requires another (Adamant needs Mysticism, AI Overhaul needs USSEP - 350 mods). The owner, 2026-09-22: "for
# this to be a meaningful change it has to not rely on the referencing another mod as a master bc that is too many mods
# and i want this to focus on the mods that are actually patches and not just requiring another mod". Earlier the same
# night: "not just ... what it references as its master, but also what the files themselves define themselves as".
# "patch" is matched as a whole word, any case, so "patched" or "dispatch" do not count. The description is read from the
# plugin's own TES4 header, so disabled mods are judged as well as enabled ones.
#
# THE WINDOW (Tools -> MO2 Patch Tagger). Every mod that qualifies is listed, and so is every mod that already carries
# "[Patch]" (the owner, 2026-09-22: "i dont see a way to untag them so they should still show up in the popup with an
# option to tick all or untick all and remove tags"). A TICK means "carries [Patch] after OK": an untagged row comes
# ticked (proposed), a tagged row comes ticked (kept); untick a tagged row and OK removes its tag, tick an untagged one
# and OK adds it. Tick all / Untick all do it wholesale. The "After OK" column shows the name each row will have.
# Nothing happens by itself: no rename on refresh, no rename on start-up. Separators, Overwrite, foreign (DLC / game)
# entries and backups are never touched.
#
# HOW THE RENAME IS DONE (1.0.0, second build). MO2's renameMod rebuilds the whole list after EVERY call (shell rename,
# rewrite of every profile's modlist.txt, dataChanged over all rows), so 350 of them in a row froze MO2 (the owner,
# 2026-09-22: "mo2 timed out bc it applied to too many mods at the same time"; then, after MO2 came back with the tags
# in place: "maybe we should have it rename them in the txt document and then refresh automatically"). So the tool
# does what MO2 would do, once: it flushes MO2's pending list writes (refresh), renames the mod FOLDERS on disk,
# rewrites the mod's line in EVERY profile's modlist.txt (after backing each one up under plugins\data\), then asks
# MO2 for ONE refresh, which re-reads the mods folder and the profile from disk. Afterwards it checks that every
# renamed mod is back at its old priority and reports.
#
# Copyright (C) 2026 ApocryphaRealm. GPL-3.0-or-later - see LICENSE and NOTICE.md.

__version__ = "1.0.0"    # issued by version-gate.ps1; never typed by hand

import os
import re
import struct
import time

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (
        QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTreeWidget,
        QTreeWidgetItem, QVBoxLayout,
    )
    _CHECKED, _UNCHECKED = Qt.CheckState.Checked, Qt.CheckState.Unchecked
    _CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    _USER = Qt.ItemDataRole.UserRole
    _NO_SELECTION = QAbstractItemView.SelectionMode.NoSelection
except ImportError:  # MO2 builds that still ship PyQt5
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import (
        QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTreeWidget,
        QTreeWidgetItem, QVBoxLayout,
    )
    _CHECKED, _UNCHECKED = Qt.Checked, Qt.Unchecked
    _CHECKABLE = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
    _USER = Qt.UserRole
    _NO_SELECTION = QAbstractItemView.NoSelection

import mobase


PLUGIN_NAME = "MO2 Patch Tagger"
TAG = "[Patch]"
BASE_MASTERS = {"skyrim.esm", "update.esm", "dawnguard.esm", "hearthfires.esm", "dragonborn.esm"}
PLUGIN_EXT = (".esp", ".esm", ".esl")


def has_tag(name):
    return TAG.lower() in name.lower()


def with_tag(name):
    return name if has_tag(name) else f"{TAG} {name}"


def without_tag(name):
    """the name with every [Patch] removed, prefix or suffix, spaces tidied"""
    out = re.sub(re.escape(TAG), "", name, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


def _is_base_master(name):
    n = name.lower()
    return n in BASE_MASTERS or n.startswith("cc")      # Creation Club content ships with the game


_PATCH_WORD = re.compile(r"(?<![a-z])patch(?:es)?(?![a-z])", re.I)


def says_patch(text):
    return bool(text) and _PATCH_WORD.search(text) is not None


def read_header(path):
    """(masters, description) from a plugin's TES4 header: the MAST entries in order and the SNAM text.
    ([], "") when the file is not a plugin or cannot be read."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
            if len(head) < 24 or head[:4] != b"TES4":
                return [], ""
            size = struct.unpack("<I", head[4:8])[0]
            data = fh.read(min(size, 4 * 1024 * 1024))
    except OSError:
        return [], ""
    masters, description, pos = [], "", 0
    while pos + 6 <= len(data):
        sig = data[pos:pos + 4]
        sub = struct.unpack("<H", data[pos + 4:pos + 6])[0]
        pos += 6
        if sig == b"XXXX" and sub == 4:                 # an oversize next subrecord: its real size follows
            real = struct.unpack("<I", data[pos:pos + 4])[0]
            pos += 4
            if pos + 6 > len(data):
                break
            sig = data[pos:pos + 4]
            pos += 6
            sub = real
        payload = data[pos:pos + sub]
        pos += sub
        if sig == b"MAST":
            masters.append(payload.split(b"\x00", 1)[0].decode("cp1252", "replace"))
        elif sig == b"SNAM":
            description = payload.split(b"\x00", 1)[0].decode("cp1252", "replace")
    return masters, description


def read_masters(path):
    return read_header(path)[0]


class MO2PatchTagger(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent = None

    # ---- IPlugin ------------------------------------------------------------------------------
    def init(self, organizer):
        self._organizer = organizer
        return True

    def name(self):
        return PLUGIN_NAME

    def author(self):
        return "ApocryphaRealm"

    def description(self):
        return ("Finds the mods that call themselves a patch (plugin header, plugin file name, mod name or MO2 category) "
                "and prefixes [Patch] to their names, from a ticked preview; untick to remove a tag.")

    def version(self):
        major, minor, patch = (int(x) for x in __version__.split("."))
        return mobase.VersionInfo(major, minor, patch, mobase.ReleaseType.FINAL)

    def isActive(self):
        return True

    def settings(self):
        return []

    # ---- IPluginTool --------------------------------------------------------------------------
    def displayName(self):
        return PLUGIN_NAME

    def tooltip(self):
        return "Prefix [Patch] to the mods that call themselves a patch (header, file name, mod name or category)"

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self._parent = widget

    def display(self):
        if self._organizer is None:
            return
        try:
            rows = self.scan()
        except Exception as exc:  # noqa: BLE001
            self._log(f"scan failed: {exc!r}")
            return
        dialog = _PreviewDialog(rows, self._parent)
        accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if not accepted:
            self._log(f"cancelled: {len(rows)} row(s) shown, nothing changed")
            return
        chosen = dialog.changes()
        if not chosen:
            self._log("no tick changed anything; nothing renamed")
            return
        try:
            summary = self.rename_on_disk(chosen)
        except Exception as exc:  # noqa: BLE001
            self._log(f"rename failed: {exc!r}")
            summary = f"The rename stopped with an error: {exc!r}\nSee plugins\\data\\mo2-patch-tagger.log."
        try:
            QMessageBox.information(self._parent, PLUGIN_NAME, summary)
        except Exception:  # noqa: BLE001
            pass

    def rename_on_disk(self, chosen):
        """Rename the chosen mods the fast way: folders + every profile's modlist.txt, then one MO2 refresh."""
        org = self._organizer
        mod_list = org.modList()
        mods_dir = org.modsPath()
        profiles_dir = os.path.join(org.basePath(), "profiles")
        # the priority each mod has now, to check against afterwards
        before = {}
        for old, _new, _why in chosen:
            try:
                before[old] = mod_list.priority(old)
            except Exception:  # noqa: BLE001
                before[old] = None
        # 1. let MO2 write anything it still has pending, so the files on disk are the current lists
        org.refresh(True)
        # 2. back every profile's modlist.txt up
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = os.path.join(org.basePath(), "plugins", "data", "patch-tagger-backups", stamp)
        profiles = []
        for prof in sorted(os.listdir(profiles_dir)):
            ml = os.path.join(profiles_dir, prof, "modlist.txt")
            if os.path.isfile(ml):
                os.makedirs(os.path.join(backup_dir, prof), exist_ok=True)
                with open(ml, "rb") as src, open(os.path.join(backup_dir, prof, "modlist.txt"), "wb") as dst:
                    dst.write(src.read())
                profiles.append(ml)
        # 3. rename the folders
        renamed, failed = [], []
        for old, new, _why in chosen:
            src, dst = os.path.join(mods_dir, old), os.path.join(mods_dir, new)
            try:
                if not os.path.isdir(src):
                    failed.append((old, "folder not found"))
                    continue
                if os.path.exists(dst):
                    failed.append((old, "target name already exists"))
                    continue
                os.rename(src, dst)
                renamed.append((old, new))
            except OSError as exc:
                failed.append((old, str(exc)))
        # 4. the same rename in every profile's modlist.txt (lines are "+Name" / "-Name"; names compare case-insensitively)
        by_lower = {old.lower(): new for old, new in renamed}
        touched = 0
        for ml in profiles:
            text = open(ml, "rb").read().decode("utf-8-sig")
            nl = "\r\n" if "\r\n" in text else "\n"
            out, changed = [], 0
            for line in text.split(nl):
                if line[:1] in "+-" and line[1:].lower() in by_lower:
                    out.append(line[0] + by_lower[line[1:].lower()])
                    changed += 1
                else:
                    out.append(line)
            if changed:
                open(ml, "wb").write(nl.join(out).encode("utf-8"))
                touched += 1
        # 5. one refresh: MO2 re-reads the mods folder and the profile's modlist.txt from disk
        org.refresh(True)
        # 6. check
        moved = []
        for old, new in renamed:
            try:
                after = mod_list.priority(new)
            except Exception:  # noqa: BLE001
                after = None
            if before.get(old) is not None and after != before[old]:
                moved.append(f"{new}: {before[old]} -> {after}")
        self._log(f"renamed {len(renamed)} of {len(chosen)} ticked on disk, {touched} profile list(s) updated, "
                  f"backups in {backup_dir}"
                  + (f" | failed: {'; '.join(f'{n} ({e})' for n, e in failed)}" if failed else "")
                  + (f" | PRIORITY CHANGED: {'; '.join(moved)}" if moved else " | every renamed mod kept its priority"))
        return (f"Renamed {len(renamed)} of {len(chosen)} ticked mod(s); {touched} profile list(s) updated.\n"
                + (f"{len(failed)} could not be renamed (see the log).\n" if failed else "")
                + (f"{len(moved)} changed priority - see the log and the backups in plugins\\data\\patch-tagger-backups.\n"
                   if moved else "Every renamed mod kept its place in the list.\n")
                + "The Keywords tab of MO2 Custom Filters now lists them under [Patch].")

    # ---- the work -----------------------------------------------------------------------------
    def scan(self):
        """[(name, qualifies, tagged, why)] for every mod that is a patch or already carries the tag"""
        org = self._organizer
        mod_list = org.modList()
        names = list(mod_list.allModsByProfilePriority())
        rows = []
        for n in names:
            if n.endswith("_separator"):
                continue
            mod = mod_list.getMod(n)
            if mod is None:
                continue
            try:
                if mod.isSeparator() or mod.isOverwrite() or mod.isForeign() or mod.isBackup():
                    continue
            except Exception:  # noqa: BLE001
                continue
            reasons = self._patch_signals(n, mod)
            tagged = has_tag(n)
            if not reasons and not tagged:
                continue
            why = " | ".join(reasons) if reasons else "(nothing says patch any more)"
            rows.append((n, bool(reasons), tagged, why))
        n_tagged = sum(1 for r in rows if r[2])
        self._log(f"scan: {len(names)} entries, {len(rows)} row(s): {n_tagged} tagged, {len(rows) - n_tagged} to tag")
        return rows

    def _patch_signals(self, name, mod):
        """Every reason this mod counts as a patch, as short strings for the window; [] when none"""
        reasons = []
        try:
            root = mod.absolutePath()
            files = [f for f in os.listdir(root) if f.lower().endswith(PLUGIN_EXT) and os.path.isfile(os.path.join(root, f))]
        except OSError:
            files, root = [], ""
        by_header, by_file = [], []
        for f in files:
            _masters, description = read_header(os.path.join(root, f))
            if says_patch(description):
                by_header.append(f)
            if says_patch(os.path.splitext(f)[0]):
                by_file.append(f)
        if by_header:
            reasons.append("header says patch: " + ", ".join(by_header))
        if by_file:
            reasons.append("file name: " + ", ".join(by_file))
        if says_patch(without_tag(name)):
            reasons.append("mod name")
        try:
            if any(c.strip().lower() == "patches" for c in mod.categories()):
                reasons.append("category Patches")
        except Exception:  # noqa: BLE001
            pass
        return reasons

    def _log(self, msg):
        try:
            path = os.path.join(self._organizer.basePath(), "plugins", "data", "mo2-patch-tagger.log")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
        except Exception:  # noqa: BLE001
            pass


class _PreviewDialog(QDialog):
    """Every patch and every tagged mod; a tick means it carries [Patch] after OK."""

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle(PLUGIN_NAME)
        self.resize(1100, 950)
        n_tagged = sum(1 for r in rows if r[2])
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            f"A mod is a patch when it calls itself one: a plugin's header description, a plugin's file name, the mod's\n"
            f"name or its MO2 category says \"patch\". Merely requiring another mod (a master) does not count.\n"
            f"A TICK means the mod carries \"{TAG}\" after OK: tick to add the tag, untick to remove it. Tagged mods are\n"
            f"listed too, so the tag can be taken off again. \"After OK\" shows the name each row will have.\n"
            f"{len(rows)} row(s): {n_tagged} tagged, {len(rows) - n_tagged} not yet."))
        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Mod (now)", "After OK", "Why it is a patch"])
        self._tree.setRootIsDecorated(False)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(_NO_SELECTION)
        self._loading = True
        for name, qualifies, tagged, why in rows:
            it = QTreeWidgetItem([name, "", why])
            it.setData(0, _USER, (name, qualifies, tagged))
            it.setFlags(_CHECKABLE)
            it.setCheckState(0, _CHECKED)            # proposed (untagged) or kept (tagged): both start ticked
            it.setToolTip(2, why)
            self._tree.addTopLevelItem(it)
            self._refresh_after(it)
        self._loading = False
        self._tree.itemChanged.connect(self._on_changed)
        self._tree.header().resizeSection(0, 380)
        self._tree.header().resizeSection(1, 420)
        lay.addWidget(self._tree, 1)

        row = QHBoxLayout()
        all_btn, none_btn = QPushButton("Tick all", self), QPushButton("Untick all", self)
        all_btn.setToolTip("Every row carries [Patch] after OK")
        none_btn.setToolTip("No row carries [Patch] after OK - removes every tag")
        all_btn.clicked.connect(lambda: self._set_all(_CHECKED))
        none_btn.clicked.connect(lambda: self._set_all(_UNCHECKED))
        row.addWidget(all_btn)
        row.addWidget(none_btn)
        row.addStretch(1)
        lay.addLayout(row)

        try:
            standard = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        except AttributeError:  # PyQt5
            standard = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        box = QDialogButtonBox(standard, self)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def _after(self, it):
        name = it.data(0, _USER)[0]
        return with_tag(name) if it.checkState(0) == _CHECKED else without_tag(name)

    def _refresh_after(self, it):
        new = self._after(it)
        it.setText(1, new if new != it.data(0, _USER)[0] else "(unchanged)")

    def _on_changed(self, it, col):
        if not self._loading and col == 0:
            self._refresh_after(it)

    def _set_all(self, state):
        self._loading = True
        for i in range(self._tree.topLevelItemCount()):
            it = self._tree.topLevelItem(i)
            it.setCheckState(0, state)
            self._refresh_after(it)
        self._loading = False

    def changes(self):
        """[(old name, new name, why)] for every row whose tick differs from what the name has now"""
        out = []
        for i in range(self._tree.topLevelItemCount()):
            it = self._tree.topLevelItem(i)
            name = it.data(0, _USER)[0]
            new = self._after(it)
            if new != name:
                out.append((name, new, it.text(2)))
        return out


def createPlugin():
    return MO2PatchTagger()
