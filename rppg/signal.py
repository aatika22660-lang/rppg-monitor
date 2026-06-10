"""
The CHROM algorithm (de Haan & Jeanne, 2013) works by projecting the 
normalized RGB traces onto a chrominance plane that is orthogonal to the 
skin-tone vector. Because specular reflection and global illumination 
changes lie along the skin-tone direction, projecting perpendicular to it 
cancels those artifacts while preserving the blood volume pulse. This makes 
it significantly more robust to lighting changes and minor motion compared 
to simple green channel mean methods.

Reference: de Haan G, Jeanne V. Robust pulse rate from chrominance-based 
rPPG. IEEE Trans Biomed Eng. 2013;60(10):2878-86.
"""
import numpy as np
from collections import deque
import scipy.signal

class RGBBuffer:
    """
    Maintains three separate rolling deques of length N=256 for R, G, B mean values.
    """
    def __init__(self, N=256):
        self.r_buffer = deque(maxlen=N)
        self.g_buffer = deque(maxlen=N)
        self.b_buffer = deque(maxlen=N)
        self.N = N
        
    def push(self, roi_frame):
        """
        Converts ROI from BGR to RGB and computes spatial mean of each channel.
        """
        if roi_frame is None or roi_frame.size == 0:
            return
            
        # Compute the spatial mean of each channel (OpenCV BGR: 0=B, 1=G, 2=R)
        # We'll compute means and then store them in RGB order in our buffers.
        b_mean = np.mean(roi_frame[:, :, 0])
        g_mean = np.mean(roi_frame[:, :, 1])
        r_mean = np.mean(roi_frame[:, :, 2])
        
        self.r_buffer.append(r_mean)
        self.g_buffer.append(g_mean)
        self.b_buffer.append(b_mean)
        
    @property
    def is_ready(self):
        """
        Returns True when buffers have at least 128 samples.
        """
        return len(self.g_buffer) >= 128
        
    def get_rgb(self):
        """
        Returns a (3, N) numpy array where rows are R, G, B traces.
        """
        return np.array([list(self.r_buffer), list(self.g_buffer), list(self.b_buffer)])

def temporal_normalize(rgb: np.ndarray) -> np.ndarray:
    """
    Normalizes each channel by its own mean and zero-centers it.
    """
    # rgb is (3, N)
    means = np.mean(rgb, axis=1, keepdims=True)
    # Avoid division by zero
    means[means == 0] = 1.0
    norm_rgb = rgb / means
    norm_rgb = norm_rgb - 1.0
    return norm_rgb

def chrom_project(rgb_norm: np.ndarray) -> np.ndarray:
    """
    Computes the CHROM pulse signal via chrominance projection.
    """
    # rgb_norm is (3, N)
    R_norm = rgb_norm[0]
    G_norm = rgb_norm[1]
    B_norm = rgb_norm[2]
    
    # X = 3R - 2G
    X = 3 * R_norm - 2 * G_norm
    # Y = 1.5R + G - 1.5B
    Y = 1.5 * R_norm + G_norm - 1.5 * B_norm
    
    std_x = np.std(X)
    std_y = np.std(Y)
    
    alpha = std_x / std_y if std_y != 0 else 0
    
    S = X - alpha * Y
    return S

def process_chrom(rgb: np.ndarray, fps=30):
    """
    Full CHROM pipeline: normalization -> projection -> windowing -> filtering -> smoothing.
    Returns (cleaned_signal, peaks) for compatibility with the tracker.
    """
    # 1. Temporal normalization
    rgb_norm = temporal_normalize(rgb)
    
    # 2. CHROM projection
    S = chrom_project(rgb_norm)
    
    # 3. Hann window to reduce spectral leakage
    S = S * np.hanning(len(S))
    
    # 4. Bandpass filter (Order 3, 0.7 - 3.5 Hz)
    nyquist = fps / 2.0
    b, a = scipy.signal.butter(3, [0.7/nyquist, 3.5/nyquist], btype='bandpass')
    filtered = scipy.signal.filtfilt(b, a, S)
    
    # 5. Savgol smoothing
    cleaned = scipy.signal.savgol_filter(filtered, window_length=11, polyorder=3)
    
    # Distance ensures we don't count double-peaks if the wave breaks.
    min_dist = int(fps * 0.4)
    peaks, _ = scipy.signal.find_peaks(cleaned, distance=min_dist)
    
    return cleaned, peaks
