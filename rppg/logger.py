import csv
import time
from datetime import datetime
import os

class DataLogger:
    """
    Logs raw and processed rPPG metrics to a timestamped CSV file 
    for post-session analysis.
    """
    def __init__(self, output_dir="logs"):
        self.csv_file = None
        self.csv_writer = None
        self.output_dir = output_dir
        
        # Ensure log directory exists so it doesn't crash on open()
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_session(self):
        """Opens a new CSV file named session_YYYYMMDD_HHMMSS.csv and writes headers."""
        # Use python's datetime strftime to format standard ISO chunks
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"session_{timestamp}.csv")
        
        # Open in append mode 'a' but since it's a new file it functions identically to 'w'
        # Ensures cross-platform newline handling with newline=''
        self.csv_file = open(filename, mode='a', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        
        # Write the column headers exactly as requested
        self.csv_writer.writerow([
            "timestamp", 
            "raw_green", 
            "filtered_signal", 
            "bpm_fft", 
            "bpm_peaks", 
            "confidence"
        ])
        print(f"📊 Logging session started: {filename}")

    def log(self, row: dict):
        """Extracts correctly typed data from dict and pushes to the CSV writer natively."""
        if not self.csv_writer:
            return
            
        # Get defaults as empty string if key is completely missing
        # This prevents crashing if metrics drop out during a frame gap
        timestamp = row.get("timestamp", time.time())
        raw_green = row.get("raw_green", "")
        filtered_sig = row.get("filtered_signal", "")
        bpm_fft = row.get("bpm_fft", "")
        bpm_peaks = row.get("bpm_peaks", "")
        confidence = row.get("confidence", "")
        
        self.csv_writer.writerow([
            timestamp,
            raw_green,
            filtered_sig,
            bpm_fft,
            bpm_peaks,
            confidence
        ])
        
    def end_session(self):
        """Flushes the buffer to disk and closes the file handle cleanly."""
        if self.csv_file and not self.csv_file.closed:
            self.csv_file.flush()
            self.csv_file.close()
            self.csv_writer = None
            print("⏹️  Logging session ended.")
