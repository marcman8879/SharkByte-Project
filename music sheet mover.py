import pygame
import pretty_midi
import time

# -----------------------------
# Configuration
# -----------------------------
MIDI_FILE = r"C:\Users\treyv\Downloads\mz_332_2.mid"  # Replace with your MIDI file path
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 600
LEFT_MARGIN = 100  # Space for key labels
TOP_MARGIN = 20
BOTTOM_MARGIN = 20
NOTE_RADIUS = 8
PIXELS_PER_SECOND = 200  # Scrolling speed

# MIDI range for piano
LOWEST_PITCH = 21
HIGHEST_PITCH = 108
NUM_KEYS = HIGHEST_PITCH - LOWEST_PITCH + 1

# -----------------------------
# Load MIDI file
# -----------------------------
pm = pretty_midi.PrettyMIDI(MIDI_FILE)
notes = []
for instrument in pm.instruments:
    for note in instrument.notes:
        notes.append({'start': note.start, 'end': note.end, 'pitch': note.pitch})

# -----------------------------
# Helper functions
# -----------------------------
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_name(pitch):
    octave = (pitch // 12) - 1
    name = NOTE_NAMES[pitch % 12]
    return f"{name}{octave}"

def pitch_to_y(pitch):
    # Scale dynamically to fit screen
    line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / NUM_KEYS
    return TOP_MARGIN + (HIGHEST_PITCH - pitch) * line_spacing

# -----------------------------
# Pygame setup
# -----------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Scrolling Music Sheet Visualizer (Scaled)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 14)

# -----------------------------
# Main loop
# -----------------------------
start_time = time.time()
running = True

while running:
    dt = clock.tick(60) / 1000
    current_time = time.time() - start_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # White background
    screen.fill((255, 255, 255))

    # Draw horizontal lines and key labels
    line_spacing = (SCREEN_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / NUM_KEYS
    for pitch in range(LOWEST_PITCH, HIGHEST_PITCH + 1):
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

    pygame.display.flip()

pygame.quit()
