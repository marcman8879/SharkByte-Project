import os
import time
import threading
import math

try:
    import pygame
except Exception:
    pygame = None

import tkinter as tk
import tkinter.font as tkfont

try:
    import pretty_midi
except Exception:
    pretty_midi = None

# Optional audio backends
NP_AVAILABLE = False
SA_AVAILABLE = False
FLUIDSYNTH_AVAILABLE = False
try:
    import numpy as np
    NP_AVAILABLE = True
except Exception:
    np = None

try:
    import simpleaudio as sa
    SA_AVAILABLE = True
except Exception:
    sa = None

try:
    import fluidsynth
    FLUIDSYNTH_AVAILABLE = True
except Exception:
    fluidsynth = None

# Basic UI / layout constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 720
LEFT_MARGIN = 80
TOP_MARGIN = 80
BOTTOM_MARGIN = 80
NOTE_RADIUS = 8
PIXELS_PER_SECOND = 150
END_WAIT_SECONDS = 2.0

BUTTON_WIDTH = 300
BUTTON_HEIGHT = 80
BACKGROUND_COLOR = (30, 30, 30)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 160, 210)
BUTTON_TEXT_COLOR = (255, 255, 255)

# Mapping dictionary: original_pitch -> mapped_pitch
mapped_notes = {}
# MIDI / synth outputs
midi_out = None


# Simple metronome helpers (minimal, used by the Tk metronome screen)
_metronome_stop = None

def _play_click(high=True):
    try:
        import platform
        if platform.system() == 'Windows':
            import winsound
            freq = 880 if high else 440
            winsound.Beep(freq, 80)
        else:
            # fallback: use simpleaudio + numpy if available
            if NP_AVAILABLE and SA_AVAILABLE:
                sample_rate = 44100
                duration = 0.08
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                freq = 880 if high else 440
                tone = np.sin(freq * t * 2 * math.pi)
                audio = (tone * 32767).astype(np.int16)
                sa.play_buffer(audio, 1, 2, sample_rate)
            elif SA_AVAILABLE:
                # try simple beep
                sa.play_buffer(b"\x00\x00", 1, 2, 44100)
    except Exception:
        pass


def metronome_thread(bpm, beats, stop_event, beat_callback=None, accented_beats=None):
    interval = 60.0 / max(1, int(bpm))
    beat = 1
    if accented_beats is None:
        accented_beats = [1]
    try:
        while not stop_event.is_set():
            # call visual callback (accented if current beat in accented_beats)
            try:
                accented = (beat in accented_beats)
                if beat_callback:
                    beat_callback(accented)
            except Exception:
                pass
            # play click (accented/high on accented beats)
            _play_click(high=(beat in accented_beats))
            # advance
            beat = (beat % beats) + 1
            stop_event.wait(interval)
    finally:
        try:
            if beat_callback:
                beat_callback(False)
        except Exception:
            pass


def start_metronome(tempo_var, status_var=None, beat_callback=None, beats=4, accented_beats=None):
    global _metronome_stop
    # stop existing
    try:
        if _metronome_stop is not None:
            _metronome_stop.set()
    except Exception:
        pass
    try:
        bpm = int(tempo_var.get())
    except Exception:
        bpm = 100
    stop_event = threading.Event()
    _metronome_stop = stop_event
    # pass accented_beats to thread
    threading.Thread(target=metronome_thread, args=(bpm, beats, stop_event, beat_callback, accented_beats), daemon=True).start()
    if status_var is not None:
        try:
            status_var.set('Running')
        except Exception:
            pass


def stop_metronome(status_var=None):
    global _metronome_stop
    try:
        if _metronome_stop is not None:
            _metronome_stop.set()
    except Exception:
        pass
    _metronome_stop = None
    if status_var is not None:
        try:
            status_var.set('Stopped')
        except Exception:
            pass


def load_midi(path):
    """Load a MIDI file and return (pm, notes, lowest, highest, end_time, num_keys).
    notes is a list of dicts with keys: start, end, pitch
    """
    if pretty_midi is None:
        # Minimal parser fallback: raise
        raise RuntimeError('pretty_midi is required to load MIDI files')
    pm = pretty_midi.PrettyMIDI(path)
    notes = []
    lowest = 127
    highest = 0
    end_time = 0.0
    for inst in pm.instruments:
        for n in inst.notes:
            notes.append({'start': n.start, 'end': n.end, 'pitch': n.pitch})
            lowest = min(lowest, n.pitch)
            highest = max(highest, n.pitch)
            end_time = max(end_time, n.end)
    if lowest > highest:
        lowest = 60
        highest = 72
    num_keys = highest - lowest + 1
    return pm, notes, lowest, highest, end_time, num_keys


def play_note_sound(pitch, duration=0.5):
    """Play a short tone for the given MIDI pitch. Uses simpleaudio/numpy if available, otherwise winsound on Windows."""
    try:
        freq = 440.0 * (2 ** ((pitch - 69) / 12.0))
    except Exception:
        return
    try:
        import platform
        if platform.system() == 'Windows':
            try:
                import winsound
                # run winsound.Beep in a short thread so it doesn't block the UI loop
                threading.Thread(target=lambda: winsound.Beep(int(freq), int(duration * 1000)), daemon=True).start()
                return
            except Exception:
                pass
        if NP_AVAILABLE and SA_AVAILABLE:
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(freq * t * 2 * math.pi)
            audio = (tone * 32767).astype(np.int16)
            try:
                sa.play_buffer(audio, 1, 2, sample_rate)
            except Exception:
                pass
    except Exception:
        pass

def run_music_sheet():
    """Run the music sheet viewer using the Music Sheet Mover layout."""
    if not pygame.get_init():
        pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Music Sheet Mover")
    clock = pygame.time.Clock()

    # Directory for MIDI files
    MIDI_DIR = os.path.expanduser("~/Music")
    if not os.path.exists(MIDI_DIR):
        MIDI_DIR = "."
    midi_files = [f for f in os.listdir(MIDI_DIR) if f.lower().endswith(('.mid', '.midi'))]
    selected_midi = midi_files[0] if midi_files else None

    # UI state
    dropdown_open = False
    dropdown_padding = 8
    time_display_width = 200
    dropdown_h = 30

    # Playback state (initialized when a file is loaded)
    pm = None
    notes = []
    lowest_pitch = 60
    highest_pitch = 72
    midi_end_time = 0.0
    NUM_KEYS = highest_pitch - lowest_pitch + 1
    prev_playing = set()

    app_active = True
    running = True
    start_time = 0.0
    end_timer_started = False
    end_timer_start = 0.0

    # Back button will be drawn in-play
    font_local = pygame.font.SysFont(None, 18)
    title_font = pygame.font.SysFont(None, 36)

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
                    # toggle fullscreen if desired
                    try:
                        pygame.display.toggle_fullscreen()
                    except Exception:
                        pass
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # dropdown rect (centered)
                dropdown_w = min(400, SCREEN_WIDTH - 2 * dropdown_padding)
                dropdown_x = (SCREEN_WIDTH - dropdown_w) // 2
                dropdown_y = 80
                dd_rect = pygame.Rect(dropdown_x, dropdown_y, dropdown_w, dropdown_h)

                # back button top-right
                back_rect = pygame.Rect(SCREEN_WIDTH - 100 - dropdown_padding, dropdown_padding, 80, dropdown_h)
                if back_rect.collidepoint(mx, my):
                    return 'main'

                if dd_rect.collidepoint(mx, my):
                    dropdown_open = not dropdown_open
                elif dropdown_open:
                    # check items
                    for idx, fname in enumerate(midi_files):
                        item_rect = pygame.Rect(dropdown_x, dropdown_y + (idx+1) * dropdown_h, dropdown_w, dropdown_h)
                        if item_rect.collidepoint(mx, my):
                            # load selected midi and start playback
                            selected_midi = fname
                            try:
                                path = os.path.join(MIDI_DIR, selected_midi)
                                pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(path)
                                # init playback
                                globals()['notes_list'] = sorted(notes, key=lambda n: n['start'])
                                globals()['next_note_idx'] = 0
                                # don't auto-start; wait for user to press Play
                                globals()['is_playing'] = False
                                globals()['play_start_time'] = 0.0
                                globals()['paused_at'] = 0.0
                                globals()['active_notes'] = []
                                prev_playing = set()
                                end_timer_started = False
                                end_timer_start = 0.0
                            except Exception as e:
                                print('Failed to load MIDI:', e)
                            dropdown_open = False
                            break
                # Play/Stop controls (click handling) if a file is loaded
                if globals().get('notes_list'):
                    info_y = TOP_MARGIN + 60
                    play_rect = pygame.Rect(LEFT_MARGIN, info_y + 36, 80, 28)
                    stop_rect = pygame.Rect(LEFT_MARGIN + 90, info_y + 36, 80, 28)
                    if play_rect.collidepoint(mx, my):
                        # start playback from beginning
                        globals()['is_playing'] = True
                        globals()['play_start_time'] = time.time()
                        globals()['paused_at'] = 0.0
                        globals()['notes_list'] = sorted(globals().get('notes_list', []), key=lambda n: n['start'])
                        globals()['next_note_idx'] = 0
                        globals()['active_notes'] = []
                        prev_playing = set()
                    if stop_rect.collidepoint(mx, my):
                        globals()['is_playing'] = False
                        globals()['paused_at'] = 0.0
                        globals()['next_note_idx'] = 0
                        globals()['active_notes'] = []

        # Draw background and UI similar to music sheet mover
        screen.fill((255,255,255))

        # Title
        title = title_font.render('Music Sheet Mover', True, (0,0,0))
        screen.blit(title, ((SCREEN_WIDTH - title.get_width())//2, 20))

        # Dropdown
        dropdown_w = min(400, SCREEN_WIDTH - 2 * dropdown_padding)
        dropdown_x = (SCREEN_WIDTH - dropdown_w) // 2
        dropdown_y = 80
        dd_rect = pygame.Rect(dropdown_x, dropdown_y, dropdown_w, dropdown_h)
        pygame.draw.rect(screen, (240,240,240), dd_rect)
        pygame.draw.rect(screen, (0,0,0), dd_rect, 2)
        sel_text = selected_midi if selected_midi else 'No MIDI files'
        txt = font_local.render(f'Selected: {sel_text}', True, (0,0,0))
        txt_x = dropdown_x + (dropdown_w - txt.get_width()) // 2
        screen.blit(txt, (txt_x, dropdown_y + (dropdown_h - txt.get_height()) // 2))

        if dropdown_open:
            max_visible = min(len(midi_files), (SCREEN_HEIGHT - dropdown_y - dropdown_h - BOTTOM_MARGIN) // dropdown_h)
            list_bg = pygame.Rect(dropdown_x, dropdown_y + dropdown_h, dropdown_w, max_visible * dropdown_h)
            pygame.draw.rect(screen, (255,255,255), list_bg)
            pygame.draw.rect(screen, (0,0,0), list_bg, 1)
            for idx, fname in enumerate(midi_files[:max_visible]):
                item_rect = pygame.Rect(dropdown_x, dropdown_y + (idx+1) * dropdown_h, dropdown_w, dropdown_h)
                if fname == selected_midi:
                    pygame.draw.rect(screen, (200,230,255), item_rect)
                pygame.draw.rect(screen, (0,0,0), item_rect, 1)
                item_txt = font_local.render(fname, True, (0,0,0))
                txt_x = item_rect.x + (item_rect.w - item_txt.get_width()) // 2
                txt_y = item_rect.y + (item_rect.h - item_txt.get_height()) // 2
                screen.blit(item_txt, (txt_x, txt_y))

        # If a MIDI is loaded, render notes and playhead
        if globals().get('notes_list'):
            notes_local = globals().get('notes_list')
            # current time
            if globals().get('is_playing', False):
                current_time = time.time() - globals().get('play_start_time', 0.0)
            else:
                current_time = globals().get('paused_at', 0.0)

            # Draw horizontal lines and labels
            line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / NUM_KEYS
            for pitch in range(lowest_pitch, highest_pitch + 1):
                y = TOP_MARGIN + (highest_pitch - pitch) * line_spacing
                color = (0,0,0)
                width = 1
                for note in notes_local:
                    if note['start'] <= current_time <= note['end'] and note['pitch'] == pitch:
                        color = (0,128,0)
                        width = 3
                pygame.draw.line(screen, color, (LEFT_MARGIN, y), (SCREEN_WIDTH, y), width)
                label = font_local.render(midi_to_name(pitch), True, (0,0,0))
                screen.blit(label, (5, y-7))

            # Playhead
            playhead_x = SCREEN_WIDTH // 2
            # thicker playhead and small triangle indicator
            pygame.draw.line(screen, (220,20,60), (playhead_x, 0), (playhead_x, SCREEN_HEIGHT), 3)
            pygame.draw.polygon(screen, (220,20,60), [(playhead_x, 6), (playhead_x-8, 18), (playhead_x+8, 18)])

            # Draw notes and detect currently playing
            playing_pitches = set()
            for note in notes_local:
                # draw as horizontal capsule showing duration
                start_x = playhead_x + (note['start'] - current_time) * PIXELS_PER_SECOND
                end_x = playhead_x + (note['end'] - current_time) * PIXELS_PER_SECOND
                note_y = TOP_MARGIN + (highest_pitch - note['pitch']) * line_spacing
                if end_x < -50 or start_x > SCREEN_WIDTH + 50:
                    continue
                rect_x = int(min(start_x, end_x))
                rect_w = max(6, int(abs(end_x - start_x)))
                rect_h = NOTE_RADIUS * 2
                pygame.draw.ellipse(screen, (40,40,120), (rect_x, int(note_y-rect_h//2), rect_w, rect_h))
                pygame.draw.ellipse(screen, (0,0,0), (rect_x, int(note_y-rect_h//2), rect_w, rect_h), 1)
                if note['start'] <= current_time <= note['end']:
                    playing_pitches.add(note['pitch'])

            # Note on/off handling (trigger sounds only once when note starts)
            new_on = playing_pitches - prev_playing
            new_off = prev_playing - playing_pitches
            # prefer MIDI out / fluidsynth if available
            try:
                midi_out
            except NameError:
                midi_out_local = None
            else:
                midi_out_local = globals().get('midi_out', None)

            if midi_out_local:
                for p in new_on:
                    if p in mapped_notes:
                        try:
                            midi_out_local.note_on(int(mapped_notes[p]), 100)
                        except Exception:
                            pass
            elif FLUIDSYNTH_AVAILABLE and globals().get('fs') and globals().get('sf2_path'):
                for p in new_on:
                    pitch = mapped_notes.get(p, p)
                    try:
                        globals()['fs'].noteon(0, int(pitch), 100)
                    except Exception as e:
                        print('FluidSynth note on error:', e)
            else:
                for p in new_on:
                    mapped = mapped_notes.get(p, p)
                    # play sounds for newly started notes
                    play_note_sound(mapped, duration=max(0.05, 0.5))

            # note offs for midi_out / fluidsynth
            if midi_out_local:
                for p in new_off:
                    if p in mapped_notes:
                        try:
                            midi_out_local.note_off(int(mapped_notes[p]), 0)
                        except Exception:
                            pass
            elif FLUIDSYNTH_AVAILABLE and globals().get('fs') and globals().get('sf2_path'):
                for p in new_off:
                    pitch = mapped_notes.get(p, p)
                    try:
                        globals()['fs'].noteoff(0, int(pitch))
                    except Exception as e:
                        print('FluidSynth note off error:', e)

            prev_playing = playing_pitches

            # Time display (top-left)
            time_text = f"Time: {current_time:.2f} / {midi_end_time:.2f} s"
            time_bg_rect = pygame.Rect(dropdown_padding, dropdown_padding, time_display_width, dropdown_h)
            pygame.draw.rect(screen, (240,240,240), time_bg_rect)
            pygame.draw.rect(screen, (0,0,0), time_bg_rect, 1)
            time_label = font_local.render(time_text, True, (0,0,0))
            screen.blit(time_label, (time_bg_rect.x + 6, time_bg_rect.y + 6))

            # End handling
            if current_time >= midi_end_time and not end_timer_started:
                end_timer_started = True
                end_timer_start = time.time()
            if end_timer_started and (time.time() - end_timer_start) >= END_WAIT_SECONDS:
                globals()['is_playing'] = False
                globals()['paused_at'] = 0.0
                end_timer_started = False

        # Back button (top-right)
        back_rect = pygame.Rect(SCREEN_WIDTH - 100 - dropdown_padding, dropdown_padding, 80, dropdown_h)
        pygame.draw.rect(screen, (200,200,200), back_rect)
        pygame.draw.rect(screen, (0,0,0), back_rect, 1)
        back_text = font_local.render("Back", True, (0,0,0))
        screen.blit(back_text, (back_rect.x + (back_rect.w - back_text.get_width())//2, back_rect.y + 6))

        pygame.display.flip()


# -----------------------------
# UI Classes
# -----------------------------
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def midi_to_name(pitch):
    octave = (pitch // 12) - 1
    name = NOTE_NAMES[pitch % 12]
    return f"{name}{octave}"

class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False
        
    def draw(self, screen, font):
        color = BUTTON_HOVER_COLOR if self.hovered else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 2)
        
        text_surface = font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.hovered and self.action:
                return self.action()
        return None

# -----------------------------
# Screen Functions
# -----------------------------
def run_main_menu():
    """Main menu screen with options to choose Metronome or Music Sheet Viewer."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Music Companion")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)
    title_font = pygame.font.SysFont(None, 64)
    
    # Calculate button positions
    center_x = SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2
    first_button_y = SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 1.5
    second_button_y = SCREEN_HEIGHT // 2 + BUTTON_HEIGHT // 2
    
    metronome_button = Button(center_x, first_button_y, BUTTON_WIDTH, BUTTON_HEIGHT, 
                            "Metronome", lambda: "metronome")
    sheet_button = Button(center_x, second_button_y, BUTTON_WIDTH, BUTTON_HEIGHT, 
                         "Music Sheet Viewer", lambda: "sheet")
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            
            result = metronome_button.handle_event(event)
            if result:
                return result
                
            result = sheet_button.handle_event(event)
            if result:
                return result
        
        # Draw
        screen.fill(BACKGROUND_COLOR)
        
        # Draw title
        title = title_font.render("Music Companion", True, BUTTON_TEXT_COLOR)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, TOP_MARGIN * 2))
        screen.blit(title, title_rect)
        
        metronome_button.draw(screen, font)
        sheet_button.draw(screen, font)
        
        pygame.display.flip()
        clock.tick(60)

def run_metronome():
    """Run the metronome application."""
    root = tk.Tk()
    root.title("Metronome")
    root.geometry("400x600")
    root.configure(bg='#2C2C2C')
    
    # Variables
    tempo_var = tk.StringVar(value="120")
    status_var = tk.StringVar(value="Ready")
    
    # Fonts
    title_font = tkfont.Font(family="Arial", size=16, weight="bold")
    label_font = tkfont.Font(family="Arial", size=14)
    button_font = tkfont.Font(family="Arial", size=12)
    
    # Title
    tk.Label(root, text="Metronome", font=title_font, bg='#2C2C2C', fg='white').pack(pady=20)
    
    # Tempo Entry
    tempo_frame = tk.Frame(root, bg='#2C2C2C')
    tempo_frame.pack(pady=20)
    tk.Label(tempo_frame, text="Tempo (BPM):", font=label_font, bg='#2C2C2C', fg='white').pack(side=tk.LEFT, padx=5)
    tk.Entry(tempo_frame, textvariable=tempo_var, width=6, font=label_font).pack(side=tk.LEFT, padx=5)

    # Beats (time signature) and accent controls
    beats_var = tk.IntVar(value=4)
    beats_frame = tk.Frame(root, bg='#2C2C2C')
    beats_frame.pack(pady=6)
    tk.Label(beats_frame, text="Beats per bar:", font=label_font, bg='#2C2C2C', fg='white').pack(side=tk.LEFT, padx=5)
    tk.Spinbox(beats_frame, from_=1, to=12, textvariable=beats_var, width=4, font=label_font).pack(side=tk.LEFT, padx=5)

    accents_container = tk.Frame(root, bg='#2C2C2C')
    accents_container.pack(pady=6)
    accent_vars = []

    def rebuild_accent_checkboxes(*_):
        # clear
        for w in accents_container.winfo_children():
            w.destroy()
        accent_vars.clear()
        n = max(1, int(beats_var.get()))
        tk.Label(accents_container, text='Accent beats:', font=label_font, bg='#2C2C2C', fg='white').pack(side=tk.LEFT, padx=(0,8))
        for i in range(n):
            v = tk.IntVar(value=1 if i == 0 else 0)
            chk = tk.Checkbutton(accents_container, text=str(i+1), variable=v, bg='#2C2C2C', fg='white', selectcolor='#2C2C2C', activebackground='#2C2C2C')
            chk.pack(side=tk.LEFT, padx=2)
            accent_vars.append(v)

    beats_var.trace_add('write', rebuild_accent_checkboxes)
    rebuild_accent_checkboxes()
    
    # Visual beat indicator
    canvas = tk.Canvas(root, width=120, height=120, bg='#2C2C2C', highlightthickness=0)
    canvas.pack(pady=10)
    # circle will show beat flashes
    circle = canvas.create_oval(10, 10, 110, 110, fill='#444444', outline='')

    def flash_indicator(accented):
        # accented -> red, normal -> yellow
        color = '#FF5555' if accented else '#FFD86B'
        try:
            canvas.itemconfig(circle, fill=color)
            # reset after short delay
            root.after(120, lambda: canvas.itemconfig(circle, fill='#444444'))
        except Exception:
            pass

    # start/stop buttons wired to metronome; pass visual callback
    def _on_start():
        accented = [i+1 for i, v in enumerate(accent_vars) if v.get()]
        start_metronome(tempo_var, status_var, beat_callback=lambda a: root.after(0, lambda: flash_indicator(a)), beats=int(beats_var.get()), accented_beats=accented)

    def _on_stop():
        stop_metronome(status_var)
        try:
            canvas.itemconfig(circle, fill='#444444')
        except Exception:
            pass

    tk.Button(root, text="Start", command=_on_start,
              font=button_font, bg='#4CAF50', fg='white', width=15).pack(pady=10)
    tk.Button(root, text="Stop", command=_on_stop,
              font=button_font, bg='#F44336', fg='white', width=15).pack(pady=10)
    
    # Status
    tk.Label(root, textvariable=status_var, font=label_font, bg='#2C2C2C', fg='white').pack(pady=20)
    
    # Back Button
    back_button = tk.Button(root, text="Back to Main Menu", command=root.destroy,
                           font=button_font, bg='#555555', fg='white', width=15)
    back_button.pack(side=tk.BOTTOM, pady=20)
    
    root.mainloop()

def run_music_sheet():
    """Run the music sheet viewer application."""
    # Initialize pygame if not already initialized
    if not pygame.get_init():
        pygame.init()
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Music Sheet Viewer")
    clock = pygame.time.Clock()
    
    # Directory for MIDI files
    MIDI_DIR = os.path.expanduser("~/Music")  # Default to user's Music folder
    if not os.path.exists(MIDI_DIR):
        MIDI_DIR = "."  # Fallback to current directory
    
    midi_files = [f for f in os.listdir(MIDI_DIR) if f.lower().endswith('.mid')]
    midi_index = 0
    selected_midi = None if not midi_files else midi_files[midi_index]
    loaded_info = None  # store tuple (pm, notes, lowest, highest, end_time, num_keys)
    
    # Create back button
    back_button = Button(SCREEN_WIDTH - 110, SCREEN_HEIGHT - 60, 100, 40, "Back", lambda: "main")
    
    running = True
    font = pygame.font.SysFont(None, 28)
    big_font = pygame.font.SysFont(None, 36)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # back button
                if back_button.rect.collidepoint(mx, my):
                    return "main"
                # left/right/select/load controls
                if midi_files:
                    left_rect = pygame.Rect(LEFT_MARGIN, TOP_MARGIN, 36, 36)
                    right_rect = pygame.Rect(LEFT_MARGIN + 40, TOP_MARGIN, 36, 36)
                    load_rect = pygame.Rect(LEFT_MARGIN + 90, TOP_MARGIN, 120, 32)
                    if left_rect.collidepoint(mx, my):
                        midi_index = (midi_index - 1) % len(midi_files)
                        selected_midi = midi_files[midi_index]
                        loaded_info = None
                    elif right_rect.collidepoint(mx, my):
                        midi_index = (midi_index + 1) % len(midi_files)
                        selected_midi = midi_files[midi_index]
                        loaded_info = None
                    elif load_rect.collidepoint(mx, my):
                        # attempt to load the selected midi
                        try:
                            path = os.path.join(MIDI_DIR, selected_midi)
                            loaded_info = load_midi(path)
                            # prepare playback state
                            if loaded_info and loaded_info[1]:
                                globals()['notes_list'] = sorted(loaded_info[1], key=lambda n: n['start'])
                                globals()['next_note_idx'] = 0
                                globals()['is_playing'] = False
                                globals()['play_start_time'] = 0.0
                                globals()['paused_at'] = 0.0
                                globals()['active_notes'] = []  # list of (pitch, end_time)
                        except Exception as e:
                            loaded_info = (None, None, None, None, None, None)
                    # clicking on key labels (left side) should play the mapped note
                    if loaded_info and loaded_info[0] is not None:
                        pm, notes, low, high, end_time, nkeys = loaded_info
                        line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / (high - low + 1)
                        for pitch in range(low, high + 1):
                            y = TOP_MARGIN + (high - pitch) * line_spacing
                            label_rect = pygame.Rect(5, int(y-12), 60, 20)
                            if label_rect.collidepoint(mx, my):
                                mapped = mapped_notes.get(pitch, pitch)
                                play_note_sound(mapped, duration=0.5)
                                break
                    # playback control clicks
                    if loaded_info and loaded_info[0] is not None:
                        info_y = TOP_MARGIN + 60
                        play_rect = pygame.Rect(LEFT_MARGIN, info_y + 36, 80, 28)
                        stop_rect = pygame.Rect(LEFT_MARGIN + 90, info_y + 36, 80, 28)
                        if play_rect.collidepoint(mx, my):
                            if not globals().get('is_playing', False):
                                globals()['is_playing'] = True
                                globals()['play_start_time'] = time.time() - globals().get('paused_at', 0.0)
                                globals()['notes_list'] = sorted(loaded_info[1], key=lambda n: n['start'])
                                # set next_note_idx to first note after paused time
                                paused = globals().get('paused_at', 0.0)
                                idx = 0
                                nl = globals()['notes_list']
                                while idx < len(nl) and nl[idx]['start'] <= paused:
                                    idx += 1
                                globals()['next_note_idx'] = idx
                                globals()['active_notes'] = []
                        if stop_rect.collidepoint(mx, my):
                            globals()['is_playing'] = False
                            globals()['paused_at'] = 0.0
                            globals()['next_note_idx'] = 0
                            globals()['active_notes'] = []

        screen.fill(BACKGROUND_COLOR)

        # Header
        title = big_font.render("Music Sheet Viewer", True, BUTTON_TEXT_COLOR)
        screen.blit(title, (LEFT_MARGIN, 10))

    # Draw selection controls
        if not midi_files:
            text = big_font.render("No MIDI files found in " + MIDI_DIR, True, BUTTON_TEXT_COLOR)
            screen.blit(text, (LEFT_MARGIN, TOP_MARGIN + 40))
        else:
            # left/right arrows and load button
            left_rect = pygame.Rect(LEFT_MARGIN, TOP_MARGIN, 36, 36)
            right_rect = pygame.Rect(LEFT_MARGIN + 40, TOP_MARGIN, 36, 36)
            load_rect = pygame.Rect(LEFT_MARGIN + 90, TOP_MARGIN, 120, 32)
            pygame.draw.rect(screen, (180,180,180), left_rect)
            pygame.draw.polygon(screen, (30,30,30), [(LEFT_MARGIN+24, TOP_MARGIN+8), (LEFT_MARGIN+12, TOP_MARGIN+18), (LEFT_MARGIN+24, TOP_MARGIN+28)])
            pygame.draw.rect(screen, (180,180,180), right_rect)
            pygame.draw.polygon(screen, (30,30,30), [(LEFT_MARGIN+52, TOP_MARGIN+8), (LEFT_MARGIN+64, TOP_MARGIN+18), (LEFT_MARGIN+52, TOP_MARGIN+28)])
            pygame.draw.rect(screen, (100,200,100), load_rect)
            screen.blit(font.render("Load", True, (0,0,0)), (load_rect.x + 28, load_rect.y + 6))

            # current selection
            sel_text = font.render(f"{midi_index+1}/{len(midi_files)}: {selected_midi}", True, BUTTON_TEXT_COLOR)
            screen.blit(sel_text, (LEFT_MARGIN + 220, TOP_MARGIN + 6))

            # If loaded, show basic info and create a music-sheet-mover-style view
            if loaded_info and loaded_info[0] is not None:
                pm, notes, low, high, end_time, nkeys = loaded_info
                info_y = TOP_MARGIN + 60
                screen.blit(font.render(f"Notes: {len(notes)}", True, BUTTON_TEXT_COLOR), (LEFT_MARGIN, info_y))
                screen.blit(font.render(f"Duration: {end_time:.2f}s", True, BUTTON_TEXT_COLOR), (LEFT_MARGIN + 140, info_y))
                screen.blit(font.render(f"Range: {low} - {high}", True, BUTTON_TEXT_COLOR), (LEFT_MARGIN + 320, info_y))

                # Music-sheet-mover style rendering
                # compute playhead in middle of screen (stationary) and render notes moving
                playhead_x = SCREEN_WIDTH // 2
                pygame.draw.line(screen, (255,0,0), (playhead_x, 0), (playhead_x, SCREEN_HEIGHT), 2)

                # playback timing
                if globals().get('is_playing', False):
                    current_time = time.time() - globals().get('play_start_time', 0.0)
                else:
                    current_time = globals().get('paused_at', 0.0)

                # draw horizontal lines and pitch labels
                line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / (high - low + 1)
                prev_playing = globals().get('prev_playing', set())
                playing_pitches = set()
                for pitch in range(low, high + 1):
                    y = TOP_MARGIN + (high - pitch) * line_spacing
                    color = (100,100,100)
                    width = 1
                    # highlight if any note occupying this pitch at current_time
                    for note in notes:
                        if note['start'] <= current_time <= note['end'] and note['pitch'] == pitch:
                            color = (0,150,0)
                            width = 3
                    pygame.draw.line(screen, color, (LEFT_MARGIN, y), (SCREEN_WIDTH, y), width)
                    # key label
                    lbl = font.render(midi_to_name(pitch), True, BUTTON_TEXT_COLOR)
                    screen.blit(lbl, (5, y-7))

                # draw notes as circles moving relative to playhead
                for note in notes:
                    note_x = playhead_x + (note['start'] - current_time) * PIXELS_PER_SECOND
                    note_y = TOP_MARGIN + (high - note['pitch']) * line_spacing
                    if -50 <= note_x <= SCREEN_WIDTH + 50:
                        pygame.draw.circle(screen, (0,0,0), (int(note_x), int(note_y)), NOTE_RADIUS)
                    # collect currently playing
                    if note['start'] <= current_time <= note['end']:
                        playing_pitches.add(note['pitch'])

                # detect note-on events (new_on) and play sounds
                new_on = playing_pitches - prev_playing
                new_off = prev_playing - playing_pitches
                for p in new_on:
                    # trigger a synthed note, using mapping if present
                    mapped = mapped_notes.get(p, p)
                    play_note_sound(mapped, duration=0.5)
                # note-off does nothing for simple synth
                globals()['prev_playing'] = playing_pitches

                # Draw current time and total duration (top-left)
                time_text = f"Time: {current_time:.2f} / {end_time:.2f} s"
                time_bg_rect = pygame.Rect(LEFT_MARGIN//2, 8, 160, 24)
                pygame.draw.rect(screen, (240,240,240), time_bg_rect)
                pygame.draw.rect(screen, (0,0,0), time_bg_rect, 1)
                time_label = font.render(time_text, True, (0,0,0))
                screen.blit(time_label, (time_bg_rect.x + 6, time_bg_rect.y + 2))

                # end-of-play handling
                if current_time >= end_time and not globals().get('end_timer_started', False):
                    globals()['end_timer_started'] = True
                    globals()['end_timer_start'] = time.time()
                if globals().get('end_timer_started', False) and (time.time() - globals().get('end_timer_start', 0.0)) >= END_WAIT_SECONDS:
                    globals()['is_playing'] = False
                    globals()['paused_at'] = 0.0
                    globals()['end_timer_started'] = False

                # playhead is already drawn at playhead_x earlier; playback timing handled above

        # Draw back button
        back_button.draw(screen, big_font)

        pygame.display.flip()
        clock.tick(60)

# -----------------------------
# Main Loop
# -----------------------------
def main():
    while True:
        choice = run_main_menu()
        
        if choice == "quit":
            break
        elif choice == "metronome":
            run_metronome()
        elif choice == "sheet":
            result = run_music_sheet()
            if result == "quit":
                break
    
    pygame.quit()

if __name__ == "__main__":
    main()