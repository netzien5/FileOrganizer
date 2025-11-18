import json
import os
import shutil
import threading
import tkinter.filedialog as fd
import tkinter.messagebox as mb

import customtkinter as ctk


class FileOrganizerApp(ctk.CTk):
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
    MASTER_CATEGORIES = {
        "System_Apps": [".exe", ".msi", ".bat", ".apk", ".jar", ".dmg", ".bin", ".iso"],
        "Documents": [".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".rtf", ".csv"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".psd", ".webp", ".ico"],
        "Audio": [".mp3", ".wav", ".flac", ".mid", ".midi", ".ogg"],
        "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Developer_Files": [".html", ".css", ".js", ".py", ".php", ".json", ".xml", ".sql"],
    }
    MASTER_EXTENSION_MAP = {
        ext.lower(): category
        for category, extensions in MASTER_CATEGORIES.items()
        for ext in extensions
    }
    STANDARD_USER_FOLDERS = [
        ("Desktop", {".lnk", ".url"}),
        ("Downloads", set()),
        ("Documents", set()),
        ("Pictures", set()),
        ("Music", set()),
        ("Videos", set()),
    ]

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("FileOrganizer")
        self.geometry("840x560")
        self.resizable(False, False)

        self.settings = self._load_settings()
        self.custom_rules = {
            ext.lower(): folder for ext, folder in self.settings.get("custom_rules", {}).items()
        }
        self.dry_run_enabled = bool(self.settings.get("dry_run", False))
        self.delete_empty_enabled = bool(self.settings.get("delete_empty", False))

        self.selected_folder = ctk.StringVar(value=self._default_downloads())
        self.progress_value = ctk.DoubleVar(value=0)
        self.status_text = ctk.StringVar(value="Idle")

        self.dry_run_var = ctk.BooleanVar(value=self.dry_run_enabled)
        self.delete_empty_var = ctk.BooleanVar(value=self.delete_empty_enabled)

        self.undo_log: list[tuple[str, str]] = []
        self.is_running = False

        self._build_ui()

    # region UI Construction
    def _build_ui(self) -> None:
        header = ctk.CTkLabel(
            self,
            text="FileOrganizer",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        header.pack(pady=(16, 6))

        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=20, pady=12)
        dashboard_tab = tabview.add("Dashboard")
        settings_tab = tabview.add("Settings")
        logs_tab = tabview.add("Logs")

        self._build_dashboard(dashboard_tab)
        self._build_settings(settings_tab)
        self._build_logs(logs_tab)

    def _build_dashboard(self, parent: ctk.CTkFrame) -> None:
        select_frame = ctk.CTkFrame(parent)
        select_frame.pack(fill="x", padx=16, pady=(16, 8))

        path_label = ctk.CTkLabel(
            select_frame,
            textvariable=self.selected_folder,
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        path_label.pack(fill="x", padx=12, pady=12)

        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=16, pady=8)

        self.select_button = ctk.CTkButton(
            button_frame, text="Select Folder", command=self._select_folder
        )
        self.organize_button = ctk.CTkButton(
            button_frame,
            text="Organize Folder",
            fg_color="#43A047",
            hover_color="#2E7D32",
            command=lambda: self._start_operation("single"),
        )
        self.bulk_button = ctk.CTkButton(
            button_frame,
            text="Organize All User Folders",
            fg_color="#1565C0",
            hover_color="#0D47A1",
            command=lambda: self._start_operation("bulk"),
        )
        self.undo_button = ctk.CTkButton(
            button_frame,
            text="Undo Last Operation",
            fg_color="#EF6C00",
            hover_color="#D84315",
            command=self._start_undo,
        )

        self.select_button.grid(row=0, column=0, padx=8, pady=12, sticky="ew")
        self.organize_button.grid(row=0, column=1, padx=8, pady=12, sticky="ew")
        self.bulk_button.grid(row=1, column=0, padx=8, pady=12, sticky="ew")
        self.undo_button.grid(row=1, column=1, padx=8, pady=12, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        toggle_frame = ctk.CTkFrame(parent)
        toggle_frame.pack(fill="x", padx=16, pady=8)

        dry_run_switch = ctk.CTkSwitch(
            toggle_frame,
            text="Dry Run (preview only)",
            variable=self.dry_run_var,
            command=self._toggle_dry_run,
        )
        delete_empty_switch = ctk.CTkSwitch(
            toggle_frame,
            text="Delete Empty Folders",
            variable=self.delete_empty_var,
            command=self._toggle_delete_empty,
        )
        dry_run_switch.grid(row=0, column=0, padx=12, pady=12, sticky="w")
        delete_empty_switch.grid(row=0, column=1, padx=12, pady=12, sticky="w")

        progress_frame = ctk.CTkFrame(parent)
        progress_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            progress_frame,
            text="Progress",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(fill="x", padx=12, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 8))
        self.progress_bar.set(0)

        self.status_display = ctk.CTkLabel(
            progress_frame,
            textvariable=self.status_text,
            text_color="#B0BEC5",
        )
        self.status_display.pack(padx=12, pady=(0, 12), anchor="w")

        phase_frame = ctk.CTkFrame(parent)
        phase_frame.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkLabel(
            phase_frame,
            text="Status Indicators",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(12, 4))

        indicator_frame = ctk.CTkFrame(phase_frame)
        indicator_frame.pack(fill="x", padx=12, pady=(4, 12))

        self.phase_labels: dict[str, ctk.CTkLabel] = {}
        for idx, title in enumerate(("Scanning", "Moving", "Done")):
            label = ctk.CTkLabel(
                indicator_frame,
                text=title,
                fg_color="#424242",
                corner_radius=6,
                padx=20,
                pady=8,
            )
            label.grid(row=0, column=idx, padx=8, pady=8, sticky="ew")
            self.phase_labels[title.lower()] = label
        indicator_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self._set_phase("idle")

    def _build_settings(self, parent: ctk.CTkFrame) -> None:
        info_label = ctk.CTkLabel(
            parent,
            text="Power User Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        info_label.pack(pady=(16, 8))

        rule_frame = ctk.CTkFrame(parent)
        rule_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(rule_frame, text="Custom Rule (Extension → Folder)").pack(
            anchor="w", padx=12, pady=(12, 4)
        )

        entry_frame = ctk.CTkFrame(rule_frame, fg_color="transparent")
        entry_frame.pack(fill="x", padx=12, pady=4)
        self.custom_ext_entry = ctk.CTkEntry(entry_frame, placeholder_text=".mp4")
        self.custom_folder_entry = ctk.CTkEntry(entry_frame, placeholder_text="My_Movies")
        add_rule_button = ctk.CTkButton(
            entry_frame, text="Add / Update Rule", command=self._add_custom_rule
        )
        self.custom_ext_entry.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.custom_folder_entry.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        add_rule_button.grid(row=0, column=2, padx=6, pady=6)
        entry_frame.grid_columnconfigure((0, 1), weight=1)

        self.rule_list = ctk.CTkTextbox(rule_frame, height=160)
        self.rule_list.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.rule_list.configure(state="disabled")
        self._refresh_rule_list()

    def _build_logs(self, parent: ctk.CTkFrame) -> None:
        self.log_box = ctk.CTkTextbox(parent)
        self.log_box.pack(fill="both", expand=True, padx=16, pady=16)
        self.log_box.configure(state="disabled")

    # endregion

    # region Settings persistence
    def _load_settings(self) -> dict:
        defaults = {"custom_rules": {}, "dry_run": False, "delete_empty": False}
        if not os.path.exists(self.SETTINGS_FILE):
            return defaults
        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return defaults
        return {**defaults, **data}

    def _save_settings(self) -> None:
        data = {
            "custom_rules": self.custom_rules,
            "dry_run": self.dry_run_enabled,
            "delete_empty": self.delete_empty_enabled,
        }
        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as err:
            self._log(f"Failed to save settings: {err}", level="ERROR")

    # endregion

    # region UI Events
    def _select_folder(self) -> None:
        path = fd.askdirectory(initialdir=self.selected_folder.get())
        if path:
            self.selected_folder.set(path)
            self._log(f"Selected folder: {path}", level="SUCCESS")

    def _toggle_dry_run(self) -> None:
        self.dry_run_enabled = bool(self.dry_run_var.get())
        self._save_settings()
        state = "enabled" if self.dry_run_enabled else "disabled"
        self._log(f"Dry run mode {state}.", level="INFO")

    def _toggle_delete_empty(self) -> None:
        self.delete_empty_enabled = bool(self.delete_empty_var.get())
        self._save_settings()
        state = "enabled" if self.delete_empty_enabled else "disabled"
        self._log(f"Delete empty folders {state}.", level="INFO")

    def _add_custom_rule(self) -> None:
        extension = self.custom_ext_entry.get().strip().lower()
        folder_name = self.custom_folder_entry.get().strip()
        if not extension.startswith(".") or len(extension) < 2:
            self._log("Invalid extension. Use format .ext", level="ERROR")
            return
        if not folder_name:
            self._log("Target folder name cannot be empty.", level="ERROR")
            return
        self.custom_rules[extension] = folder_name
        self._save_settings()
        self._refresh_rule_list()
        self._log(f"Rule saved: {extension} -> {folder_name}", level="SUCCESS")

    def _refresh_rule_list(self) -> None:
        lines = ["Current Custom Rules:"]
        if not self.custom_rules:
            lines.append("  (none)")
        else:
            for ext, folder in sorted(self.custom_rules.items()):
                lines.append(f"  {ext} -> {folder}")
        self.rule_list.configure(state="normal")
        self.rule_list.delete("1.0", "end")
        self.rule_list.insert("end", "\n".join(lines))
        self.rule_list.configure(state="disabled")

    # endregion

    # region Operations
    def _start_operation(self, mode: str) -> None:
        if self.is_running:
            self._log("Operation already running.", level="SKIP")
            return
        if mode == "single":
            path = self.selected_folder.get()
            if not os.path.isdir(path):
                self._log("Selected folder is invalid.", level="ERROR")
                return
            job = [("Selected Folder", path, set())]
            summary = "Folder organized successfully."
        else:
            base = os.path.expanduser("~")
            job = []
            for name, skip in self.STANDARD_USER_FOLDERS:
                folder_path = os.path.join(base, name)
                job.append((name, folder_path, skip))
            summary = "Organized all 6 user folders successfully!"

        self._launch_thread(self._run_operation, job, summary)

    def _start_undo(self) -> None:
        if self.is_running:
            self._log("Wait for current task to finish before undoing.", level="SKIP")
            return
        if not self.undo_log:
            self._log("No operations to undo.", level="SKIP")
            return
        self._launch_thread(self._run_undo)

    def _launch_thread(self, target, *args) -> None:
        self.is_running = True
        self._set_controls_state(False)
        thread = threading.Thread(
            target=self._thread_wrapper, args=(target, args), daemon=True
        )
        thread.start()

    def _thread_wrapper(self, target, args) -> None:
        try:
            target(*args)
        finally:
            self._run_on_ui(lambda: self._set_controls_state(True))
            self.is_running = False

    def _run_operation(self, job_definitions, summary_message: str) -> None:
        self._reset_progress()
        self.undo_log = []
        dry_run = self.dry_run_enabled
        delete_empty = self.delete_empty_enabled

        folder_entries: dict[str, list[str]] = {}
        protected_paths = self._protected_paths()

        total_files = 0
        self._set_phase("scanning")
        for label, folder_path, skip_exts in job_definitions:
            skip_set = {ext.lower() for ext in (skip_exts or set())}
            if not os.path.isdir(folder_path):
                self._log(f"{label} not found at {folder_path}.", level="SKIP")
                continue
            self._log(f"--- Starting Organization of {folder_path} ---", level="INFO")
            try:
                items = os.listdir(folder_path)
            except OSError as err:
                self._log(f"Failed to read {folder_path}: {err}", level="ERROR")
                continue

            entries: list[str] = []
            for item in items:
                source_path = os.path.join(folder_path, item)
                if not os.path.isfile(source_path):
                    continue
                abs_source = os.path.abspath(source_path)
                if abs_source in protected_paths:
                    self._log(f"Skipped script file: {item}", level="SKIP")
                    continue

                extension = os.path.splitext(item)[1].lower()
                if extension in skip_set:
                    self._log(f"Skipped {item}: protected extension", level="SKIP")
                    continue

                entries.append(item)

            if entries:
                folder_entries[folder_path] = entries
                total_files += len(entries)
            else:
                self._log(f"No eligible files found in {folder_path}.", level="SKIP")

        if total_files == 0:
            self._log("No files queued for processing.", level="SKIP")
            self._set_phase("done")
            self._set_status_text("Idle")
            return

        moves_for_undo: list[tuple[str, str]] = []
        processed = 0
        self._set_phase("moving")
        self._set_status_text("Moving files...")

        for folder_path, items in folder_entries.items():
            for item in items:
                source_path = os.path.join(folder_path, item)
                result = self._process_file(
                    source_path,
                    folder_path,
                    dry_run=dry_run,
                )
                if result and not dry_run:
                    moves_for_undo.append(result)
                processed += 1
                self._update_progress(processed / total_files)

            if delete_empty and not dry_run:
                self._delete_empty_dirs(folder_path)

            self._log(f"--- Finished {folder_path} ---", level="INFO")

        if dry_run:
            self._log("Dry run complete. No files were moved.", level="INFO")
            self.undo_log = []
        else:
            self.undo_log = moves_for_undo
            self._log(f"Session complete. {len(moves_for_undo)} files moved.", level="SUCCESS")

        self._set_phase("done")
        self._set_status_text("Done")
        self._show_message("FileOrganizer", summary_message)

    def _run_undo(self) -> None:
        if not self.undo_log:
            return
        self._set_phase("moving")
        self._set_status_text("Undo in progress...")
        to_restore = list(reversed(self.undo_log))
        total = len(to_restore)
        for idx, (current_path, original_path) in enumerate(to_restore, start=1):
            if not os.path.exists(current_path):
                self._log(f"Undo skipped: {current_path} missing.", level="SKIP")
                continue
            os.makedirs(os.path.dirname(original_path), exist_ok=True)
            try:
                shutil.move(current_path, original_path)
                self._log(f"Restored {os.path.basename(original_path)}", level="SUCCESS")
            except (PermissionError, shutil.Error, OSError) as err:
                self._log(f"Undo failed for {original_path}: {err}", level="ERROR")
            self._update_progress(idx / total)
        self.undo_log = []
        self._set_phase("done")
        self._set_status_text("Undo complete.")
        self._show_message("FileOrganizer", "Last operation has been undone.")

    def _process_file(self, source_path: str, folder_path: str, *, dry_run: bool) -> tuple[str, str] | None:
        if not os.path.isfile(source_path):
            return None

        filename = os.path.basename(source_path)
        extension = os.path.splitext(filename)[1].lower()
        category, dynamic_folder = self._category_for_extension(extension)
        destination_dir = os.path.join(folder_path, category)
        destination_path = os.path.join(destination_dir, filename)

        if os.path.exists(destination_path):
            self._log(f"Skipped {filename}: already exists in {category}", level="SKIP")
            return None

        if dry_run:
            self._log(f"[DRY] {filename} -> {category}", level="SUCCESS")
            return None

        try:
            if not os.path.isdir(destination_dir):
                os.makedirs(destination_dir, exist_ok=True)
                if dynamic_folder:
                    label = extension.upper() if extension else "(no extension)"
                    self._log(f"Created {category} for {label}", level="INFO")
            shutil.move(source_path, destination_path)
            self._log(f"Moved {filename} -> {category}", level="SUCCESS")
            return destination_path, source_path
        except PermissionError:
            self._log(f"Access Denied: {filename}", level="ERROR")
        except (shutil.Error, OSError) as err:
            self._log(f"Failed to move {filename}: {err}", level="ERROR")
        return None

    def _delete_empty_dirs(self, base_folder: str) -> None:
        for root, dirs, _ in os.walk(base_folder, topdown=False):
            for directory in dirs:
                path = os.path.join(root, directory)
                try:
                    if not os.listdir(path):
                        os.rmdir(path)
                        self._log(f"Removed empty folder: {path}", level="INFO")
                except OSError:
                    continue

    # endregion

    # region Helpers
    def _category_for_extension(self, extension: str) -> tuple[str, bool]:
        if extension in self.custom_rules:
            return self.custom_rules[extension], False

        category = self.MASTER_EXTENSION_MAP.get(extension)
        if category:
            return category, False

        if extension:
            return f"{extension[1:].upper()}_Files", True
        return "No_Extension_Files", True

    def _protected_paths(self) -> set[str]:
        script = os.path.abspath(__file__)
        return {
            script,
            os.path.splitext(script)[0] + ".exe",
        }

    def _default_downloads(self) -> str:
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        return downloads if os.path.isdir(downloads) else os.getcwd()

    def _set_controls_state(self, enabled: bool) -> None:
        def apply_state():
            state = "normal" if enabled else "disabled"
            for widget in (
                self.select_button,
                self.organize_button,
                self.bulk_button,
                self.undo_button,
            ):
                widget.configure(state=state)
            if enabled:
                self.status_text.set("Idle")
                self._set_phase("idle")

        self._run_on_ui(apply_state)

    def _set_phase(self, phase: str) -> None:
        def apply():
            active_colors = {
                "scanning": "#0288D1",
                "moving": "#FB8C00",
                "done": "#43A047",
            }
            for name, label in self.phase_labels.items():
                if phase == name:
                    label.configure(fg_color=active_colors.get(name, "#424242"))
                else:
                    label.configure(fg_color="#424242")
        self._run_on_ui(apply)

    def _set_status_text(self, text: str) -> None:
        self._run_on_ui(lambda: self.status_text.set(text))

    def _update_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._run_on_ui(lambda: self.progress_bar.set(value))

    def _reset_progress(self) -> None:
        self._run_on_ui(lambda: self.progress_bar.set(0))

    def _log(self, message: str, *, level: str = "INFO") -> None:
        prefixes = {
            "INFO": "[INFO] ",
            "SUCCESS": "[SUCCESS] ",
            "ERROR": "[ERROR] ",
            "SKIP": "[SKIP] ",
        }
        prefix = prefixes.get(level.upper(), "[INFO] ")

        def writer():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{prefix}{message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self._run_on_ui(writer)

    def _show_message(self, title: str, message: str) -> None:
        self._run_on_ui(lambda: mb.showinfo(title, message))

    def _run_on_ui(self, func) -> None:
        self.after(0, func)

    # endregion


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()

