package jagex2.client;
import jagex2.config.*;
import jagex2.dash3d.*;
import jagex2.graphics.*;
import jagex2.io.*;
import java.nio.file.*; import java.util.*; import java.io.*;
import java.awt.image.BufferedImage; import javax.imageio.ImageIO;

// Offline scene render with the real client code (javaclient classes on the classpath): builds a
// 104x104 scene from packed map files and draws it with World3D, the way the client would, to PNGs.
// Written 2026-09-10 to check the imported Warriors' Guild before anyone logged in.
//
// dir must hold: config.jag and textures.jag (archives 2 and 6 of a client cache), models.txt
// ("<model id> <path to .ob2>" per line, from content/pack/model.pack), and maps/<mx>_<mz>.land /
// .loc (gunzipped map files from cache idx4, named by map square).
//   java -cp javaclient/build/classes/java/main:. jagex2.client.SceneRender <dir> <baseX> <baseZ> view...
// view = name:tileX:tileZ:cameraHeight:yaw:pitch:topLevel:groundLevel
//   yaw 0 = looking north, 1536 = looking east; pitch 128 (flat) .. 383 (straight down);
//   topLevel hides floors above it (0 = ground floor only, 3 = everything incl. roofs).
public class SceneRender {
    public static void main(String[] a) throws Exception {
        String dir = a[0];
        int baseX = Integer.parseInt(a[1]), baseZ = Integer.parseInt(a[2]);
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
        List<int[]> sq = new ArrayList<>();
        for (int mx = (baseX >> 6) - 1; mx <= (baseX + 104 >> 6); mx++) for (int mz = (baseZ >> 6) - 1; mz <= (baseZ + 104 >> 6); mz++) sq.add(new int[]{mx, mz});
        for (int[] s : sq) {
            Path p = Paths.get(dir, "maps", s[0] + "_" + s[1] + ".land");
            int ox = s[0] * 64 - baseX, oz = s[1] * 64 - baseZ;
            if (Files.exists(p)) w.method22(oz, baseZ, ox, Files.readAllBytes(p), baseX, col);
        }
        for (int[] s : sq) {
            Path p = Paths.get(dir, "maps", s[0] + "_" + s[1] + ".loc");
            int ox = s[0] * 64 - baseX, oz = s[1] * 64 - baseZ;
            if (Files.exists(p)) w.method27(oz, col, ox, scene, Files.readAllBytes(p));
        }
        w.method15(col, scene);
        scene.method275(0);
        for (int i = 3; i < a.length; i++) {
            String[] v = a[i].split(":");
            int cx = (Integer.parseInt(v[1]) - baseX) * 128 + 64, cz = (Integer.parseInt(v[2]) - baseZ) * 128 + 64;
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
