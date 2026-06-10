import cv2
import urllib.request
import os
import numpy as np

class FaceCapture:
    """Class to capture video from webcam and isolate the forehead region for rPPG."""
    
    def __init__(self, camera_index=0):
        # Open the default webcam
        self.cap = cv2.VideoCapture(camera_index)
        
        # Load the Haar Cascade for frontal face detection.
        # We download it temporarily if it doesn't exist locally to ensure it works anywhere
        cascade_path = "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            print("Downloading Haarcascade XML...")
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
            urllib.request.urlretrieve(url, cascade_path)
            
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def get_frame(self):
        """Read and return the raw BGR frame from the webcam."""
        ret, frame = self.cap.read()
        if not ret:
            return None
        # Flip frame horizontally for a more natural mirror effect
        return cv2.flip(frame, 1)

    def get_roi(self, frame):
        """
        Detect the largest face in the frame and extract the forehead ROI.
        Assumes the forehead is the top 30% of the bounding box, and the 
        center 60% of the width.
        
        Returns:
            Tuple of (roi_image, (x, y, w, h)) or (None, None) if no face found.
        """
        if frame is None:
            return None, None
            
        # Convert frame to grayscale for the cascade classifier
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces (scaleFactor, minNeighbors, minSize)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
        
        if len(faces) == 0:
            return None, None
            
        # Find the largest face by area (w * h)
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face
        
        # Calculate Forehead ROI boundaries
        # We want the top 30% of the height, and center 60% of the width
        # Width: trim 20% off the left, 20% off the right
        # Height: start at the top, go down 30%
        
        roi_x = int(x + (w * 0.2))
        roi_y = int(y)
        roi_w = int(w * 0.6)
        roi_h = int(h * 0.3)
        
        # Extract the pixels
        roi_img = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        return roi_img, (roi_x, roi_y, roi_w, roi_h)

    def release(self):
        """Release the webcam resource."""
        self.cap.release()

class LightingChecker:
    """Evaluates frame brightness to warn user if conditions are too poor for rPPG."""
    def check(self, frame):
        if frame is None:
            return "OK"
            
        # Convert to HSV color space to easily extract the Value (brightness) channel
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Calculate mean brightness across the entire image
        mean_v = np.mean(hsv[:, :, 2])
        
        if mean_v < 80:
            return "TOO DARK"
        elif mean_v > 210:
            return "TOO BRIGHT"
            
        return "OK"

class MotionDetector:
    """
    Detects excessive movement in the ROI to prevent motion artifacts 
    from contaminating the rPPG signal.
    """
    def __init__(self, threshold=8.0):
        self.threshold = threshold
        self.prev_roi = None
        self.motion_level = 0.0
        
    def is_motion_high(self, roi_frame):
        if roi_frame is None or roi_frame.size == 0:
            return False
            
        # Convert to grayscale and resize to a fixed size for consistent analysis
        gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        gray_roi = cv2.resize(gray_roi, (100, 100))
        
        if self.prev_roi is None:
            self.prev_roi = gray_roi
            return False
            
        # Calculate absolute difference between current and previous ROI
        diff = cv2.absdiff(gray_roi, self.prev_roi)
        self.motion_level = float(np.mean(diff))
        
        # Update previous ROI for next frame
        self.prev_roi = gray_roi
        
        return self.motion_level > self.threshold
