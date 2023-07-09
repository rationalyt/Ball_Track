import argparse
import asyncio
import logging, socket

import cv2
from aiortc import (
    RTCIceCandidate,
    RTCPeerConnection,
    RTCSessionDescription,
)

from aiortc.contrib.signaling import BYE, TcpSocketSignaling
from aiortc.contrib.media import MediaRecorder
from server import BallStreamTrack
import numpy as np
import os
import threading


def process_image(image):
    """
    Evaluates the coordinates of the ball from the obtained image
    and sends it back to the server
    """

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply a Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Perform edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Perform Hough Circle Transform
    circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, dp=1,
                            minDist=100, param1=50, param2=30, minRadius=0, maxRadius=0)

    # Check if any circles were found
    if circles is not None:
        # Convert the coordinates and radius to integers
        circles = np.round(circles[0, :]).astype("int")

        # Loop over the detected circles
        for (x, y, r) in circles:
            # Draw the circle on the image
            cv2.circle(image, (x, y), r, (0, 255, 0), 2)
            # Draw a small circle at the center
            cv2.circle(image, (x, y), 2, (0, 0, 255), 3)

            """ Display the coordinates of the center
            print("Center coordinates: ({}, {})".format(x, y))"""
            
            # Create a client socket
            clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Connect to the server
            clientSocket.connect(("127.0.0.1", 9090))

            # Send data to server
            data = f"{x},{y}"
            clientSocket.send(data.encode())


def detect_entry():
    """
    Detects entry of new image from server in the folder and evaluates the coordinates
    """
    def check_entry():
        i = 1
        while True:
            filename = f"ball-{i}.png"
            if os.path.isfile(f"./images/{filename}"):
                img = cv2.imread(f"./images/{filename}")
                
                # Initiate a thread to process the new file
                t = threading.Thread(target=process_image, args=(img,))
                t.start()
                i += 1
                t.join()

    t = threading.Thread(target=check_entry)
    t.daemon = True
    t.start()

async def run(pc, recorder, signaling):
    def add_tracks():
        pc.addTrack(BallStreamTrack())

    @pc.on("track")
    def on_track(track):
        print("Receiving %s" % track.kind)
        recorder.addTrack(track)

    # connect signaling
    await signaling.connect()

    # consume signaling
    while True:
        obj = await signaling.receive()

        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
            await recorder.start()

            if obj.type == "offer":
                # send answer
                add_tracks()
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break


if __name__ == "__main__":

    # create signaling and peer connection
    signaling = TcpSocketSignaling('127.0.0.1', 8000)
    pc = RTCPeerConnection()

    detect_entry()

    # create media sink
    recorder = MediaRecorder("./images/ball-%1d.png")

    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            run(
                pc=pc,
                recorder=recorder,
                signaling=signaling,
            )
        )
    except KeyboardInterrupt:
        pass
    finally:
        # cleanup
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(pc.close())
