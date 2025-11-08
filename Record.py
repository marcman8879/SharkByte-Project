import sys
import wave
import numpy as np
import pyaudio
from scipy.io import wavfile
import tkinter as tk
from scipy.fftpack import fft
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# main.py
# Record audio with PyAudio, save with scipy.io.wavfile, then play it back.


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
OUT_FILENAME = "recording.wav"
SMOOTH_WINDOW = 5  # moving average window (in frames)


def analyze_audio_chunk_single_freq(data, rate):
    # FFT
    N = len(data)
    fft_data = fft(data)
    freq = np.fft.fftfreq(N, 1.0/rate)
    magnitude = np.abs(fft_data)

    # Only positive frequencies
    pos_mask = freq > 0
    freq = freq[pos_mask]
    magnitude = magnitude[pos_mask]

    # Find dominant frequency
    dominant_index = np.argmax(magnitude)
    dominant_freq = freq[dominant_index]
    dominant_magnitude = magnitude[dominant_index]

    return dominant_freq, dominant_magnitude


# Add this function to compute average frequency
def compute_average_frequency(filename: str = OUT_FILENAME):
    # Read the WAV file
    rate, data = wavfile.read(filename)
    
    # Flatten in case of stereo
    if data.ndim > 1:
        data = data[:,0]
    
    # FFT
    N = len(data)
    fft_data = fft(data)
    freq = np.fft.fftfreq(N, 1.0/rate)
    magnitude = np.abs(fft_data)
    
    # Consider only positive frequencies
    pos_mask = freq > 0
    freq = freq[pos_mask]
    magnitude = magnitude[pos_mask]
    
    # Compute weighted average frequency
    avg_freq = np.sum(freq * magnitude) / np.sum(magnitude)
    
    return avg_freq


def record(seconds: float, filename: str = OUT_FILENAME):
    # Create the main window
    root = tk.Tk()
    root.title("Frequency Analyzer - Recording")
    root.geometry("800x600")

    # Create matplotlib figure
    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print(f"Recording {seconds:.2f} seconds...")
    frames = []
    times = []
    freqs_raw = []
    freqs_smooth = []
    
    def update_plot():
        if len(frames) > 0:
            # Get the latest frame
            latest_data = np.frombuffer(frames[-1], dtype=np.int16)

            # Analyze frequencies using the same function as playback
            dominant_freq, dominant_magnitude = analyze_audio_chunk_single_freq(latest_data, RATE)

            # Append time and raw frequency
            t = len(frames) * (CHUNK / RATE)
            times.append(t)
            freqs_raw.append(dominant_freq)

            # Compute smoothed frequency (moving average)
            if len(freqs_raw) >= SMOOTH_WINDOW:
                smooth_val = np.mean(freqs_raw[-SMOOTH_WINDOW:])
            else:
                smooth_val = np.mean(freqs_raw)
            freqs_smooth.append(smooth_val)

            # Plot dominant frequency over time as a smoothed line
            ax.clear()
            ax.plot(times, freqs_smooth, '-o', color='red')
            ax.set_ylim(0, 3200)
            ax.set_xlim(0, seconds)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_title('Dominant Frequency over Time')
            canvas.draw()
        
        if len(frames) < int(RATE / CHUNK * seconds):
            root.after(50, update_plot)  # Update every 50ms
        else:
            root.quit()

    def record_chunk():
        if len(frames) < int(RATE / CHUNK * seconds):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            root.after(1, record_chunk)

    # Start recording and updating
    root.after(1, record_chunk)
    root.after(1, update_plot)
    
    # Start the GUI main loop
    root.mainloop()

    stream.stop_stream()
    stream.close()
    p.terminate()
    
    raw = b"".join(frames)
    samples = np.frombuffer(raw, dtype=np.int16)
    wavfile.write(filename, RATE, samples)
    print(f"Saved to {filename}")


def analyze_audio_chunk(data, rate):
    # Just use the single frequency analysis for consistency
    return analyze_audio_chunk_single_freq(data, rate)

def play(filename: str = OUT_FILENAME, callback=None):
    rate, data = wavfile.read(filename)
    # Ensure int16 format
    if data.dtype != np.int16:
        # convert floats in [-1,1] to int16
        if np.issubdtype(data.dtype, np.floating):
            data = (data * 32767).astype(np.int16)
        else:
            data = data.astype(np.int16)
    channels = 1 if data.ndim == 1 else data.shape[1]

    # Create window for playback visualization
    root = tk.Tk()
    root.title("Frequency Analyzer - Playback")
    root.geometry("800x600")

    def on_retry():
        root.quit()
        if callback:
            callback('R')

    def on_exit():
        root.quit()
        if callback:
            callback('E')

    # Create button frame
    button_frame = tk.Frame(root)
    button_frame.pack(side=tk.BOTTOM, pady=10)
    
    retry_btn = tk.Button(button_frame, text="Retry Recording", command=on_retry, 
                         bg='#4CAF50', fg='white', font=('Arial', 12))
    retry_btn.pack(side=tk.LEFT, padx=10)
    
    exit_btn = tk.Button(button_frame, text="Exit", command=on_exit,
                        bg='#f44336', fg='white', font=('Arial', 12))
    exit_btn.pack(side=tk.LEFT, padx=10)

    # Create matplotlib figure
    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    output=True)
    
    chunk_size = CHUNK
    position = 0
    play_times = []
    play_raw = []
    play_smooth = []
    
    def update_plot():
        nonlocal position
        if position < len(data):
            # Get current chunk of audio data
            chunk = data[position:position + chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            
            # Play the chunk
            stream.write(chunk.tobytes())
            
            # Analyze frequencies (dominant frequency for this chunk)
            dominant_freq, dominant_magnitude = analyze_audio_chunk_single_freq(chunk, rate)

            # Append time and raw frequency
            t = position / rate
            play_times.append(t)
            play_raw.append(dominant_freq)

            # Compute smoothed frequency (moving average)
            if len(play_raw) >= SMOOTH_WINDOW:
                p_smooth = np.mean(play_raw[-SMOOTH_WINDOW:])
            else:
                p_smooth = np.mean(play_raw)
            play_smooth.append(p_smooth)

            # Update the plot as a smoothed line of dominant frequency over time
            ax.clear()
            ax.plot(play_times, play_smooth, '-o', color='blue')
            ax.set_ylim(0, 3200)
            ax.set_xlim(0, len(data) / rate)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_title('Dominant Frequency over Time (Playback)')
            canvas.draw()
            position += chunk_size
            root.after(1, update_plot)
        else:
            stream.stop_stream()
            stream.close()
            p.terminate()
            # Don't quit - wait for user choice
            retry_btn.config(state=tk.NORMAL)  # Enable buttons after playback
            exit_btn.config(state=tk.NORMAL)
            ax.set_title('Playback Complete - Choose Retry or Exit')
            canvas.draw()
    
    # Disable buttons during playback
    retry_btn.config(state=tk.DISABLED)
    exit_btn.config(state=tk.DISABLED)
    
    print(f"Playing {filename}...")
    root.after(1, update_plot)
    root.mainloop()


def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
            print("Usage: python main.py [seconds]\nIf seconds omitted, defaults to 15.")
            return
        seconds = 15.0
        if len(sys.argv) > 1:
            try:
                seconds = float(sys.argv[1])
            except ValueError:
                pass
        
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