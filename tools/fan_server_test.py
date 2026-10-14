"""Local private fan-server test window. Run python -m tools.fan_server_test."""
from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

DEFAULT_ROOT = r"C:\Program Files (x86)\EA Games\Motor City Online"


class TesterWindow:
    def __init__(self, window):
        self.window = window
        self.events = queue.Queue()
        self.cancelled = threading.Event()
        self.running = False
        self.selection = None
        self.personas = []
        window.title("Motor City fan-server connection test")
        window.geometry("680x610")
        window.minsize(590, 510)
        window.protocol("WM_DELETE_WINDOW", self.close)
        panel = ttk.Frame(window, padding=18)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="Fan-server connection test", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(panel, text="Checks account, persona, lobby, primary connection and garage data.\nUse your fan-server account. Credentials are kept only for this test.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 18))
        self.root = tk.StringVar(value=DEFAULT_ROOT)
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        ttk.Label(panel, text="Original installation").grid(row=2, column=0, sticky="w")
        self.root_entry = ttk.Entry(panel, textvariable=self.root)
        self.root_entry.grid(row=2, column=1, sticky="ew", padx=10)
        self.browse_button = ttk.Button(panel, text="Browse…", command=self.browse)
        self.browse_button.grid(row=2, column=2)
        ttk.Label(panel, text="Account name").grid(row=3, column=0, sticky="w", pady=10)
        self.user_entry = ttk.Entry(panel, textvariable=self.username)
        self.user_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(10, 0))
        ttk.Label(panel, text="Password").grid(row=4, column=0, sticky="w")
        self.pass_entry = ttk.Entry(panel, textvariable=self.password, show="•")
        self.pass_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=(10, 0))
        buttons = ttk.Frame(panel)
        buttons.grid(row=5, column=0, columnspan=3, sticky="w", pady=16)
        self.test_button = ttk.Button(buttons, text="Test connection", command=self.start)
        self.test_button.pack(side="left")
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=10)
        self.progress = ttk.Progressbar(panel, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.status = tk.StringVar(value="Ready. No account test has run.")
        ttk.Label(panel, textvariable=self.status, wraplength=620).grid(row=7, column=0, columnspan=3, sticky="w", pady=10)
        self.persona_frame = ttk.LabelFrame(panel, text="Choose a persona", padding=10)
        self.persona_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.persona_frame.columnconfigure(0, weight=1)
        self.persona_box = ttk.Combobox(self.persona_frame, state="readonly")
        self.persona_box.grid(row=0, column=0, sticky="ew")
        ttk.Button(self.persona_frame, text="Continue", command=self.choose_persona).grid(row=0, column=1, padx=(10, 0))
        self.persona_frame.grid_remove()
        self.output = tk.Text(panel, height=12, wrap="word", state="disabled")
        self.output.grid(row=9, column=0, columnspan=3, sticky="nsew")
        panel.rowconfigure(9, weight=1)
        window.after(100, self.poll)

    def browse(self):
        selected = filedialog.askdirectory(parent=self.window, title="Select original Motor City Online installation")
        if selected:
            self.root.set(selected)

    def write(self, message):
        self.output.configure(state="normal")
        self.output.insert("end", message + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def start(self):
        if self.running:
            return
        root, username, password = self.root.get(), self.username.get(), self.password.get()
        if not root.strip() or not username or not password:
            self.status.set("Enter the installation folder, account name and password.")
            return
        self.running = True
        self.cancelled.clear()
        self.password.set("")
        for control in (self.root_entry, self.browse_button, self.user_entry, self.pass_entry, self.test_button):
            control.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.status.set("Checking the installed fan-server configuration…")
        self.progress.start(15)
        threading.Thread(target=self.worker, args=(root, username, password), daemon=True).start()

    def worker(self, root, username, password):
        try:
            from client.fanserver_test import run_test
            from pathlib import Path as _Path
            data_root = _Path(root)
            catalogue_path = data_root / 'Data' / 'DB' / 'Online.mdb'
            if not catalogue_path.is_file():
                catalogue_path = data_root / 'data' / 'db' / 'online.mdb'
            use_catalogue = catalogue_path.is_file()
            result = run_test(root, username, password, on_stage=lambda stage: self.events.put(("stage", stage)),
                              on_personas=self.request_persona, cancelled=self.cancelled.is_set,
                              fetch_garage=True, use_catalogue=use_catalogue, probe_race_entry=True)
            self.events.put(("result", result))
        except Exception:
            # Exception contents, URLs and account payloads are never displayed.
            self.events.put(("failure", None))
        finally:
            root = username = password = None
            self.events.put(("finished", None))

    def request_persona(self, personas):
        reply = queue.Queue(maxsize=1)
        self.events.put(("personas", (personas, reply)))
        while not self.cancelled.is_set():
            try:
                return reply.get(timeout=0.1)
            except queue.Empty:
                pass
        return None

    def choose_persona(self):
        index = self.persona_box.current()
        if self.selection is not None and 0 <= index < len(self.personas):
            self.selection.put(self.personas[index]["persona_id"])
            self.selection = None
            self.persona_frame.grid_remove()
            self.status.set("Continuing with the selected persona…")

    def cancel(self):
        self.cancelled.set()
        self.persona_frame.grid_remove()
        self.selection = None
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelling; waiting for the current network operation to finish…")

    def close(self):
        self.cancelled.set()
        self.password.set("")
        self.window.destroy()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "stage":
                    # Only the orchestration module's fixed stage names are shown.
                    stages = {"preflight": "Configuration checked", "authorization": "Authorizing account", "login": "Checking binary account login",
                              "personas": "Reading personas", "persona": "Selecting persona", "lobby": "Connecting to lobby", "primary": "Connecting to primary service", "garage": "Reading persona garage data", "race_entry": "Validating recovered race-entry path", "complete": "Test complete"}
                    label = stages.get(value) if isinstance(value, str) else None
                    if label:
                        self.status.set(label + "…")
                        self.write(label)
                elif kind == "personas":
                    candidates, reply = value
                    self.personas = [p for p in candidates if isinstance(p, dict) and type(p.get("persona_id")) is int and isinstance(p.get("name"), str)]
                    if self.cancelled.is_set() or not self.personas:
                        reply.put(None)
                    else:
                        self.selection = reply
                        self.persona_box.configure(values=[f"{p['name']} (ID {p['persona_id']})" for p in self.personas])
                        self.persona_box.current(0)
                        self.persona_frame.grid()
                        self.status.set("Choose a persona, then press Continue.")
                elif kind == "result":
                    self.show_result(value)
                elif kind == "failure":
                    self.status.set("Test could not complete. Check the installation and server availability.")
                    self.write("The tester stopped. Private error details were withheld.")
                elif kind == "finished":
                    self.running = False
                    self.selection = None
                    self.persona_frame.grid_remove()
                    self.progress.stop()
                    for control in (self.root_entry, self.browse_button, self.user_entry, self.pass_entry, self.test_button):
                        control.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.password.set("")
        except queue.Empty:
            pass
        self.window.after(100, self.poll)

    def show_result(self, result):
        if not isinstance(result, dict):
            self.status.set("The tester returned no safe result.")
            return
        if self.cancelled.is_set():
            self.status.set("Test cancelled.")
        else:
            self.status.set("Test finished. See the verified stages below.")
        # Deliberately exclude arbitrary text, URLs, account objects and exception repr.
        labels = {"success": "Test succeeded", "cancelled": "Cancelled", "account_authenticated": "Account authenticated",
                  "lobby_connected": "Lobby connected", "primary_connected": "Primary connected", "garage_loaded": "Garage data received",
                  "persona_count": "Personas found", "garage_record_count": "Garage records received",
                  "race_entry_probe_passed": "Race-entry probe passed", "positional_updates_hz": "Configured position update rate (Hz)"}
        labels["room_channel_probe_passed"] = "Room channel probe passed"
        for key, label in labels.items():
            value = result.get(key)
            if type(value) is bool:
                self.write(f"{label}: {'yes' if value else 'no'}")
            elif type(value) is int and value >= 0:
                self.write(f"{label}: {value}")
            elif type(value) is float and value > 0:
                self.write(f"{label}: {value:.4f}")
        kinds = result.get('recovered_task_kinds')
        if isinstance(kinds, list) and kinds:
            self.write(f"Recovered race-entry task kinds: {', '.join(str(kind) for kind in kinds)}")
        interval = result.get('update_interval_seconds')
        if isinstance(interval, (int, float)) and interval > 0:
            self.write(f"Configured update interval (seconds): {interval:.4f}")
        self.write("This checks protocol stages and data access; it does not certify racing or full game compatibility.")


def main():
    window = tk.Tk()
    TesterWindow(window)
    window.mainloop()


if __name__ == "__main__":
    main()

