import java.io.*;
import java.util.*;
import jagex2.client.DevLog;
import jagex2.client.GroundItemPrefs;
import jagex2.client.MenuSwaps;
import jagex2.client.QolSettings;

/**
 * Harness for the left-click swapper.
 *
 * Two halves. MenuSwaps is exercised as the REAL compiled class, against the real swaps file,
 * because its whole job is surviving disk. Client.applyMenuSwap() is extracted verbatim from
 * Client.java at test-build time - NOT retyped - and run against stub menu arrays.
 */
public class MenuSwapTest {

	// ---- stub menu ----------------------------------------------------------------------------
	String[] menuOption = new String[500];
	int[] menuAction = new int[500];
	int[] menuParamA = new int[500];
	int[] menuParamB = new int[500];
	int[] menuParamC = new int[500];
	int menuSize;
	boolean menuSwapMode;
	int[] swapRowOp = new int[500];
	String[] swapRowKind = new String[500];
	String[] swapRowTarget = new String[500];
	String[] swapRowVerb = new String[500];
	int objSelected, spellSelected;
	static List<String> messages = new ArrayList<>();
	void addMessage(String from, String text, int type) { messages.add(text); }

	// ---- the code under test (extracted from Client.java) --------------------------------------
__BODY__

	// ---- helpers ------------------------------------------------------------------------------
	void menu(String... opts) {
		menuSize = 0;
		for (String o : opts) {
			menuOption[menuSize] = o;
			// 14 is what handleViewportOptions() gives the real Walk here entry; the swapper finds it
			// by action, not by name, so the fixture has to carry the same number.
			menuAction[menuSize] = o.startsWith("Walk here") ? 14 : 100 + menuSize;
			menuParamA[menuSize] = 1000 + menuSize;
			menuParamB[menuSize] = 2000 + menuSize;
			menuParamC[menuSize] = 3000 + menuSize;
			menuSize++;
		}
	}
	String top() { return menuOption[menuSize - 1]; }
	/** Index of the first swap-menu row whose text starts with this, or -1. */
	int row(String prefix) {
		for (int i = 0; i < menuSize; i++) {
			if (menuOption[i] != null && menuOption[i].startsWith(prefix)) { return i; }
		}
		return -1;
	}

	static int fails;
	static void check(boolean ok, String what) {
		System.out.println((ok ? "  ok   " : "  FAIL ") + what);
		if (!ok) { fails++; }
	}
	static File swapFile() {
		return new File(sign.signlink.findcachedir() + "qol_swaps.dat");
	}
	static void wipe() {
		swapFile().delete();
		MenuSwaps.load();
	}

	public static void main(String[] args) throws Exception {
		MenuSwapTest c = new MenuSwapTest();

		System.out.println("parsing a menu option into verb / kind / target");
		String npc = "Attack @yel@Guard@gr2@ (level-21)";
		int at = MenuSwaps.tagAt(npc);
		check(at == 7, "tag found at 7, got " + at);
		check(MenuSwaps.parseVerb(npc, at).equals("Attack"), "verb, got " + MenuSwaps.parseVerb(npc, at));
		check(MenuSwaps.parseKind(npc, at).equals("yel"), "kind, got " + MenuSwaps.parseKind(npc, at));
		check(MenuSwaps.parseTarget(npc, at).equals("Guard"),
			"target drops the colour tag AND the level suffix, got '" + MenuSwaps.parseTarget(npc, at) + "'");
		String obj = "Bury @lre@Bones";
		at = MenuSwaps.tagAt(obj);
		check(MenuSwaps.parseVerb(obj, at).equals("Bury") && MenuSwaps.parseTarget(obj, at).equals("Bones"),
			"ground obj parses, got " + MenuSwaps.parseVerb(obj, at) + "/" + MenuSwaps.parseTarget(obj, at));
		String use = "Use Knife with @lre@Logs";
		at = MenuSwaps.tagAt(use);
		check(MenuSwaps.parseVerb(use, at).equals("Use Knife with"), "multi-word verb survives, got " + MenuSwaps.parseVerb(use, at));
		check(MenuSwaps.tagAt("Cancel") == -1 && MenuSwaps.tagAt("Walk here") == -1,
			"options with no target report no tag");
		check(MenuSwaps.tagAt(null) == -1, "null option does not throw");
		check(MenuSwaps.tagAt("@yel@") == -1, "a bare tag with nothing after it is not a target");

		System.out.println("the level suffix is what makes a swap portable");
		String lvl2 = "Attack @yel@Goblin@gr2@ (level-2)";
		String lvl5 = "Attack @yel@Goblin@gre@ (level-5)";
		check(MenuSwaps.parseTarget(lvl2, MenuSwaps.tagAt(lvl2))
				.equals(MenuSwaps.parseTarget(lvl5, MenuSwaps.tagAt(lvl5))),
			"two levels of the same monster give the same target");

		System.out.println("storing swaps");
		wipe();
		check(MenuSwaps.count() == 0, "starts empty");
		check(MenuSwaps.add("yel", "Guard", "Attack"), "add");
		check(MenuSwaps.count() == 1 && MenuSwaps.verb(0).equals("Attack") && MenuSwaps.target(0).equals("Guard"),
			"stored, got " + MenuSwaps.verb(0) + "/" + MenuSwaps.target(0));
		MenuSwaps.add("yel", "Guard", "Pickpocket");
		check(MenuSwaps.count() == 1 && MenuSwaps.verb(0).equals("Pickpocket"),
			"same kind+target REPLACES rather than stacking a second rule, got " + MenuSwaps.count() + " rules");
		MenuSwaps.add("lre", "Guard", "Take");
		check(MenuSwaps.count() == 2, "same name, different kind, is a different swap");

		System.out.println("matching");
		wipe();
		MenuSwaps.add("yel", "Guard", "Attack");
		MenuSwaps.add("lre", MenuSwaps.ANY, "Bury");
		check(MenuSwaps.match("yel", "Guard", "Attack") == 0, "exact match");
		check(MenuSwaps.match("yel", "guard", "attack") == 0, "match ignores case");
		check(MenuSwaps.match("yel", "Goblin", "Attack") == -1, "wrong target does not match");
		check(MenuSwaps.match("cya", "Guard", "Attack") == -1, "wrong kind does not match");
		check(MenuSwaps.match("lre", "Big bones", "Bury") == 1, "wildcard matches any target of its kind");
		MenuSwaps.add("lre", "Bones", "Bury");
		check(MenuSwaps.match("lre", "Bones", "Bury") == 2, "an exact rule beats a wildcard for the same verb");

		System.out.println("cycling a swap: this target -> any -> gone");
		wipe();
		MenuSwaps.add("yel", "Guard", "Attack");
		MenuSwaps.cycle(0);
		check(MenuSwaps.count() == 1 && MenuSwaps.isAny(0), "first click widens it to any npc");
		MenuSwaps.cycle(0);
		check(MenuSwaps.count() == 0, "second click removes it");
		MenuSwaps.cycle(0);
		check(MenuSwaps.count() == 0, "cycling an index that is gone does not throw");

		System.out.println("the cap");
		wipe();
		for (int i = 0; i < MenuSwaps.MAX; i++) { MenuSwaps.add("yel", "npc" + i, "Attack"); }
		check(MenuSwaps.count() == MenuSwaps.MAX && MenuSwaps.full(), "fills to MAX, got " + MenuSwaps.count());
		check(!MenuSwaps.add("yel", "one more", "Attack"), "refuses the one past the cap");
		check(MenuSwaps.add("yel", "npc0", "Pickpocket"), "but still lets you change one you have");

		System.out.println("surviving disk");
		wipe();
		MenuSwaps.add("yel", "Guard", "Attack");
		MenuSwaps.add("lre", MenuSwaps.ANY, "Bury");
		MenuSwaps.load();
		check(MenuSwaps.count() == 2 && MenuSwaps.verb(0).equals("Attack") && MenuSwaps.isAny(1),
			"reloads from the file, got " + MenuSwaps.count() + " swaps");
		PrintWriter w = new PrintWriter(new FileWriter(swapFile()));
		w.println("version=1");
		w.println("yel|Guard|Attack");
		w.println("this line is nonsense");
		w.println("yel||Attack");
		w.println("|Guard|Attack");
		w.println("cya|Door|Open");
		w.close();
		MenuSwaps.load();
		check(MenuSwaps.count() == 2, "garbage lines are skipped, good ones still parse; got " + MenuSwaps.count());
		FileOutputStream fo = new FileOutputStream(swapFile());
		byte[] junk = new byte[4096];
		new Random(7).nextBytes(junk);
		fo.write(junk); fo.close();
		MenuSwaps.load();
		check(true, "a file of random bytes did not throw (" + MenuSwaps.count() + " swaps kept)");
		swapFile().delete();
		MenuSwaps.load();
		check(MenuSwaps.count() == 0, "no file at all means no swaps");

		System.out.println("applying the swap to a built menu");
		wipe();
		MenuSwaps.add("yel", "Guard", "Attack");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		int wantA = c.menuParamA[2], wantB = c.menuParamB[2], wantC = c.menuParamC[2], wantAct = c.menuAction[2];
		c.applyMenuSwap();
		check(c.top().startsWith("Attack"), "the chosen option is now the left-click, got " + c.top());
		check(c.menuAction[c.menuSize - 1] == wantAct && c.menuParamA[c.menuSize - 1] == wantA
				&& c.menuParamB[c.menuSize - 1] == wantB && c.menuParamC[c.menuSize - 1] == wantC,
			"its action and all three params moved with it");
		check(c.menuOption[2].startsWith("Talk-to"), "the displaced option took its place, not lost");
		check(c.menuOption[0].equals("Cancel"), "Cancel is still pinned at index 0");
		check(c.menuSize == 4, "nothing was added or dropped");

		System.out.println("when it must NOT act");
		c.menu("Cancel", "Walk here", "Attack @yel@Goblin@gr2@ (level-2)", "Talk-to @yel@Goblin@gr2@ (level-2)");
		c.applyMenuSwap();
		check(c.top().startsWith("Talk-to"), "no rule for this target, menu untouched, got " + c.top());
		wipe();
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().startsWith("Attack"), "no rules at all, menu untouched");
		MenuSwaps.add("yel", "Guard", "Attack");
		c.menu("Cancel", "Attack @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().startsWith("Attack") && c.menuSize == 2, "Cancel plus one option: nothing to choose between");
		c.menu();
		c.applyMenuSwap();
		check(c.menuSize == 0, "an empty menu does not throw");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Examine @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().startsWith("Attack"), "a rule promotes even past Examine, got " + c.top());

		System.out.println("already the default");
		wipe();
		MenuSwaps.add("yel", "Guard", "Talk-to");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().startsWith("Talk-to") && c.menuOption[2].startsWith("Attack"),
			"a rule naming what is already the left-click changes nothing");

		System.out.println("shift + right-click builds a menu of swaps, not actions");
		wipe();
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		check(c.buildSwapMenu(), "there is something swappable under the cursor");
		check(c.menuSwapMode, "swap mode is on");
		check(c.menuSize == 4, "Cancel, a walk-here row and one row per option (Walk here itself has no "
			+ "target of its own), got " + c.menuSize);
		check(c.menuOption[0].equals("Cancel"), "Cancel still at 0, got " + c.menuOption[0]);
		check(c.row("Left-click Attack") > 0, "row for Attack");
		check(c.row("Left-click Talk-to") > 0, "row for Talk-to");
		int attack = c.row("Left-click Attack");
		check(c.swapRowVerb[attack].equals("Attack") && c.swapRowTarget[attack].equals("Guard")
				&& c.swapRowKind[attack].equals("yel"),
			"the row carries what it would store, got " + c.swapRowVerb[attack] + "/" + c.swapRowTarget[attack]);
		check(c.swapRowVerb[0] == null, "Cancel's row stores nothing");
		check(c.menuOption[attack].indexOf("(level-21)") < 0, "the level suffix is not shown in the swap row");

		System.out.println("picking a row stores it and performs nothing");
		messages.clear();
		c.applySwapChoice(attack);
		check(MenuSwaps.count() == 1 && MenuSwaps.verb(0).equals("Attack") && MenuSwaps.target(0).equals("Guard"),
			"the swap was stored, got " + MenuSwaps.count());
		check(messages.size() == 1 && messages.get(0).contains("Attack"), "the player is told, got " + messages);
		messages.clear();
		c.applySwapChoice(0);
		check(MenuSwaps.count() == 1 && messages.isEmpty(), "Cancel does nothing");
		c.applySwapChoice(-1);
		c.applySwapChoice(99);
		check(MenuSwaps.count() == 1, "a click that missed does nothing and does not throw");

		System.out.println("a reset row appears only once a swap exists");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		c.buildSwapMenu();
		check(c.menuSize == 5, "the same rows plus a reset row, got " + c.menuSize);
		int reset = c.row("Reset left-click");
		check(reset == c.menuSize - 1, "reset row last, got index " + reset + " of " + c.menuSize);
		check(c.swapRowVerb[reset] == null, "a null verb marks the reset row");
		messages.clear();
		c.applySwapChoice(reset);
		check(MenuSwaps.count() == 0, "reset removed it");
		check(messages.size() == 1 && messages.get(0).contains("back to normal"), "and said so, got " + messages);
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)");
		c.buildSwapMenu();
		check(c.row("Reset left-click") < 0, "no swap stored, so no reset row");

		System.out.println("when shift + right-click should leave the menu alone");
		wipe();
		c.menu("Cancel", "Walk here");
		c.menuSwapMode = false;
		check(!c.buildSwapMenu(), "bare ground: nothing swappable");
		check(!c.menuSwapMode && c.menuSize == 2 && c.menuOption[1].equals("Walk here"),
			"the real menu is untouched, got " + c.menuSize + " entries");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)");
		c.objSelected = 1;
		c.menuSwapMode = false;
		check(!c.buildSwapMenu(), "not while an item is selected - the verb is a one-off, not a preference");
		check(c.menuOption[2].startsWith("Attack"), "and that menu is left alone too");
		c.objSelected = 0;
		c.spellSelected = 1;
		check(!c.buildSwapMenu(), "same for a selected spell");
		c.spellSelected = 0;

		System.out.println("duplicate options collapse to one row");
		wipe();
		c.menu("Cancel", "Take @lre@Bones", "Take @lre@Bones", "Examine @lre@Bones");
		c.buildSwapMenu();
		check(c.menuSize == 3, "two identical Take entries give one row, got " + c.menuSize);
		check(c.row("Left-click Walk here") < 0, "and no walk row: this menu has no Walk here entry");

		System.out.println("the cap is reported, not silently ignored");
		wipe();
		for (int i = 0; i < MenuSwaps.MAX; i++) { MenuSwaps.add("yel", "npc" + i, "Attack"); }
		c.menu("Cancel", "Attack @yel@Someone else@gr2@ (level-3)");
		c.buildSwapMenu();
		messages.clear();
		c.applySwapChoice(1);
		check(MenuSwaps.count() == MenuSwaps.MAX, "nothing was stored past the cap");
		check(messages.size() == 1 && messages.get(0).contains("F10"), "and the player is told how to fix it, got " + messages);

		System.out.println("Walk here: making a thing un-clickable");
		wipe();
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		c.buildSwapMenu();
		check(c.menuOption[1].startsWith("Left-click Walk here"),
			"a walk-here row is offered, at the bottom of the menu, got " + c.menuOption[1]);
		check(c.swapRowVerb[1].equals("Walk here") && c.swapRowTarget[1].equals("Guard"),
			"stored against the target, got " + c.swapRowVerb[1] + "/" + c.swapRowTarget[1]);
		check(c.menuSize == 4, "one walk row plus the two options, got " + c.menuSize);
		c.applySwapChoice(1);
		check(MenuSwaps.count() == 1 && MenuSwaps.verb(0).equals("Walk here"), "stored as a normal swap");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().equals("Walk here"),
			"left-clicking the Guard now walks instead of touching him, got " + c.top());
		check(c.menuAction[c.menuSize - 1] == 14, "and it is the real Walk here action, got " + c.menuAction[c.menuSize - 1]);
		check(c.menuOption[1].startsWith("Talk-to") || c.menuOption[2].startsWith("Talk-to"),
			"the options are all still in the menu for a right-click");

		System.out.println("walk-here competes on the same terms as any other rule");
		wipe();
		MenuSwaps.add("yel", MenuSwaps.ANY, "Walk here");   // catch-all: never touch npcs
		MenuSwaps.add("yel", "Guard", "Attack");            // except this one
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)", "Talk-to @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().startsWith("Attack"), "the named exception still wins over a walk-here catch-all, got " + c.top());
		c.menu("Cancel", "Walk here", "Attack @yel@Goblin@gr2@ (level-2)", "Talk-to @yel@Goblin@gr2@ (level-2)");
		c.applyMenuSwap();
		check(c.top().equals("Walk here"), "and applies to every other npc, got " + c.top());
		wipe();
		MenuSwaps.add("yel", "Guard", "Walk here");
		MenuSwaps.add("yel", MenuSwaps.ANY, "Attack");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().equals("Walk here"), "and the reverse: an exact walk-here beats an attack catch-all, got " + c.top());

		System.out.println("walk-here must work when the option is ALREADY the default");
		wipe();
		MenuSwaps.add("yel", "Guard", "Walk here");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().equals("Walk here"),
			"Attack was the left-click and had to be demoted, got " + c.top());

		System.out.println("a walk-here rule only fires for its own target");
		wipe();
		MenuSwaps.add("yel", "Guard", "Walk here");
		c.menu("Cancel", "Walk here", "Take @lre@Bones");
		c.applyMenuSwap();
		check(c.top().startsWith("Take"), "bones on the tile are still takeable, got " + c.top());
		c.menu("Cancel", "Walk here", "Take @lre@Bones", "Attack @yel@Guard@gr2@ (level-21)");
		c.applyMenuSwap();
		check(c.top().equals("Walk here"),
			"but a Guard standing on them makes the tile walk-only, got " + c.top());

		System.out.println("no Walk here entry, no walk-here row or rule");
		wipe();
		c.menu("Cancel", "Bury @lre@Bones", "Drop @lre@Bones");   // an inventory menu has no Walk here
		c.buildSwapMenu();
		check(c.menuSize == 3, "no walk row offered where walking is not an option, got " + c.menuSize);
		MenuSwaps.add("lre", "Bones", "Walk here");               // set anyway, by hand
		c.menu("Cancel", "Bury @lre@Bones", "Drop @lre@Bones");
		c.applyMenuSwap();
		check(c.top().startsWith("Drop"), "and a stale walk-here rule cannot promote what is not there, got " + c.top());

		System.out.println("a player on the tile already has a real Walk here option");
		wipe();
		c.menu("Cancel", "Walk here @whi@Zezima", "Trade with @whi@Zezima", "Follow @whi@Zezima");
		c.buildSwapMenu();
		int walkRows = 0;
		for (int i = 1; i < c.menuSize; i++) {
			if (c.menuOption[i].startsWith("Left-click Walk here")) { walkRows++; }
		}
		check(walkRows == 1, "exactly one walk-here row, not one from each path, got " + walkRows);

		System.out.println("wildcards across a whole kind");
		wipe();
		MenuSwaps.add("lre", MenuSwaps.ANY, "Bury");
		c.menu("Cancel", "Walk here", "Bury @lre@Big bones", "Take @lre@Big bones");
		c.applyMenuSwap();
		check(c.top().startsWith("Bury"), "wildcard promotes on a target never named, got " + c.top());
		c.menu("Cancel", "Walk here", "Bury @yel@Big bones", "Take @yel@Big bones");
		c.applyMenuSwap();
		check(c.top().startsWith("Take"), "wildcard does not leak into another kind");

		System.out.println("exact beats wildcard in a real menu");
		wipe();
		MenuSwaps.add("lre", MenuSwaps.ANY, "Bury");
		MenuSwaps.add("lre", "Zombie bones", "Take");
		c.menu("Cancel", "Walk here", "Bury @lre@Zombie bones", "Take @lre@Zombie bones", "Examine @lre@Zombie bones");
		c.applyMenuSwap();
		check(c.top().startsWith("Take"), "the named exception wins over the catch-all, got " + c.top());

		System.out.println("ground item rules ride the same menu");
		wipe();
		new File(sign.signlink.findcachedir() + "qol_grounditems.dat").delete();
		GroundItemPrefs.load();
		c.menu("Cancel", "Walk here", "Take @lre@Bones", "Bury @lre@Bones");
		c.buildSwapMenu();
		int hideRow = c.row("Hide ");
		int litRow = c.row("Highlight ");
		check(hideRow > 0 && litRow > 0, "a ground item offers Hide and Highlight");
		check(hideRow == c.menuSize - 2 && litRow == c.menuSize - 1,
			"grouped at the top of the menu, got " + hideRow + "/" + litRow + " of " + c.menuSize);
		messages.clear();
		c.applySwapChoice(hideRow);
		check(GroundItemPrefs.isHidden("Bones"), "the rule was stored");
		check(messages.size() == 1 && messages.get(0).contains("hidden"), "and the player is told, got " + messages);
		check(MenuSwaps.count() == 0, "and it did NOT become a left-click swap");
		c.menu("Cancel", "Walk here", "Take @lre@Bones", "Bury @lre@Bones");
		c.buildSwapMenu();
		check(c.row("Stop hiding ") > 0, "the row now offers to undo it");
		c.applySwapChoice(c.row("Stop hiding "));
		check(!GroundItemPrefs.isHidden("Bones"), "and undoes it");

		System.out.println("hide/highlight is offered only where it makes sense");
		c.menu("Cancel", "Bury @lre@Bones", "Drop @lre@Bones");   // inventory: no Walk here
		c.buildSwapMenu();
		check(c.row("Hide ") < 0,
			"an inventory menu gets no hide row - ground objs and inventory items share @lre@ and only "
			+ "the Walk here entry tells them apart");
		c.menu("Cancel", "Walk here", "Attack @yel@Guard@gr2@ (level-21)");
		c.buildSwapMenu();
		check(c.row("Hide ") < 0, "and an npc is not a ground item");

		System.out.println("hidden and highlighted are one rule, not two that disagree");
		new File(sign.signlink.findcachedir() + "qol_grounditems.dat").delete();
		GroundItemPrefs.load();
		c.menu("Cancel", "Walk here", "Take @lre@Bones");
		c.buildSwapMenu();
		c.applySwapChoice(c.row("Hide "));
		c.menu("Cancel", "Walk here", "Take @lre@Bones");
		c.buildSwapMenu();
		c.applySwapChoice(c.row("Highlight "));
		check(GroundItemPrefs.count() == 1 && GroundItemPrefs.isHighlighted("Bones")
				&& !GroundItemPrefs.isHidden("Bones"),
			"highlighting something hidden moves it, it does not add a second rule; got "
				+ GroundItemPrefs.count() + " rules");

		System.out.println("two stacks of the same item give one pair of rows");
		c.menu("Cancel", "Walk here", "Take @lre@Bones", "Bury @lre@Bones", "Take @lre@Coins");
		c.buildSwapMenu();
		int hides = 0;
		for (int i = 1; i < c.menuSize; i++) {
			if (c.menuOption[i].startsWith("Hide ") || c.menuOption[i].startsWith("Stop hiding ")) { hides++; }
		}
		check(hides == 2, "one hide row per distinct item, got " + hides);

		new File(sign.signlink.findcachedir() + "qol_grounditems.dat").delete();
		swapFile().delete();
		System.out.println();
		System.out.println(fails == 0 ? "ALL PASS" : fails + " FAILED");
		if (fails != 0) { System.exit(1); }
	}
}
