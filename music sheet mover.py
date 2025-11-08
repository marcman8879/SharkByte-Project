import pygame
import pretty_midi
import time
import os
try:
    import pygame.midi
    PYGAME_MIDI_AVAILABLE = True
except Exception:
    PYGAME_MIDI_AVAILABLE = False

try:
    import fluidsynth
    FLUIDSYNTH_AVAILABLE = True
except Exception:
    FLUIDSYNTH_AVAILABLE = False

# -----------------------------
# Configuration
# -----------------------------
MIDI_FILE = r"C:\Users\godzi\Downloads\untitled.mid"  # Replace with your MIDI file path
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 600
LEFT_MARGIN = 100  # Space for key labels
TOP_MARGIN = 20
BOTTOM_MARGIN = 20
NOTE_RADIUS = 8
PIXELS_PER_SECOND = 200  # Scrolling speed
END_WAIT_SECONDS = 3  # Time to wait after reaching end

# -----------------------------
# MIDI loading utility
# -----------------------------
def load_midi(midi_path):
    pm_local = pretty_midi.PrettyMIDI(midi_path)
    notes_local = []
    for instrument in pm_local.instruments:
        for note in instrument.notes:
            notes_local.append({'start': note.start, 'end': note.end, 'pitch': note.pitch})

    if notes_local:
        lowest_pitch_local = min(n['pitch'] for n in notes_local)
        highest_pitch_local = max(n['pitch'] for n in notes_local)
        midi_end_time_local = max(n['end'] for n in notes_local)
    else:
        lowest_pitch_local = 21
        highest_pitch_local = 108
        midi_end_time_local = 60

    num_keys_local = highest_pitch_local - lowest_pitch_local + 1
    return pm_local, notes_local, lowest_pitch_local, highest_pitch_local, midi_end_time_local, num_keys_local


# initially load the default MIDI
pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(MIDI_FILE)

# Directory containing MIDI files (default to the MIDI_FILE's folder or cwd)
MIDI_DIR = os.path.dirname(MIDI_FILE) if os.path.isdir(os.path.dirname(MIDI_FILE)) else os.getcwd()
midi_files = [f for f in os.listdir(MIDI_DIR) if f.lower().endswith(('.mid', '.midi'))]
selected_midi = os.path.basename(MIDI_FILE) if os.path.basename(MIDI_FILE) in midi_files else (midi_files[0] if midi_files else None)

# Dropdown UI state
dropdown_open = False
dropdown_x = LEFT_MARGIN
dropdown_y = 5
dropdown_w = 400
dropdown_h = 28

# mapping from target MIDI pitches (C4..B4) to replacement MIDI pitch
# default empty (no mapping)
mapped_notes = {}

# MIDI/audio output setup
midi_out = None
fs = None
sf2_path = None
current_preset = 0

if PYGAME_MIDI_AVAILABLE:
    try:
        pygame.midi.init()
        midi_out = pygame.midi.Output(pygame.midi.get_default_output_id())
    except Exception:
        midi_out = None

if FLUIDSYNTH_AVAILABLE:
    try:
        fs = fluidsynth.Synth()
        fs.start()
    except Exception as e:
        print("FluidSynth error:", e)
        fs = None

# -----------------------------
# Helper functions
# -----------------------------
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_name(pitch):
    octave = (pitch // 12) - 1
    name = NOTE_NAMES[pitch % 12]
    return f"{name}{octave}"

def pitch_to_y(pitch):
    line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / NUM_KEYS
    return TOP_MARGIN + (highest_pitch - pitch) * line_spacing

# -----------------------------
# Pygame setup
# -----------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Scrolling Music Sheet Visualizer (Dynamic Range)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 16)


# -----------------------------
# Main Menu
# -----------------------------
def run_main_menu():
    """Show a simple main screen with the MIDI dropdown and OK/Quit buttons.
    Returns the selected filename (basename) or None if the user quits.
    """
    menu_open = True
    local_dropdown_open = False
    local_selected = selected_midi
    # place the menu dropdown a bit higher on the screen
    menu_y = dropdown_y + 40

    while menu_open:
        # prepare rects so events can reference them
        dd_rect = pygame.Rect(dropdown_x, menu_y, dropdown_w, dropdown_h)
        ok_rect = pygame.Rect(dd_rect.x + dd_rect.w + 20, dd_rect.y, 80, dropdown_h)
        quit_rect = pygame.Rect(dd_rect.x + dd_rect.w + 110, dd_rect.y, 80, dropdown_h)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos

                # Dropdown click
                if dd_rect.collidepoint(mx, my):
                    local_dropdown_open = not local_dropdown_open
                elif local_dropdown_open:
                    clicked_item = False
                    for idx, fname in enumerate(midi_files):
                        item_rect = pygame.Rect(dd_rect.x, dd_rect.y + (idx+1) * dropdown_h, dropdown_w, dropdown_h)
                        if item_rect.collidepoint(mx, my):
                            # select but don't exit until OK
                            local_selected = fname
                            clicked_item = True
                            break
                    if not clicked_item:
                        local_dropdown_open = False
                elif ok_rect.collidepoint(mx, my):
                    return local_selected
                elif quit_rect.collidepoint(mx, my):
                    return None
                else:
                    # click outside closes dropdown
                    local_dropdown_open = False

        # Draw menu
        screen.fill((40, 40, 40))
        title_font = pygame.font.SysFont(None, 40)
        title = title_font.render('Music Sheet Mover - Select MIDI', True, (255,255,255))
        screen.blit(title, ((SCREEN_WIDTH - title.get_width())//2, 20))

        # dropdown
        pygame.draw.rect(screen, (240,240,240), dd_rect)
        pygame.draw.rect(screen, (0,0,0), dd_rect, 2)
        sel_text = local_selected if local_selected else 'No MIDI files'
        txt = font.render(f'{sel_text}', True, (0,0,0))
        screen.blit(txt, (dd_rect.x + 6, dd_rect.y + 6))

        # OK and Quit buttons
        pygame.draw.rect(screen, (100,200,100), ok_rect)
        pygame.draw.rect(screen, (200,100,100), quit_rect)
        ok_txt = font.render('OK', True, (0,0,0))
        quit_txt = font.render('Quit', True, (0,0,0))
        screen.blit(ok_txt, (ok_rect.x + (ok_rect.w - ok_txt.get_width())/2, ok_rect.y + 6))
        screen.blit(quit_txt, (quit_rect.x + (quit_rect.w - quit_txt.get_width())/2, quit_rect.y + 6))

        # dropdown list if open
        if local_dropdown_open:
            for idx, fname in enumerate(midi_files):
                item_rect = pygame.Rect(dd_rect.x, dd_rect.y + (idx+1) * dropdown_h, dd_rect.w, dropdown_h)
                pygame.draw.rect(screen, (255,255,255), item_rect)
                pygame.draw.rect(screen, (0,0,0), item_rect, 1)
                item_txt = font.render(fname, True, (0,0,0))
                # highlight selected
                if fname == local_selected:
                    pygame.draw.rect(screen, (200, 230, 255), item_rect)
                screen.blit(item_txt, (item_rect.x + 6, item_rect.y + 6))

        pygame.display.flip()
        clock.tick(30)


def run_sf2_selection():
    """Screen to select an SF2 file and choose a preset from it."""
    global sf2_path, current_preset, fs

    if not FLUIDSYNTH_AVAILABLE or not fs:
        print("FluidSynth not available")
        return

    screen.fill((50, 50, 60))
    title = pygame.font.SysFont(None, 36).render('Select SF2 File', True, (255,255,255))
    screen.blit(title, (LEFT_MARGIN, 40))

    # File selection button
    select_rect = pygame.Rect(LEFT_MARGIN, 100, 200, 40)
    pygame.draw.rect(screen, (200,200,200), select_rect)
    select_txt = font.render('Choose SF2 File...', True, (0,0,0))
    screen.blit(select_txt, (select_rect.x + 10, select_rect.y + 10))

    if sf2_path:
        # Show current SF2 file
        txt = font.render(f'Current: {os.path.basename(sf2_path)}', True, (255,255,255))
        screen.blit(txt, (LEFT_MARGIN, 160))

        # Previous/Next preset buttons
        prev_rect = pygame.Rect(LEFT_MARGIN, 200, 100, 40)
        next_rect = pygame.Rect(LEFT_MARGIN + 120, 200, 100, 40)
        pygame.draw.rect(screen, (200,200,200), prev_rect)
        pygame.draw.rect(screen, (200,200,200), next_rect)
        screen.blit(font.render('< Prev', True, (0,0,0)), (prev_rect.x + 10, prev_rect.y + 10))
        screen.blit(font.render('Next >', True, (0,0,0)), (next_rect.x + 10, next_rect.y + 10))

        # Show current preset name if available
        try:
            preset_name = fs.channel_info(0)[3] if fs else f"Preset {current_preset}"
            txt = font.render(f'Current Preset: {preset_name}', True, (255,255,255))
            screen.blit(txt, (LEFT_MARGIN, 260))
        except:
            pass

    pygame.display.flip()

    selecting = True
    while selecting:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                
                if select_rect.collidepoint(mx, my):
                    # Open file dialog (you might need to implement this differently)
                    from tkinter import filedialog, Tk
                    root = Tk()
                    root.withdraw()
                    new_sf2 = filedialog.askopenfilename(
                        title="Select SF2 File",
                        filetypes=[("SoundFont Files", "*.sf2")]
                    )
                    if new_sf2:
                        sf2_path = new_sf2
                        try:
                            if fs:
                                fs.delete()
                            fs = fluidsynth.Synth()
                            fs.start()
                            sfid = fs.sfload(sf2_path)
                            fs.program_select(0, sfid, 0, 0)
                            current_preset = 0
                            return  # Successfully loaded
                        except Exception as e:
                            print("Error loading SF2:", e)
                
                if sf2_path:
                    if prev_rect.collidepoint(mx, my):
                        current_preset = max(0, current_preset - 1)
                        try:
                            sfid = fs.sfload(sf2_path)
                            fs.program_select(0, sfid, 0, current_preset)
                        except Exception as e:
                            print("Error changing preset:", e)
                    
                    elif next_rect.collidepoint(mx, my):
                        current_preset += 1
                        try:
                            sfid = fs.sfload(sf2_path)
                            fs.program_select(0, sfid, 0, current_preset)
                        except Exception as e:
                            print("Error changing preset:", e)

def run_mapping_screen():
    """Screen to assign mapped MIDI notes for each pitch that appears in the MIDI.
    Each note starts mapped to itself. Click a cell to cycle through possible replacement notes.
    Play button tests the tone (via MIDI out if available).
    """
    # Use all available MIDI notes as both targets and options
    targets = list(range(48, 84))  # C3 to B5
    target_names = [midi_to_name(p) for p in targets]

    # Same range for replacement options
    options = targets.copy()
    option_names = target_names.copy()

    # Start with each note mapped to itself (index is position in options list)
    sel_indices = {t: (options.index(mapped_notes[t]) if t in mapped_notes else options.index(t)) for t in targets}

    mapping_open = True
    while mapping_open:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                # Back and Save buttons
                back_rect = pygame.Rect(LEFT_MARGIN, SCREEN_HEIGHT - 60, 120, 36)
                save_rect = pygame.Rect(LEFT_MARGIN + 140, SCREEN_HEIGHT - 60, 120, 36)
                if back_rect.collidepoint(mx, my):
                    return
                if save_rect.collidepoint(mx, my):
                    # write selections into mapped_notes
                    for t in targets:
                        idx = sel_indices.get(t, -1)
                        if idx >= 0:
                            mapped_notes[t] = options[idx]
                        elif t in mapped_notes:
                            del mapped_notes[t]
                    print('Mappings saved:', mapped_notes)
                    return

                # click on mapping cells to cycle
                # layout cells in a grid
                cell_width = 140
                cells_per_row = max(1, min(6, (SCREEN_WIDTH - LEFT_MARGIN*2) // (cell_width + 20)))
                for i, t in enumerate(targets):
                    row = i // cells_per_row
                    col = i % cells_per_row
                    cell_x = LEFT_MARGIN + col * (cell_width + 20)
                    cell_y = 120 + row * 60
                    cell_rect = pygame.Rect(cell_x, cell_y, 120, 40)
                    if cell_rect.collidepoint(mx, my):
                        # cycle index
                        idx = sel_indices.get(t, -1) + 1
                        if idx >= len(options):
                            idx = -1
                        sel_indices[t] = idx
                        break
                # play test area click
                play_rect = pygame.Rect(SCREEN_WIDTH - 140, SCREEN_HEIGHT - 60, 120, 36)
                if play_rect.collidepoint(mx, my):
                    # play all mapped notes briefly
                    if midi_out:
                        for t, idx in sel_indices.items():
                            if idx >= 0:
                                outp = options[idx]
                                midi_out.note_on(outp, 100)
                        pygame.time.delay(300)
                        for t, idx in sel_indices.items():
                            if idx >= 0:
                                outp = options[idx]
                                midi_out.note_off(outp, 0)

        # draw mapping UI
        screen.fill((50, 50, 60))
        title = pygame.font.SysFont(None, 36).render('Map Notes (Default: Each note maps to itself)', True, (255,255,255))
        screen.blit(title, (LEFT_MARGIN, 40))

        # draw cells in rows and columns for all targets
        cell_width = 140
        cells_per_row = max(1, min(6, (SCREEN_WIDTH - LEFT_MARGIN*2) // (cell_width + 20)))
        for i, t in enumerate(targets):
            row = i // cells_per_row
            col = i % cells_per_row
            cell_x = LEFT_MARGIN + col * (cell_width + 20)  # add spacing between cells
            cell_y = 120 + row * 60  # spacing between rows
            # target label
            lbl = font.render(target_names[i], True, (255,255,255))
            screen.blit(lbl, (cell_x, cell_y - 30))
            # selection box
            cell_rect = pygame.Rect(cell_x, cell_y, 120, 40)
            pygame.draw.rect(screen, (220,220,220), cell_rect)
            pygame.draw.rect(screen, (0,0,0), cell_rect, 1)
            idx = sel_indices.get(t, -1)
            text = option_names[idx] if idx >= 0 else 'None'
            txt = font.render(text, True, (0,0,0))
            screen.blit(txt, (cell_x + 8, cell_y + 10))

        # buttons
        back_rect = pygame.Rect(LEFT_MARGIN, SCREEN_HEIGHT - 60, 120, 36)
        save_rect = pygame.Rect(LEFT_MARGIN + 140, SCREEN_HEIGHT - 60, 120, 36)
        play_rect = pygame.Rect(SCREEN_WIDTH - 140, SCREEN_HEIGHT - 60, 120, 36)
        pygame.draw.rect(screen, (200,100,100), back_rect)
        pygame.draw.rect(screen, (100,200,100), save_rect)
        pygame.draw.rect(screen, (120,160,240), play_rect)
        screen.blit(font.render('Back', True, (0,0,0)), (back_rect.x + 30, back_rect.y + 8))
        screen.blit(font.render('Save', True, (0,0,0)), (save_rect.x + 30, save_rect.y + 8))
        screen.blit(font.render('Play Test', True, (0,0,0)), (play_rect.x + 8, play_rect.y + 8))

        pygame.display.flip()
        clock.tick(30)


# -----------------------------
# Main loop
# -----------------------------
# Show main menu first; allow mapping screen to be opened from menu
while True:
    menu_choice = run_main_menu()
    if menu_choice is None:
        pygame.quit()
        raise SystemExit(0)
    # user selected a file (or re-selected the same one) -> load it, choose SF2, then mapping
    if menu_choice:
        selected_midi = menu_choice
        MIDI_PATH = os.path.join(MIDI_DIR, selected_midi)
        try:
            pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(MIDI_PATH)
        except Exception as e:
            print('Failed to load MIDI from menu:', e)
            continue

        # First select SF2 and preset
        if FLUIDSYNTH_AVAILABLE:
            run_sf2_selection()
        
        # Then go to mapping screen
        run_mapping_screen()
        break

app_active = True

while app_active:
    # (re)start playback
    start_time = time.time()
    running = True
    end_timer_started = False
    end_timer_start = 0
    # tracking currently playing pitches for mapping playback
    prev_playing = set()

    while running:
        dt = clock.tick(60) / 1000
        current_time = time.time() - start_time

        exit_reason = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                app_active = False
                exit_reason = 'quit'
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # Dropdown rect
                dropdown_rect = pygame.Rect(dropdown_x, dropdown_y, dropdown_w, dropdown_h)
                if dropdown_rect.collidepoint(mx, my):
                    dropdown_open = not dropdown_open
                elif dropdown_open:
                    # check items
                    for idx, fname in enumerate(midi_files):
                        item_rect = pygame.Rect(dropdown_x, dropdown_y + (idx+1) * dropdown_h, dropdown_w, dropdown_h)
                        if item_rect.collidepoint(mx, my):
                            # load selected MIDI
                            selected_midi = fname
                            MIDI_PATH = os.path.join(MIDI_DIR, selected_midi)
                            try:
                                pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(MIDI_PATH)
                                print(f'Loaded {selected_midi}')
                            except Exception as e:
                                print('Failed to load MIDI:', e)
                            dropdown_open = False
                            # restart playback immediately
                            running = False
                            exit_reason = 'reload'
                            break
            # other events are ignored here

        # White background
        screen.fill((255, 255, 255))

        # Draw dropdown (MIDI file selector)
        dropdown_rect = pygame.Rect(dropdown_x, dropdown_y, dropdown_w, dropdown_h)
        pygame.draw.rect(screen, (240,240,240), dropdown_rect)
        pygame.draw.rect(screen, (0,0,0), dropdown_rect, 2)
        sel_text = selected_midi if selected_midi else 'No MIDI files'
        txt = font.render(f'MIDI: {sel_text}', True, (0,0,0))
        screen.blit(txt, (dropdown_x + 6, dropdown_y + 6))

        if dropdown_open:
            # draw list of files
            for idx, fname in enumerate(midi_files):
                item_rect = pygame.Rect(dropdown_x, dropdown_y + (idx+1) * dropdown_h, dropdown_w, dropdown_h)
                pygame.draw.rect(screen, (255,255,255), item_rect)
                pygame.draw.rect(screen, (0,0,0), item_rect, 1)
                item_txt = font.render(fname, True, (0,0,0))
                screen.blit(item_txt, (item_rect.x + 6, item_rect.y + 6))

        # Draw horizontal lines and key labels
        line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / NUM_KEYS
        for pitch in range(lowest_pitch, highest_pitch + 1):
            y = pitch_to_y(pitch)
            color = (0,0,0)
            width = 1
            for note in notes:
                if note['start'] <= current_time <= note['end'] and note['pitch'] == pitch:
                    color = (0,128,0)
                    width = 3
            pygame.draw.line(screen, color, (LEFT_MARGIN, y), (SCREEN_WIDTH, y), width)
            # Key label
            label = font.render(midi_to_name(pitch), True, (0,0,0))
            screen.blit(label, (5, y-7))

        # Draw stationary playhead
        playhead_x = SCREEN_WIDTH // 2
        pygame.draw.line(screen, (255,0,0), (playhead_x, 0), (playhead_x, SCREEN_HEIGHT), 2)

        # First compute currently playing pitches
        playing_pitches = set()
        for note in notes:
            if note['start'] <= current_time <= note['end']:
                playing_pitches.add(note['pitch'])
            note_x = playhead_x + (note['start'] - current_time) * PIXELS_PER_SECOND
            note_y = pitch_to_y(note['pitch'])
            if 0 <= note_x <= SCREEN_WIDTH:
                pygame.draw.circle(screen, (0,0,0), (int(note_x), int(note_y)), NOTE_RADIUS)

        # detect note-on / note-off events for mapping playback
        new_on = playing_pitches - prev_playing
        new_off = prev_playing - playing_pitches
        # handle note-ons using either MIDI out or FluidSynth
        if midi_out:
            for p in new_on:
                if p in mapped_notes:
                    try:
                        midi_out.note_on(int(mapped_notes[p]), 100)
                    except Exception:
                        pass
        elif fs and sf2_path:  # Use FluidSynth if available
            for p in new_on:
                pitch = mapped_notes.get(p, p)  # Use mapped note or original if not mapped
                try:
                    fs.noteon(0, int(pitch), 100)
                except Exception as e:
                    print("FluidSynth note on error:", e)

        # handle note-offs
        if midi_out:
            for p in new_off:
                if p in mapped_notes:
                    try:
                        midi_out.note_off(int(mapped_notes[p]), 0)
                    except Exception:
                        pass
        elif fs and sf2_path:  # Use FluidSynth if available
            for p in new_off:
                pitch = mapped_notes.get(p, p)  # Use mapped note or original if not mapped
                try:
                    fs.noteoff(0, int(pitch))
                except Exception as e:
                    print("FluidSynth note off error:", e)

        prev_playing = playing_pitches

        # Draw current time and total duration
        time_text = f"Time: {current_time:.2f} / {midi_end_time:.2f} s"
        label = font.render(time_text, True, (0,0,0))
        screen.blit(label, (SCREEN_WIDTH - 250, 10))

        pygame.display.flip()

        # Check if we've reached the end
        if current_time >= midi_end_time and not end_timer_started:
            end_timer_started = True
            end_timer_start = time.time()

        # Stop playback after a few seconds past the end
        if end_timer_started and (time.time() - end_timer_start) >= END_WAIT_SECONDS:
            running = False
            exit_reason = 'finished'

    # playback finished — decide next step depending on exit reason
    if not app_active:
        break

    # If a reload was requested (file selection), immediately continue to restart playback
    if exit_reason == 'reload':
        continue

    # After playback finishes, return to the main menu so the user can pick another file or quit
    menu_choice = run_main_menu()
    if menu_choice is None:
        # user chose to quit from main menu
        break
    # load the selected file (even if it's the same) and show mapping before playback
    if menu_choice:
        selected_midi = menu_choice
        MIDI_PATH = os.path.join(MIDI_DIR, selected_midi)
        try:
            pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(MIDI_PATH)
            
            # First select SF2 and preset
            if FLUIDSYNTH_AVAILABLE:
                run_sf2_selection()
            
            # Then mapping screen
            run_mapping_screen()
            # restart playback loop automatically with new selection/mapping
            continue
        except Exception as e:
            print('Failed to load selected MIDI from menu:', e)
            # fall through to replay current file
            continue

pygame.quit()