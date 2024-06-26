import socket, sys, os
import struct
import time
import threading
import ipaddress
import logging

def is_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        print('Invalid IP address')
        return False

def is_port(port):
    if port < 1024  or port > 65535:
        print('Invalid port number')
        return False
    return True

class Sender(object):
    def __init__(self, file_name, dest_addr, dest_port, win_size, ack_port):
        self.ack_num = 0
        self.seq_num = 0
        # self.MAX_SEG_SIZ = 576
        self.MAX_SEG_SIZ = 16

        self.BUF_SIZ = 1024
        self.file_name = file_name
        self.dest_addr = dest_addr
        self.dest_port = dest_port
        self.win_size = win_size
        self.ack_port = ack_port
        self.estimated_rtt = 0.1
        self.sample_rtt = 0.1
        # self.timeout = 0
        self.timeout = 0.5

        self.resend_dict = {}
        self.add_list = []

        self.end = False
        self.recieve_map = {}

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.udp_sock.bind(('127.0.0.1', 4070))

        # initialize the listening socket
        self.ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ack_sock.bind(('127.0.0.1', self.ack_port))
        print('Listening at port ', self.ack_port)

        self.file_size = os.path.getsize(file_name)
        # total packet include syn-ack
        self.total_pack = self.file_size // self.MAX_SEG_SIZ + 2
        if self.file_size % self.MAX_SEG_SIZ > 0:
            self.total_pack += 1
        for i in range(self.total_pack + 1):
            self.recieve_map[i] = False


        send_thread = threading.Thread(target=self.send, args=())
        recv_thread = threading.Thread(target=self.recieve, args=())
        resend_thread = threading.Thread(target=self.resend, args=())

        recv_thread.start()
        send_thread.start()
        resend_thread.start()

    def get_timeout_interval(self):
        self.estimated_rtt = self.estimated_rtt * 0.875 + self.sample_rtt * 0.125
        dev_rtt = 0.75 * self.sample_rtt + 0.25 * abs(self.sample_rtt - self.estimated_rtt)
        self.timeout = self.estimated_rtt + 4 * dev_rtt
        # print('timeout:', self.timeout)

    def get_checksum(self, header, data):
        checksum = 0
        # chunk the header + data in 16-bit chunks
        msg = header + data
        for i in range(0, len(msg), 2):
            # network is encoded in big endian
            checksum = checksum ^ int.from_bytes(msg[i:i+2], 'big')
        return checksum

    def get_header(self, ack, syn, fin, checksum)-> bytes:
        # urg, ack, psh, rst, syn, fin
        flags = '0' + str(ack) + '00' + str(syn) + str(fin)

        header = struct.pack(
        '!HHIIBBHHH',
        self.ack_port,      # source port
        self.dest_port,     # destination port
        self.seq_num,       # sequence Number
        self.ack_num,       # acknowledgement number
        0,                  # reserved data
        int(flags, 2),      # control flags
        self.win_size,      # window size
        checksum,           # Checksum (initial value)
        0                   # Urgent pointer
        )
        return header

    def get_packet(self, ack, syn, fin, data):
        data = data.encode()
        header = self.get_header(ack, syn, fin, 0)
        checksum = self.get_checksum(header, data)
        header = self.get_header(ack, syn, fin, checksum)
        # header = self.get_header(ack, syn, fin, 0)

        msg = header + data
        # print(msg)
        return msg


    def send_packet(self, msg):
        self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
        # seq_num: (timeout_time, msg, have_resend)
        # have_resend is to make sure sampleRTT calculated correctly
        self.add_list.append((self.seq_num, (time.perf_counter(), msg, False)))
        self.seq_num += 1

    def send(self):
        # initialize handshake
        msg = self.get_packet(0, 1, 0, '')
        self.send_packet(msg)

        while True:
            # waiting for reciever's response
            if self.ack_num:
                break

        with open(self.file_name, 'r') as f:
        # while self.seq_num < self.total_pack:
            while True:
                # time.sleep(0.2)
                data = f.read(self.MAX_SEG_SIZ)
                if not data:
                    break

                msg = self.get_packet(0, 0, 0, data)
                self.send_packet(msg)



    def recieve(self):
        while True:
            msg, addr = self.ack_sock.recvfrom(self.BUF_SIZ)
            header = msg[:20]
            header_val = struct.unpack('!HHIIBBHHH', header)
            flags = header_val[5]
            flags = "{0:b}".format(flags)
            if len(flags) < 6:
                # pad the zeroes
                flags = '0'*(6-len(flags)) + flags
            seq = header_val[2]
            ack = flags[1]
            syn = flags[4]
            fin = flags[5]

            if self.recieve_map[seq]:
                logging.error('Recieved duplicated ack for packet_%d'%(seq))
                continue
            print('Recieved ACK_%d: ack: %c syn: %c fin: %c'%(seq, ack, syn, fin))

            self.recieve_map[seq] = True
            if seq in self.resend_dict:
                value = self.resend_dict[seq]
                if value[2] == False:
                    # update time_out interval
                    self.sample_rtt = time.perf_counter() - value[0]
                    self.get_timeout_interval()

            if syn == '1' and ack == '1':
                # send an ack msg and stablish connection
                self.ack_num += 1
                msg = self.get_packet(1, 0, 0, '')
                self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
                print('TCP connection established with ' + str(addr))
            elif ack == '1' and fin == '1':
                msg = self.get_packet(1, 0, 0, '')
                self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
                print('Reciever has recieved the file')
                print('Ending the connection...')
                self.end = True
                # end connection
                break
            elif ack == '1':
                self.ack_num += 1
                if self.ack_num == (self.total_pack - 1):
                    msg = self.get_packet(0, 0, 1, '')
                    self.send_packet(msg)
                    # self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
            else:
                print('unknown msg recieved')

    def resend(self):
        while True:
            # time.sleep(self.timeout)
            if self.end:
                break
            while len(self.add_list) != 0:
                v = self.add_list.pop()
                self.resend_dict[v[0]] = v[1]
                # print('test')
            tmp_dict = {}
            for k, v in self.recieve_map.items():
                if k in self.resend_dict and not v:
                    tmp_dict[k] = self.resend_dict[k]
            for seq_num, value in tmp_dict.items():
                # timeout -> retransmission
                curr = time.perf_counter()
                if curr >= value[0] + self.timeout:
                    # print('Resending packet_%d...'%(seq_num))
                    logging.error('Timeout for packet_%d'%(seq_num))
                    logging.error('Retransmitting packet_%d'%(seq_num))

                    self.udp_sock.sendto(value[1], (self.dest_addr, self.dest_port))
                    k = list(value)
                    k[0] = curr
                    k[2] = True
                    self.resend_dict[seq_num] = tuple(k)




def main():
    if len(sys.argv) != 6:
        print('Usage: python sender.py <file_name> <udp_addr> <udp_port> <window_size> <ack_port>')
        sys.exit()

    file_name = sys.argv[1]
    dest_addr = sys.argv[2]

    logging.basicConfig(filename='log1.txt',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

    try:
        dest_port = int(sys.argv[3])
    except ValueError:
        print('Invalid <udp_port>')
        sys.exit()
    try:
        win_size = int(sys.argv[4])
    except ValueError:
        print('Invalid <window_size>')
        sys.exit()
    try:
        ack_port = int(sys.argv[5])
    except ValueError:
        print('Invalid <ack_port>')
        sys.exit()
    if is_ip(dest_addr) and is_port(dest_port) and is_port(ack_port):
        s = Sender(file_name, dest_addr, dest_port, win_size, ack_port)
    else:
        print('Invalid parameters')
        sys.exit()

if __name__ == "__main__":
    main()


