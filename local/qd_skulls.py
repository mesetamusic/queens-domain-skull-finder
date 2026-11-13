"""
Queen's Domain - Silver Skull checker (reads your save)

Reads every Silver Skull pickup straight out of the game's level files and checks
each one against your save, so you see exactly which skulls you still need, with
world coordinates and the nearest Crystal Monument.

    python qd_skulls.py            -> missing skulls only
    python qd_skulls.py --all      -> all 69 with status
    python qd_skulls.py --save "C:\\path\\to\\World0.sav"
    python qd_skulls.py --pak  "D:\\...\\QueensDomain-WindowsNoEditor.pak"

Read-only: it never writes to the save or the game files. The first run scans
the game's levels (around a minute) and caches the result in qd_skulls_cache.json
next to this script. Later runs are instant, and the cache rebuilds itself after
a game update.

How it works: each skull actor in a level has a GUID. When you pick a skull up,
the game writes that GUID into the save's SavableActorStates map. A skull whose
GUID is missing from that map hasn't been collected yet.
"""
import argparse, glob, json, math, os, struct, sys

DEFAULT_PAKS = [
    r"D:\SteamLibrary\steamapps\common\QueensDomain\QueensDomain\Content\Paks\QueensDomain-WindowsNoEditor.pak",
    r"C:\Program Files (x86)\Steam\steamapps\common\QueensDomain\QueensDomain\Content\Paks\QueensDomain-WindowsNoEditor.pak",
]
SAVE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "QueensDomain", "Saved", "SaveGames")
MAP_DIR = "RuinsLevel/Maps/"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qd_skulls_cache.json")
CACHE_VERSION = 3

AREAS = {
    "100_GR": "Isle of Neasied", "110_GR_dungeon": "Isle of Neasied", "130_GR_outerisles": "Isle of Neasied (outer isles)",
    "140_GR_ShopIsleOnly": "Umbada's Islet", "200_AQ": "Obmuer Temple", "210_AQ_underground": "Obmuer Temple (underground)",
    "300_LIB": "Tower of Knowledge", "310_LIB_exterior": "Tower of Knowledge (exterior)", "320_LIB_basement": "Tower of Knowledge (basement)",
    "400_MAUS_entrance": "Deimpo Mausoleum (entrance)", "420_MAUS_mid": "Deimpo Mausoleum", "450_MAUS_darkmaze": "Deimpo Mausoleum (dark maze)",
    "500_AUT": "Ancient World", "510_AUT_droptunnel": "Ancient World (drop tunnel)", "600_Castle": "Siraatsu Castle",
    "610_Castle_Ext": "Siraatsu Castle (exterior)", "700_SZ_GR": "Underworld (below Isle of Neasied)", "710_SZ_AQ": "Underworld (below Obmuer)",
    "720_SZ_LIB": "Underworld (below Tower)", "730_HOD": "Underworld (Halls of Darkness)", "740_SZ_Prison": "Forgotten Dungeon",
    "750_SZ_MAUS2": "Underworld (below Mausoleum)", "760_Dekanima": "Dekanima (off Record of Sin)", "760_SZ_AUT": "Record of Sin",
    "770_SZ_Swamp": "Rotting Cavern", "780_SZ_Depths": "Underworld (Depths)", "790_SG": "Petrified Garden", "800_FinalZone": "Final Zone",
}
# Classes that make poor landmarks
NOISE = ("Light", "FX", "Decal", "Spline", "JumpHelper", "Markup", "Volume", "Trigger", "Sound", "Audio",
         "Fog", "PostProcess", "Dust", "Water", "Blocker", "Camera", "Nav", "Deco_Rock", "Scrap", "Foliage")


# ---------------------------------------------------------------- binary helpers
class R:
    def __init__(s, b, o=0): s.b, s.o = b, o
    def i32(s): v = struct.unpack_from("<i", s.b, s.o)[0]; s.o += 4; return v
    def u32(s): v = struct.unpack_from("<I", s.b, s.o)[0]; s.o += 4; return v
    def u64(s): v = struct.unpack_from("<Q", s.b, s.o)[0]; s.o += 8; return v
    def raw(s, n): v = s.b[s.o:s.o + n]; s.o += n; return v
    def fstr(s):
        n = s.i32()
        if n == 0: return ""
        if n < 0: return s.raw(-n * 2).decode("utf-16-le")[:-1]
        return s.raw(n)[:-1].decode("latin-1")


# ---------------------------------------------------------------- .pak (UE4.27, v11, unencrypted, uncompressed)
class Pak:
    def __init__(s, path):
        s.f = f = open(path, "rb"); f.seek(0, 2); size = f.tell()
        f.seek(size - 300); tail = f.read(300)
        i = tail.find(struct.pack("<I", 0x5A6F12E1))
        if i < 0: sys.exit("That .pak file doesn't look like an Unreal pak.")
        if tail[i - 1]: sys.exit("The game's pak index is encrypted; this script can't read it.")
        off, sz = struct.unpack_from("<qq", tail, i + 8)
        f.seek(off); r = R(f.read(sz))
        mount = r.fstr(); r.i32(); r.u64()
        if r.u32(): r.raw(36)
        r.u32(); fdo, fds = struct.unpack("<qq", r.raw(16)); r.raw(20)
        s.enc = r.raw(r.i32())
        f.seek(fdo); d = R(f.read(fds)); s.files = {}
        for _ in range(d.i32()):
            dn = d.fstr()
            for _ in range(d.i32()):
                fn = d.fstr(); s.files[(mount + dn + fn).replace("../../../", "")] = d.i32()

    def read(s, name):
        e = R(s.enc, s.files[name]); v = e.u32()
        if (v & 0x3F) == 0x3F: e.u32()
        if (v >> 23) & 0x3F or (v >> 22) & 1: raise ValueError("compressed/encrypted entry: " + name)
        off = e.u32() if (v >> 31) & 1 else e.u64()
        size = e.u32() if (v >> 30) & 1 else e.u64()
        s.f.seek(off + 53); return s.f.read(size)


# ---------------------------------------------------------------- cooked .umap/.uexp
class Pkg:
    def __init__(s, ua, ue):
        r = R(ua); s.ue = ue
        r.u32(); r.i32(); r.i32(); r.i32(); r.i32()
        for _ in range(r.i32()): r.raw(20)
        s.hdr = r.i32(); r.fstr(); flags = r.u32()
        nc, no = r.i32(), r.i32()
        if not flags & 0x80000000: r.fstr()
        r.i32(); r.i32()
        ec, eo, ic, io = r.i32(), r.i32(), r.i32(), r.i32()
        r = R(ua, no); s.names = []
        for _ in range(nc): s.names.append(r.fstr()); r.raw(4)
        r = R(ua, io); s.imports = []
        for _ in range(ic):
            s.fn(r); s.fn(r); r.i32(); s.imports.append(s.fn(r))
        r = R(ua, eo); s.exports = []
        for _ in range(ec):
            ci = r.i32(); r.i32(); r.i32(); oi = r.i32(); on = s.fn(r); r.u32()
            sz, off = struct.unpack("<qq", r.raw(16)); r.raw(60)
            s.exports.append((ci, oi, on, sz, off))

    def fn(s, r):
        i, n = r.i32(), r.i32()
        return s.names[i] if n == 0 else f"{s.names[i]}_{n - 1}"

    def objname(s, i):
        return s.imports[-i - 1] if i < 0 else s.exports[i - 1][2] if i > 0 else ""

    def props(s, idx):
        _, _, _, sz, off = s.exports[idx]
        b = s.ue[off - s.hdr: off - s.hdr + sz]; r = R(b); out = {}
        while r.o < len(b) - 8:
            name = s.fn(r)
            if name == "None": break
            typ = s.fn(r); size = r.i32(); r.i32()
            if typ == "StructProperty": s.fn(r); r.raw(16)
            elif typ == "BoolProperty": r.raw(1)
            elif typ in ("ByteProperty", "EnumProperty", "ArrayProperty", "SetProperty"): s.fn(r)
            elif typ == "MapProperty": s.fn(r); s.fn(r)
            if r.raw(1)[0]: r.raw(16)
            out[name] = r.raw(size)
        return out

    def location(s, pr):
        if "RootComponent" not in pr: return None
        ri = struct.unpack("<i", pr["RootComponent"])[0]
        if ri <= 0: return None
        rp = s.props(ri - 1)
        return list(struct.unpack("<3f", rp["RelativeLocation"])) if "RelativeLocation" in rp else None


def nice(name):
    for suf in ("_BP_C", "_C"):
        if name.endswith(suf): name = name[: -len(suf)]; break
    for pre in ("OW_MK_", "OW_", "SG_", "FS_"):
        if name.startswith(pre): name = name[len(pre):]
    return name.replace("_", " ").strip()


def scan_levels(pak):
    skulls, monuments = [], []
    levels = sorted(k for k in pak.files if MAP_DIR in k and k.endswith(".umap"))
    for n, path in enumerate(levels, 1):
        ua = pak.read(path)
        has_skull = b"SkullKeyRelic" in ua
        if not has_skull and b"Checkpoint_C" not in ua: continue
        mapname = path.rsplit("/", 1)[1][:-5]
        print(f"  scanning {mapname} ({n}/{len(levels)})...", file=sys.stderr)
        p = Pkg(ua, pak.read(path[:-5] + ".uexp"))
        actors, found = [], []
        for i, (ci, oi, on, _, _) in enumerate(p.exports):
            cls = p.objname(ci)
            if oi == 0 or not cls.endswith("_C"): continue
            if not has_skull and cls != "Checkpoint_C": continue
            try:
                pr = p.props(i); loc = p.location(pr)
            except Exception:
                continue
            if loc is None: continue
            if cls == "SkullKeyRelic_BP_C" and "GUIDs" in pr:
                found.append(dict(map=mapname, actor=on, guid=pr["GUIDs"][-16:].hex(), loc=loc))
            elif cls == "Checkpoint_C":
                ld = struct.unpack("<i", pr["LocationData"])[0] if "LocationData" in pr else 0
                actors.append(("monument", p.objname(ld) or on, loc))
            elif not any(x in cls for x in NOISE):
                actors.append(("thing", nice(cls), loc))
        monuments += [(a[1], a[2], mapname[0]) for a in actors if a[0] == "monument"]
        for sk in found:
            near, seen = [], set()
            for d, nm in sorted((math.dist(a[2], sk["loc"]), a[1]) for a in actors if a[0] == "thing"):
                if d > 1500 or len(near) >= 4: break
                if nm not in seen: seen.add(nm); near.append(f"{nm} ({int(d)})")
            sk["near"] = near
            skulls.append(sk)
    # Sub-levels of one region (5xx = Ancient World, 6xx = Castle, 7xx = underworld...) share
    # coordinates; other regions can overlap in space, so only compare within the region.
    for sk in skulls:
        mons = sorted((math.dist(loc, sk["loc"]), nm) for nm, loc, reg in monuments if reg == sk["map"][0])
        sk["monument"] = [mons[0][1], int(mons[0][0])] if mons else None
    return skulls


def load_skulls(pak_path):
    st = os.stat(pak_path); key = f"{CACHE_VERSION}:{st.st_size}:{int(st.st_mtime)}"
    try:
        with open(CACHE) as fh:
            c = json.load(fh)
        if c.get("key") == key: return c["skulls"]
    except (OSError, ValueError):
        pass
    print("First run: reading skull locations from the game files...", file=sys.stderr)
    skulls = scan_levels(Pak(pak_path))
    with open(CACHE, "w") as fh:
        json.dump({"key": key, "skulls": skulls}, fh)
    return skulls


# ---------------------------------------------------------------- save (GVAS)
def read_save(path):
    sv = open(path, "rb").read()
    if sv[:4] != b"GVAS": sys.exit(f"{path} is not an Unreal save file.")
    key = b"SavableActorStates\0"; o = sv.find(key)
    if o < 0: sys.exit("Couldn't find SavableActorStates in the save - the format may have changed.")
    r = R(sv, o + len(key)); r.fstr(); r.raw(8); r.fstr(); r.fstr(); r.raw(1); r.i32()
    states = {}
    for _ in range(r.i32()):
        g = r.raw(16).hex(); states[g] = r.i32()

    def named_int(name):
        k = name.encode() + b"\0"; i = sv.find(struct.pack("<i", len(k)) + k)
        return struct.unpack_from("<i", sv, i + 4 + len(k))[0] if i >= 0 else None

    k = b"SkullKeyRelic_Data.SkullKeyRelic_Data\0"; i = sv.find(k)
    held = struct.unpack_from("<i", sv, i + len(k))[0] if i >= 0 else 0
    return states, named_int("SkullsTurnedIn"), held


def pick_save():
    cands = [p for p in glob.glob(os.path.join(SAVE_DIR, "*", "World*.sav")) if "backup" not in p.lower()]
    if not cands: sys.exit(f"No World*.sav found under {SAVE_DIR}. Use --save to point at your save.")
    return max(cands, key=os.path.getmtime)


def main():
    ap = argparse.ArgumentParser(description="Show which Silver Skulls you're missing in Queen's Domain.")
    ap.add_argument("--save", help="save file (default: most recently written World*.sav)")
    ap.add_argument("--pak", help="path to QueensDomain-WindowsNoEditor.pak")
    ap.add_argument("--all", action="store_true", help="list all skulls, not only missing ones")
    a = ap.parse_args()

    pak = a.pak or next((p for p in DEFAULT_PAKS if os.path.exists(p)), None)
    if not pak: sys.exit("Couldn't find the game's .pak file. Pass it with --pak.")
    save = a.save or pick_save()

    skulls = load_skulls(pak)
    states, turned_in, held = read_save(save)
    for s in skulls: s["have"] = s["guid"] in states
    missing = [s for s in skulls if not s["have"]]
    have = len(skulls) - len(missing)

    print(f"Save: {save}")
    print(f"Silver Skulls collected: {have}/{len(skulls)}"
          + (f"   (turned in at the skull door: {turned_in}, still carrying: {held})" if turned_in is not None else ""))
    if turned_in is not None and turned_in + held != have:
        print("  note: turned-in + carried doesn't match the pickup count; treat results with care.")
    print()

    shown = skulls if a.all else missing
    if not shown:
        if turned_in is not None and turned_in >= len(skulls):
            print("You have all of them, and all are turned in at the skull door. Nothing left to find!")
        else:
            print("You have all of them! Hand them in under the Petrified Garden for The Call From Beyond / Ending 4.")
        return
    print("MISSING:" if not a.all else "ALL SKULLS:")
    for s in sorted(shown, key=lambda s: (s["map"], s["actor"])):
        x, y, z = (int(v) for v in s["loc"])
        tag = "" if not a.all else ("[x] " if s["have"] else "[ ] ")
        print(f"  {tag}{AREAS.get(s['map'], s['map'])}  -  X {x}  Y {y}  Z {z}   ({s['map']} / {s['actor']})")
        if not a.all or not s["have"]:
            if s.get("monument"):
                print(f"       nearest Crystal Monument: {nice(s['monument'][0]).replace('Loc ', '')}  ({s['monument'][1]} units away)")
            if s.get("near"):
                print(f"       right next to: {', '.join(s['near'])}")
    print("\n(Distances are in Unreal units: 100 = 1 metre. Z is height.)")


if __name__ == "__main__":
    main()
