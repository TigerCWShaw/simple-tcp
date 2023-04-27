import socket, sys, os
import struct
import time

def rtt(sample_rtt):
    estimated_rtt = estimated_rtt * 0.875 + sample_rtt * 0.125
    dev_rtt = 0.75 * sample_rtt + 0.25 * abs(sample_rtt - estimated_rtt)
    time_out_interval = estimated_rtt + 4 * dev_rtt
    return time_out_interval

class Sender(object):
    def __init__(self, file_name, dest_addr, dest_port, win_size, ack_port):
        self.ack_num = 0
        self.seq_num = 0
        # self.fin = 0
        self.MAX_SEG_SIZ = 576
        self.BUF_SIZ = 1024
        self.file_name = file_name
        self.dest_addr = dest_addr
        self.dest_port = dest_port
        self.win_size = win_size
        self.ack_port = ack_port
        self.timeout = 0.5
        self.resend_dict = {}

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # self.udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        # initialize the listening socket
        self.ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ack_sock.bind(('127.0.0.1', self.ack_port))

        self.file_size = os.path.getsize(file_name)
        self.total_pack = self.file_size // self.MAX_SEG_SIZ
        if self.file_size % self.MAX_SEG_SIZ > 0:
            self.total_pack += 1

    def get_checksum(header, data):
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
        self.seq_num,       # Sequence Number
        self.ack_num,       # ack number
        0,                  # reserved data
        int(flags, 2),      # control flags
        self.win_size,      # window size
        checksum,           # Checksum (initial value)
        0                   # Urgent pointer
        )
        return header

    def get_packet(self, ack, syn, fin, data):
        header = self.get_header(ack, syn, fin, 0)
        checksum = self.get_checksum(header)
        header = self.get_header(ack, syn, fin, checksum)
        msg = header + data.encode()
        return msg


    def send_packet(self, msg):
        self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
        # seq_num: (timeout_time, msg)
        self.resend_dict[self.seq_num] = (time.time() + self.timeout, msg)
        self.seq_num += 1

    def send(self):
        fin = 0
        # initialize handshake
        msg = self.get_packet(0, 1, fin, '')
        self.send_packet(msg)

        # header = self.get_header(ack=0, syn=1, fin=fin, checksum=0)
        # checksum = self.get_checksum(header)
        # header = self.get_header(ack=0, syn=1, fin=fin, checksum=checksum)
        # self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
        # self.resend_dict[self.seq_num] = (time.time() + self.timeout, header)
        # self.seq_num += 1


        with open(self.file_name, 'r') as f:
        # while self.seq_num < self.total_pack:
            while True:
                data = f.read(self.MAX_SEG_SIZ)
                if not data:
                    break
                if self.seq_num == self.total_pack - 1:
                    fin = 1

                msg = self.get_packet(0, 0, fin, data)
                self.send_packet(msg)

                # header = self.get_header(ack=0, syn=0, fin=fin, checksum=0)
                # checksum = self.get_checksum(header + data.encode())
                # header = self.get_header(ack=0, syn=0, fin=fin, checksum=checksum)
                # msg = header + data.encode()
                # self.udp_sock.sendto(msg, (self.dest_addr, self.dest_port))
                # self.resend_dict[self.seq_num] = (time.time() + self.timeout, msg)

                self.seq_num += 1


    def recieve(self):
        while self.ack_num < self.total_pack:
            msg, addr = self.ack_sock.recvfrom(self.BUF_SIZ)
            header = msg[:20]
            data = msg[20:].decode()
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

            if syn == 1 and ack == 1:
                # send an ack msg and stablish connection
                msg = self.get_packet(1, 0, 0, '')
                self.send_packet(msg)
            elif ack == 1 and fin ==1:
                self.ack_num += 1
                msg = self.get_packet(1, 0, 0, '')
                self.send_packet(msg)
                # end connection
                break
            elif ack == 1:
                self.ack_num += 1
                # remove msg from resend_dict
                self.resend_dict.pop(seq)
            else:
                print('unknown msg recieved')

    def resend(self):
        pass



def main():
    if len(sys.argv) != 6:
        print('Usage: python client.py <file_name> <udp_addr> <udp_port> <windowsize> <ack_port>')
    file_name = sys.argv[1]
    dest_addr = sys.argv[2]
    dest_port = int(sys.argv[3])
    win_size = int(sys.argv[4])
    ack_port = int(sys.argv[5])


