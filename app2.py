#!/usr/bin/python3
import sys
import subprocess
import os
import signal
import threading
from datetime import datetime
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio


class MeetingRecorderWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Local Meeting Recorder")
        self.set_default_size(380, 280)
        self.set_resizable(True)  # Allows resizing/moving dynamically

        # Base directory for logs
        self.log_dir = os.path.expanduser("~/AI/logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # --- Window Shell & HeaderBar (Moveable / Floating Window) ---
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Native GNOME HeaderBar with Window Buttons (Close/Minimize)
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        main_box.append(header)

        # Content Box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        main_box.append(box)

        # Header Title
        title_label = Gtk.Label(label="Meeting Recorder")
        title_label.add_css_class("title-2")
        box.append(title_label)

        # Status Label
        self.status_label = Gtk.Label(label="Status: Idle")
        self.status_label.add_css_class("dim-label")
        box.append(self.status_label)

        # --- Action 1: Standard Full Recording ---
        self.btn_mode_1 = Gtk.Button(label="Start Meeting Record with wireless")
        self.btn_mode_1.add_css_class("suggested-action")
        self.btn_mode_1.add_css_class("pill")
        self.btn_mode_1.connect("clicked", self.on_mode_1_toggled)
        box.append(self.btn_mode_1)

        # --- Action 2: Alternative Recording Script ---
        self.btn_mode_2 = Gtk.Button(label="Start Meeting Record with wired")
        self.btn_mode_2.add_css_class("accent")
        self.btn_mode_2.add_css_class("pill")
        self.btn_mode_2.connect("clicked", self.on_mode_2_toggled)
        box.append(self.btn_mode_2)

        # State Tracking
        self.active_proc = None
        self.active_mode = None  # None, 1, or 2

	# --- Terminal Output Window (Below Buttons) ---
        log_frame = Gtk.Frame()
        log_frame.set_vexpand(True)
        box.append(log_frame)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_has_frame(False)
        log_frame.set_child(self.scrolled_window)

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_monospace(True)  # Monospace terminal font
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_buffer = self.text_view.get_buffer()
        self.scrolled_window.set_child(self.text_view)

	# State Variables
        self.active_proc = None
        self.active_mode = None

        # --- Intercept Window Close Event ---
        self.connect("close-request", self.on_close_requested)

    # --- Close Event Handler ---
    def on_close_requested(self, window):
        """Triggered when the user clicks the 'X' button or closes the window."""
        if self.active_proc and self.active_proc.poll() is None:
            print("[GUI] Window closing while recording... Sending SIGINT to process.")
            try:
                # Stop active recording process before window destroys
                pgid = os.getpgid(self.active_proc.pid)
                os.killpg(pgid, signal.SIGINT)
            except ProcessLookupError:
                pass
        # Return False to allow GTK to close the window normally
        return False
    # --- Button Handler: Mode 1 ---

    def on_mode_1_toggled(self, button):
        if self.active_mode == 1:
            self.stop_current_recording()
        else:
            self.start_script(
                mode=1,
                script_name="./record_wireless.sh",
                status_text="🔴 Recording Meeting with wireless..."
            )

    # --- Button Handler: Mode 2 ---
    def on_mode_2_toggled(self, button):
        if self.active_mode == 2:
            self.stop_current_recording()
        else:
            self.start_script(
                mode=2,
                script_name="./record_wired.sh",
                status_text="🎙️ Recording Meeting with wired..."
            )

    # --- Process Management ---
    def start_script(self, mode, script_name, status_text):
        script_path = os.path.expanduser(script_name)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_log_file = os.path.join(self.log_dir, f"{mode}_{timestamp}.log")

        # Attach to new process group so SIGINT reaches sub-processes
        self.active_proc = subprocess.Popen(
            ["bash", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line-buffered output
            start_new_session=True
        )
        self.active_mode = mode

        # UI updates based on active mode
        if mode == 1:
            self.btn_mode_1.set_label("Stop Recording & Process")
            self.btn_mode_1.remove_css_class("suggested-action")
            self.btn_mode_1.add_css_class("destructive-action")
            self.btn_mode_2.set_sensitive(False)
        elif mode == 2:
            self.btn_mode_2.set_label("Stop Quick Record & Process")
            self.btn_mode_2.remove_css_class("accent")
            self.btn_mode_2.add_css_class("destructive-action")
            self.btn_mode_1.set_sensitive(False)

        self.status_label.set_label(f"Status: {status_text}")

	# Worker thread to read and stream script output to GUI
        threading.Thread(
           target=self._stream_output_task,
           args=(self.current_log_file,),
           daemon=True
        ).start()

    def _stream_output_task(self, log_path):
        """Tees process output simultaneously to disk and to the GTK text viewer."""
        with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
            for line in iter(self.active_proc.stdout.readline, ''):
                if line:
                    # Write to file on disk and flush immediately
                    log_fp.write(line)
                    log_fp.flush()
                    # Schedule GTK buffer update on the UI thread
                    GLib.idle_add(self.append_log, line)

            self.active_proc.stdout.close()
            self.active_proc.wait()
            log_fp.write("\n=== Process Finished ===\n")
        GLib.idle_add(self._reset_ui_state)

    def append_log(self, text):
        """Appends log text and auto-scrolls to the bottom."""
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)

        # Auto-scroll to bottom of window
        mark = self.text_buffer.create_mark(None, self.text_buffer.get_end_iter(), False)
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def stop_current_recording(self):
        if self.active_proc and self.active_proc.poll() is None:
            # Disable buttons while post-processing runs
            self.btn_mode_1.set_sensitive(False)
            self.btn_mode_2.set_sensitive(False)
            self.status_label.set_label("Status: ⏳ Stopping & Processing Transcription...")

            # Run process shutdown and transcription asynchronously to prevent UI freeze
            threading.Thread(target=self._async_stop_task, daemon=True).start()

    def _async_stop_task(self):
        try:
            # Send SIGINT (Ctrl+C equivalent) to child process group
            pgid = os.getpgid(self.active_proc.pid)
            os.killpg(pgid, signal.SIGINT)

            # Wait for bash script post-processing (Whisper/Ollama) to complete
            self.active_proc.wait()
        except ProcessLookupError:
            pass

        # Update UI back on GTK main thread
        GLib.idle_add(self._reset_ui_state)

    def _reset_ui_state(self):
        self.active_proc = None
        self.active_mode = None

        # Reset Button 1
        self.btn_mode_1.set_sensitive(True)
        self.btn_mode_1.set_label("Start Meeting Record with wireless")
        self.btn_mode_1.remove_css_class("destructive-action")
        self.btn_mode_1.add_css_class("suggested-action")

        # Reset Button 2
        self.btn_mode_2.set_sensitive(True)
        self.btn_mode_2.set_label("Start Meeting Record with wired")
        self.btn_mode_2.remove_css_class("destructive-action")
        self.btn_mode_2.add_css_class("accent")

        self.status_label.set_label("Status: Idle (Task Finished)")
        self.append_log("\n=== Process Finished ===\n")


class MeetingApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.github.local_meeting_recorder",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MeetingRecorderWindow(application=self)
        win.present()


if __name__ == "__main__":
    app = MeetingApp()
    app.run(sys.argv)
