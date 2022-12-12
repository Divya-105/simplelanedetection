# -*- coding: utf-8 -*-
# Import required libraries

import cv2
from matplotlib import pyplot as plt
import numpy as np
import streamlit as st
import requests
#importing some useful packages
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
import tempfile
import pandas as pd
import subprocess
import sys
# Import everything needed to edit/save/watch video clips
from moviepy.editor import VideoFileClip
from IPython.display import HTML

#%matplotlib inline

import math
# Home UI 

def main():

    st.set_page_config(layout="wide")

    font_css = """
    <style>
    button[data-baseweb="tab"] {
    font-size: 26px;
    }
    </style>
    """

    st.write(font_css, unsafe_allow_html=True)

    tabs = st.tabs(('Image Lane Detection', 'Video Lane Detection'))

    # UI Options  
    with tabs[0]:
        laneimage()
    with tabs[1]:
        lanevideo()

# Pre-process Image
def preProcessImg(img):
    # Pre-processing image: resize image
    height, width, _ = img.shape
    width = int(480/height*width)
    height = 480
    img = cv2.resize(img,(width,height))
    return img

# Upload Image
def uploadImage(key):
    uploaded_file = st.file_uploader("Choose a Image file",key=key)
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

        # Pre-processing image: resize image
        return preProcessImg(img)
    
    return cv2.cvtColor(preProcessImg(cv2.imread('sample.jpg')),cv2.COLOR_BGR2RGB)

def laneimage():   
# def averageFilter():
    st.header("Image Lane Detection")

    img = uploadImage(0)

    originalImg, filteredImg = st.columns(2)

    with originalImg:
        # Original Image
        st.subheader("Original Image")
        st.image(img,use_column_width=True)

    with filteredImg:    
        st.subheader("Lane Detected Image")
        fig = plt.figure(figsize=(20, 10))
        image = img
        st.image(lane_finding_pipeline(image))
        
def lanevideo():
    st.header("Video Lane Detection")
    st.title('Lane Detection')
    st.header('Upload a video and detect lane')

    st.header('Input Video')

    f = st.file_uploader("Upload file")
    if f is not None:
        file_details = {"FileName":f.name,"FileType":f.type}
        st.write(file_details)  
    with open(f.name,"wb") as ff: 
        ff.write(f.getbuffer())         
    st.success("Saved File")
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(f.read())

    vf = cv2.VideoCapture(tfile.name)

    stframe = st.empty()

    while vf.isOpened():
        ret, frame = vf.read()
        # if frame is read correctly ret is True
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        stframe.image(gray)
        
    st.header('Processing......')
    white_output = './output.mp4'
    clip1 = VideoFileClip(f.name)#("input.mp4")
    white_clip = clip1.fl_image(lane_finding_pipeline) #NOTE: this function expects color images!!
    white_clip.write_videofile(white_output, audio=False)

    video_file = open('output.mp4', 'rb')
    video_bytes = video_file.read()

    st.video(video_bytes)


def canny(img, low_threshold, high_threshold):
    """Applies the Canny transform"""
    return cv2.Canny(img, low_threshold, high_threshold)

def gaussian_blur(img, kernel_size):
    """Applies a Gaussian Noise kernel"""
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)

def region_of_interest(img, vertices):
    """
    Applies an image mask.
    
    Only keeps the region of the image defined by the polygon
    formed from `vertices`. The rest of the image is set to black.
    `vertices` should be a numpy array of integer points.
    """
    #defining a blank mask to start with
    mask = np.zeros_like(img)   
    
    #defining a 3 channel or 1 channel color to fill the mask with depending on the input image
    if len(img.shape) > 2:
        channel_count = img.shape[2]  # i.e. 3 or 4 depending on your image
        ignore_mask_color = (255,) * channel_count
    else:
        ignore_mask_color = 255
        
    #filling pixels inside the polygon defined by "vertices" with the fill color    
    cv2.fillPoly(mask, vertices, ignore_mask_color)
    
    #returning the image only where mask pixels are nonzero
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image


def draw_lines(img, lines, color=[255, 0, 0], thickness=10):
    for line in lines:
        for x1,y1,x2,y2 in line:
            cv2.line(img, (x1, y1), (x2, y2), color, thickness)

def slope_lines(image,lines):
    
    img = image.copy()
    poly_vertices = []
    order = [0,1,3,2]

    left_lines = [] # Like /
    right_lines = [] # Like \
    for line in lines:
        for x1,y1,x2,y2 in line:

            if x1 == x2:
                pass #Vertical Lines
            else:
                m = (y2 - y1) / (x2 - x1)
                c = y1 - m * x1

                if m < 0:
                    left_lines.append((m,c))
                elif m >= 0:
                    right_lines.append((m,c))

    left_line = np.mean(left_lines, axis=0)
    right_line = np.mean(right_lines, axis=0)

    #print(left_line, right_line)

    for slope, intercept in [left_line, right_line]:

        #getting complete height of image in y1
        rows, cols = image.shape[:2]
        y1= int(rows) #image.shape[0]

        #taking y2 upto 60% of actual height or 60% of y1
        y2= int(rows*0.6) #int(0.6*y1)

        #we know that equation of line is y=mx +c so we can write it x=(y-c)/m
        x1=int((y1-intercept)/slope)
        x2=int((y2-intercept)/slope)
        poly_vertices.append((x1, y1))
        poly_vertices.append((x2, y2))
        draw_lines(img, np.array([[[x1,y1,x2,y2]]]))
    
    poly_vertices = [poly_vertices[i] for i in order]
    cv2.fillPoly(img, pts = np.array([poly_vertices],'int32'), color = (0,255,0))
    return cv2.addWeighted(image,0.7,img,0.4,0.)
    
    #cv2.polylines(img,np.array([poly_vertices],'int32'), True, (0,0,255), 10)
    #print(poly_vertices)

def hough_lines(img, rho, theta, threshold, min_line_len, max_line_gap):
    """
    `img` should be the output of a Canny transform.
        
    Returns an image with hough lines drawn.
    """
    lines = cv2.HoughLinesP(img, rho, theta, threshold, np.array([]), minLineLength=min_line_len, maxLineGap=max_line_gap)
    line_img = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    #draw_lines(line_img, lines)
    line_img = slope_lines(line_img,lines)
    return line_img

# Python 3 has support for cool math symbols.

def weighted_img(img, initial_img, α=0.1, β=1., γ=0.):
    lines_edges = cv2.addWeighted(initial_img, α, img, β, γ)
    #lines_edges = cv2.polylines(lines_edges,get_vertices(img), True, (0,0,255), 10)
    return lines_edges
def get_vertices(image):
    rows, cols = image.shape[:2]
    bottom_left  = [cols*0.15, rows]
    top_left     = [cols*0.45, rows*0.6]
    bottom_right = [cols*0.95, rows]
    top_right    = [cols*0.55, rows*0.6] 
    
    ver = np.array([[bottom_left, top_left, top_right, bottom_right]], dtype=np.int32)
    return ver

# Lane finding Pipeline
def lane_finding_pipeline(image):
    
    #Grayscale
    gray_img = grayscale(image)
    #Gaussian Smoothing
    smoothed_img = gaussian_blur(img = gray_img, kernel_size = 5)
    #Canny Edge Detection
    canny_img = canny(img = smoothed_img, low_threshold = 180, high_threshold = 240)
    #Masked Image Within a Polygon
    masked_img = region_of_interest(img = canny_img, vertices = get_vertices(image))
    #Hough Transform Lines
    houghed_lines = hough_lines(img = masked_img, rho = 1, theta = np.pi/180, threshold = 20, min_line_len = 20, max_line_gap = 180)
    #Draw lines on edges
    output = weighted_img(img = houghed_lines, initial_img = image, α=0.8, β=1., γ=0.)
    
    return output

def grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Or use BGR2GRAY if you read an image with cv2.imread()
    # return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
if __name__ == "__main__":
    main()
