"""
The client module contains... well... the Client class that is used
to handle the protocol itself such as packet receiving and sending.

It can be used independently from :class:`pyclassic.PyClassic` if
you want to. However you won't have the event system obviously.

This class allows the connection and packet handling as well as some
additional methods to make programming easier.
"""
import pyclassic, socket
from pyclassic.utils import *
from pyclassic.auth import SimpleAuth

class Client:
    """
    Client class

    :param auth: Authentication class to connect the client to a server.
    :param client_name: Client name, can be changed as you wish but
                        defaults to `"pyclassic <VERSION>"`. Can be
                        useful sometimes :troll:

    :type auth: pyclassic.auth.SimpleAuth
    :type client_name: str or None, optional
    """
    def __init__(self, auth: SimpleAuth, client_name = None):
        self.auth = auth
        self.socket = None
        if not client_name:
            self.client_name = f"pyclassic {pyclassic.PYCLASSIC_VERSION}"
        else:
            self.client_name = client_name

    def recv(self):
        """
        Receives a packet and decodes it appropriately.

        :raise pyclassic.utils.PyClassicError: no more data is received.
        :return: packet information and the decoded packet
                 (without the packet ID as there is packet info)
        :rtype:  (:class:`pyclassic.utils.PacketFormat`, list)
        """
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
        """
        Sends a packet to the server.

        :param pid: Packet ID
        :param args: arguments

        :type pid: int

        :raise pyclassic.utils.PyClassicError: Invalid packet.
        """
        packet = encode_packet(packet_id_c[pid], *args)
        if not packet:
            raise PyClassicError("Invalid send packet.")
        self.socket.sendall(bytes([pid]) + packet)
 
    def connect(self, **kargs):
        """
        Connects to a server. Will use the specified
        :class:`pyclassic.auth.SimpleAuth`-based class to retrieve the
        IP, port, username and server salt.
        See :func:`pyclassic.auth.SimpleAuth.connect`

        If a socket is already active, it will disconnect it first then
        reconnect.

        :param kargs: Arguments to pass to the auth object to retrieve
                      the server and the credentials to connect.
        :raise pyclassic.utils.PyClassicError: Failed to connect.
        :raise pyclassic.utils.PyClassicError: Kicked from server on
                                               connect.

        :return: Server information or None
        :rtype:  (str, str) or None
        """
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
        """
        Disconnects the client if it's connected to a server,
        otherwise does a great amount of nothing.
        """
        if self.socket:
            self.socket.close()
            self.socket = None

    def message(self, message):
        """
        Sends a message to the server.

        :param message: Message to send
        :type message:  str
        """
        self.send(0xd, 0xff, message)

    def move(self, x, y, z, pitch = 0, yaw = 0):
        """
        Teleports the player at the specified position and direction.
        This functions relies on block position.
        See :func:`pyclassic.client.Client.move_precise` for more
        precise teleportation.

        .. note::
            Pitch and yaw angles are between 0 and 255 and not 0 and
            359 since these fits in a byte.

        :type x: int
        :type y: int
        :type z: int
        :type pitch: int, optional
        :type yaw:   int, optional
        """
        x *= 32
        y *= 32
        z *= 32
        self.move_precise(x, y, z, pitch, yaw)

    def move_precise(self, x, y, z, pitch = 0, yaw = 0):
        """
        Teleports the player at the specified position and direction.

        .. note::
            Pitch and yaw angles are between 0 and 255 and not 0 and
            359 since these fits in a byte.

        :type x: int
        :type y: int
        :type z: int
        :type pitch: int, optional
        :type yaw:   int, optional
        """
        self.send(0x8, -1, x, y, z, pitch, yaw)
        

    def set_block(self, x, y, z, block_id):
        """
        Make the client place a block at a specified position.

        .. note::
            Abuse this and you'll get kicked lmao.

        :type x: int
        :type y: int
        :type z: int
        :type block_int: int
        """
        self.move(x-1, y, z)
        self.send(5, x, y, z, 1, block_id)
        """
        if self.map:
            self.map[x, y, z] = block_id
        """
