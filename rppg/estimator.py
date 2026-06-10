import numpy as np
import scipy.signal
from collections import deque
from typing import Optional

def estimate_hr(signal: np.ndarray, fps=30) -> Optional[float]:
    """
    Estimates heart rate in BPM from a processed signal array using FFT and PSD.
    """
    n = len(signal)
    if n == 0:
        return None
        
    # Apply Hanning window to reduce spectral leakage
    windowed = signal * np.hanning(n)
    
    # Calculate real discrete Fourier transform
    freqs = np.fft.rfftfreq(n, d=1.0/fps)
    fft_magnitudes = np.abs(np.fft.rfft(windowed))
    
    # Power Spectral Density (magnitude squared of FFT)
    psd = fft_magnitudes ** 2
    
    # Isolate the frequency band corresponding to human heart rates (0.7 Hz to 3.5 Hz)
    valid_indices = np.where((freqs >= 0.7) & (freqs <= 3.5))[0]
    
    if len(valid_indices) == 0:
        return None
        
    valid_freqs = freqs[valid_indices]
    valid_psd = psd[valid_indices]
    
    # Find dominant frequency peak using prominence to reject noise
    max_psd = np.max(valid_psd)
    if max_psd == 0:
        return None
        
    # Find peaks with prominence > 0.3 * max_peak
    peaks, _ = scipy.signal.find_peaks(valid_psd, prominence=0.3 * max_psd)
    
    if len(peaks) == 0:
        return None
        
    # Use the highest peak among those found
    best_peak_idx = peaks[np.argmax(valid_psd[peaks])]
    dominant_hz = valid_freqs[best_peak_idx]
    
    # Convert Hz to Beats Per Minute (BPM)
    bpm = dominant_hz * 60.0
    
    return round(float(bpm), 1)

class HRTracker:
    """
    Tracks and smooths consecutive heart rate estimates over time, 
    managing both the FFT baseline metrics and the Peak Counter metrics simultaneously.
    """
    def __init__(self, history_size=10):
        # Rolling histories
        self.fft_history = deque(maxlen=history_size)
        self.peak_history = deque(maxlen=history_size)
        self.latest_fft_success = False
        
    def update(self, fft_bpm: Optional[float], peaks: np.ndarray, signal_length: int, fps=30):
        """Append a newly calculated BPM estimate to the rolling histories."""
        # 1. Update FFT Array
        self.latest_fft_success = (fft_bpm is not None)
        if fft_bpm is not None:
            self.fft_history.append(fft_bpm)
            
        # 2. Update Peak Detection Array
        if len(peaks) >= 2:
            # We must have at least 2 peaks to measure the distance (pulse) between them.
            # Convert frame count between first and last peak to seconds
            time_span_seconds = (peaks[-1] - peaks[0]) / fps
            
            # (Total peaks minus 1 = total intervals) / duration * 60 seconds
            if time_span_seconds > 0:
                bpm_from_peaks = ((len(peaks) - 1) / time_span_seconds) * 60.0
                self.peak_history.append(bpm_from_peaks)
        
    @property
    def stable_fft_hr(self):
        """Returns the median of recent FFT estimates."""
        if len(self.fft_history) < 5:
            return None
        return round(float(np.median(self.fft_history)), 1)
        
    @property
    def stable_peak_hr(self):
        """Returns the median of recent Peak Detection estimates."""
        if len(self.peak_history) < 5:
            return None
        return round(float(np.median(self.peak_history)), 1)
        
    @property
    def confidence(self):
        """
        Confidence ranking based on FFT array variance.
        """
        if len(self.fft_history) < 5:
            return "ACQUIRING"
            
        std_dev = np.std(self.fft_history)
        
        if std_dev < 2.0 and self.latest_fft_success:
            return "HIGH"
        elif std_dev < 5.0:
            return "MEDIUM"
        else:
            return "LOW"
