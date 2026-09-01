package jagex2.client;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.regex.Pattern;

// --- Dev client only (Corey, 2026-09-01) ---
// Logs every player interaction (menu actions/clicks, chat sent/received, login/logout) to both
// the console (System.out) and a plain-text log file (dev-client.log, written next to wherever the
// jar is run from, one line appended per event, flushed immediately). This class does not exist in
// the normal (non-dev) client build - it's only wired up in this javaclient-dev copy.
public final class DevLog {
	private static final SimpleDateFormat TIME_FORMAT = new SimpleDateFormat("HH:mm:ss.SSS");
	private static final Pattern TAG_PATTERN = Pattern.compile("@\\w+@");
	private static PrintWriter fileOut;

	static {
		PrintWriter writer;
		try {
			writer = new PrintWriter(new FileWriter("dev-client.log", true), true);
			writer.println();
			writer.println("=== dev client session started " + new Date() + " ===");
		} catch (IOException e) {
			writer = null;
			System.out.println("[DevLog] could not open dev-client.log for writing: " + e.getMessage());
		}
		fileOut = writer;
	}

	private DevLog() {
	}

	// Strips RS2's inline colour/format tags (e.g. "@whi@", "@gr2@") out of menu option text so log
	// lines stay readable, e.g. "Attack @whi@Goblin" -> "Attack Goblin".
	public static String stripTags(String text) {
		if (text == null) {
			return "";
		}
		return TAG_PATTERN.matcher(text).replaceAll("");
	}

	public static void log(String category, String detail) {
		String line = "[" + TIME_FORMAT.format(new Date()) + "] [" + category + "] " + detail;
		System.out.println(line);
		if (fileOut != null) {
			fileOut.println(line);
		}
	}
}
