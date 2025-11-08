import sys
import wave
import numpy as np
import pyaudio
from scipy.io import wavfile

# main.py
# Record audio with PyAudio, save with scipy.io.wavfile, then play it back.


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
OUT_FILENAME = "recording.wav"


def record(seconds: float, filename: str = OUT_FILENAME):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    print(f"Recording {seconds:.2f} seconds...")
    frames = []
    for _ in range(0, int(RATE / CHUNK * seconds)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()
    raw = b"".join(frames)
    samples = np.frombuffer(raw, dtype=np.int16)
    wavfile.write(filename, RATE, samples)
    print(f"Saved to {filename}")


def play(filename: str = OUT_FILENAME):
    rate, data = wavfile.read(filename)
    # Ensure int16 format
    if data.dtype != np.int16:
        # convert floats in [-1,1] to int16
        if np.issubdtype(data.dtype, np.floating):
            data = (data * 32767).astype(np.int16)
        else:
            data = data.astype(np.int16)
    channels = 1 if data.ndim == 1 else data.shape[1]

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    output=True)
    print(f"Playing {filename}...")
    stream.write(data.tobytes())
    stream.stop_stream()
    stream.close()
    p.terminate()


def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
            print("Usage: python main.py [seconds]\nIf seconds omitted, defaults to 5.")
            return
        seconds = 5.0
        if len(sys.argv) > 1:
            try:
                seconds = float(sys.argv[1])
            except ValueError:
                pass
        record(seconds, OUT_FILENAME)
        play(OUT_FILENAME)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()