import sys
import numpy as np
import pyaudio
from scipy.io import wavfile
import tkinter as tk
from scipy.fftpack import fft
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
OUT_FILENAME = "recording.wav"
SMOOTH_WINDOW_RECORD = 5  # frames to smooth in recording plot
PLOT_UPDATE_EVERY_PLAY = 5 # update plot every N chunks during playback

def analyze_audio_chunk_single_freq(data, rate):
    N = len(data)
    fft_data = fft(data)
    freq = np.fft.fftfreq(N, 1.0/rate)
    magnitude = np.abs(fft_data)
    pos_mask = freq > 0
    freq = freq[pos_mask]
    magnitude = magnitude[pos_mask]
    dominant_index = np.argmax(magnitude)
    return freq[dominant_index], magnitude[dominant_index]

def compute_average_frequency(filename: str = OUT_FILENAME):
    rate, data = wavfile.read(filename)
    if data.ndim > 1:
        data = data[:,0]
    N = len(data)
    fft_data = fft(data)
    freq = np.fft.fftfreq(N, 1.0/rate)
    magnitude = np.abs(fft_data)
    pos_mask = freq > 0
    freq = freq[pos_mask]
    magnitude = magnitude[pos_mask]
    avg_freq = np.sum(freq * magnitude) / np.sum(magnitude)
    return avg_freq

def record(seconds: float, filename: str = OUT_FILENAME):
    root = tk.Tk()
    root.title("Frequency Analyzer - Recording")
    root.geometry("800x600")

    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    times, freqs_raw, freqs_smooth = [], [], []

    def update_plot():
        if frames:
            latest_data = np.frombuffer(frames[-1], dtype=np.int16)
            dominant_freq, _ = analyze_audio_chunk_single_freq(latest_data, RATE)

            t = len(frames) * (CHUNK / RATE)
            times.append(t)
            freqs_raw.append(dominant_freq)

            # smoothing
            if len(freqs_raw) >= SMOOTH_WINDOW_RECORD:
                smooth_val = np.mean(freqs_raw[-SMOOTH_WINDOW_RECORD:])
            else:
                smooth_val = np.mean(freqs_raw)
            freqs_smooth.append(smooth_val)

            ax.clear()
            ax.plot(times, freqs_smooth, color='red')
            ax.set_ylim(0, 3200)
            ax.set_xlim(0, seconds)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_title('Dominant Frequency over Time (Recording)')
            canvas.draw()

        if len(frames) < int(RATE / CHUNK * seconds):
            root.after(50, update_plot)
        else:
            root.quit()

    def record_chunk():
        if len(frames) < int(RATE / CHUNK * seconds):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            root.after(1, record_chunk)

    root.after(1, record_chunk)
    root.after(1, update_plot)
    root.mainloop()

    stream.stop_stream()
    stream.close()
    p.terminate()

    raw = b"".join(frames)
    samples = np.frombuffer(raw, dtype=np.int16)
    wavfile.write(filename, RATE, samples)
    print(f"Saved to {filename}")

def play(filename: str = OUT_FILENAME, callback=None):
    rate, data = wavfile.read(filename)
    if data.ndim > 1:
        data = data[:, 0]
    total_samples = len(data)

    root = tk.Tk()
    root.title("Frequency Analyzer - Playback")
    root.geometry("800x600")

    choice = {'val': None}
    def on_retry(): choice['val'] = 'R'; root.quit()
    def on_exit(): choice['val'] = 'E'; root.quit()
    button_frame = tk.Frame(root)
    button_frame.pack(side=tk.BOTTOM, pady=10)
    tk.Button(button_frame, text="Retry Recording", command=on_retry, bg='#4CAF50', fg='white', font=('Arial',12)).pack(side=tk.LEFT, padx=10)
    tk.Button(button_frame, text="Exit", command=on_exit, bg='#f44336', fg='white', font=('Arial',12)).pack(side=tk.LEFT, padx=10)

    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_ylim(0, 3200)
    ax.set_xlim(0, total_samples / rate)
    ax.set_title('Dominant Frequency over Time (Playback)')

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=rate, output=True)

    position = 0
    play_times, play_freqs = [], []

    def update_playback():
        nonlocal position
        if position >= total_samples:
            stream.stop_stream()
            stream.close()
            p.terminate()
            ax.set_title('Playback Complete - Choose Retry or Exit')
            canvas.draw()
            return

        chunk = data[position:position+CHUNK]
        if len(chunk) < CHUNK:
            chunk = np.pad(chunk, (0, CHUNK-len(chunk)))
        position += CHUNK
        stream.write(chunk.tobytes())

        dominant_freq, _ = analyze_audio_chunk_single_freq(chunk, rate)
        play_times.append(position/rate)
        play_freqs.append(dominant_freq)

        if len(play_times) % PLOT_UPDATE_EVERY_PLAY == 0:
            ax.clear()
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_ylim(0, 3200)
            ax.set_xlim(0, total_samples / rate)
            ax.plot(play_times, play_freqs, color='blue')
            ax.set_title('Dominant Frequency over Time (Playback)')
            canvas.draw()

        root.after(1, update_playback)

    root.after(1, update_playback)
    root.mainloop()

    if callback:
        callback(choice['val'])

def main():
    try:
        seconds = 3.0
        choice = None
        def handle_choice(c):
            nonlocal choice
            choice = c

        while True:
            record(seconds, OUT_FILENAME)
            avg_freq = compute_average_frequency(OUT_FILENAME)
            print(f"\nEstimated average frequency of the note: {avg_freq:.2f} Hz")

            choice = None
            play(OUT_FILENAME, callback=handle_choice)

            if choice == 'E':
                print("Exiting program.")
                break
            elif choice == 'R':
                print("\nStarting new recording...")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
