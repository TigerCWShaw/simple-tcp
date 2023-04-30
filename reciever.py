import socket, sys, os
import struct

class Reciever(object):
    def __init__(self, file_name, udp_port, ack_addr, ack_port):
        self.file_name = file_name
        self.udp_port = udp_port
        self.ack_addr = ack_addr
        self.ack_port = ack_port
        self.BUF_SIZ = 1024
        self.fin = False

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(('127.0.0.1', udp_port))
        self.file_map = {}
        print('Listening at port ', self.udp_port)
        self.recieve()

    def check_checksum(self, msg):
        header = msg[:20]
        data = msg[20:]
        header_val = struct.unpack('!HHIIBBHHH', header)
        checksum = header_val[7]
        k = list(header_val)
        k[7] = 0

        tmp_header = struct.pack('!HHIIBBHHH', *tuple(k))
        tmp_msg = tmp_header + data
        cs = 0
        for i in range(0, len(tmp_msg), 2):
            # network is encoded in big endian
            cs = cs ^ int.from_bytes(tmp_msg[i:i+2], 'big')

        return cs == checksum

    def save_file(self):
        with open(self.file_name, 'w') as f:
            for i in self.file_map:
            # dictionary key is sorted by default in python 3.7
                f.write(self.file_map[i])
        print('< ' + self.file_name + ' recieved successfully! >')

    def set_flags(self, header, ack, syn, fin):
        new_flags = int('0' + str(ack) + '00' + str(syn) + str(fin), 2)
        k = list(header)
        k[5] = new_flags
        msg = struct.pack('!HHIIBBHHH', *tuple(k))
        return msg

    def recieve(self):
        while True:
            msg, addr = self.udp_sock.recvfrom(self.BUF_SIZ)
            if not self.check_checksum(msg):
                print('Recieved packet has invalid checksum')
                continue
            header = msg[:20]
            data = msg[20:].decode()
            header_val = struct.unpack('!HHIIBBHHH', header)
            # print(header_val)
            flags = header_val[5]
            flags = "{0:b}".format(flags)
            if len(flags) < 6:
                # pad the zeroes
                flags = '0'*(6-len(flags)) + flags
            seq = header_val[2]
            ack = flags[1]
            syn = flags[4]
            fin = flags[5]
            print('Recieved packet_%d: ack: %c syn: %c fin: %c'%(seq, ack, syn, fin))
            if syn == '1':
                msg = self.set_flags(header_val, '1', syn, fin)
                self.udp_sock.sendto(msg, (self.ack_addr, self.ack_port))
            elif fin == '1':
                # set fin, ack flags
                self.fin = True
                msg = self.set_flags(header_val, '1', syn, fin)
                self.udp_sock.sendto(msg, (self.ack_addr, self.ack_port))
                self.save_file()
            elif ack == '1':
                if not fin:
                    print('TCP connection established with ' + str(addr))
            else:
                # ignore retransmitted messages
                if seq not in self.file_map:
                    self.file_map[seq] = data
                msg = self.set_flags(header_val, '1', syn, fin)
                self.udp_sock.sendto(msg, (self.ack_addr, self.ack_port))







def main():
    if len(sys.argv) != 5:
        print('Usage: python reciever.py <file_name> <udp_port> <ack_addr> <ack_port>')
        sys.exit()
    file_name = sys.argv[1]
    udp_port = int(sys.argv[2])
    ack_addr = sys.argv[3]
    ack_port = int(sys.argv[4])
    r = Reciever(file_name, udp_port, ack_addr, ack_port)


if __name__ == "__main__":
    main()