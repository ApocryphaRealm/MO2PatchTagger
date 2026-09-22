# MO2 Patch Tagger

A Mod Organizer 2 tool that finds the mods that call themselves a patch and puts `[Patch]` in front of
their names - from a ticked preview, in one pass, and reversibly.

## What it is for

A big list has hundreds of compatibility patches scattered through it. Tagging them lets you see them
as a group: with [MO2 Custom Filters](https://github.com/ApocryphaRealm/MO2CustomFilters) installed,
`[Patch]` appears in its Keywords tab automatically and one tick shows every patch in the list (or
hides them all).

## What counts as a patch

A mod that **says** it is one, in any of these places - the window shows which:

* a plugin's own header description (the text its author wrote into the `.esp`) says "patch";
* a plugin file is called `..._patch.esp` or the like;
* the mod's name says "patch" or "patches";
* the mod sits in MO2's **Patches** category.

"patch" is matched as a whole word, any case, so "patched" and "dispatch" do not count.

What a plugin lists as its **masters is deliberately not a rule**. A first build used it, and it swept
in every mod that merely requires another one - a perk overhaul that needs a magic overhaul, an NPC
overhaul that needs the unofficial patch - 350 mods on the list it was written for. That is
"depends on", not "patches".

## How to use it

1. Copy `plugins\MO2PatchTagger.py` into the MO2 instance's `plugins` folder and restart MO2.
2. **Tools -> MO2 Patch Tagger** (it can go on the toolbar).
3. The window lists every mod that qualifies and every mod that already carries `[Patch]`. A tick
   means "carries `[Patch]` after OK": untagged patches come ticked (proposed), tagged mods come
   ticked (kept). Untick a tagged mod to remove its tag. **Tick all** / **Untick all** do it
   wholesale; the "After OK" column shows each row's resulting name.
4. OK applies. Only rows whose tick differs from their current name are renamed.

## How the rename is done

MO2's own rename rebuilds the whole list after every call - 350 in a row froze it. So the tool does
what MO2 would do, once:

1. asks MO2 to write anything it still has pending (one refresh);
2. backs every profile's `modlist.txt` up to `plugins\data\patch-tagger-backups\<timestamp>\`;
3. renames the mod folders on disk;
4. rewrites the renamed lines in every profile's `modlist.txt` - same enabled/disabled state, same
   position;
5. asks MO2 for one refresh, which re-reads the mods folder and the profile from disk;
6. checks that every renamed mod is back at its previous priority and shows a short summary.

Nothing happens by itself: no rename on refresh, no rename at start-up. Separators, Overwrite, the
game's own entries and backups are never touched.

## Requirements

Mod Organizer 2 2.5.x (tested on 2.5.2). A PyQt5 fallback for 2.4 exists but is untested.

## Debugging

`<instance>\plugins\data\mo2-patch-tagger.log` - every scan and every rename, with what failed and
why. Send it with any bug report. The `modlist.txt` backups sit beside it.

## Licence

GPL-3.0-or-later. Copyright (C) 2026 ApocryphaRealm. See `LICENSE` and `NOTICE.md`.
