"""
Simple sheet music generator.

Usage examples:
  # Demo C major scale (quarter notes) -> writes demo.musicxml
  python create_sheet.py

  # Provide notes: token format NAME_OCTAVE:DURATION, comma-separated
  python create_sheet.py --notes "C4:quarter,D4:quarter,E4:quarter,F4:quarter"

  # Write to specific file and produce PDF (requires MuseScore on PATH or --musescore)
  python create_sheet.py --out demo.musicxml --to-pdf --musescore "C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe"

Supported durations: whole, half, quarter, eighth, sixteenth (also numeric quarterLength like 0.5)
"""

import argparse
import os
import shutil
import subprocess

try:
    from music21 import stream, note, meter, tempo, metadata, converter
    MUSIC21_AVAILABLE = True
except Exception:
    MUSIC21_AVAILABLE = False


def find_musescore_executable(provided_path=None):
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
    if out_pdf_path is None:
        base = os.path.splitext(musicxml_path)[0]
        out_pdf_path = base + '.pdf'

    exe = find_musescore_executable(musescore_exe)
    if exe is None:
        raise RuntimeError('MuseScore executable not found. Install MuseScore or provide path with --musescore')

    cmd = [exe, '-o', out_pdf_path, musicxml_path]
    subprocess.run(cmd, check=True)
    return out_pdf_path


def parse_note_token(token):
    # token: NAME_OCTAVE:DURATION  e.g. C4:quarter or G#3:0.5
    if ':' in token:
        name, dur = token.split(':', 1)
    else:
        name, dur = token, 'quarter'
    name = name.strip()
    dur = dur.strip()
    # try numeric duration
    try:
        qlen = float(dur)
        return name, qlen
    except Exception:
        mapping = {
            'whole': 4.0,
            'half': 2.0,
            'quarter': 1.0,
            'eighth': 0.5,
            'sixteenth': 0.25
        }
        qlen = mapping.get(dur.lower(), 1.0)
        return name, qlen


def build_score_from_tokens(tokens, title='Untitled', tempo_bpm=100, time_signature='4/4'):
    if not MUSIC21_AVAILABLE:
        raise RuntimeError('music21 is not installed. Install music21 to generate scores.')

    s = stream.Score()
    s.insert(0, metadata.Metadata())
    s.metadata.title = title

    p = stream.Part()
    p.append(meter.TimeSignature(time_signature))
    p.append(tempo.MetronomeMark(number=tempo_bpm))

    for tok in tokens:
        name, qlen = parse_note_token(tok)
        n = note.Note(name)
        n.duration.quarterLength = qlen
        p.append(n)

    s.append(p)
    return s


def main():
    parser = argparse.ArgumentParser(description='Create a simple music sheet from note tokens')
    parser.add_argument('--notes', help='Comma-separated tokens like C4:quarter,D4:quarter', default=None)
    parser.add_argument('--out', help='Output MusicXML path', default='demo.musicxml')
    parser.add_argument('--to-pdf', action='store_true', help='Also produce a PDF using MuseScore if available')
    parser.add_argument('--musescore', help='Path to MuseScore executable (optional)')
    parser.add_argument('--title', help='Score title', default='Demo Score')
    parser.add_argument('--tempo', type=int, help='Tempo in BPM', default=100)
    parser.add_argument('--timesig', help='Time signature', default='4/4')
    args = parser.parse_args()

    if not MUSIC21_AVAILABLE:
        print('music21 is not available. Install music21 to use this script (pip install music21).')
        return

    if args.notes:
        tokens = [t.strip() for t in args.notes.split(',') if t.strip()]
    else:
        # default demo: C major scale
        tokens = ['C4:quarter', 'D4:quarter', 'E4:quarter', 'F4:quarter', 'G4:quarter', 'A4:quarter', 'B4:quarter', 'C5:whole']

    score = build_score_from_tokens(tokens, title=args.title, tempo_bpm=args.tempo, time_signature=args.timesig)

    outpath = args.out
    score.write('musicxml', fp=outpath)
    print(f'Wrote MusicXML to {outpath}')

    if args.to_pdf:
        try:
            pdf_path = convert_musicxml_to_pdf(outpath, musescore_exe=args.musescore)
            print(f'Wrote PDF to {pdf_path}')
        except Exception as exc:
            print(f'Failed to write PDF: {exc}')


if __name__ == '__main__':
    main()
