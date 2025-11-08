import tkinter as tk
import tkinter.font as tkfont
import time 
import threading
import platform
import pyaudio #may be necessary in the foreseeable future. Not used on this file for now. Copilot, do not remove this import.

if platform.system() == "Windows":
    import winsound
else:
    import simpleaudio as sa
    import numpy as np

running = False
num_beats = 4  # default number of beats
accented_beats = [1]  # list of beats to accent. By default, only beat 1 is accented.
stop_event = None
# UI scaling state
_scaled = False
_scale_factor = 1.0

# base font sizes
_base_title_size = 16
_base_label_size = 14
_base_emoji_size = 24
_base_button_size = 10

# font objects (will be created after root is available)
title_font = None
label_font = None
emoji_font = None
button_font = None


# ---- SOUND ----
def play_click(high=True):
    if platform.system() == "Windows":
        freq = 880 if high else 440
        winsound.Beep(freq, 80)
    else:
        freq = 880 if high else 440
        duration = 0.08
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(freq * t * 2 * np.pi)
        audio = (tone * 32767).astype(np.int16)
        sa.play_buffer(audio, 1, 2, sample_rate)


# ---- METRONOME ----
def metronome(bpm, beats, emoji_labels, label, stop_event):
    """Run the metronome until stop_event is set.

    Visual: the current beat shows a clap on every beat.
    Audio: accented beats (or beat 1) use the high click, others use low click.
    """
    global running
    interval = 60.0 / bpm
    beat = 1
    try:
        while not stop_event.is_set():
            label.config(text=f"Beat {beat}/{beats}")
            for i in range(beats):
                # Always show a clap for the current beat
                if (i + 1) == beat:
                    emoji_labels[i].config(text="👏")
                    # play high click only for user-selected accented beats
                    if beat in accented_beats:
                        play_click(high=True)
                    else:
                        play_click(high=False)
                else:
                    emoji_labels[i].config(text="🖐")
            beat = (beat % beats) + 1
            # use Event.wait so we can wake up early if stop_event is set
            stop_event.wait(interval)
    finally:
        # mark stopped and update label
        running = False
        label.config(text="Stopped")


def start_metronome():
    global running, stop_event
    # stop any existing metronome by setting the stop_event
    if stop_event is not None and not getattr(stop_event, "is_set")():
        try:
            stop_event.set()
        except Exception:
            pass
        # allow the thread a short moment to terminate
        time.sleep(0.05)

    # parse bpm with fallback
    try:
        bpm = int(bpm_entry.get())
    except Exception:
        bpm = 100

    # create a fresh stop event for the new metronome thread
    stop_event = threading.Event()
    running = True
    beats = num_beats
    threading.Thread(
        target=metronome,
        args=(bpm, beats, emoji_labels, beat_label, stop_event),
        daemon=True,
    ).start()


def stop_metronome():
    global running, stop_event
    running = False
    if stop_event is not None:
        try:
            stop_event.set()
        except Exception:
            pass


# ---- NAVIGATION ----
def show_main_menu():
    # ensure any running metronome is stopped when returning to main menu
    try:
        stop_metronome()
    except Exception:
        # defensive: if stop_metronome is not available for some reason,
        # fall back to setting the running flag to False
        try:
            globals()['running'] = False
        except Exception:
            pass
    metronome_frame.pack_forget()
    settings_frame.pack_forget()
    accent_frame.pack_forget()
    main_menu.pack(fill="both", expand=True)


def show_metronome():
    main_menu.pack_forget()
    metronome_frame.pack(fill="both", expand=True)
    setup_emojis()  # adjust number of emojis


def show_settings():
    main_menu.pack_forget()
    metronome_frame.pack_forget()
    accent_frame.pack_forget()
    settings_frame.pack(fill="both", expand=True)


def show_accent_settings():
    # first, ensure the beats value in the settings entry is applied so the
    # Configure Accents screen shows the correct number of checkboxes.
    if not apply_beats_setting():
        return
    settings_frame.pack_forget()
    accent_frame.pack(fill="both", expand=True)
    setup_accent_checkboxes()


# ---- ROOT ----
root = tk.Tk()
root.title("Metronome App")
root.geometry("450x350")
root.resizable(True, True)

# create shared fonts
title_font = tkfont.Font(family="Arial", size=_base_title_size)
label_font = tkfont.Font(family="Arial", size=_base_label_size)
emoji_font = tkfont.Font(family="Arial", size=_base_emoji_size)
button_font = tkfont.Font(family="Arial", size=_base_button_size)


def _apply_scale(factor: float):
    """Apply a continuous scale factor to shared fonts."""
    global _scale_factor, title_font, label_font, emoji_font, button_font
    # clamp factor to reasonable range
    factor = max(1.0, min(factor, 2.0))
    # avoid unnecessary reconfiguration
    if abs(_scale_factor - factor) < 0.01:
        return
    _scale_factor = factor
    title_font.configure(size=max(8, int(_base_title_size * factor)))
    label_font.configure(size=max(8, int(_base_label_size * factor)))
    emoji_font.configure(size=max(10, int(_base_emoji_size * factor)))
    button_font.configure(size=max(8, int(_base_button_size * factor)))


def _on_configure(event=None):
    """Handler for window configure events — detect maximize/zoom and scale UI."""
    try:
        state = root.state()
        if state == 'zoomed':
            _apply_scale(1.4)
            return
        # not zoomed: compute proportional scale based on width
        width = root.winfo_width()
        base = 450
        factor = max(1.0, min(1.8, width / base))
        _apply_scale(factor)
    except Exception:
        # fallback: if window width is large, scale up
        try:
            width = root.winfo_width()
            base = 450
            factor = max(1.0, min(1.8, width / base))
            _apply_scale(factor)
        except Exception:
            pass

# bind configure to adjust scaling
root.bind('<Configure>', _on_configure)

# ---- MAIN MENU ----
main_menu = tk.Frame(root)
main_menu.pack(fill="both", expand=True)
center_frame = tk.Frame(main_menu)
center_frame.pack(expand=True)

tk.Label(center_frame, text="Welcome to the Metronome App", font=title_font).pack(pady=20)
tk.Button(center_frame, text="Open Metronome", command=show_metronome, width=20, height=2, font=button_font).pack(pady=10)
tk.Button(center_frame, text="Settings", command=show_settings, width=20, height=2, font=button_font).pack(pady=10)

# ---- SETTINGS FRAME ----
settings_frame = tk.Frame(root)
tk.Label(settings_frame, text="Settings", font=title_font).pack(pady=15)

beats_frame = tk.Frame(settings_frame)
beats_frame.pack(pady=10)
tk.Label(beats_frame, text="Number of beats:", font=label_font).grid(row=0, column=0, padx=5)
beats_entry_settings = tk.Spinbox(beats_frame, from_=1, to=8, width=5, wrap=True)
beats_entry_settings.delete(0, tk.END)
beats_entry_settings.insert(0, str(num_beats))
beats_entry_settings.grid(row=0, column=1, padx=5)
tk.Label(beats_frame, text="(Must be between 1 and 8)", font=label_font).grid(row=0, column=2, padx=5)


def apply_beats_setting():
    """Validate and apply the number entered in the beats settings entry.

    Returns True if the value was valid and applied, False otherwise.
    """
    global num_beats, accented_beats
    try:
        val = int(beats_entry_settings.get())
        if 1 <= val <= 8:
            num_beats = val
            # trim any accented beats that are now out of range
            accented_beats = [b for b in accented_beats if 1 <= b <= num_beats]
            return True
        else:
            tk.messagebox.showerror("Error", "Beats must be 1-8")
            return False
    except ValueError:
        tk.messagebox.showerror("Error", "Invalid number")
        return False


def save_settings():
    # apply and persist beats from the settings entry, then return to main menu
    if apply_beats_setting():
        show_main_menu()


tk.Button(settings_frame, text="Configure Accents", command=show_accent_settings, width=20, font=button_font).pack(pady=10)
tk.Button(settings_frame, text="Save & Back", command=save_settings, width=20, font=button_font).pack(pady=10)

# ---- ACCENT SETTINGS FRAME ----
accent_frame = tk.Frame(root)
accent_vars = []


def setup_accent_checkboxes():
    global accent_vars
    for widget in accent_frame.winfo_children():
        widget.destroy()
    tk.Label(accent_frame, text="Select beats to accent", font=label_font).pack(pady=10)
    checkbox_frame = tk.Frame(accent_frame)
    checkbox_frame.pack()
    accent_vars = []
    for i in range(num_beats):
        var = tk.BooleanVar(value=(i + 1 in accented_beats))
        chk = tk.Checkbutton(checkbox_frame, text=str(i + 1), variable=var, font=button_font)
        chk.grid(row=0, column=i, padx=5)
        accent_vars.append(var)

    def save_accents():
        global accented_beats
        accented_beats = [i + 1 for i, var in enumerate(accent_vars) if var.get()]
        show_settings()

    tk.Button(accent_frame, text="Save & Back", command=save_accents, width=15, font=button_font).pack(pady=20)


# ---- METRONOME FRAME ----
metronome_frame = tk.Frame(root)
tk.Label(metronome_frame, text="BPM:", font=label_font).grid(row=0, column=0, padx=5, pady=5)
bpm_entry = tk.Spinbox(metronome_frame, from_=1, to=208, width=5, wrap=True)
bpm_entry.delete(0, tk.END)
bpm_entry.insert(0, "100")
bpm_entry.grid(row=0, column=1)


start_button = tk.Button(metronome_frame, text="Start", command=start_metronome, font=button_font)
start_button.grid(row=1, column=0, pady=10)
stop_button = tk.Button(metronome_frame, text="Stop", command=stop_metronome, font=button_font)
stop_button.grid(row=1, column=1, pady=10)

beat_label = tk.Label(metronome_frame, text="Ready", font=label_font)
beat_label.grid(row=2, column=0, columnspan=2, pady=5)

# Emoji display
emoji_frame = tk.Frame(metronome_frame)
emoji_frame.grid(row=3, column=0, columnspan=2, pady=10)
emoji_labels = []


def setup_emojis():
    for widget in emoji_frame.winfo_children():
        widget.destroy()
    global emoji_labels
    emoji_labels = []
    # ensure metronome_frame columns expand so emoji_frame can be centered
    try:
        metronome_frame.grid_columnconfigure(0, weight=1)
        metronome_frame.grid_columnconfigure(1, weight=1)
    except Exception:
        pass

    # pack labels horizontally inside emoji_frame so they stay centered
    for i in range(num_beats):
        lbl = tk.Label(emoji_frame, text="🖐", font=emoji_font)
        lbl.pack(side='left', padx=5)
        emoji_labels.append(lbl)


back_button = tk.Button(metronome_frame, text="← Back", command=show_main_menu, font=button_font)
back_button.grid(row=4, column=0, columnspan=2, pady=10)

root.mainloop()
