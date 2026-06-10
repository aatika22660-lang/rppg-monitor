import cv2
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont, QBrush


# ─── Palette ──────────────────────────────────────────
CREAM      = "#F4EFE8"
PANEL_BG   = "#EDE8E2"
DUSTY_BLUE = "#7E8FB2"
BOLD_BLUE  = "#6B7DA6"
LIGHT_BLUE = "#A3B0C8"
FAINT_LINE = "#D0CABC"
TEXT_DARK  = "#5A6A8C"


class WaveformWidget(QWidget):
    """Clean scrolling waveform."""
    def __init__(self, parent=None, title="Signal"):
        super().__init__(parent)
        self.setMinimumSize(300, 140)
        self.data = []
        self.title = title

    def update_data(self, new_data):
        if len(new_data) > 150:
            self.data = list(new_data[-150:])
        else:
            self.data = list(new_data)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor(CREAM))
        
        # Bottom border line
        painter.setPen(QPen(QColor(FAINT_LINE), 1))
        painter.drawLine(0, h - 1, w, h - 1)
        
        # Title
        painter.setFont(QFont("Georgia", 10))
        painter.setPen(QColor(LIGHT_BLUE))
        painter.drawText(8, 20, self.title)
        
        if not self.data or len(self.data) < 2:
            return
            
        min_val, max_val = min(self.data), max(self.data)
        val_range = (max_val - min_val) if (max_val - min_val) > 0.01 else 1.0
        
        step_x = w / max(1, len(self.data) - 1)
        points = []
        for i in range(len(self.data)):
            x = int(i * step_x)
            y_raw = int(h - ((self.data[i] - min_val) / val_range * h))
            pad = h * 0.15
            usable = h - (pad * 2)
            y = int(pad + ((y_raw / h) * usable))
            points.append((x, y))
        
        # Main waveform line
        pen = QPen(QColor(DUSTY_BLUE))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])


class DebugPlotWidget(QWidget):
    """Minimal R/G/B trace plot."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 70)
        self.r_data, self.g_data, self.b_data = [], [], []

    def update_data(self, r, g, b):
        limit = 150
        self.r_data = list(r[-limit:]) if len(r) > limit else list(r)
        self.g_data = list(g[-limit:]) if len(g) > limit else list(g)
        self.b_data = list(b[-limit:]) if len(b) > limit else list(b)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor(CREAM))
        
        painter.setPen(QPen(QColor(FAINT_LINE), 1))
        painter.drawLine(0, h - 1, w, h - 1)
        
        painter.setFont(QFont("Georgia", 9))
        painter.setPen(QColor(LIGHT_BLUE))
        painter.drawText(8, 14, "R / G / B")

        dataset = [self.r_data, self.g_data, self.b_data]
        colors = [QColor(DUSTY_BLUE), QColor(LIGHT_BLUE), QColor(BOLD_BLUE)]

        for data, color in zip(dataset, colors):
            if len(data) < 2: continue
            min_v, max_v = min(data), max(data)
            v_range = (max_v - min_v) if (max_v - min_v) > 0.01 else 1.0
            painter.setPen(QPen(color, 1))
            step_x = w / max(1, len(data) - 1)
            for i in range(len(data) - 1):
                x1, x2 = int(i * step_x), int((i + 1) * step_x)
                y1 = int(h - ((data[i] - min_v) / v_range * h))
                y2 = int(h - ((data[i+1] - min_v) / v_range * h))
                painter.drawLine(x1, y1, x2, y2)


class Dashboard(QMainWindow):
    """
    Clean cream + dusty blue UI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("rPPG Heart Rate Monitor")
        self.setFixedSize(920, 600)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {CREAM};
            }}
        """)
        self.init_ui()
        
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(28)
        
        # ─── LEFT ──────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(14)
        
        # Camera viewer
        self.video_label = QLabel()
        self.video_label.setFixedSize(480, 360)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Camera Offline")
        self.video_label.setStyleSheet(f"""
            background-color: {PANEL_BG};
            border: 1px solid {FAINT_LINE};
            border-radius: 6px;
            color: {LIGHT_BLUE};
            font-family: Georgia;
            font-size: 14px;
        """)
        left.addWidget(self.video_label)
        
        # Button
        self.btn_toggle = QPushButton("Start Camera")
        self.btn_toggle.setFixedHeight(44)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {DUSTY_BLUE};
                color: {CREAM};
                font-family: Georgia;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {BOLD_BLUE};
            }}
        """)
        left.addWidget(self.btn_toggle)
        main_layout.addLayout(left)
        
        # ─── RIGHT ─────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(6)
        
        # Small subtitle
        lbl_sub = QLabel("the reading of")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet(f"""
            font-family: Georgia;
            font-size: 12px;
            color: {LIGHT_BLUE};
            padding-top: 8px;
            font-style: italic;
        """)
        right.addWidget(lbl_sub)
        
        # Big bold title
        lbl_title = QLabel("heart rate")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"""
            font-family: Georgia;
            font-size: 28px;
            font-weight: bold;
            color: {DUSTY_BLUE};
            padding-bottom: 2px;
        """)
        right.addWidget(lbl_title)
        
        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {FAINT_LINE}; margin: 0 40px;")
        sep.setFixedHeight(1)
        right.addWidget(sep)
        
        # BPM value
        self.lbl_bpm_value = QLabel("--")
        self.lbl_bpm_value.setAlignment(Qt.AlignCenter)
        self.lbl_bpm_value.setStyleSheet(f"""
            font-family: Georgia;
            font-size: 64px;
            font-weight: bold;
            color: {BOLD_BLUE};
            padding: 4px 0;
        """)
        right.addWidget(self.lbl_bpm_value)
        
        # Waveform
        self.waveform_plot = WaveformWidget(title="pulse signal")
        right.addWidget(self.waveform_plot)
        
        # Debug
        self.debug_plot = DebugPlotWidget()
        right.addWidget(self.debug_plot)
        
        # Readouts
        readout_widget = QWidget()
        readout_layout = QVBoxLayout(readout_widget)
        readout_layout.setContentsMargins(0, 8, 0, 0)
        readout_layout.setSpacing(2)
        
        self.lbl_status_bpm = QLabel("Recent BPM: --")
        self.lbl_status_conf = QLabel("Confidence: --")
        self.lbl_status_samples = QLabel("Buffer: 0 / 150")
        
        for lbl in [self.lbl_status_bpm, self.lbl_status_conf, self.lbl_status_samples]:
            lbl.setStyleSheet(f"""
                font-family: Georgia;
                font-size: 11px;
                color: {LIGHT_BLUE};
                padding: 1px 0;
            """)
            readout_layout.addWidget(lbl)
            
        right.addWidget(readout_widget)
        right.addStretch()
        main_layout.addLayout(right)

    # ─── Controller Hooks ──────────────────────────────
    
    def set_button_state(self, is_running):
        if is_running:
            self.btn_toggle.setText("Stop Camera")
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BOLD_BLUE};
                    color: {CREAM};
                    font-family: Georgia;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background-color: {TEXT_DARK};
                }}
            """)
        else:
            self.btn_toggle.setText("Start Camera")
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DUSTY_BLUE};
                    color: {CREAM};
                    font-family: Georgia;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background-color: {BOLD_BLUE};
                }}
            """)
            
    def set_camera_frame(self, bgr_frame):
        rgb_image = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(480, 360, Qt.KeepAspectRatio)
        self.video_label.setPixmap(pixmap)
        
    def show_placeholder(self, text):
        self.video_label.clear()
        self.video_label.setText(text)
        self.waveform_plot.update_data([])
        
    def set_waveform(self, signal):
        self.waveform_plot.update_data(signal)

    def set_debug_plot(self, r, g, b):
        self.debug_plot.update_data(r, g, b)
        
    def clear_metrics(self):
        self.lbl_bpm_value.setText("--  /  --")
        self.lbl_bpm_value.setStyleSheet(f"""
            font-family: Georgia; font-size: 52px; font-weight: bold;
            color: {LIGHT_BLUE}; padding: 4px 0;
        """)
        self.lbl_status_bpm.setText("FFT: -- | Peak: --")
        self.lbl_status_conf.setText("Confidence: --")
        self.lbl_status_samples.setText("Buffer: 0 / 150")

    def set_metrics(self, stable_fft, stable_peaks, confidence, samples):
        self.lbl_status_samples.setText(f"Buffer: {samples} / 150")
        
        if stable_fft is None or confidence is None:
            return
            
        fft_text = f"{stable_fft:.1f}" if stable_fft is not None else "--"
        peak_text = f"{stable_peaks:.1f}" if stable_peaks is not None else "--"
        
        self.lbl_status_bpm.setText(f"FFT: {fft_text}  |  Peak: {peak_text}")
        self.lbl_status_conf.setText(f"Confidence: {confidence}")
        
        fft_int = int(stable_fft) if stable_fft is not None else "--"
        peak_int = int(stable_peaks) if stable_peaks is not None else "--"
        self.lbl_bpm_value.setText(f"{fft_int}  /  {peak_int}")
        
        if confidence == "HIGH":
            color = TEXT_DARK
        elif confidence == "MEDIUM":
            color = DUSTY_BLUE
        else:
            color = LIGHT_BLUE
            
        self.lbl_bpm_value.setStyleSheet(f"""
            font-family: Georgia; font-size: 52px; font-weight: bold;
            color: {color}; padding: 4px 0;
        """)
