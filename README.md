# RING-LWE_Cryptography
Secure Text, Voice and File Implementation using Ring-LWE with Python.


# Instructions To Implement
•	Install the numpy and pyaudio libraries in a command prompt using the following commands:
o	pip install numpy
o	pip install pyaudio
•	Download the server, client, ringlwe, and chacha20 python files into a common directory.
•	Run the server file first. Upon successful running, it should print the Server IP and Port.
•	Run client files as many as clients are required. Each client will require an IP and name.
o	If the client is run on the same machine as the server, input “localhost” for the IP field.
o	If the client is run on a different machine than the server, enter the IP printed on the server.
•	Upon connection, the client will print a welcome message along with help commands while the server will print an alert that the client has joined.
•	We can then:
o	Enter “/list” to print the available users.
o	Enter “/contact <user>” to initiate the connection between two users.
o	Enter “/accept <user>” to accept the connection. However you may choose to decline the connection as well by entering “/decline <user>”.
o	Enter “/leave” to exit the connection.

For voice messages:
o	Enter “/voice record” to record the message.
o	Enter “/voice stop” to stop recording the message.
o	Enter “/voice send” to send the recorded message.
o	On the receivers end, this message will be reassembled upon receiving. Simply enter “/voice play” to play the last received voice recording.

For files:
o	Enter “/file input” to input a file. A tkinter dialogue will be opened for the input.
o	Enter “file send” to send the inputted file.
o	On the receivers end, simply enter “/file download” to download the assembled bytes.
