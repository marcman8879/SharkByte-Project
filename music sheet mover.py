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
    menu_y = dropdown_y + 100

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
                            return fname
                    if not clicked_item:
                        local_dropdown_open = False
                elif ok_rect.collidepoint(mx, my):
                    return selected_midi
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
        sel_text = selected_midi if selected_midi else 'No MIDI files'
        txt = font.render(f'{sel_text}', True, (0,0,0))
        screen.blit(txt, (dd_rect.x + 6, dd_rect.y + 6))

        # OK and Quit buttons
        ok_rect = pygame.Rect(dd_rect.x + dd_rect.w + 20, dd_rect.y, 80, dropdown_h)
        quit_rect = pygame.Rect(dd_rect.x + dd_rect.w + 110, dd_rect.y, 80, dropdown_h)
        pygame.draw.rect(screen, (100,200,100), ok_rect)
        pygame.draw.rect(screen, (200,100,100), quit_rect)

pygame.quit()
