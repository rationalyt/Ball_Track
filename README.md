The idea of the project is to generate frames which consists of a ball in a screen and send it to the client which then computes the ball coordinates and sends it back to the server for calculating error.

To achieve this we have 2 files server.py and client.py

Server:

The server.py generates frames of a ball at different (x,y) coordinates.
These coordinates are stored into a queue for future computations.
Each frame is of size (400,400). It uses TcpSocketSignaling and connects to
the specified port. It then instantiates a RTCPeerConnection with the client and adds the required MediaTracks to the channel to communicate with the client. The get_coord() function is run on a daemon thread to continuously listen to the client so that it can receive the coordinates of the ball computed by the client. After receiving the coordinates, it computes the error by popping out the actual values from the queue and displays it on the command line.

Client:

The client.py receives frames sent by the server and saves it to the images folder which is initially empty. The images are stored with the format ball_1.png, ball_2.png,...
Whenever a image entry in the foler is observed, the detect_entry() function initiates a thread to compute the coordinates of the ball and send it back to the server. To view the received images in order see the 'images' folder.

Commands to run in order:

python3 server.py
python3 client.py

