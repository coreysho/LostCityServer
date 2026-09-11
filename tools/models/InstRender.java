package jagex2.client;
import jagex2.config.*;
import jagex2.dash3d.*;
import jagex2.graphics.*;
import jagex2.io.*;
import java.nio.file.*; import java.util.*; import java.io.*;
import java.awt.image.BufferedImage; import javax.imageio.ImageIO;

// Offline render of an INSTANCED (REBUILD_REGION) scene with the real client code: the same
// method16 / method14 / method28 / method20 sequence Client.buildScene() runs when sceneInstanced.
// Written 2026-09-11 for the POH groundwork, to check template chunks and rotations before login.
//   java -cp <client classes>:. jagex2.client.InstRender <dir> <palette.txt> view...
// palette.txt: "destLevel destZoneX destZoneZ srcLevel srcTileX srcTileZ rot" per line (13x13 scene)
// view = name:tileX:tileZ:cameraHeight:yaw:pitch:topLevel:groundLevel (scene-local tiles)
public class InstRender {
    public static void main(String[] a) throws Exception {
        String dir = a[0];
        World.lowMem = false; World3D.lowMem = false; Pix3D.lowMem = false; LocType.lowMem = false;
        Jagfile cfg = new Jagfile(Files.readAllBytes(Paths.get(dir, "config.jag")));
        LocType.unpack(cfg); FloType.unpack(cfg); SeqType.unpack(cfg); VarbitType.unpack(cfg);
        Model.init(70000, null);
        for (String l : Files.readAllLines(Paths.get(dir, "models.txt"))) {
            String[] p = l.split(" ", 2);
            Model.method357(Files.readAllBytes(Paths.get(p[1])), Integer.parseInt(p[0]), (byte) 7);
        }
        sun.misc.Unsafe u; java.lang.reflect.Field f = sun.misc.Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); u = (sun.misc.Unsafe) f.get(null);
        Client c = (Client) u.allocateInstance(Client.class); c.varps = new int[4000];
        ClientLocAnim.varProvider = c;
        int W = 765, H = 503;
        int[] px = new int[W * H];
        Pix2D.bind(W, H, px);
        Pix3D.unpackTextures(new Jagfile(Files.readAllBytes(Paths.get(dir, "textures.jag"))));
        Pix3D.initColourTable(0.8D); Pix3D.initPool(20);
        Pix3D.init3D(H, W);
        int[] distance = new int[9];
        for (int x = 0; x < 9; x++) { int angle = x * 32 + 128 + 15; int offset = angle * 3 + 600; distance[x] = offset * Pix3D.sinTable[angle] >> 16; }
        World3D.init(H, distance, 800, 500, W);
        int[][][] heights = new int[4][105][105];
        byte[][][] flags = new byte[4][104][104];
        World3D scene = new World3D(heights, 104, 4, 104);
        CollisionMap[] col = new CollisionMap[4];
        for (int i = 0; i < 4; i++) col[i] = new CollisionMap(104, 104);
        World w = new World(heights, flags, 104, 104);
        int[][][] region = new int[4][13][13];
        for (int[][] r : region) for (int[] rr : r) Arrays.fill(rr, -1);
        for (String l : Files.readAllLines(Paths.get(a[1]))) {
            if (l.isBlank() || l.startsWith("#")) continue;
            String[] p = l.trim().split("\\s+");
            int dl = Integer.parseInt(p[0]), dx = Integer.parseInt(p[1]), dz = Integer.parseInt(p[2]);
            int sl = Integer.parseInt(p[3]), sx = Integer.parseInt(p[4]) >> 3, sz = Integer.parseInt(p[5]) >> 3, rot = Integer.parseInt(p[6]);
            region[dl][dx][dz] = (sl << 24) | (sx << 14) | (sz << 3) | (rot << 1);
        }
        java.util.function.Function<int[], byte[]> load = (k) -> {
            try { Path pp = Paths.get(dir, "maps", (k[0] / 8 >> 3) + "_" + (k[1] / 8 >> 3) + (k[2] == 0 ? ".land" : ".loc")); return Files.exists(pp) ? Files.readAllBytes(pp) : null; } catch (IOException e) { return null; }
        };
        for (int lv = 0; lv < 4; lv++) for (int x = 0; x < 13; x++) for (int z = 0; z < 13; z++) {
            int v = region[lv][x][z]; boolean done = false;
            if (v != -1) {
                int sl = v >> 24 & 3, rot = v >> 1 & 3, szx = v >> 14 & 0x3FF, szz = v >> 3 & 0x7FF;
                byte[] land = load.apply(new int[]{szx * 8, szz * 8, 0});
                if (land != null) { w.method16(rot, (szz & 7) * 8, land, lv, sl, x * 8, col, z * 8, (szx & 7) * 8); done = true; }
            }
            if (!done) w.method14(lv, z * 8, x * 8);
        }
        for (int x = 0; x < 13; x++) for (int z = 0; z < 13; z++) if (region[0][x][z] == -1) w.method28(x * 8, z * 8, 8, 8);
        for (int lv = 0; lv < 4; lv++) for (int x = 0; x < 13; x++) for (int z = 0; z < 13; z++) {
            int v = region[lv][x][z];
            if (v == -1) continue;
            int sl = v >> 24 & 3, rot = v >> 1 & 3, szx = v >> 14 & 0x3FF, szz = v >> 3 & 0x7FF;
            byte[] loc = load.apply(new int[]{szx * 8, szz * 8, 1});
            if (loc != null) w.method20(lv, col, scene, loc, z * 8, rot, (szx & 7) * 8, x * 8, (szz & 7) * 8, sl);
        }
        w.method15(col, scene);
        scene.method275(0);
        // dump walk-blocked flags of level 0 as text, for comparison with the server-side copy
        try (PrintWriter pw = new PrintWriter(new File(dir, "inst_collision.txt"))) {
            for (int lv = 0; lv < 4; lv++) for (int x = 0; x < 104; x++) for (int z = 0; z < 104; z++) {
                int fl = col[lv].field1585[x][z];
                if (fl != 0) pw.println(lv + " " + x + " " + z + " " + fl);
            }
        }
        for (int i = 2; i < a.length; i++) {
            String[] v = a[i].split(":");
            int cx = Integer.parseInt(v[1]) * 128 + 64, cz = Integer.parseInt(v[2]) * 128 + 64;
            int lv = Integer.parseInt(v[7]);
            int ground = heights[lv][cx >> 7][cz >> 7];
            int cy = ground - Integer.parseInt(v[3]);
            Arrays.fill(px, 0);
            Pix3D.init3D(H, W);
            scene.draw(cx, Integer.parseInt(v[6]), cy, cz, Integer.parseInt(v[4]), Integer.parseInt(v[5]));
            BufferedImage img = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
            img.setRGB(0, 0, W, H, px, 0, W);
            ImageIO.write(img, "png", new File(dir, v[0] + ".png"));
            System.out.println("wrote " + v[0]);
        }
    }
}
