# rPPG Heart Rate Monitor

A real-time remote photoplethysmography (rPPG) monitoring application that estimates heart rate from a webcam feed using advanced signal processing.

![rPPG Demo Placeholder](https://via.placeholder.com/800x450.png?text=rPPG+Monitor+Interface+Showing+Waveforms+and+BPM)

## 🚀 Features

- **Chrominance-based (CHROM) Processing**: Uses the robust CHROM algorithm (de Haan & Jeanne, 2013) to minimize motion artifacts and lighting variations.
- **Dual BPM Estimation**:
  - **FFT-based**: Frequency domain analysis using Power Spectral Density (PSD) for precision.
  - **Peak-counting**: Time-domain rhythm analysis for stability.
- **Dynamic UI Dashboard**:
  - Live webcam feed with forehead Region of Interest (ROI) tracking.
  - Real-time scrolling plot of the **CHROM pulse signal**.
  - **RGB Debug Traces** to visualize raw sensor input.
  - Confidence indicators (HIGH, MEDIUM, LOW, ACQUIRING).
- **Intelligent Monitoring**:
  - **Motion Detector**: Automatically pauses buffer collection during excessive movement.
  - **Lighting Checker**: Warns the user if the environment is too dark or too bright.
- **Data Logging**: Optional CSV logging of session metrics for offline analysis.

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- A functional webcam

### Setup

1. Clone or download the repository.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage

Run the monitor from the terminal:

```bash
python main.py
```

### Command Line Arguments

| Flag    | Description                                         |
| ------- | --------------------------------------------------- |
| `--log` | Enables CSV data logging to the `./logs` directory. |

### Tips for Best Results

- **Stability**: Keep your head relatively still. The motion detector will pause collection if movement is too high.
- **Lighting**: Ensure even lighting on your face. Avoid harsh backlighting or extreme shadows.
- **ROI**: The red rectangle should be positioned on your forehead for optimal signal extraction.

## 🗺️ Walkthrough: How to Run

Follow these steps from start to finish to get the rPPG monitor running on your machine.

### Step 1 — Clone the Repository

```bash
git clone https://github.com/<your-username>/rppg-monitor.git
cd rppg-monitor
```

### Step 2 — Create a Virtual Environment

```bash
python3 -m venv venv
```

### Step 3 — Activate the Virtual Environment

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

> You should see `(venv)` appear at the beginning of your terminal prompt.

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
| Package         | Purpose                                    |
| --------------- | ------------------------------------------ |
| `opencv-python` | Webcam capture & face detection (Haar)     |
| `numpy`         | Numerical operations on signal buffers     |
| `scipy`         | Bandpass filtering & FFT for HR estimation |
| `PyQt5`         | GUI framework for the dashboard            |

### Step 5 — Run the Application

**Basic launch (no logging):**
```bash
python main.py
```

**With CSV session logging enabled:**
```bash
python main.py --log
```
> When `--log` is passed, each session's metrics (timestamps, raw green channel, filtered signal, BPM estimates, and confidence) are saved as CSV files inside the `./logs` directory.

### Step 6 — Using the Interface

1. **Click "▶ Start Camera"** — this activates your webcam and begins face detection.
2. **Position your face** so the red rectangle (ROI) sits on your forehead.
3. **Hold still** — the buffer fills to ~150 samples, then real-time heart rate estimation begins.
4. **Monitor the dashboard:**
   - **Pulse Signal** — the CHROM-processed waveform scrolls in real time.
   - **RGB Debug** — raw R, G, B channel traces from the forehead ROI.
   - **BPM (FFT)** — heart rate estimated via frequency analysis.
   - **BPM (Peaks)** — heart rate estimated via peak counting.
   - **Confidence** — quality indicator (HIGH, MEDIUM, LOW, or ACQUIRING).
5. **Click "⏹ Stop Camera"** when done — the webcam releases and (if logging) the CSV file is finalized.

### Troubleshooting

| Problem                          | Solution                                                                 |
| -------------------------------- | ------------------------------------------------------------------------ |
| `ModuleNotFoundError`            | Make sure your virtual environment is activated and dependencies are installed. |
| Camera doesn't open              | Check that no other app is using the webcam. Try restarting your terminal. |
| "No face detected" on screen     | Ensure adequate lighting and face the camera directly.                   |
| `WARNING: TOO DARK / TOO BRIGHT` | Adjust your room lighting — avoid harsh backlights or direct sunlight.   |
| `WARNING: MOTION DETECTED`       | Keep your head still — the buffer pauses during high motion.             |
| BPM reads `--`                   | Wait for the buffer to fill (~5 seconds). The status area shows sample progress. |

## 📂 Project Structure

- `main.py`: The central controller unit orchestrating capture, processing, and UI updates.
- `rppg/`: The core logic package.
  - `capture.py`: Handles OpenCV video capture, face detection, and lighting/motion checks.
  - `signal.py`: Implements the `RGBBuffer` and the **CHROM** signal processing pipeline.
  - `estimator.py`: Contains HR calculation logic (FFT/PSD) and the `HRTracker`.
  - `logger.py`: Manages CSV serialization of session data.
- `ui/`: The presentation layer.
  - `dashboard.py`: A PyQt5-based GUI featuring custom drawing widgets for waveforms.

## 🧪 Scientific Reference

The core signal extraction uses the **CHROM** algorithm as described by:

> de Haan G, Jeanne V. _Robust pulse rate from chrominance-based rPPG._ IEEE Trans Biomed Eng. 2013;60(10):2878-86.

## 📜 License

This project is for educational and experimental purposes.
