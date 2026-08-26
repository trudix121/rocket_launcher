import ctypes
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter

DATA_FILE = "data.json"

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
DANGER = "#EF4444"
DANGER_HOVER = "#DC2626"
SUCCESS = "#22C55E"
CARD_COLOR = "#1E1E2E"
CARD_HOVER = "#252538"
BG_COLOR = "#141420"
SUBTEXT = "#9CA3AF"
BORDER = "#2A2A3C"

STATUS_CLEAR_DELAY_MS = 4000


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Add / Edit dialog
# ---------------------------------------------------------------------------
class ExeDialog(customtkinter.CTkToplevel):
    """Dialog used for both adding and editing an application entry."""

    def __init__(self, parent, name="", directory="", editing=False):
        super().__init__(parent)

        self.title("Edit Application" if editing else "Add Application")
        self.geometry("460x320")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        self.result = None

        customtkinter.CTkLabel(
            self,
            text="Edit Application" if editing else "Add a New Application",
            font=customtkinter.CTkFont(size=17, weight="bold"),
        ).pack(padx=24, pady=(24, 16), anchor="w")

        customtkinter.CTkLabel(
            self, text="Name", anchor="w", text_color=SUBTEXT, font=customtkinter.CTkFont(size=12)
        ).pack(padx=24, fill="x")
        self.name_entry = customtkinter.CTkEntry(
            self, placeholder_text="e.g. Visual Studio Code", height=36
        )
        self.name_entry.pack(padx=24, pady=(2, 14), fill="x")
        self.name_entry.insert(0, name)

        customtkinter.CTkLabel(
            self, text="Path to executable", anchor="w", text_color=SUBTEXT, font=customtkinter.CTkFont(size=12)
        ).pack(padx=24, fill="x")

        path_row = customtkinter.CTkFrame(self, fg_color="transparent")
        path_row.pack(padx=24, pady=(2, 6), fill="x")
        path_row.grid_columnconfigure(0, weight=1)

        self.dir_entry = customtkinter.CTkEntry(
            path_row, placeholder_text=r"C:\Program Files\...\app.exe", height=36
        )
        self.dir_entry.grid(row=0, column=0, sticky="ew")
        self.dir_entry.insert(0, directory)

        customtkinter.CTkButton(
            path_row, text="📁 Browse", width=90, height=36, command=self.browse
        ).grid(row=0, column=1, padx=(8, 0))

        self.error_label = customtkinter.CTkLabel(
            self, text="", text_color=DANGER, font=customtkinter.CTkFont(size=11), anchor="w"
        )
        self.error_label.pack(padx=24, pady=(0, 14), fill="x")

        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(4, 20))

        self.save_btn = customtkinter.CTkButton(
            button_frame,
            text="Save",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            width=150,
            command=self.submit,
        )
        self.save_btn.pack(side="left", padx=6)

        customtkinter.CTkButton(
            button_frame,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            width=150,
            command=self.cancel,
        ).pack(side="left", padx=6)

        # Keyboard shortcuts for a faster workflow
        self.bind("<Return>", lambda _e: self.submit())
        self.bind("<Escape>", lambda _e: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self._center_on_parent(parent)
        self.grab_set()
        self.focus_force()
        self.name_entry.focus()

    def _center_on_parent(self, parent):
        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = 460, 320
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select the executable",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, path)
            if not self.name_entry.get():
                self.name_entry.insert(0, os.path.splitext(os.path.basename(path))[0])
            self.error_label.configure(text="")

    def submit(self):
        name = self.name_entry.get().strip()
        directory = self.dir_entry.get().strip()

        if not name or not directory:
            self.error_label.configure(text="⚠ Please fill in both the name and the path.")
            return

        if not os.path.exists(directory):
            self.error_label.configure(text="⚠ That path doesn't seem to exist. You can still save it.")
            # Don't block saving — the user might add the file later, or it's on
            # removable/network storage that isn't currently mounted.

        self.result = {"name": name, "directory": directory}
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
class App(customtkinter.CTk):
    def resource_path(self, filename):
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base_path / filename

    def __init__(self):
        super().__init__()

        self.title("Rocket Launcher")
        self.geometry("720x580")
        self.minsize(580, 440)
        self.configure(fg_color=BG_COLOR)

        icon_path = self.resource_path("logo.ico")
        try:
            self.iconbitmap(str(icon_path))
        except Exception:
            pass  # Missing icon shouldn't crash the app

        self.data = load_data()
        self.search_query = ""
        self._status_after_id = None
        self.sort_mode = "name"  # "name" | "recent" | "most_run"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_search_bar()
        self._build_list()
        self._build_status_bar()

        self.bind("<Control-n>", lambda _e: self.open_add_dialog())

        self.refresh_list()

    # -- UI construction ---------------------------------------------------
    def _build_header(self):
        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(20, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_box = customtkinter.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")

        customtkinter.CTkLabel(
            title_box,
            text="🚀 Rocket Launcher",
            font=customtkinter.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")

        self.count_label = customtkinter.CTkLabel(
            title_box, text="", text_color=SUBTEXT, font=customtkinter.CTkFont(size=12), anchor="w"
        )
        self.count_label.pack(anchor="w")

        customtkinter.CTkButton(
            header,
            text="＋  Add App",
            command=self.open_add_dialog,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            height=36,
            width=130,
        ).grid(row=0, column=1, sticky="e")

    def _build_search_bar(self):
        row = customtkinter.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, padx=24, pady=(6, 10), sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self.search_entry = customtkinter.CTkEntry(
            row, placeholder_text="🔍  Search for an application...", height=38
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Escape>", lambda _e: self.clear_search())

        self.sort_menu = customtkinter.CTkOptionMenu(
            row,
            values=["Name (A-Z)", "Most recently run", "Most launched"],
            width=170,
            height=38,
            command=self.on_sort_change,
        )
        self.sort_menu.set("Name (A-Z)")
        self.sort_menu.grid(row=0, column=1, padx=(8, 0))

    def _build_list(self):
        self.apps_frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        self.apps_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.apps_frame.grid_columnconfigure(0, weight=1)

    def _build_status_bar(self):
        self.status_label = customtkinter.CTkLabel(
            self, text="", text_color=SUBTEXT, font=customtkinter.CTkFont(size=12), anchor="w"
        )
        self.status_label.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")

    # -- Helpers -------------------------------------------------------
    def set_status(self, text, color=SUBTEXT):
        self.status_label.configure(text=text, text_color=color)
        if self._status_after_id is not None:
            self.after_cancel(self._status_after_id)
        self._status_after_id = self.after(STATUS_CLEAR_DELAY_MS, lambda: self.status_label.configure(text=""))

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.search_query = ""
        self.refresh_list()

    def on_search(self, _event=None):
        self.search_query = self.search_entry.get().strip().lower()
        self.refresh_list()

    def on_sort_change(self, choice):
        self.sort_mode = {
            "Name (A-Z)": "name",
            "Most recently run": "recent",
            "Most launched": "most_run",
        }.get(choice, "name")
        self.refresh_list()

    def _sorted_names(self):
        names = list(self.data.keys())
        if self.search_query:
            names = [n for n in names if self.search_query in n.lower()]

        if self.sort_mode == "name":
            names.sort(key=str.lower)
        elif self.sort_mode == "most_run":
            names.sort(key=lambda n: self.data[n].get("run_count", 0), reverse=True)
        elif self.sort_mode == "recent":
            def last_run_key(n):
                raw = self.data[n].get("last_run")
                if not raw:
                    return datetime.min
                try:
                    return datetime.strptime(raw, "%d.%m.%Y %H:%M")
                except ValueError:
                    return datetime.min

            names.sort(key=last_run_key, reverse=True)

        return names

    # -- Data / list rendering ----------------------------------------------
    def refresh_list(self):
        for widget in self.apps_frame.winfo_children():
            widget.destroy()

        total = len(self.data)
        self.count_label.configure(
            text=f"{total} app{'s' if total != 1 else ''} saved" if total else "No apps yet"
        )

        names = self._sorted_names()

        if not names:
            empty_text = (
                "No applications match your search." if self.search_query else
                "You haven't added any applications yet.\nClick \"＋ Add App\" to get started."
            )
            customtkinter.CTkLabel(
                self.apps_frame, text=empty_text, text_color=SUBTEXT, justify="center"
            ).grid(row=0, column=0, pady=40)
            return

        for row, name in enumerate(names):
            info = self.data[name]
            self.create_app_card(row, name, info)

    def create_app_card(self, row, name, info):
        directory = info.get("dir", "")
        run_count = info.get("run_count", 0)
        last_run = info.get("last_run")

        card = customtkinter.CTkFrame(
            self.apps_frame, fg_color=CARD_COLOR, corner_radius=12,
            border_width=1, border_color=BORDER,
        )
        card.grid(row=row, column=0, padx=6, pady=6, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        exists = os.path.exists(directory)
        icon = "🟢" if exists else "⚠️"

        customtkinter.CTkLabel(
            card, text=icon, font=customtkinter.CTkFont(size=20)
        ).grid(row=0, column=0, rowspan=3, padx=(16, 10), pady=14)

        customtkinter.CTkLabel(
            card, text=name, anchor="w", font=customtkinter.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=1, sticky="ew", pady=(12, 0))

        subtitle = directory if exists else f"{directory}   ·   not found"
        sub_color = SUBTEXT if exists else DANGER
        customtkinter.CTkLabel(
            card, text=subtitle, anchor="w", text_color=sub_color,
            font=customtkinter.CTkFont(size=11),
        ).grid(row=1, column=1, sticky="ew", pady=(0, 4))

        meta_text = f"Launched {run_count}x" if run_count else "Never launched"
        if last_run:
            meta_text += f"   ·   last run: {last_run}"
        customtkinter.CTkLabel(
            card, text=meta_text, anchor="w", text_color=SUBTEXT,
            font=customtkinter.CTkFont(size=10),
        ).grid(row=2, column=1, sticky="ew", pady=(0, 10))

        btn_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=3, padx=12, pady=10)

        launch_btn = customtkinter.CTkButton(
            btn_frame, text="▶ Launch", width=100, height=30,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=lambda n=name: self.run_executable(n),
        )
        launch_btn.grid(row=0, column=0, padx=3, pady=2)
        if not exists:
            launch_btn.configure(state="disabled", fg_color=BORDER)

        customtkinter.CTkButton(
            btn_frame, text="✏️", width=36, height=30,
            fg_color="transparent", border_width=1,
            command=lambda n=name: self.open_edit_dialog(n),
        ).grid(row=0, column=1, padx=3, pady=2)

        customtkinter.CTkButton(
            btn_frame, text="🗑️", width=36, height=30,
            fg_color="transparent", border_width=1,
            hover_color=DANGER_HOVER,
            command=lambda n=name: self.delete_executable(n),
        ).grid(row=0, column=2, padx=3, pady=2)

        # Subtle hover feedback on the whole card
        def on_enter(_e, c=card):
            c.configure(fg_color=CARD_HOVER)

        def on_leave(_e, c=card):
            c.configure(fg_color=CARD_COLOR)

        for widget in (card,):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        # Double-click anywhere on the card (except the buttons) launches the app
        card.bind("<Double-Button-1>", lambda _e, n=name: self.run_executable(n))

    # -- Actions --------------------------------------------------------
    def run_executable(self, name):
        info = self.data.get(name)
        if not info:
            return
        directory = info.get("dir", "")

        if not os.path.exists(directory):
            self.set_status(f"❌ Executable for \"{name}\" was not found.", DANGER)
            messagebox.showerror(
                "Not found",
                f"The executable for \"{name}\" could not be found:\n{directory}\n\n"
                "You can fix the path by clicking the edit (✏️) button.",
            )
            self.refresh_list()
            return

        try:
            os.startfile(directory)
            info["run_count"] = info.get("run_count", 0) + 1
            info["last_run"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            save_data(self.data)
            self.set_status(f"✅ \"{name}\" was launched.", SUCCESS)
            self.refresh_list()

        except Exception as error:
            self.set_status(f"❌ Failed to launch \"{name}\".", DANGER)
            messagebox.showerror("Error", str(error))

    def open_add_dialog(self):
        dialog = ExeDialog(self)
        self.wait_window(dialog)

        if dialog.result is None:
            return

        name = dialog.result["name"]
        directory = dialog.result["directory"]

        if name in self.data:
            messagebox.showwarning("Duplicate name", "An application with this name already exists.")
            return

        self.data[name] = {"dir": directory, "run_count": 0, "last_run": None}
        save_data(self.data)
        self.set_status(f"➕ \"{name}\" was added.", SUCCESS)
        self.refresh_list()

    def open_edit_dialog(self, name):
        info = self.data.get(name, {})
        dialog = ExeDialog(self, name=name, directory=info.get("dir", ""), editing=True)
        self.wait_window(dialog)

        if dialog.result is None:
            return

        new_name = dialog.result["name"]
        new_directory = dialog.result["directory"]

        if new_name != name and new_name in self.data:
            messagebox.showwarning("Duplicate name", "An application with this name already exists.")
            return

        updated_info = self.data.pop(name)
        updated_info["dir"] = new_directory
        self.data[new_name] = updated_info

        save_data(self.data)
        self.set_status(f"✏️ \"{name}\" was updated.", SUCCESS)
        self.refresh_list()

    def delete_executable(self, name):
        if messagebox.askyesno("Confirm deletion", f"Are you sure you want to delete \"{name}\"?"):
            self.data.pop(name, None)
            save_data(self.data)
            self.set_status(f"🗑️ \"{name}\" was deleted.", DANGER)
            self.refresh_list()


if __name__ == "__main__":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("trudix.app_launcher")
    except Exception:
        pass  # Not on Windows, or taskbar grouping isn't critical
    app = App()
    app.mainloop()