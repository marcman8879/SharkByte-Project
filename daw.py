"""
Simple DAW-like app with piano keys using pygame.
Features:
- Visual keyboard (2 octaves by default)
- Play notes with mouse or computer keyboard
- Optional MIDI output via pygame.midi if available
- Record notes (press R to start/stop recording), save to MIDI with 'S'
- Export recorded MIDI to MusicXML if music21 installed (press X)

Usage:
  python daw.py

Controls:
  Mouse click = play note
  z/s/x/c/v/b/n/m and q/2/w/3/e = computer-key mapping for two octaves (see mapping in code)
  R = toggle recording
  S = save recorded MIDI to recording.mid
  X = export recording.mid to MusicXML (requires music21)
  Esc or window close = quit

Note: This is a simple proof-of-concept. Sound output requires a MIDI synth and pygame.midi available on your system.
"""

import sys
import time
import os
import math

import pygame
import pretty_midi

# optional modules
try:
    import pygame.midi
    PYGAME_MIDI_AVAILABLE = True
except Exception:
    PYGAME_MIDI_AVAILABLE = False

try:
    from music21 import converter
    MUSIC21_AVAILABLE = True
except Exception:
    MUSIC21_AVAILABLE = False

# Configuration
WHITE_KEYS = 14  # two octaves (C to B * 2)
START_MIDI_NOTE = 60  # Middle C (C4)
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 300
FPS = 60

# Staff (sheet) display configuration
SHOW_STAFF = True
STAFF_LEFT = 20
STAFF_RIGHT = WINDOW_WIDTH - 20
STAFF_TOP = 20
STAFF_LINE_SPACING = 12  # pixels between staff lines
STAFF_NUM_LINES = 5
STAFF_MIDDLE_C = 60  # MIDI note number used as reference (C4)

# Keyboard mapping (computer keys -> semitone offsets)
KEYBOARD_MAP = {
    pygame.K_z: 0,  # C
    pygame.K_s: 1,
    pygame.K_x: 2,
    pygame.K_d: 3,
    pygame.K_c: 4,
    pygame.K_v: 5,
    pygame.K_g: 6,
    pygame.K_b: 7,
    pygame.K_h: 8,
    pygame.K_n: 9,
    pygame.K_j: 10,
    pygame.K_m: 11,
    pygame.K_q: 12,  # next octave C
    pygame.K_2: 13,
    pygame.K_w: 14,
    pygame.K_3: 15,
    pygame.K_e: 16,
}

# Reverse helper
WHITE_IN_OCTAVE = [0, 2, 4, 5, 7, 9, 11]
BLACK_POSITIONS = [1, 3, 6, 8, 10]

class DAW:
    def __init__(self):
        pygame.init()
        if PYGAME_MIDI_AVAILABLE:
            pygame.midi.init()
            try:
                self.midi_out = pygame.midi.Output(pygame.midi.get_default_output_id())
            except Exception:
                self.midi_out = None
        else:
            self.midi_out = None

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Simple DAW - Piano Keyboard')
        self.clock = pygame.time.Clock()

        # layout
        self.white_key_width = WINDOW_WIDTH / WHITE_KEYS
        self.pressed = set()

        # recording state
        self.recording = False
        self.recorded_events = []  # tuples: (time_from_start, note, velocity, on_off)
        self.record_start_time = None

    def midi_note_on(self, note, velocity=100):
        if self.midi_out:
            try:
                self.midi_out.note_on(int(note), int(velocity))
            except Exception:
                pass

    def midi_note_off(self, note, velocity=0):
        if self.midi_out:
            try:
                self.midi_out.note_off(int(note), int(velocity))
            except Exception:
                pass

    def play_note(self, midi_note):
        self.pressed.add(midi_note)
        self.midi_note_on(midi_note)
        if self.recording:
            t = time.time() - self.record_start_time
            self.recorded_events.append((t, midi_note, 100, 'on'))

    def stop_note(self, midi_note):
        if midi_note in self.pressed:
            self.pressed.remove(midi_note)
        self.midi_note_off(midi_note)
        if self.recording:
            t = time.time() - self.record_start_time
            self.recorded_events.append((t, midi_note, 0, 'off'))

    def midi_save_recording(self, out_path='recording.mid'):
        if not self.recorded_events:
            print('No recorded events to save.')
            return None

        # convert recorded events (time, note, vel, 'on'/'off') into pretty_midi
        pm = pretty_midi.PrettyMIDI()
        inst = pretty_midi.Instrument(program=0)

        # pair on/off into notes
        on_stack = {}
        for t, note, vel, kind in self.recorded_events:
            if kind == 'on':
                # push start time
                on_stack.setdefault(note, []).append((t, vel))
            else:
                # pop last on
                if note in on_stack and on_stack[note]:
                    start_t, start_vel = on_stack[note].pop(0)
                    # create pretty_midi Note
                    pm_note = pretty_midi.Note(velocity=int(start_vel), pitch=int(note), start=start_t, end=t)
                    inst.notes.append(pm_note)
                else:
                    # unmatched note_off, ignore
                    pass

        pm.instruments.append(inst)
        pm.write(out_path)
        print(f'Saved recording to {out_path}')
        return out_path

    def export_recording_to_musicxml(self, midi_path, out_musicxml=None):
        if not MUSIC21_AVAILABLE:
            print('music21 not installed; cannot export to MusicXML')
            return None
        if out_musicxml is None:
            out_musicxml = os.path.splitext(midi_path)[0] + '.musicxml'
        score = converter.parse(midi_path)
        score.write('musicxml', fp=out_musicxml)
        print(f'Wrote MusicXML to {out_musicxml}')
        return out_musicxml

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        # toggle recording
                        if not self.recording:
                            self.recording = True
                            self.recorded_events = []
                            self.record_start_time = time.time()
                            print('Recording started')
                        else:
                            self.recording = False
                            print('Recording stopped')
                    elif event.key == pygame.K_s:
                        # save recording
                        out = self.midi_save_recording()
                        if out:
                            print('Saved MIDI to', out)
                    elif event.key == pygame.K_x:
                        # export to musicxml from current saved midi
                        midi_path = 'recording.mid'
                        if os.path.exists(midi_path):
                            self.export_recording_to_musicxml(midi_path)
                        else:
                            print('No recording.mid found; save a recording first (press S)')
                    else:
                        if event.key in KEYBOARD_MAP:
                            midi_note = START_MIDI_NOTE + KEYBOARD_MAP[event.key]
                            self.play_note(midi_note)
                elif event.type == pygame.KEYUP:
                    if event.key in KEYBOARD_MAP:
                        midi_note = START_MIDI_NOTE + KEYBOARD_MAP[event.key]
                        self.stop_note(midi_note)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    key_index = int(x // self.white_key_width)
                    midi_note = START_MIDI_NOTE + key_index
                    self.play_note(midi_note)
                elif event.type == pygame.MOUSEBUTTONUP:
                    x, y = event.pos
                    key_index = int(x // self.white_key_width)
                    midi_note = START_MIDI_NOTE + key_index
                    self.stop_note(midi_note)

            # draw background
            self.screen.fill((80, 80, 80))

            # draw staff (sheet) at top
            if SHOW_STAFF:
                # staff lines
                for i in range(STAFF_NUM_LINES):
                    y = STAFF_TOP + i * STAFF_LINE_SPACING
                    pygame.draw.line(self.screen, (230, 230, 230), (STAFF_LEFT, y), (STAFF_RIGHT, y), 2)

                # draw note heads for currently pressed notes
                for note in list(self.pressed):
                    x_index = note - START_MIDI_NOTE
                    # clamp x to the keyboard width
                    x_index = max(0, min(WHITE_KEYS - 1, x_index))
                    x = x_index * self.white_key_width + self.white_key_width / 2
                    # map midi note to staff y: each semitone = half staff_step
                    semitone_step = STAFF_LINE_SPACING / 2.0
                    y = STAFF_TOP + (STAFF_NUM_LINES - 1) * STAFF_LINE_SPACING / 2.0 - (note - STAFF_MIDDLE_C) * semitone_step
                    # draw note head
                    note_w = 14
                    note_h = 10
                    pygame.draw.ellipse(self.screen, (20, 20, 20), (x - note_w/2, y - note_h/2, note_w, note_h))
                    pygame.draw.ellipse(self.screen, (255, 255, 255), (x - note_w/2, y - note_h/2, note_w, note_h), 2)

            # draw white keys below staff
            keys_top = STAFF_TOP + STAFF_NUM_LINES * STAFF_LINE_SPACING + 20
            for i in range(WHITE_KEYS):
                x = i * self.white_key_width
                midi_note = START_MIDI_NOTE + i
                color = (255, 255, 255) if midi_note not in self.pressed else (180, 255, 180)
                pygame.draw.rect(self.screen, color, (x, keys_top, self.white_key_width, WINDOW_HEIGHT - keys_top))
                pygame.draw.rect(self.screen, (0, 0, 0), (x, keys_top, self.white_key_width, WINDOW_HEIGHT - keys_top), 1)

            # TODO: draw black keys on top if desired (map positions)

            # status
            font = pygame.font.SysFont(None, 24)
            rec_text = 'REC' if self.recording else 'REC (off)'
            txt = font.render(f'{rec_text}  Recorded events: {len(self.recorded_events)}', True, (255, 255, 255))
            self.screen.blit(txt, (10, keys_top + 10))

            pygame.display.flip()
            self.clock.tick(FPS)

        # cleanup
        if self.midi_out:
            try:
                self.midi_out.close()
            except Exception:
                pass
        if PYGAME_MIDI_AVAILABLE:
            try:
                pygame.midi.quit()
            except Exception:
                pass
        pygame.quit()


if __name__ == '__main__':
    app = DAW()
    app.run()
