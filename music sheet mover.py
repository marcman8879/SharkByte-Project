import pygame
import pretty_midi
import time
import os

# -----------------------------
# Configuration
# -----------------------------
MIDI_FILE = r"C:\Users\treyv\Downloads\untitled.mid"  # Replace with your MIDI file path
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
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                dd_rect = pygame.Rect(dropdown_x, menu_y, dropdown_w, dropdown_h)
                ok_rect = pygame.Rect(dropdown_x + dropdown_w + 20, menu_y, 80, dropdown_h)
                quit_rect = pygame.Rect(dropdown_x + dropdown_w + 110, menu_y, 80, dropdown_h)

                # Dropdown click
                if dd_rect.collidepoint(mx, my):
                    local_dropdown_open = not local_dropdown_open
                elif local_dropdown_open:
                    clicked_item = False
                    for idx, fname in enumerate(midi_files):
                        item_rect = pygame.Rect(dropdown_x, menu_y + (idx+1) * dropdown_h, dropdown_w, dropdown_h)
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
        dd_rect = pygame.Rect(dropdown_x, menu_y, dropdown_w, dropdown_h)
        pygame.draw.rect(screen, (240,240,240), dd_rect)
        pygame.draw.rect(screen, (0,0,0), dd_rect, 2)
        sel_text = local_selected if local_selected else 'No MIDI files'
        txt = font.render(f'{sel_text}', True, (0,0,0))
        screen.blit(txt, (dd_rect.x + 6, dd_rect.y + 6))

        # OK and Quit buttons
        ok_rect = pygame.Rect(dd_rect.x + dd_rect.w + 20, dd_rect.y, 80, dropdown_h)
        quit_rect = pygame.Rect(dd_rect.x + dd_rect.w + 110, dd_rect.y, 80, dropdown_h)
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


# -----------------------------
# Main loop
# -----------------------------
# Show main menu first
menu_choice = run_main_menu()
if menu_choice is None:
    pygame.quit()
    raise SystemExit(0)

# if user picked a file from menu, load it
if menu_choice and menu_choice != selected_midi:
    selected_midi = menu_choice
    MIDI_PATH = os.path.join(MIDI_DIR, selected_midi)
    pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(MIDI_PATH)

app_active = True

while app_active:
    # (re)start playback
    start_time = time.time()
    running = True
    end_timer_started = False
    end_timer_start = 0

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

        # Draw notes as black circles
        for note in notes:
            note_x = playhead_x + (note['start'] - current_time) * PIXELS_PER_SECOND
            note_y = pitch_to_y(note['pitch'])
            if 0 <= note_x <= SCREEN_WIDTH:
                pygame.draw.circle(screen, (0,0,0), (int(note_x), int(note_y)), NOTE_RADIUS)

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
    # if the user selected a different file, load it
    if menu_choice and menu_choice != selected_midi:
        selected_midi = menu_choice
        MIDI_PATH = os.path.join(MIDI_DIR, selected_midi)
        try:
            pm, notes, lowest_pitch, highest_pitch, midi_end_time, NUM_KEYS = load_midi(MIDI_PATH)
            # restart playback loop automatically
            continue
        except Exception as e:
            print('Failed to load selected MIDI from menu:', e)
            # fall through to replay current file
            continue

pygame.quit()
