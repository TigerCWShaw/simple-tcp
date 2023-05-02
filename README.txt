Name: Chun-Wei Shaw
Uni: cs4213

The program was tested on Python 3.10.10 ubuntu 18.04
No additional packeges used

Commands to run the program:
    Run proxy server:
        ./newudpl -p 2222:3333 -i127.0.0.1:4070 -o127.0.0.1:4010 -vv -L 50

    Run Reciever:
        python reciever.py file2.txt 4010 127.0.0.1 4000

    Run Sender:
        python sender.py file1.txt 127.0.0.1 2222 1024 4000

Structure of the program:
    Sender:
    I implemented sender using multithreading with a thread in each of the functionality:
        1. Sending the packets
        2. Recieving ACK
        3. Retransmitting timeout packets

    Reciever:
    Reciever is a simple code that recieve the packets and send ack messages

1. Three-way handshake implementation
    Sender will first send a packet with syn flag = 1 to the reciever  and wait for the reciever's response. (sender.py line 123)

    Reciever will respond by sending a syn-ack message to the sender. (reciever.py line 87)

    Sender will send an ack message after recieving the syn-ack message, establishing the TCP connection. (sender.py line 173)

2. Data transmission and reception
    After establshing connection with the reciever, sender will send the file in multiple packets each <= maximum segment size. (sender.py line 133) I set the max segment size to 16 byte for more convenient testing.

    Each time we send a message we will add this message to a dictionary along with the current time, its sequence number and a flag to indicates if the message have been retransmitted to make sure timeout is calculated correctly. (sender.py line 113)

    I used the selective repeat method in the slides to implement my retransmission. The resend thread will periodically check the dictionary to see if there is a timeout in any of the messages and will resend any timeout message as well as update its current time. (sender.py line 213)

3. Fin request
    After sender recieved an ack message for all the packets(ack_num is used to keep track of the number of acks), sender will send a packet with fin flag = 1 to the reciever and wait for the reciever's response. (sender.py line 189)

    Reciever will respond by sending a fin-ack message to the sender. (reciever.py line 90)

    Sender will send an ack message after recieving the fin-ack message, closing the TCP connection. (sender.py line 179)

4. Error logging
    Sender will log the error messages to log1.txt and reciever will log the error messages to log2.txt

Sender:
    Sender will log duplicate ack messages. (see log1.txt line 57 adn sender.py line 162)

    I produced the error message by setting the initial timeout value to 0. (sender.py line 37)

    Sender will log retransmission messages. (sender.py line 215)

Reciever:
    Reciever will check the checksum of the packet and will ignore the packet if it is incorrect. (see log2.txt and reciever.py line 69)

    I produced the error message by setting the checksum value to 0. (sender.py line 109)

5. TCP header
I used struct.pack() to implement my tcp header. The format I implemented my header: (sender.py line 90)
-------------------------------------
source port
destination port
sequence number
acknowledgement number
reserver flags(set to 0)
flags (urg, ack, psh, rst, syn, fin)
window size
checksum
urgent pointer(set to 0)
-------------------------------------
Sender will first produce an initial header with checksum=0, after calculating the checksum for this header+data, sender will update the header. (sender.py line 104)

6. Sequence number
    Initially set to 0, the first time we send a packet, we set its sequence number to the current sequence number and incrementing the sequence number by 1. (sender.py 121)

7. Retransmission timer
    Each time we recieve an ack from a packet that has not been retransmitted, we will obtain a new sample_rtt(sender.py line 171) and calculate a new timeout interval using the equations from the slides(sender.py line 72).

8. Calculating checksum
    The Check sum is calculated by chunking (header + data to 16-bit chunks) (sender.py line 77)
    With an initial check_sum value of 0, we perform consecutive bitwise xor with each chunk(2 bytes = 16 bits) and adding the final check sum value to the header.

    Similarly, when the reciever recieves a packet, it will first calculate the checksum with the checksum value in the header as 0, then comparing its value with the one in the header. (reciever.py line 35)

9. Handling command line arguments
    The program will:
        1. Check if the number of arguments is correct.
        2. Check if ip address is valid with ipaddress.ip_address()
        3. Check if 1024 < port < 65535

10. Tradeoffs and design
    To implement retransmission in my tcp connection, I used a dictionary to store my messages. However I did not implement a way to remove the messages, I simply ignore the dictionary entry if that packet has been acknoledged. The reason I did this was because I will need to consider locking machanism for multiple threads to write and delete entries in the dictionary, this will over complicate the program thus I opt not to implement this.
    I decided to implemented sender.py asynchronously because I wanted to observe packet loss easily, by examining the recieved packets and their sequence number, I can easily observe the packets that were discarded by the proxy server.

------------------------------------------------------

Screen dump

Reciever:
$ python reciever.py file2.txt 4010 127.0.0.1 4000
Listening at port  4010
Recieved packet_0: ack: 0 syn: 1 fin: 0
Recieved packet_1: ack: 0 syn: 0 fin: 0
Recieved packet_2: ack: 0 syn: 0 fin: 0
Recieved packet_3: ack: 0 syn: 0 fin: 0
Recieved packet_4: ack: 0 syn: 0 fin: 0
Recieved packet_5: ack: 0 syn: 0 fin: 0
Recieved packet_8: ack: 0 syn: 0 fin: 0
Recieved packet_9: ack: 0 syn: 0 fin: 0
Recieved packet_11: ack: 0 syn: 0 fin: 0
Recieved packet_12: ack: 0 syn: 0 fin: 0
Recieved packet_15: ack: 0 syn: 0 fin: 0
Recieved packet_13: ack: 0 syn: 0 fin: 0
Recieved packet_10: ack: 0 syn: 0 fin: 0
Recieved packet_14: ack: 0 syn: 0 fin: 0
Recieved packet_6: ack: 0 syn: 0 fin: 0
Recieved packet_7: ack: 0 syn: 0 fin: 0
Recieved packet_16: ack: 0 syn: 0 fin: 1
< file2.txt recieved successfully! >

Sender:
$ python sender.py file1.txt 127.0.0.1 2222 1024 4000
Listening at port  4000
Recieved ACK_0: ack: 1 syn: 1 fin: 0
TCP connection established with ('127.0.0.1', 4010)
Recieved ACK_1: ack: 1 syn: 0 fin: 0
Recieved ACK_2: ack: 1 syn: 0 fin: 0
Recieved ACK_3: ack: 1 syn: 0 fin: 0
Recieved ACK_4: ack: 1 syn: 0 fin: 0
Recieved ACK_5: ack: 1 syn: 0 fin: 0
Recieved ACK_8: ack: 1 syn: 0 fin: 0
Recieved ACK_9: ack: 1 syn: 0 fin: 0
Recieved ACK_11: ack: 1 syn: 0 fin: 0
Recieved ACK_12: ack: 1 syn: 0 fin: 0
Recieved ACK_15: ack: 1 syn: 0 fin: 0
Recieved ACK_13: ack: 1 syn: 0 fin: 0
Recieved ACK_10: ack: 1 syn: 0 fin: 0
Recieved ACK_14: ack: 1 syn: 0 fin: 0
Recieved ACK_6: ack: 1 syn: 0 fin: 0
Recieved ACK_7: ack: 1 syn: 0 fin: 0
Recieved ACK_16: ack: 1 syn: 0 fin: 1
Reciever has recieved the file
Ending the connection...




