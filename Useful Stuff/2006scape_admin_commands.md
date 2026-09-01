# 2006Scape staff/admin chat commands

Read directly from `engine/src/network/game/client/handler/ClientCheatHandler.ts`. Your account is
`staffModLevel = 3`, and your server's `engine/.env` has `NODE_PRODUCTION=true` — so the commands
below marked "prod-gated" are available to you, but the developer-only tier (which requires
`NODE_PRODUCTION=false`, i.e. a non-production dev environment) is **not**, regardless of staff
level, since your server is configured as production.

All commands are typed in the chat box prefixed with `::`.

## Available to you (staffModLevel ≥ 2, "super-mod" tier)

- `::getcoord` — prints your current coordinate as `level,mx,mz,lx,lz`.
- `::tele <level,mx,mz[,lx,lz]>` — teleports you to that coordinate. Level 0–3, mx/mz 0–255, lx/lz
  0–63 (defaults to 32,32 if omitted).
- `::teleto <username>` — teleports you to another online player. *(prod-gated, available)*
- `::setvis <0|1|2>` — sets your visibility (0 = default/visible, 1 = soft mod-invisible, 2 = hard
  invisible). *(prod-gated, available)*
- `::ban <username> <minutes>` — bans a player for N minutes. *(prod-gated, available)*
- `::mute <username> <minutes>` — mutes a player for N minutes. *(prod-gated, available)*
- `::kick <username>` — disconnects a player immediately. *(prod-gated, available)*

## Available to you (staffModLevel ≥ 3, "admin" tier)

- `::setvar <varp-or-varbit-name> <value>` — sets a player variable or varbit by its debug name to
  an integer value. This is the command we used for `::setvar biohazard 16` / `::setvar upass 10` /
  `::setvar ibanmulti 2048`.
- `::setvarother <username> <name> <value>` — same, but on another online player. *(prod-gated)*
- `::getvar <name>` — prints the current value of a varp/varbit.
- `::getvarother <username> <name>` — same, on another player. *(prod-gated)*
- `::give <item> [amount]` — adds item(s) to your own inventory. `<item>` is the item's **technical
  name** (not its display name) — see the item list below. Amount defaults to 1.
- `::giveother <username> <item> [amount]` — same, to another player's inventory. *(prod-gated)*
- `::givecrap` — fills your inventory with 28 random (non-members-only-if-not-members, non-dummy,
  non-cert) items. Undocumented exact original behavior, implemented best-guess.
- `::givemany <item>` — gives you 1000 of an item.
- `::broadcast <message>` — sends a server-wide broadcast message. *(prod-gated)*
- `::reboot` — shuts the world down for a reboot immediately. *(prod-gated)*
- `::slowreboot <seconds>` — same, but with a countdown timer. *(prod-gated)*
- `::serverdrop` — forcibly disconnects your own client (for testing reconnect behavior).
- `::teleother <username>` — teleports another player to your location. *(prod-gated)*
- `::setstat <skill> <level>` — sets a skill to an exact level, no XP-drop message.
- `::advancestat <skill> <level>` — sets a skill's level via XP gain, triggering the normal
  level-up message/effects.
- `::minme` — sets all your stats to level 1 (10 HP).
- `::locadd <locname>` — spawns a temporary loc (technical name) at your position (despawns after
  ~500 ticks/5 min).
- `::npcadd <npcname>` — spawns a temporary NPC (technical name) at your position (despawns after
  ~500 ticks/5 min).
- `::openmain <interfacename>` — opens a main-screen interface component by its technical name.
- `::openoverlay <interfacename>` — opens an overlay interface component.
- `::closeoverlay` — closes your current overlay.
- `::snapshot` — writes a V8 heap snapshot to disk (server-side debugging, not gameplay-relevant).

## NOT available to you (requires a non-production dev environment, `staffModLevel ≥ 4`)

These exist in the code but are gated behind `!Environment.NODE_PRODUCTION`, which is false on your
server (since `NODE_PRODUCTION=true` is set) — so they won't fire no matter your staff level:

- `::reload` — reloads the world.
- `::rebuild` — rebuilds/repacks scripts without a full restart.
- `::speed <ms>` — changes the world tick rate.
- `::fly` — toggles a no-clip/flying movement mode.
- `::naive` — toggles a "naive" pathfinding movement mode.
- `::random` — forces an AFK/random event to become ready.
- `::<debugprocname> [args...]` — runs any `[debugproc,name]` script directly with typed arguments
  (int/string/obj/npc/loc/seq/stat/inv/coord/interface/spotanim/idkit).

If you ever want these (handy for content debugging), you'd set `NODE_PRODUCTION=false` in
`engine/.env` and restart — worth knowing that flipping it also re-gates the several `staffModLevel
≥ 2/3` commands marked "prod-gated" above the other way (they'd stop working while it's false).
