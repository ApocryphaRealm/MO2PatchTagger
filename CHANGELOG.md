# Changelog - MO2 Patch Tagger

Versions are issued by the project's version gate. Written as the change happens (rule 61).

## 1.0.1 - 2026-09-29

* Fixed: an instance that keeps its profiles somewhere other than directly under its own folder (MO2 Settings > Paths, e.g. Mo2/SSE/profiles) failed to rename: the profiles folder was taken as basePath()/profiles. It is now the folder MO2 itself uses (the parent of the active profile's folder), as MO2's own rename does. Found from the Nexus report by Mordre on MO2 Modlist Manager, 2026-09-29.
* Python's fault handler is armed on load, into plugins\data\faults.log, so a crash inside MO2 names the
  plugin and line (the standing rule for our MO2 plugins, 2026-09-23).

## 1.0.0 - 2026-09-22 - first release

* Tools-menu window listing every mod that calls itself a patch - a plugin's header description, a
  plugin's file name, the mod's name, or MO2's Patches category says "patch" (whole word, any case) -
  and every mod already carrying `[Patch]`, with the signal that fired in a "why" column.
* A tick means "carries `[Patch]` after OK": tick to add the prefix, untick to remove it; Tick all /
  Untick all; an "After OK" column showing each resulting name. Only rows whose tick differs from
  the current name are renamed.
* Renames done in one pass on disk - folders plus every profile's `modlist.txt` (backed up first) -
  followed by a single MO2 refresh and a priority check, instead of MO2's per-mod rename, which
  rebuilds the list after every call.
* Log at `plugins\data\mo2-patch-tagger.log`.

### Development history the same night (all under 1.0.0, each superseded before it was proven)

* First build: patch = a plugin masters another mod's plugin; tag appended. The owner: prefix, not
  suffix. Then 350 `renameMod` calls froze MO2 - rebuilt to rename on disk with one refresh. Then
  tagged mods had no way back - the window now lists them and Untick all removes tags. Then the
  master rule was widened with header / file-name / mod-name / category signals, and finally the
  master rule was dropped altogether: "focus on the mods that are actually patches and not just
  requiring another mod".
