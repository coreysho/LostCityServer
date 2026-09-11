
import java.util.*;
import jagex2.client.GameShell;
import jagex2.client.GroundItemPrefs;

/**
 * Harness for Client.drawGroundItems(). The method body below is extracted verbatim from
 * Client.java at test-build time - NOT retyped - so this exercises the shipped source text.
 * Everything it touches (projection, fonts, the obj cache, the player) is stubbed so the merge,
 * value and layout logic can be run headless.
 */
/** Stands in for GameShell, which the extracted code reaches through `super`. */
class Shell {
	int[] actionKey = new int[128];
	int mouseClickX, mouseClickY;
}

public class GroundItemsTest extends Shell {

	// ---- stubs -------------------------------------------------------------------------------
	static class ObjType {
		String field811; int field827; boolean field853;
		static Map<Integer, ObjType> table = new HashMap<>();
		static int getCalls;
		static ObjType get(int id) { getCalls++; return table.get(id); }
	}
	static class ClientObj { int field873, field875; }
	static class LinkList {
		List<ClientObj> items = new ArrayList<>();
		int cursor;
		ClientObj tail() { if (items.isEmpty()) { return null; } cursor = items.size() - 2; return items.get(items.size() - 1); }
		ClientObj prev() { if (cursor < 0) { return null; } return items.get(cursor--); }
	}
	static class ClientPlayer { int field1157, field1158; }
	static class Font {
		int height = 11;
		// Every glyph 5px wide keeps the expected layout arithmetic doable by hand in the assertions.
		int stringWid(String s) { return s == null ? 0 : s.length() * 5; }
		void centreString(int x, int y, int colour, String s) { drawn.add(x + "," + y + "," + Integer.toHexString(colour) + "," + s); }
		void drawString(int x, int colour, int y, String s) { pieces.add(x + "," + y + "," + Integer.toHexString(colour) + "," + s); }
	}
	static List<String> drawn = new ArrayList<>();
	static List<String> pieces = new ArrayList<>();   // drawString calls, used by the Alt layout
	static List<String> messages = new ArrayList<>();
	void addMessage(String from, String text, int type) { messages.add(text); }

	static ClientPlayer localPlayer;
	LinkList[][][] objStacks = new LinkList[4][104][104];
	int currentLevel;
	int projectX, projectY;
	Font fontPlain11 = new Font();
	// Flat-on view from straight above, centred on the player: a tile n east of him lands n*4 px
	// right of screen centre. Relative, not absolute, so a tile at the edge of the 104x104 map does
	// not land outside the viewport and get culled by the guard under test.
	void projectFromGround(int x, int height, int z) {
		projectX = ((x >> 7) - (localPlayer.field1157 >> 7)) * 4 + 256;
		projectY = ((z >> 7) - (localPlayer.field1158 >> 7)) * 4 + 167 - (height / 8);
	}
	static String formatObjCount(int n) { return n < 100000 ? String.valueOf(n) : (n < 10000000 ? (n / 1000) + "K" : (n / 1000000) + "M"); }

	// ---- the code under test (extracted from Client.java) -------------------------------------
__BODY__

	// ---- fixtures ----------------------------------------------------------------------------
	static void obj(int id, String name, int cost, boolean stackable) {
		ObjType t = new ObjType(); t.field811 = name; t.field827 = cost; t.field853 = stackable;
		ObjType.table.put(id, t);
	}
	void put(int x, int z, int id, int count) {
		if (objStacks[currentLevel][x][z] == null) { objStacks[currentLevel][x][z] = new LinkList(); }
		ClientObj o = new ClientObj(); o.field873 = id; o.field875 = count;
		objStacks[currentLevel][x][z].items.add(o);
	}
	static int fails;
	static void check(boolean ok, String what) {
		System.out.println((ok ? "  ok   " : "  FAIL ") + what);
		if (!ok) { fails++; }
	}
	static GroundItemsTest fresh(int px, int pz) {
		GroundItemsTest c = new GroundItemsTest();
		localPlayer = new ClientPlayer();
		localPlayer.field1157 = (px << 7) + 64;
		localPlayer.field1158 = (pz << 7) + 64;
		drawn.clear();
		pieces.clear();
		messages.clear();
		ObjType.getCalls = 0;
		return c;
	}

	static void wipePrefs() {
		new java.io.File(sign.signlink.findcachedir() + "qol_grounditems.dat").delete();
		GroundItemPrefs.load();
	}

	public static void main(String[] args) {
		wipePrefs();
		obj(526, "Bones", 1, false);
		obj(995, "Coins", 1, true);
		obj(1050, "Santa hat", 12000000, false);
		obj(561, "Nature rune", 200, true);
		obj(999, null, 5, false);          // a type with no name at all
		obj(4151, "Abyssal whip", 1500000, false);

		System.out.println("merge duplicate stacks of the same id");
		GroundItemsTest c = fresh(50, 50);
		c.put(50, 50, 526, 1); c.put(50, 50, 526, 1); c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2, "three sets of bones -> one row (shadow + text = 2 draws), got " + drawn.size());
		check(drawn.get(1).endsWith("Bones x 3"), "merged label, got " + drawn.get(1));

		System.out.println("distinct ids each get a row, stacked upward, bottom row on the tile");
		c = fresh(50, 50);
		c.put(50, 50, 526, 1); c.put(50, 50, 995, 100); c.put(50, 50, 561, 5);
		c.drawGroundItems();
		check(drawn.size() == 6, "three rows = 6 draws, got " + drawn.size());
		int[] ys = new int[3];
		for (int i = 0; i < 3; i++) { ys[i] = Integer.parseInt(drawn.get(i * 2 + 1).split(",")[1]); }
		check(ys[1] - ys[0] == 12 && ys[2] - ys[1] == 12, "rows 12px apart, got " + Arrays.toString(ys));
		check(ys[2] == 167 - 3, "last row sits on the tile (y=164), got " + ys[2]);

		System.out.println("value tiers");
		c = fresh(50, 50);
		c.put(50, 50, 1050, 1);   // 12,000,000 -> top tier
		c.put(51, 50, 4151, 1);   // 1,500,000  -> top tier
		c.put(52, 50, 561, 600);  // 120,000    -> second tier
		c.put(53, 50, 561, 60);   // 12,000     -> third tier
		c.put(54, 50, 561, 6);    // 1,200      -> fourth tier
		c.put(55, 50, 526, 1);    // 1          -> plain white
		c.drawGroundItems();
		String[] want = { "ff9040", "ff9040", "40c0ff", "40ff40", "ffff80", "ffffff" };
		for (int i = 0; i < want.length; i++) {
			String got = drawn.get(i * 2 + 1).split(",")[2];
			check(got.equals(want[i]), "tier " + i + " colour " + want[i] + ", got " + got);
		}

		System.out.println("stackable value is count x price; non-stackable is not");
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);
		// 60 sets of bones merge to one row of 60; bones are NOT stackable so value stays 1, white.
		for (int i = 0; i < 59; i++) { c.put(50, 50, 526, 1); }
		c.drawGroundItems();
		check(drawn.get(1).split(",")[2].equals("ffffff"), "60 bones still white, got " + drawn.get(1));
		check(drawn.get(1).endsWith("Bones x 60"), "merged to 60, got " + drawn.get(1));

		System.out.println("no int overflow on a huge stackable pile");
		c = fresh(50, 50);
		c.put(50, 50, 995, 60000); c.put(50, 50, 995, 60000);   // 120,000 coins
		obj(996, "Platinum token", 1000, true);
		c.put(51, 50, 996, 60000); c.put(51, 50, 996, 60000);   // 120,000 x 1000 = 120,000,000
		c.drawGroundItems();
		check(drawn.get(1).split(",")[2].equals("40c0ff"), "120k coins -> second tier, got " + drawn.get(1));
		check(drawn.get(3).split(",")[2].equals("ff9040"), "120m of tokens -> top tier (no overflow), got " + drawn.get(3));
		check(drawn.get(3).endsWith("x 120K"), "count abbreviated, got " + drawn.get(3));

		System.out.println("a nameless type is skipped without shifting the rows below it");
		c = fresh(50, 50);
		c.put(50, 50, 999, 1); c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2, "only the named row draws, got " + drawn.size());
		check(Integer.parseInt(drawn.get(1).split(",")[1]) == 167 - 3 - 12,
			"the unnamed entry keeps its (empty) slot rather than the column compacting, got " + drawn.get(1));

		System.out.println("radius and level");
		c = fresh(50, 50);
		c.put(50 + 12, 50, 526, 1);   // on the edge
		c.put(50 + 13, 50, 526, 1);   // one past it
		c.drawGroundItems();
		check(drawn.size() == 2, "12 tiles away draws, 13 does not; got " + drawn.size() / 2 + " rows");
		c = fresh(50, 50);
		c.currentLevel = 0; c.put(50, 50, 526, 1);
		c.currentLevel = 1;
		c.drawGroundItems();
		check(drawn.isEmpty(), "items on another level are not drawn");

		System.out.println("edge cases that must not throw");
		c = fresh(0, 0);   // corner of the map, radius clamps
		c.put(0, 0, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2, "map corner clamps and still draws, got " + drawn.size());
		c = fresh(103, 103);
		c.put(103, 103, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2, "far corner clamps and still draws, got " + drawn.size());
		c = fresh(50, 50);
		localPlayer = null;
		c.drawGroundItems();
		check(drawn.isEmpty(), "no local player -> nothing drawn, no NPE");

		System.out.println("per-tile and per-frame caps");
		c = fresh(50, 50);
		for (int i = 0; i < 12; i++) { obj(20000 + i, "Junk" + i, 1, false); c.put(50, 50, 20000 + i, 1); }
		c.drawGroundItems();
		check(drawn.size() == 8 * 2, "at most 8 distinct ids per tile, got " + drawn.size() / 2);
		c = fresh(50, 50);
		for (int t = 0; t < 20; t++) { for (int i = 0; i < 8; i++) { c.put(45 + t % 10, 45 + t / 10, 20000 + i, 1); } }
		c.drawGroundItems();
		check(drawn.size() / 2 <= 48 + 8, "frame cap holds near 48, got " + drawn.size() / 2);

		System.out.println("scratch arrays are not reused across tiles");
		c = fresh(50, 50);
		c.put(50, 50, 995, 7);
		c.put(51, 50, 995, 3);
		c.drawGroundItems();
		check(drawn.get(1).endsWith("Coins x 7") && drawn.get(3).endsWith("Coins x 3"),
			"counts do not leak between tiles, got " + drawn.get(1) + " / " + drawn.get(3));

		System.out.println("the radius comes from the player's settings");
		wipePrefs();
		c = fresh(50, 50);
		c.put(50 + 12, 50, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2, "default radius 12 still reaches 12 tiles, got " + drawn.size() / 2);
		for (int i = 0; i < 7 && GroundItemPrefs.radius() != 8; i++) { GroundItemPrefs.cycleRadius(); }
		check(GroundItemPrefs.radius() == 8, "cycled down to 8, got " + GroundItemPrefs.radius());
		c = fresh(50, 50);
		c.put(50 + 12, 50, 526, 1);
		c.put(50 + 8, 50, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2, "at radius 8 the tile 12 away is gone, the one at 8 is not; got " + drawn.size() / 2);
		wipePrefs();

		System.out.println("the value floor");
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);      // Bones, 1gp
		c.put(51, 50, 1050, 1);     // Santa hat, 12m
		c.drawGroundItems();
		check(drawn.size() == 4, "floor off: both labelled, got " + drawn.size() / 2);
		while (GroundItemPrefs.minValue() != 1000) { GroundItemPrefs.cycleMinValue(); }
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);
		c.put(51, 50, 1050, 1);
		c.drawGroundItems();
		check(drawn.size() == 2 && drawn.get(1).endsWith("Santa hat"),
			"at 1k only the santa hat is labelled, got " + drawn);
		wipePrefs();

		System.out.println("hiding and highlighting");
		c = fresh(50, 50);
		GroundItemPrefs.toggle("Bones", GroundItemPrefs.HIDE);
		c.put(50, 50, 526, 1);
		c.put(51, 50, 995, 5);
		c.drawGroundItems();
		check(drawn.size() == 2 && drawn.get(1).endsWith("Coins x 5"), "bones hidden, coins not; got " + drawn);
		check(GroundItemPrefs.isHidden("bones"), "matching is case-insensitive");
		c = fresh(50, 50);
		c.put(50, 50, 526, 60);
		c.drawGroundItems();
		check(drawn.isEmpty(), "a hidden item stays hidden as a stack of 60 - the rule is on the bare name");
		GroundItemPrefs.toggleShowHidden();
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(drawn.size() == 2 && drawn.get(1).split(",")[2].equals("707070"),
			"reveal shows it greyed rather than in its normal colour, got " + drawn);
		GroundItemPrefs.toggleShowHidden();
		wipePrefs();

		System.out.println("a highlight beats both the floor and the tiers");
		while (GroundItemPrefs.minValue() != 1000000) { GroundItemPrefs.cycleMinValue(); }
		GroundItemPrefs.toggle("Bones", GroundItemPrefs.HIGHLIGHT);
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);      // worth 1gp, floor is 1m
		c.drawGroundItems();
		check(drawn.size() == 2, "a highlighted item is drawn however worthless, got " + drawn.size() / 2);
		check(drawn.get(1).split(",")[2].equals("ff40ff"), "in the highlight colour, got " + drawn.get(1));
		wipePrefs();

		System.out.println("a skipped row keeps its slot so the column does not shift");
		GroundItemPrefs.toggle("Bones", GroundItemPrefs.HIDE);
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);
		c.put(50, 50, 995, 5);
		c.drawGroundItems();
		check(drawn.size() == 2, "only the coins draw, got " + drawn.size() / 2);
		int y = Integer.parseInt(drawn.get(1).split(",")[1]);
		c = fresh(50, 50);
		wipePrefs();
		c.put(50, 50, 526, 1);
		c.put(50, 50, 995, 5);
		c.drawGroundItems();
		int y2 = -1;
		for (int i = 1; i < drawn.size(); i += 2) {
			if (drawn.get(i).endsWith("Coins x 5")) { y2 = Integer.parseInt(drawn.get(i).split(",")[1]); }
		}
		check(y == y2, "the coins sit at the same height whether or not the bones are hidden, got " + y + " vs " + y2);

		System.out.println("holding Alt grows the controls onto every label");
		wipePrefs();
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(c.giZoneCount == 0 && pieces.isEmpty(), "no Alt, no controls and no click targets");
		c = fresh(50, 50);
		c.actionKey[GameShell.KEY_ALT] = 1;
		c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(c.giZoneCount == 1, "one click target per label, got " + c.giZoneCount);
		check(drawn.isEmpty() && pieces.size() == 6, "drawn as [-] [+] name with shadows, got " + pieces.size() + " pieces");
		check(c.giZoneName[0].equals("Bones"), "the target carries the BARE name, got " + c.giZoneName[0]);
		check(c.giZoneMinusX[0] < c.giZonePlusX[0] && c.giZonePlusX[0] < c.giZoneNameX[0]
				&& c.giZoneNameX[0] < c.giZoneNameEndX[0], "laid out left to right");
		int centre = (c.giZoneMinusX[0] + c.giZoneNameEndX[0]) / 2;
		check(Math.abs(centre - 256) <= 1, "the row stays centred on the tile as it grows, got " + centre);

		System.out.println("clicking the controls");
		c.mouseClickX = c.giZoneMinusX[0] + 4 + 4;      // +4 to undo QOL_PANEL_ORIGIN
		c.mouseClickY = c.giZoneTop[0] + 4 + 4;
		check(c.handleGroundItemClick(), "minus reports it consumed the click");
		check(GroundItemPrefs.isHidden("Bones"), "and hid the item");
		check(messages.size() == 1 && messages.get(0).contains("hidden"), "and said so, got " + messages);
		c.mouseClickX = c.giZonePlusX[0] + 4 + 4;
		messages.clear();
		check(c.handleGroundItemClick() && !GroundItemPrefs.isHidden("Bones"), "plus puts it back to normal");
		check(messages.size() == 1 && messages.get(0).contains("back to normal"), "and says so, got " + messages);
		c.mouseClickX = c.giZoneNameX[0] + 4 + 2;
		check(c.handleGroundItemClick() && GroundItemPrefs.isHighlighted("Bones"), "the name highlights");
		check(c.handleGroundItemClick() && !GroundItemPrefs.isHighlighted("Bones"), "and un-highlights");
		c.mouseClickX = c.giZoneNameEndX[0] + 4 + 40;
		check(!c.handleGroundItemClick(), "a click past the row is not consumed, so it still walks");
		c.mouseClickX = c.giZoneMinusX[0] + 4 + 4;
		c.mouseClickY = c.giZoneTop[0] + 4 - 20;
		check(!c.handleGroundItemClick(), "nor is one above the row");
		wipePrefs();

		System.out.println("Alt reveals hidden items so they have a [+] to click");
		GroundItemPrefs.toggle("Bones", GroundItemPrefs.HIDE);
		c = fresh(50, 50);
		c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(c.giZoneCount == 0 && drawn.isEmpty(), "hidden and no Alt: nothing at all");
		c = fresh(50, 50);
		c.actionKey[GameShell.KEY_ALT] = 1;
		c.put(50, 50, 526, 1);
		c.drawGroundItems();
		check(c.giZoneCount == 1, "with Alt held it comes back with a control, got " + c.giZoneCount);
		wipePrefs();

		System.out.println("double-tapping Alt toggles reveal; holding it does not");
		c = fresh(50, 50);
		check(!GroundItemPrefs.showHidden(), "starts off");
		c.actionKey[GameShell.KEY_ALT] = 1; c.updateAltState();
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();
		c.actionKey[GameShell.KEY_ALT] = 1; c.updateAltState();
		check(GroundItemPrefs.showHidden(), "two taps in quick succession turn it on");
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();
		c.actionKey[GameShell.KEY_ALT] = 1; c.updateAltState();
		check(GroundItemPrefs.showHidden(), "a third tap does not toggle it straight back off");
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();
		c.actionKey[GameShell.KEY_ALT] = 1; c.updateAltState();
		check(!GroundItemPrefs.showHidden(), "but the fourth, pairing with the third, does");
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();
		GroundItemPrefs.toggleShowHidden();
		GroundItemPrefs.toggleShowHidden();
		boolean before = GroundItemPrefs.showHidden();
		c.actionKey[GameShell.KEY_ALT] = 1;
		for (int i = 0; i < 50; i++) { c.updateAltState(); }   // an auto-repeating hold
		check(GroundItemPrefs.showHidden() == before,
			"holding Alt down does not read as a stream of taps - the edge is what counts");
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();
		try { Thread.sleep(450); } catch (Exception ignored) { }
		c.actionKey[GameShell.KEY_ALT] = 1; c.updateAltState();
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();
		try { Thread.sleep(450); } catch (Exception ignored) { }
		c.actionKey[GameShell.KEY_ALT] = 1; c.updateAltState();
		check(GroundItemPrefs.showHidden() == before, "two slow taps are two taps, not a double-tap");
		c.actionKey[GameShell.KEY_ALT] = 0; c.updateAltState();

		wipePrefs();
		System.out.println();
		System.out.println(fails == 0 ? "ALL PASS" : fails + " FAILED");
		if (fails != 0) { System.exit(1); }
	}
}
