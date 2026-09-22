MO2 Patch Tagger
================
Version 1.0.0

A Mod Organizer 2 tool that finds the mods that call themselves a patch and puts [Patch] in front of
their names - from a ticked preview, in one pass, and reversibly. With MO2 Custom Filters installed,
[Patch] appears in its Keywords tab automatically.

THIS IS NOT A MOD. Do not install it with the mod manager.

REQUIREMENTS
------------
Mod Organizer 2 2.5.x (tested on 2.5.2).

INSTALLATION
------------
Copy plugins\MO2PatchTagger.py into your MO2 folder's "plugins" folder, next to the other .py
plugins, and restart MO2. It appears under Tools -> MO2 Patch Tagger (and can go on the toolbar).
To remove it, delete the file.

WHAT COUNTS AS A PATCH
----------------------
A mod that says it is one: a plugin's header description says "patch", a plugin file is called
..._patch.esp, the mod's name says "patch" / "patches", or the mod sits in MO2's Patches category.
Whole word, any case. Merely requiring another mod (a master) does NOT count.

USE
---
- Open Tools -> MO2 Patch Tagger. Every qualifying mod and every already-tagged mod is listed; the
  "Why it is a patch" column says which signal fired.
- A tick means the mod carries [Patch] after OK. Untick a tagged mod to remove its tag. Tick all /
  Untick all do it wholesale. "After OK" shows each row's resulting name.
- OK renames only the rows whose tick differs from their current name: folders on disk and every
  profile's modlist.txt (backed up first under plugins\data\patch-tagger-backups\), then one MO2
  refresh. Order and enabled state are kept; a summary confirms it.

DEBUGGING
---------
<your MO2 folder>\plugins\data\mo2-patch-tagger.log - send it with any bug report.

LICENCE
-------
GPL-3.0-or-later. Copyright (C) 2026 ApocryphaRealm. See LICENSE and NOTICE.md.
Source: https://github.com/ApocryphaRealm/MO2PatchTagger
