import asyncio
import socket, threading
import random
from collections import deque

import cv2
from aiortc import (
    RTCIceCandidate,
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
)

from aiortc.contrib.signaling import BYE, TcpSocketSignaling
from av import VideoFrame
import numpy as np

queue = deque([])

class BallStreamTrack(VideoStreamTrack):
    """
    A track that returns frames which consists of a ball.
    """

    def __init__(self):
        super().__init__()
        self.frames = []
        self.counter = 0
        for k in range(100):
            # Create a black image with dimensions 400x400
            image = np.zeros((400, 400, 3), dtype=np.uint8)

            # Define the ball's properties
            x = random.randint(1,400)
            y = random.randint(1,400)
            ball_center = (x, y)  # Center coordinates of the ball
            ball_radius = 20  # Radius of the ball
            ball_color = (0, 0, 255)  # Color of the ball (BGR format)
            queue.append((x,y))

            # Draw the ball on the image
            image = cv2.circle(image, ball_center, ball_radius, ball_color, -1)
            self.frames.append(VideoFrame.from_ndarray(image,format="bgr24"))

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        if self.counter <= 100:
            frame = self.frames[self.counter % 100]
            frame.pts = pts
            frame.time_base = time_base
        self.counter += 1
        return frame
    
def get_coord():
    """
    Receives coordinates of ball from client and evaluates error
    """
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind and listen
    serverSocket.bind(("127.0.0.1", 9090))
    serverSocket.listen()

    # Accept connections
    while(True):
        (clientConnected, clientAddress) = serverSocket.accept()

        dataFromClient = clientConnected.recv(1024)
        coord_arr = dataFromClient.decode().split(",")
        x = int(coord_arr[0])
        y = int(coord_arr[1])
        if queue:
            real_x,real_y = queue.popleft()
            error = abs((real_x-x) + (real_y-y))
            print(f"Coordinates error : {error}")

async def run(pc, signaling):
    def add_tracks():
        pc.addTrack(BallStreamTrack())

    @pc.on("track")
    def on_track(track):
        print("Receiving %s" % track.kind)

    # connect signaling
    await signaling.connect()

    # send offer
    add_tracks()
    await pc.setLocalDescription(await pc.createOffer())
    await signaling.send(pc.localDescription)

    # consume signaling
    while True:
        obj = await signaling.receive()

        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

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

    # thread for obtaining co-ordinates from client

    t = threading.Thread(target=get_coord)
    t.daemon = True
    t.start()


    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            run(
                pc=pc,
                signaling=signaling,
            )
        )
    except KeyboardInterrupt:
        pass
    finally:
        # cleanup
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(pc.close())
