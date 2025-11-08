import argparse
import os
import pretty_midi
import pygame
import time
import subprocess
import shutil

# optional dependency for exporting sheet music
try:
    from music21 import converter
    MUSIC21_AVAILABLE = True
except Exception:
    MUSIC21_AVAILABLE = False


# -----------------------------
# Visualization code (kept largely the same)
# -----------------------------
def run_visualizer(midi_file_path):
    pm = pretty_midi.PrettyMIDI(midi_file_path)

    pygame.init()
    WIDTH, HEIGHT = 1000, 300
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MIDI File Piano Visualizer")
    clock = pygame.time.Clock()

    # Piano key layout
    NUM_WHITE_KEYS = 52
    WHITE_WIDTH = WIDTH / NUM_WHITE_KEYS
    pressed_keys = set()

    # Collect all notes from MIDI file
    notes = []
    for instrument in pm.instruments:
        for note in instrument.notes:
            notes.append({
                'start': note.start,
                'end': note.end,
                'note': note.pitch
            })

    notes.sort(key=lambda x: x['start'])  # sort by start time

    # Visualization loop
    start_time = time.time()
    running = True
    while running:
        current_time = time.time() - start_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Update pressed keys based on time
        pressed_keys.clear()
        for n in notes:
            if n['start'] <= current_time <= n['end']:
                pressed_keys.add(n['note'])

        # Draw white keys
        screen.fill((50, 50, 50))
        for i in range(NUM_WHITE_KEYS):
            x = i * WHITE_WIDTH
            note = 21 + i  # starting from A0
            color = (255, 255, 255) if note not in pressed_keys else (0, 255, 0)
            pygame.draw.rect(screen, color, (x, 0, WHITE_WIDTH, HEIGHT))
            pygame.draw.rect(screen, (0, 0, 0), (x, 0, WHITE_WIDTH, HEIGHT), 1)

        # Draw black keys
        black_width = WHITE_WIDTH * 0.6
        black_height = HEIGHT * 0.6
        for i in range(NUM_WHITE_KEYS):
            pos_in_octave = i % 7
            if pos_in_octave in [0, 1, 3, 4, 5]:
                x = i * WHITE_WIDTH + WHITE_WIDTH * 0.75
                note = 22 + i  # approximate mapping
                color = (0, 0, 0) if note not in pressed_keys else (255, 0, 0)
                pygame.draw.rect(screen, color, (x, 0, black_width, black_height))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# -----------------------------
# Export to MusicXML using music21
# -----------------------------
def export_to_musicxml(midi_file_path, out_path=None):
    """
    Convert a MIDI file to MusicXML using music21 and write to out_path.
    If music21 is not available, raises RuntimeError.
    """
    if not MUSIC21_AVAILABLE:
        raise RuntimeError("music21 is not installed or failed to import. Install music21 to enable MusicXML export.")

    if out_path is None:
        base = os.path.splitext(midi_file_path)[0]
        out_path = base + ".musicxml"

    # music21 can parse MIDI files directly
    score = converter.parse(midi_file_path)
    score.write('musicxml', fp=out_path)
    return out_path


def find_musescore_executable(provided_path=None):
    """Try to find a MuseScore executable. If provided_path is given and valid, return it.
    Otherwise try common executable names via PATH.
    Returns path or None if not found.
    """
    if provided_path:
        if os.path.isfile(provided_path) or shutil.which(provided_path):
            return provided_path

    candidates = [
        'mscore', 'mscore3', 'mscore4', 'MuseScore', 'MuseScore3', 'MuseScore4',
        'mscore.exe', 'mscore3.exe', 'mscore4.exe', 'MuseScore.exe', 'MuseScore3.exe', 'MuseScore4.exe'
    ]
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def convert_musicxml_to_pdf(musicxml_path, out_pdf_path=None, musescore_exe=None):
    """Use MuseScore command-line to convert MusicXML to PDF.
    If musescore_exe is None, try to auto-detect. Returns output PDF path.
    """
    if out_pdf_path is None:
        base = os.path.splitext(musicxml_path)[0]
        out_pdf_path = base + '.pdf'

    exe = find_musescore_executable(musescore_exe)
    if exe is None:
        raise RuntimeError('MuseScore executable not found. Install MuseScore or provide path with --musescore')

    # Call MuseScore to export PDF. Most MuseScore CLI accept: musescore -o out.pdf in.musicxml
    cmd = [exe, '-o', out_pdf_path, musicxml_path]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f'MuseScore failed to convert MusicXML to PDF: {exc}')

    return out_pdf_path


def main():
    parser = argparse.ArgumentParser(description='MIDI visualizer and simple MusicXML exporter')
    parser.add_argument('midi', nargs='?', default=r"C:\Users\treyv\Downloads\mz_332_2.mid", help='Path to MIDI file')
    parser.add_argument('--export-musicxml', '-e', nargs='?', const=True, help='Export the MIDI to MusicXML. Optionally provide output path')
    parser.add_argument('--to-pdf', nargs='?', const=True, help='Export a printable PDF. Optionally provide output PDF path')
    parser.add_argument('--musescore', nargs='?', help='Path to MuseScore executable (optional). If omitted the script will try to find MuseScore in PATH')
    parser.add_argument('--no-visualize', action='store_true', help='Do not launch the Pygame visualizer')
    args = parser.parse_args()

    midi_path = args.midi

    # If user passed --export-musicxml but no path (const True), we derive path
    if args.export_musicxml is not None:
        # args.export_musicxml is either True (const) or a string path
        out = None if args.export_musicxml is True else args.export_musicxml
        try:
            written = export_to_musicxml(midi_path, out_path=out)
            print(f"Wrote MusicXML to: {written}")
        except Exception as exc:
            print(f"Failed to export MusicXML: {exc}")

    # Handle PDF export (will export MusicXML first if needed)
    if args.to_pdf is not None:
        # If user provided a path for PDF, args.to_pdf will be a string; if const True then derive
        pdf_out = None if args.to_pdf is True else args.to_pdf
        try:
            # ensure we have a MusicXML file first
            base_musicxml = os.path.splitext(midi_path)[0] + '.musicxml'
            if os.path.exists(base_musicxml):
                musicxml_path = base_musicxml
            else:
                musicxml_path = export_to_musicxml(midi_path)

            written_pdf = convert_musicxml_to_pdf(musicxml_path, out_pdf_path=pdf_out, musescore_exe=args.musescore)
            print(f"Wrote PDF to: {written_pdf}")
        except Exception as exc:
            print(f"Failed to create PDF: {exc}")

    if not args.no_visualize:
        run_visualizer(midi_path)


if __name__ == '__main__':
    main()

