package jagex2.client;
import jagex2.io.Packet;
import java.nio.file.*;
// Decodes a REBUILD_REGION body exactly as Client.java ptype 53 does (same Packet methods, same order).
public class RegionDecode {
    public static void main(String[] a) throws Exception {
        byte[] b = Files.readAllBytes(Paths.get(a[0]));
        Packet in = new Packet(b);
        int zoneX = in.g2_alt2();
        in.accessBits();
        int n = 0;
        for (int lv = 0; lv < 4; lv++) for (int x = 0; x < 13; x++) for (int z = 0; z < 13; z++) {
            if (in.gBit(1) == 1) {
                int v = in.gBit(26);
                System.out.println("lv" + lv + " x" + x + " z" + z + " srcLevel=" + (v >> 24 & 3) + " srcZoneX=" + (v >> 14 & 0x3FF) + " srcZoneZ=" + (v >> 3 & 0x7FF) + " rot=" + (v >> 1 & 3));
                n++;
            }
        }
        in.accessBytes();
        int zoneZ = in.g2_alt2();
        System.out.println("zoneX=" + zoneX + " zoneZ=" + zoneZ + " templates=" + n + " consumed=" + in.pos + "/" + b.length);
    }
}
