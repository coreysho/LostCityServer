import java.io.*;
import java.util.*;
import jagex2.client.MenuSwaps;

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

	// ---- the code under test (extracted from Client.java) --------------------------------------
__BODY__

	// ---- helpers ------------------------------------------------------------------------------
	void menu(String... opts) {
		menuSize = 0;
		for (String o : opts) {
			menuOption[menuSize] = o;
			menuAction[menuSize] = 100 + menuSize;
			menuParamA[menuSize] = 1000 + menuSize;
			menuParamB[menuSize] = 2000 + menuSize;
			menuParamC[menuSize] = 3000 + menuSize;
			menuSize++;
		}
	}
	String top() { return menuOption[menuSize - 1]; }

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

		swapFile().delete();
		System.out.println();
		System.out.println(fails == 0 ? "ALL PASS" : fails + " FAILED");
		if (fails != 0) { System.exit(1); }
	}
}
