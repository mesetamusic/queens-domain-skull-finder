"""
Queen's Domain Skull Finder - a small Windows app that reads your save and shows
which of the 69 Silver Skulls you still need, and where they are.

Read-only: it never modifies the game or your save.
"""
import os, queue, sys, threading, time, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import qdcore as core

APP_NAME = "Queen's Domain Skull Finder"
VERSION = "1.0"
WATCH_MS = 3000  # how often to look for a newer save while the game is running


class App:
    def __init__(self, root):
        self.root = root
        self.settings = core.load_settings()
        self.skulls = None
        self.save_path = None
        self.save_mtime = None
        # a save passed on the command line (or dragged onto the .exe) is used for this session
        args = [a for a in sys.argv[1:] if a.lower().endswith(".sav") and os.path.isfile(a)]
        self.once_save = args[0] if args else None
        self.q = queue.Queue()
        self.item_skull = {}

        root.title(APP_NAME)
        ico = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "skull.ico")
        try: root.iconbitmap(default=ico)
        except tk.TclError: pass
        root.geometry(self.settings.get("geometry", "1060x660"))
        root.minsize(760, 460)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.build_ui()
        root.after(100, self.start_load)
        root.after(100, self.pump)

    # ------------------------------------------------------------ UI
    def build_ui(self):
        st = ttk.Style()
        st.configure("Count.TLabel", font=("Segoe UI", 20, "bold"))
        st.configure("Sub.TLabel", foreground="#666")
        st.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        st.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        top = ttk.Frame(self.root, padding=(14, 12, 14, 6)); top.pack(fill="x")
        left = ttk.Frame(top); left.pack(side="left", fill="x", expand=True)
        self.count_lbl = ttk.Label(left, text="Loading...", style="Count.TLabel"); self.count_lbl.pack(anchor="w")
        self.bar = ttk.Progressbar(left, maximum=core.TOTAL_SKULLS, length=360); self.bar.pack(anchor="w", pady=(4, 2))
        self.sub_lbl = ttk.Label(left, text="", style="Sub.TLabel"); self.sub_lbl.pack(anchor="w")

        btns = ttk.Frame(top); btns.pack(side="right", anchor="n")
        ttk.Button(btns, text="Refresh", command=self.refresh).grid(row=0, column=0, padx=3, sticky="ew")
        ttk.Button(btns, text="Choose save...", command=self.choose_save).grid(row=0, column=1, padx=3, sticky="ew")
        ttk.Button(btns, text="Game folder...", command=self.choose_game).grid(row=0, column=2, padx=3, sticky="ew")
        self.show_all = tk.BooleanVar(value=self.settings.get("show_all", False))
        ttk.Checkbutton(btns, text="Show collected skulls too", variable=self.show_all,
                        command=self.populate).grid(row=1, column=0, columnspan=3, sticky="e", pady=(6, 0))

        pane = ttk.PanedWindow(self.root, orient="horizontal"); pane.pack(fill="both", expand=True, padx=14, pady=(4, 6))
        self.root.after(150, lambda: pane.sashpos(0, int(pane.winfo_width() * 0.6)))
        lf = ttk.Frame(pane); pane.add(lf, weight=3)
        self.tree = ttk.Treeview(lf, columns=("where",), selectmode="browse")
        self.tree.heading("#0", text="Area / skull", anchor="w"); self.tree.column("#0", width=230, stretch=False)
        self.tree.heading("where", text="Where to look", anchor="w"); self.tree.column("where", width=420)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True); sb.pack(side="left", fill="y")
        self.tree.tag_configure("area", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("have", foreground="#999")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        rf = ttk.Frame(pane, padding=(10, 0, 0, 0)); pane.add(rf, weight=2)
        self.detail_title = ttk.Label(rf, text="Select a skull", font=("Segoe UI", 12, "bold"), wraplength=360)
        self.detail_title.pack(anchor="w")
        self.detail = tk.Text(rf, wrap="word", height=10, relief="flat", font=("Segoe UI", 10),
                              background=self.root.cget("background"), padx=0, pady=8, cursor="arrow",
                              spacing1=2, spacing3=10, highlightthickness=0, borderwidth=0)
        self.detail.pack(fill="both", expand=True)
        self.detail.configure(state="disabled")
        self.copy_btn = ttk.Button(rf, text="Copy coordinates", command=self.copy_coords, state="disabled")
        self.copy_btn.pack(anchor="w", pady=(0, 4))

        foot = ttk.Frame(self.root, padding=(14, 0, 14, 8)); foot.pack(fill="x")
        self.status = ttk.Label(foot, text="", style="Sub.TLabel"); self.status.pack(side="left")
        ttk.Label(foot, text=f"v{VERSION} - read-only, never changes your save", style="Sub.TLabel").pack(side="right")

    def set_detail(self, title, lines):
        self.detail_title.configure(text=title)
        self.detail.configure(state="normal"); self.detail.delete("1.0", "end")
        self.detail.insert("1.0", "\n".join(lines)); self.detail.configure(state="disabled")

    # ------------------------------------------------------------ loading
    def start_load(self, rescan=False):
        pak = core.find_pak(self.settings)
        if not pak:
            self.count_lbl.configure(text="Game not found")
            self.sub_lbl.configure(text="Click \"Game folder...\" and pick your Queen's Domain install folder.")
            self.set_detail("Can't find Queen's Domain",
                            ["Skull Finder reads skull locations from the game's own files, but couldn't find the install.",
                             "Click \"Game folder...\" and select the QueensDomain folder (in Steam: right-click the game > "
                             "Manage > Browse local files)."])
            return
        self.status.configure(text="Reading skull locations from the game files...")
        self.count_lbl.configure(text="Loading...")
        if rescan:
            try: os.remove(core.CACHE_FILE)
            except OSError: pass

        def work():
            try:
                skulls = core.load_skulls(pak, progress=lambda n, t, m: self.q.put(("progress", f"Scanning levels... {n}/{t}")))
                self.q.put(("skulls", skulls))
            except core.QDError as e:
                self.q.put(("error", str(e)))
            except Exception:
                self.q.put(("error", "Couldn't read the game files.\n\n" + traceback.format_exc(limit=3)))
        threading.Thread(target=work, daemon=True).start()

    def pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "progress": self.status.configure(text=val)
                elif kind == "skulls":
                    self.skulls = val; self.status.configure(text="")
                    self.refresh(); self.root.after(WATCH_MS, self.watch)
                elif kind == "error":
                    self.count_lbl.configure(text="Something went wrong"); self.status.configure(text="")
                    messagebox.showerror(APP_NAME, val)
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def current_save(self):
        if self.once_save and os.path.isfile(self.once_save): return self.once_save
        fixed = self.settings.get("save")
        if fixed and os.path.isfile(fixed): return fixed
        saves = core.find_saves()
        return saves[0] if saves else None

    def refresh(self):
        if self.skulls is None: return
        path = self.current_save()
        if not path:
            self.count_lbl.configure(text="No save found")
            self.sub_lbl.configure(text=f"Looked in {core.SAVE_ROOT}. Use \"Choose save...\" to pick one.")
            return
        try:
            save = core.read_save(path)
        except PermissionError:
            self.status.configure(text="The game is writing the save - will retry in a moment."); return
        except core.QDError as e:
            messagebox.showerror(APP_NAME, f"{e}\n\n{path}"); return
        self.save_path, self.save_mtime = path, os.path.getmtime(path)
        missing = core.check(self.skulls, save)
        have = len(self.skulls) - len(missing)
        self.bar["maximum"] = len(self.skulls); self.bar["value"] = have
        if not missing:
            self.count_lbl.configure(text=f"All {len(self.skulls)} Silver Skulls found!")
        else:
            self.count_lbl.configure(text=f"{len(missing)} Silver Skull{'s' if len(missing) != 1 else ''} remaining"
                                          f"   ({have}/{len(self.skulls)} found)")
        extra = ""
        if save["turned_in"] is not None:
            extra = f"   |   Turned in at the skull door: {save['turned_in']}, carrying: {save['held']}"
        when = time.strftime("%b %d, %I:%M %p", time.localtime(self.save_mtime))
        self.sub_lbl.configure(text=f"Save: {os.path.basename(path)} (saved {when}){extra}")
        self.status.configure(text=f"Checked at {time.strftime('%I:%M:%S %p')} - updates automatically when the game saves.")
        self.populate()
        if not missing:
            done = save["turned_in"] is not None and save["turned_in"] >= len(self.skulls)
            self.set_detail("Nothing left to find!",
                            ["You've picked up every Silver Skull."] +
                            ([] if done else ["Turn them in at the skull door below the Petrified Garden for "
                                              "\"The Call From Beyond\" and Ending 4."]))

    def populate(self):
        if self.skulls is None: return
        self.settings["show_all"] = self.show_all.get()
        sel = self.tree.selection(); sel_guid = self.item_skull.get(sel[0], {}).get("guid") if sel else None
        self.tree.delete(*self.tree.get_children()); self.item_skull = {}
        order = []
        for s in sorted(self.skulls, key=lambda s: (s["map"], s["loc"][0])):
            if s["area"] not in order: order.append(s["area"])
        for area in order:
            group = [s for s in self.skulls if s["area"] == area]
            miss = [s for s in group if not s["have"]]
            shown = group if self.show_all.get() else miss
            if not shown: continue
            label = f"{area}  ({len(group) - len(miss)}/{len(group)})"
            aid = self.tree.insert("", "end", text=label, open=True, tags=("area",),
                                   values=(f"{len(miss)} missing" if miss else "complete",))
            for n, s in enumerate(sorted(shown, key=lambda s: s["have"]), 1):
                name = f"Skull {n}" + ("  (found)" if s["have"] else "")
                iid = self.tree.insert(aid, "end", text=name, values=(s["short"],),
                                       tags=("have",) if s["have"] else ())
                self.item_skull[iid] = s
                if s["guid"] == sel_guid: self.tree.selection_set(iid); self.tree.see(iid)
        first = next(iter(self.item_skull), None)
        if not sel_guid and first and not self.item_skull[first]["have"]:
            self.tree.selection_set(first)

    def on_select(self, _e=None):
        sel = self.tree.selection()
        s = self.item_skull.get(sel[0]) if sel else None
        if not s:
            self.copy_btn.configure(state="disabled"); return
        x, y, z = (int(v) for v in s["loc"])
        lines = list(s["details"]) or ["No nearby landmarks recorded."]
        lines.append(f"World coordinates: X {x}, Y {y}, Z {z} (Unreal units, 100 = 1 m; Z is height).")
        lines.append(f"Internal ID: {s['map']} / {s['actor']}")
        status = "Already collected." if s["have"] else "Not collected yet."
        self.set_detail(f"{s['area']} - {status}", lines)
        self.copy_btn.configure(state="normal")

    def copy_coords(self):
        sel = self.tree.selection(); s = self.item_skull.get(sel[0]) if sel else None
        if not s: return
        x, y, z = (int(v) for v in s["loc"])
        self.root.clipboard_clear(); self.root.clipboard_append(f"{x} {y} {z}")
        self.status.configure(text=f"Copied {x} {y} {z}")

    def watch(self):
        try:
            path = self.current_save()
            if path and (path != self.save_path or os.path.getmtime(path) != self.save_mtime):
                self.refresh()
        except OSError:
            pass
        self.root.after(WATCH_MS, self.watch)

    # ------------------------------------------------------------ buttons
    def choose_save(self):
        start = os.path.dirname(self.save_path) if self.save_path else core.SAVE_ROOT
        p = filedialog.askopenfilename(title="Choose your Queen's Domain save", initialdir=start,
                                       filetypes=[("Queen's Domain save", "*.sav"), ("All files", "*.*")])
        if not p: return
        if messagebox.askyesno(APP_NAME, "Always use this save?\n\nChoose No to use it just for now - next launch "
                                         "goes back to picking your newest save automatically."):
            self.settings["save"] = p
        else:
            self.settings.pop("save", None)
        self.once_save = p
        core.save_settings(self.settings)
        self.refresh()

    def choose_game(self):
        d = filedialog.askdirectory(title="Select your Queen's Domain install folder")
        if not d: return
        pak = core.pak_from_folder(d)
        if not pak:
            messagebox.showerror(APP_NAME, "Couldn't find QueensDomain-WindowsNoEditor.pak in that folder.\n\n"
                                           "In Steam: right-click Queen's Domain > Manage > Browse local files, "
                                           "and select that folder.")
            return
        self.settings["pak"] = pak; core.save_settings(self.settings)
        self.skulls = None; self.start_load()

    def on_close(self):
        self.settings["geometry"] = self.root.geometry()
        try: core.save_settings(self.settings)
        except OSError: pass
        self.root.destroy()


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
