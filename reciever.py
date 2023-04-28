import socket, sys, os
import struct

class Reciever(object):
    def __init__(self, file_name, udp_port, ack_addr, ack_port):
        self.file_name = file_name
        self.udp_port = udp_port
        self.ack_addr = ack_addr
        self.ack_port = ack_port
        self.BUF_SIZ = 1024

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(('127.0.0.1', udp_port))

    def check_checksum(self, msg):
        pass

    def recieve(self):
        while True:
            msg, addr = self.udp_sock.recvfrom(self.BUF_SIZ)

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
            if syn == 1:
                msg = self.get_packet(1, 0, 0, '')
                # set syn, ack flags
                new_flags = int('010010', 2)
                k = list(header_val)
                k[5] = new_flags
                struct.pack('!HHIIBBHHH', *tuple(k))
                self.udp_sock.sendto(msg, (self.ack_addr, self.ack_port))
            if fin == 1:
                msg = self.get_packet(1, 0, 0, '')
                # set syn, ack flags
                new_flags = int('010010', 2)
                k = list(header_val)
                k[5] = new_flags
                struct.pack('!HHIIBBHHH', *tuple(k))
                self.udp_sock.sendto(msg, (self.ack_addr, self.ack_port))



def main():
    if len(sys.argv) != 4:
        print('Usage: python reciever.py <file_name> <udp_port> <ack_addr> <ack_port>')
        sys.exit()
    file_name = sys.argv[1]
    udp_port = int(sys.argv[2])
    ack_addr = sys.argv[3]
    ack_port = sys.argv[4]


if __name__ == "__main__":
    main()