# Wilderness Slayer: options for this server

This tables the Horror from the Deep work for now and covers what "wilderness slayer" could mean for
this project, what's already built, what the real OSRS feature actually is, and the paths forward with
their tradeoffs. Nothing here has been implemented — this is a decision document.

## The core tension up front

"Wilderness Slayer" as most people mean it — Krystilia, a dedicated slayer master standing in the
Edgeville jail who assigns wilderness-only tasks for points and unique drops — is not 2006 content. She
was released as a plain NPC on 11 July 2013 and only became a functioning slayer master on 13 April
2017, more than a decade after this server's January 2006 cutoff. So the first real decision isn't a
technical one, it's scope: does "wilderness slayer" for this project mean *the wilderness-located
monsters that 2006's five real slayer masters already assign* (which is period-accurate and, per the
audit below, already partly built), or does it mean *building Krystilia's actual system* as a deliberate
piece of bonus content that knowingly breaks the project's own accuracy premise? Both are legitimate
things a private server can do; they're just different projects with very different amounts of work.

## What already exists in this codebase today

The audit below is current as of this session, from `content/scripts/skill_slayer/` and
`content/scripts/areas/area_wilderness/`.

### The five real 2006-era slayer masters

Exactly the classic five exist, no more and no less: Turael (Burthorpe, no requirements), Mazchna
(Canifis, combat 20), Vannaka (under Edgeville, combat 40), Chaeldar (Zanaris, combat 70), and Duradel
(Shilo Village, combat 100 + 50 Slayer). Their task pools live in `configs/slayer_master_tasks.dbrow`
(which tasks each master can assign) and `configs/slayer_tasks.dbrow` (weight/min-kills/max-kills per
task, ~157 entries total across all five). No Krystilia, no Nieve/Steve, no Konar, no post-2011 master
of any kind exists anywhere in the tree — consistent with the project's stated era.

### Wilderness monsters already assignable, right now, through those five masters

This is the part worth sitting with: 2006's real slayer masters already send players into the
Wilderness for certain tasks, and that assignment logic is already built and enabled in this codebase.
Specifically:

- **Green dragons** — Vannaka only (weight 6, 40–80 kill count). Not offered by Chaeldar or Duradel in
  this implementation.
- **Black demons** — Chaeldar (weight 10, 110–170) and Duradel (weight 8, 130–200). Note black demons
  also spawn in Brimhaven Dungeon in this era, so the task isn't wilderness-exclusive, but wilderness
  black demons are a legitimate way to complete it.
- **Black dragons** — Duradel only (weight 9, 10–20 — a much lower kill-count range than the bulk
  tasks, more boss-hunt than grind).
- **Earth Warriors** (the classic wilderness dungeon monster) — Mazchna and Vannaka.

All four are currently enabled and assignable with no wilderness-specific restriction or bonus logic —
they're just tasks that happen to send a player into the wilderness, exactly as they did in real 2006
OSRS. This is, in the strictest sense, already "wilderness slayer" for this project's target era.

### What's conspicuously NOT in the task pools

Ankou, Dark Warriors, Bandits/Rogues/Highwaymen, Chaos Druids, Spiritual creatures, Lava dragons, and
Mammoths are not wired into any of the five masters' task tables, even though several of them are
period-appropriate 2006 wilderness monsters and one (Chaos Druid) already has full combat AI built in
this codebase (`content/scripts/npc/scripts/chaos_druid.rs2` — bind spell, confuse debuff, freeze-on-hit
— it's combat-ready, just not currently a slayer target). Revenants are correctly absent everywhere:
they didn't exist until 2008, so their absence is accurate, not a gap. A `highwayman.rs2` combat AI file
also exists but isn't wired into slayer either.

### The wilderness substrate already built

Separately from slayer, `area_wilderness/` already has a fair amount of infrastructure a wilderness
slayer feature (of either flavor) would lean on: wilderness-level detection (`wilderness_level()`,
computed from z-coordinate, one level per 8 tiles), a `%wilderness` zone flag set on entry/exit, the
full six-obelisk random-teleport network, King Black Dragon as a complete wilderness boss encounter,
Bandit Camp NPCs, the Lava Maze treasure chest, wilderness interface overlays, and a full PK skull
system (`skill_combat/scripts/pvp/pk_skull.rs2`) plus a parallel PvP combat stack (melee/ranged/magic/
specials, all separate from the PvE combat files). What's *not* there: any multi-combat-zone scripting
authored in these files (multi-combat is presumably inherited passively from the original 377 map
cache's per-square flags rather than scripted here), any slayer-points variable or reward shop, any
risk-based bonus loot table, and no dedicated wilderness slayer master NPC or dialogue at all. The only
"rewards" economy in Slayer right now is the flat, always-available Slayer Equipment shop (gem, mirror
shield, leaf-bladed spear, broad arrows, rock hammer, facemask, earmuffs, etc.) — no points gate it,
which is itself period-accurate, since OSRS's Slayer Reward Points system didn't launch until 2011.

## What the real Wilderness Slayer (Krystilia) actually is, for reference

For comparison, since the ask was to include everything:

**Who and where.** Krystilia — "a witch who likes chaos, she looks dangerous" — stands in the Edgeville
jail, northeast of the bank. Reachable by fairy ring, amulet of glory, or Paddewwa teleport; players can
also pay 5,000,000gp to set their respawn point to Edgeville for faster re-entry after dying.

**Requirements.** Just level 1 Slayer (trivial to get). She'll assign literally any monster on her list
regardless of the player's combat level — there's no combat-level gating the way Mazchna/Vannaka/
Chaeldar/Duradel have. A player can only hold one task at a time between her and the regular masters —
taking a Turael task cancels a wilderness streak in progress.

**The catch that defines the whole system.** Only kills that happen while the player is physically
standing in the Wilderness count toward the task. This is what makes it a genuinely different kind of
slayer task rather than just "some of the monsters happen to be up north" — the entire point is forcing
extended, repeated time-at-risk in a PvP-enabled zone, since every kill is a kill made while skullable
and visible to other players hunting slayer-task PKs.

**Points economy.** No points at all for the first four tasks (a soft anti-farming ramp); from the 5th
task onward, 25 points per task, with milestone bonuses at 10th (125), 50th (375), 100th (625), 250th
(875), and 1,000th (1,250) tasks. Blocking an unwanted task costs 100 points. Points spend in a
dedicated Wilderness Slayer rewards shop (separate from the regular Slayer Equipment shop) — full
pricing wasn't something I could pull completely from the wiki source this pass, but the shop is
real and distinct.

**Unique mechanics and drops.** Wilderness-slayer kills have their own chance at Larran's key (opens
Larran's chest, a wilderness-exclusive loot table) and at "Slayer's enchantment," on top of whatever
that monster's normal drop table gives. The task list itself is large — 40+ monster types including
abyssal demons, dust devils, greater demons, lava dragons, and the Wilderness God Wars Dungeon bosses —
several gated behind quests (Priest in Peril, Desert Treasure I, Death Plateau) or skill levels up to 85
Slayer, with the God Wars Dungeon tasks additionally requiring 60 Agility or 60 Strength to reach.

None of this — the NPC, the points, the shop, the unique drops, the "only wilderness kills count"
rule — has any equivalent in a 2006 client.

## Options

**Option A — Do nothing further; this is already "done."** The four wilderness-flagged tasks
(green dragons, black demons, black dragons, earth warriors) that Vannaka/Chaeldar/Duradel/Mazchna
already assign, exactly as they did in 2006, already constitute this server's wilderness slayer content.
Zero additional work, zero accuracy risk, nothing to design. The tradeoff is that it's a thin feature —
four tasks out of ~157, no wilderness-specific identity, nothing that reads as "wilderness slayer" to a
player the way it would on live OSRS even in 2006.

**Option B — Broaden the existing masters' wilderness task pool, still period-accurate.** Add
wilderness monsters that were plausibly assignable by the real 2006 masters but aren't currently wired
in — Chaos Druids (combat AI already built), Ankou, Dark Warriors, Bandits/Rogues — as new entries in
`slayer_tasks.dbrow`/`slayer_master_tasks.dbrow` under whichever of the five masters actually offered
them historically. This stays inside the project's own accuracy premise, but it needs the same
discipline as the rest of this project: each addition should be checked against a real 2006-era task-
list source (the OSRS wiki's task tables usually note when a task was added) before assuming it belongs,
rather than added because it "feels right" for a wilderness monster to be a slayer target. Moderate
work, low risk, and it's the option that most directly answers "give players more to do in the
wilderness via slayer" without leaving the 2006 target.

**Option C — Build Krystilia and the real Wilderness Slayer system as deliberate bonus content.** This
means an NPC, a full task table (40+ entries with their weights and quest/level gates), the points
economy, the separate rewards shop, the "only wilderness kills count" tracking, and the Larran's key/
Slayer's enchantment unique drops. It's a real, substantial feature — probably comparable in scope to
the Dagannoth Kings/Horror from the Deep build already underway — and it explicitly is not 2006 content,
so it would need to be framed to players as an intentional addition rather than presented as authentic,
the same way this project has been careful to exclude other post-2006 changes elsewhere. The wilderness
substrate already built (zone detection, skull system, PvP stack, obelisks) covers a real chunk of the
groundwork; what's missing is entirely new: the master, the task/points/shop data, and the unique loot.

**Option D — A custom wilderness bounty/task system, not a recreation of Krystilia.** Same spirit as
Option C (more reason to fight in the wilderness, task-driven), but built as the server's own thing
rather than an attempt to reproduce a specific 2013–2017 Jagex feature stage-for-stage — e.g., a
wilderness-only bonus applied to tasks already assignable by the real five masters when completed at
risk, rather than a whole separate master and points shop. Less work than Option C, doesn't claim
authenticity it doesn't have, but is a bigger design commitment than Option B since it's inventing new
server-specific mechanics rather than just re-enabling more of the real 2006 task list.

## Where this leaves it

Options A and B stay inside the project's own stated premise and are the lower-risk, lower-effort paths;
A needs nothing, B is a bounded content pass using assets (Chaos Druid AI, the wilderness zone/skull
substrate) that already exist. Options C and D are both real feature builds on the order of a boss/quest
addition, and both require an explicit decision to add non-2006 (or invented) content on purpose — worth
being deliberate about given how much of this project's effort elsewhere has gone into excluding exactly
that kind of anachronism. Happy to scope any of the four in more detail, or start on B or C, once you've
picked a direction.
