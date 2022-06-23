# Client class
import pyclassic, socket
from pyclassic.utils import *
from pyclassic.auth import SimpleAuth

class Client:
    def __init__(self, auth: SimpleAuth, client_name = None):
        self.auth = auth
        self.socket = None
        if not client_name:
            self.client_name = f"pyclassic {pyclassic.PYCLASSIC_VERSION}"
        else:
            self.client_name = client_name

    def recv(self):
        s = self.socket
        data = s.recv(1)
        if not data:
            self.disconnect()
            raise PyClassicError("no more data, disconnected.")
        elif len(data) != 1: return
        packet_id = data[0]
        packet_info = packet_id_s.get(packet_id)
        if not packet_info:
            raise PyClassicError("Invalid packet.")
        psize = len(packet_info)
        if psize == 0: return packet_info, []
        data = b''
        while len(data) < len(packet_info):
            data += s.recv(len(packet_info) - len(data))

        return packet_info, decode_packet(packet_info, data)

    def send(self, pid, *args):
        packet = encode_packet(packet_id_c[pid], *args)
        if not packet:
            raise PyClassicError("Invalid send packet.")
        self.socket.sendall(bytes([pid]) + packet)

    def connect(self, **kargs):
        if self.socket:
            # raise PyClassicError("The socket is not null, plase disconnect.")
            self.disconnect()
            self.socket = None

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip, port, username, mppass = self.auth.connect(**kargs)
        
        self.socket = s
        s.connect((ip, port))
        s.sendall(b'\x00' + encode_packet(packet_id_c[0x0], 7,
                                          username, mppass, 0x42)) ##TODO: make 0x42 configurable (cpe on or off)

        pid, auth_or_cpe = self.recv()

        if not auth_or_cpe:
            self.disconnect()
            raise PyClassicError("Failed to connect to server.")
        elif pid.name == "DISCONNECT":
                self.disconnect()
                error = auth_or_cpe[1] if len(auth_or_cpe) == 2 else ""
                raise PyClassicError(f"Kicked! {error}")

        if pid.name == "EXT_INFO":
            # Maybe turn the socket into a "server" class or smth?
            #    we could store server information in there also.
            # TODO: Maybe make this cleaner?
            self.send(0x10, self.client_name, 2)
            # Why are we not checking for cross compataiblity here? 
            self.send(0x11, "BlockDefinitions", 1)
            # Cross compataiblity will not change anything, as the
            # underlying map code can use any ID
            self.send(0x11, "CustomBlocks", 1) 
        else:
            return auth_or_cpe[1], auth_or_cpe[2]

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def message(self, message):
        self.send(0xd, 0xff, message)

    def move(self, x, y, z, pitch = 0, yaw = 0):
        x *= 32
        y *= 32
        z *= 32
        self.move_precise(x, y, z, pitch, yaw)

    def move_precise(self, x, y, z, pitch = 0, yaw = 0):
        self.send(0x8, -1, x, y, z, pitch, yaw)
        

    def set_block(self, x, y, z, block_id):
        self.move(x-1, y, z)
        self.send(5, x, y, z, 1, block_id)
        if self.map:
            self.map[x, y, z] = block_id
