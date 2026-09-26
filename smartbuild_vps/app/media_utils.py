# media_utils.py
import os
import glob
import shutil
import subprocess
import cv2
from buildercv.smartbuild_vps.app.config import ANNOTATED_DIR

DEFAULT_ANNOTATED_DIR = ANNOTATED_DIR

def get_latest_frame(folder=DEFAULT_ANNOTATED_DIR):
    """Ищет самую свежую картинку в папке"""
    if not os.path.exists(folder):
        return None
    list_of_files = glob.glob(f"{folder}/*.[jJ][pP][gG]") + glob.glob(f"{folder}/*.[pP][nN][gG]")
    if not list_of_files:
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def generate_timelapse(input_folder=DEFAULT_ANNOTATED_DIR, output_file="temp_timelapse.mp4", fps=5):
    """Склеивает кадры в MP4, совместимый с браузерным видеоплеером."""
    images = sorted(glob.glob(f"{input_folder}/*.[jJ][pP][gG]"))
    if not images:
        return False
        
    frame = cv2.imread(images[0])
    height, width, layers = frame.shape
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
    
    for image_path in images[-100:]: 
        img = cv2.imread(image_path)
        video.write(img)
        
    video.release()
    return True