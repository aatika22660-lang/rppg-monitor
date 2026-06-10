import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from rppg.capture import FaceCapture, LightingChecker, MotionDetector
from rppg.signal import RGBBuffer, process_chrom
from rppg.estimator import estimate_hr, HRTracker
from rppg.logger import DataLogger
from ui.dashboard import Dashboard
import time
import argparse

class Controller:
    def __init__(self, enable_logging=False):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        
        # Init View
        self.dashboard = Dashboard()
        
        # Init Models
        self.capture = None
        self.lighting_checker = LightingChecker()
        self.motion_detector = MotionDetector(threshold=8.0)
        self.signal_buffer = RGBBuffer()
        self.hr_tracker = HRTracker()
        self.fps = 30
        
        # Optional Logger Object if --log passed to CLI
        self.enable_logging = enable_logging
        self.logger = DataLogger() if enable_logging else None
        
        # Connect View buttons
        self.dashboard.btn_toggle.clicked.connect(self.toggle_camera)
        
        # Hook cleanup on exit
        self.app.aboutToQuit.connect(self.cleanup)
        
        # Init Loop Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_tick)
        
    def start(self):
        self.dashboard.show()
        sys.exit(self.app.exec_())
        
    def toggle_camera(self):
        if self.capture is None:
            # Start Camera
            self.capture = FaceCapture()
            self.signal_buffer = RGBBuffer()
            self.hr_tracker = HRTracker()
            
            self.dashboard.set_button_state(is_running=True)
            self.dashboard.clear_metrics()
            
            # Hook CSV writer
            if self.enable_logging:
                self.logger.start_session()
            
            self.timer.start(33) # ~30fps
        else:
            # Stop Camera
            self.timer.stop()
            self.capture.release()
            self.capture = None
            
            # Close CSV file
            if self.enable_logging:
                self.logger.end_session()
                
            self.dashboard.set_button_state(is_running=False)
            self.dashboard.clear_metrics()
            self.dashboard.show_placeholder("Camera Offline")
            
    def update_tick(self):
        if self.capture is None:
            return
            
        # 1. Grab raw frame
        frame = self.capture.get_frame()
        if frame is None:
            return
            
        # 2. Extract ROI
        roi_img, bbox = self.capture.get_roi(frame)
        
        motion_alert = False
        if roi_img is None:
            # Show "No face detected" overlay
            cv2.putText(frame, "No face detected", (frame.shape[1]//2 - 100, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            
            # Detect motion in ROI
            if self.motion_detector.is_motion_high(roi_img):
                motion_alert = True
                # Skip pushing this frame to the buffer to keep the signal clean
            else:
                # 3. Push ROI to buffer
                self.signal_buffer.push(roi_img)
            
        # 3b. Evaluate Lighting Conditions
        lighting_status = self.lighting_checker.check(frame)
        
        # Draw Warnings (Lighting or Motion)
        if lighting_status != "OK" or motion_alert:
            # Draw semi-transparent background bar for alerts
            overlay = frame.copy()
            
            # If motion is high, use CYAN. Lighting use RED/ORANGE as before.
            if motion_alert:
                banner_color = (255, 255, 0) # Cyan in BGR
                alert_text = "WARNING: MOTION DETECTED"
            else:
                banner_color = (0, 0, 255) if lighting_status == "TOO DARK" else (0, 165, 255)
                alert_text = f"WARNING: {lighting_status}"
            
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], 40), banner_color, -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            text_w, text_h = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0] 
            center_x = (frame.shape[1] - text_w) // 2
            
            cv2.putText(frame, alert_text, (center_x, 28), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            
        # Update UI Frame
        self.dashboard.set_camera_frame(frame)
        
        # Status
        # Use g_buffer as the sample count reference
        samples = len(self.signal_buffer.g_buffer)
        
        # 4. Processing
        if self.signal_buffer.is_ready:
            # get_rgb returns (3, N) -> [R_trace, G_trace, B_trace]
            rgb_data = self.signal_buffer.get_rgb()
            
            # Switch to CHROM projection pipeline
            filtered_signal, peaks = process_chrom(rgb_data, fps=self.fps)
            
            new_bpm = estimate_hr(filtered_signal, fps=self.fps)
            self.hr_tracker.update(new_bpm, peaks, len(filtered_signal), fps=self.fps)
                
            # 5. Push processed signal + metrics
            self.dashboard.set_waveform(filtered_signal)
            self.dashboard.set_debug_plot(rgb_data[0], rgb_data[1], rgb_data[2])
            self.dashboard.set_metrics(
                stable_fft=self.hr_tracker.stable_fft_hr,
                stable_peaks=self.hr_tracker.stable_peak_hr,
                confidence=self.hr_tracker.confidence,
                samples=samples
            )
            
            # 6. Log Row to CSV File
            if self.enable_logging:
                # The 'latest' sample value is mechanically at the very end of our signal lists
                metrics_row = {
                    "timestamp": time.time(),
                    "raw_green": round(rgb_data[1][-1], 2),
                    "filtered_signal": round(filtered_signal[-1], 2),
                    "bpm_fft": self.hr_tracker.stable_fft_hr,
                    "bpm_peaks": self.hr_tracker.stable_peak_hr,
                    "confidence": self.hr_tracker.confidence
                }
                self.logger.log(metrics_row)
            
        else:
            # Push raw signal while loading memory buffer
            rgb_data = self.signal_buffer.get_rgb()
            raw_signal = rgb_data[1] if samples > 0 else np.array([])
            self.dashboard.set_waveform(raw_signal)
            self.dashboard.set_debug_plot(rgb_data[0], rgb_data[1], rgb_data[2])
            self.dashboard.set_metrics(None, None, None, samples)
            
            if self.enable_logging and len(raw_signal) > 0:
                self.logger.log({
                    "timestamp": time.time(),
                    "raw_green": round(raw_signal[-1], 2),
                    "filtered_signal": "",
                    "bpm_fft": "",
                    "bpm_peaks": "",
                    "confidence": ""
                })

    def cleanup(self):
        """Releases the webcam and flushes disk resources cleanly on window close."""
        if self.capture:
            self.capture.release()
        if self.enable_logging and self.logger:
            self.logger.end_session()

def main():
    parser = argparse.ArgumentParser(description="rPPG Heart Rate Monitor")
    parser.add_argument("--log", action="store_true", help="Enable CSV data logging to ./logs directory")
    args = parser.parse_args()
    
    controller = Controller(enable_logging=args.log)
    controller.start()

if __name__ == "__main__":
    main()
