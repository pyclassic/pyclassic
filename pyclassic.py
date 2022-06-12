#!/usr/bin/env python3
# PyClassic - Minecraft Classic client
import socket, json, requests, time, asyncio, re
from dataclasses import dataclass

######################################################################
class PyClassicError(Exception): pass

_packet_fmt_types = {
    "BYTE": 1, "SBYTE": 1, "SHORT": 2, "STRING": 64, "ARRAY": 1024
}

_cc_api = "http://www.classicube.net/api"
######################################################################

enc = lambda n: n.encode('us-ascii')
encstr = lambda n: enc(n) + bytes([0x20 for x in range(64-len(enc(n)))])
decstr = lambda n: n[:64].decode('us-ascii').strip()
decint = lambda n, s = True: int.from_bytes(n, byteorder='big',
                                     signed=s)
encint = lambda n, l = 2: n.to_bytes(l, 'big')
api_url = lambda n: _cc_api + n
def sanitize(msg):
    return re.sub('\&.', '', msg)
def contains_all(needle, haystack):
    for el in needle:
        if el not in haystack:
            return False
        elif needle[el] != haystack[el]:
            return False
    return True

# BYTE, SBYTE, SHORT, ARRAY, STRING
@dataclass
class PacketFormat:
    pid: int
    name: str
    content: list[str]

    def __len__(self):
        return sum(_packet_fmt_types[x] for x in self.content)
    def __bool__(self):
        return True

def find_packet_id(t):
    for c, i in enumerate(packet_id_s):
        if t == packet_id_s[i].name:
            return packet_id_s[i].pid
    return -1
def encode_packet(fmt, *args):
    if len(args) != len(fmt.content): return

    packet = b''
    for f, a in zip(fmt.content, args):
        if   f == "BYTE":   packet += bytes([a & 0xff])
        elif f == "SBYTE":  packet += encint(a, 1)
        elif f == "SHORT":  packet += encint(a&0xffff, 2)
        elif f == "STRING": packet += encstr(a[:64])
        elif f == "ARRAY":  packet += a[:1024]
    return packet
def decode_packet(fmt, packet: bytes):
    if len(fmt) != len(packet): return

    args = []
    for f in fmt.content:
        if   f == "BYTE":   args.append(packet[0])
        elif f == "SBYTE":  args.append(decint(packet[:1]))
        elif f == "SHORT":  args.append(decint(packet[:2]))
        elif f == "STRING": args.append(decstr(packet[:64]))
        elif f == "ARRAY":  args.append(packet[:1024])
        packet = packet[_packet_fmt_types[f]:]

    return args

packet_id_s = {
    0x0: PacketFormat(0, "AUTH", ['BYTE', 'STRING', 'STRING', 'BYTE']),
    0x1: PacketFormat(1, "PING", []),
    0x2: PacketFormat(2, "LEVEL_INIT", []),
    0x3: PacketFormat(3, "LEVEL_DATA_CHUNK", ['SHORT', 'ARRAY', 'BYTE']),
    0x4: PacketFormat(4, "LEVEL_FINALIZE", ['SHORT'] * 3),
    0x6: PacketFormat(6, "SET_BLOCK", ['SHORT']*3 + ['BYTE']),
    0x7: PacketFormat(7, "SPAWN", ['SBYTE', 'STRING'] + \
                       ['SHORT']*3 + ['BYTE']*2),
    0x8: PacketFormat(8, "TELEPORT", ['SBYTE'] + ['SHORT']*3 + ['BYTE']*2),
    0x9: PacketFormat(9, "POS_ORI", ['SBYTE']*4 + ['BYTE']*2),
    0xa: PacketFormat(10, "POS", ['SBYTE']*4),
    0xb: PacketFormat(11, "ORI", ['SBYTE'] + ['BYTE']*2),
    0xc: PacketFormat(12, "DESPAWN", ['BYTE']),
    0xd: PacketFormat(13, "MESSAGE", ['SBYTE', 'STRING']),
    0xe: PacketFormat(14, "DISCONNECT", ['STRING']),
    0xf: PacketFormat(15, "USERTYPE", ['BYTE'])
}
packet_id_c = {
    0x0: PacketFormat(1, "AUTH", ['BYTE', 'STRING', 'STRING', 'BYTE']),
    0x5: PacketFormat(5, "SET_BLOCK", ['SHORT']*3 + ['BYTE']*2),
    0x8: PacketFormat(8, "POS_ORI", ['BYTE'] + ['SHORT']*3 + ['BYTE']*2),
    0xd: PacketFormat(13, "MESSAGE", ['BYTE', 'STRING'])
}

@dataclass
class Player:
    name: str
    x: int
    y: int
    z: int
    pitch: int
    yaw: int


class ClassiCubeAuth:
    def __init__(self, username, password):
        self.session = self.get_session(username, password)
        self.username = username

    def check_auth(self):
        login = self.session.get(api_url('/login'))
        if login.status_code != 200: return None
        login_content = login.json()
        return login_content.get('authenticated')

    def get_session(self, username, password):
        session = requests.Session()
        token = session.get(api_url("/login"))
        assert token.status_code == 200, "Login did not return OK"
        token = token.json().get('token')
        if not token:
            raise PyClassicError("Token not found.")
        
        login = session.post(api_url("/login/"),
                              data = {"username": username,
                                      "password": password,
                                      "token": token})
        text = login.json()
        if not text.get('authenticated'):
            print(text)
            errors = text.get('errors')
            error = ""
            if 'password' in errors:
                error = "Invalid password."
            elif 'username' in errors:
                error = "Invalid username."
            elif 'token' in errors:
                error = "Invalid token. (what?)"
            elif 'verification' in errors:
                error = "Account must be verified."
            raise PyClassicError(error)
        return session

    def server_list(self):
        if not self.check_auth():
            raise PyClassicError("User is not authenticated.")

        servers = self.session.get(api_url("/servers"))
        return servers.json().get('servers')

######################################################################

class PyClassic:
    def __init__(self, auth):
        self.auth = auth
        self.players = {}
        self.event_functions = {}
        self.socket = None
        self.loop = None

    ##################################################################
    def log(self, *msg):
        print("[#]", ' '.join(msg))
    def die(self, *msg):
        print("[!]", ' '.join(msg))

    ##################################################################
    def event(self, fn):
        n = fn.__name__
        if n == "on_packet_recv":
            self.event_functions['recv'] = fn
        elif n == "on_connect":
            self.event_functions['connect'] = fn
        elif n == "on_move":
            self.event_functions['move'] = fn
        elif n.startswith("on_"):
            t = find_packet_id(n[3:].upper())
            if t == -1: return
            self.event_functions[t] = fn
    ##################################################################

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
    ##################################################################

    async def asend(self, pid, *args):
        self.send(pid, *args)
    async def message(self, message):
        self.send(0xd, 0xff, message)

    async def move(self, x, y, z):
        x *= 32
        y *= 32
        z *= 32
        self.send(0x8, -1, x, y, z, 0, 0)
    async def set_block(self, x, y, z, block_id):
        await self.move(x-1, y, z)
        self.send(5, x, y, z, 1, block_id)

    ##################################################################

    def update_player(self, playerid,
                      name = None,
                      x = None,
                      y = None,
                      z = None,
                      pitch = None,
                      yaw = None,
                      relative = False):
        name = sanitize(name) if name else None
        if playerid not in self.players:
            self.players[playerid] = Player(name,x,y,z,pitch,yaw)
            return
        p = self.players[playerid]
        
        if name: p.name = name
        if x: p.x = p.x+x if relative else x
        if y: p.y = p.y+y if relative else y
        if z: p.z = p.z+z if relative else z
        if pitch: p.pitch = pitch
        if yaw: p.yaw = yaw
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
    def connect(self, **kargs):
        if self.socket:
            raise PyClassicError("The socket is not null, plase disconnect.")
        serverlist = self.auth.server_list()
        server = [x for x in serverlist
                  if contains_all(kargs, x)]
        if len(server) == 0:
            raise PyClassicError("Server not found")
        server = server[0]

        ip, port = server['ip'], server['port']
        username = self.auth.username
        mppass = server.get('mppass')
        if not mppass:
            raise PyClassicError("mppass not found, is the user authenticated?")

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = s
        s.connect((ip, port))
        s.sendall(b'\x00' + encode_packet(packet_id_c[0x0], 7,
                                          username, mppass, 0))
        pid, auth_packet = self.recv()
        if not auth_packet:
            self.disconnect()
            raise PyClassicError("Failed to connect to server.")
        elif pid.name == "DISCONNECT":
            self.disconnect()
            raise PyClassicError(f"Kicked: {auth_packet[1]}")

        return auth_packet[1], auth_packet[2]
    ##################################################################

    async def event_loop(self):
        def run_event(name, *args):
            fn = self.event_functions.get(name)
            if fn:
                task = asyncio.ensure_future(fn(self, *args))

        try:
            run_event("connect")
            while True:
                info, packet = self.recv()
                run_event("recv", info, packet)
                run_event(info.pid, *packet)
                
                if info.name == "DISCONNECT":
                    self.die("Kicked!", packet[0])
                    self.loop.stop()
                    return
                elif info.name == "SPAWN":
                    self.update_player(*packet)
                elif info.name == "DESPAWN":
                    del self.players[packet[0]]

                elif info.name == "TELEPORT":
                    run_event("move", info.name, *packet)
                    if packet[0] == -1:
                        self.move(packet[1]//32,
                                        packet[2]//32 + 2,
                                        packet[3]//32)
                    self.update_player(packet[0], None, *packet[1:])
                elif info.name in ["POS", "ORI", "POS_ORI"]:
                    run_event("move", info.name, *packet)
                    
                    pid = packet[0]
                    newpos = [None, None, None]
                    newangle = [None, None]
                    if info.name == "POS":
                        newpos = packet[1:]
                    elif info.name == "ORI":
                        newangle = packet[1:]
                    elif info.name == "POS_ORI":
                        newpos = packet[1:4]
                        newangle = packet[4:]

                    self.update_player(pid, None, *(newpos+newangle),
                                       True)
                await asyncio.sleep(0)
        except KeyboardInterrupt:
            self.loop.stop()
            return
    ##################################################################

    def run(self, **kargs): # TODO: finish
        err = None
        self.connect(**kargs)

        self.loop = asyncio.get_event_loop()
        # self.loop.create_task(self.event_loop())
        try:
            # asyncio.run(self.event_loop())
            self.loop.run_until_complete(self.event_loop())
        except Exception as e:
            err = e
        finally:
            self.loop.close()
        self.loop = None

        self.disconnect()
        if err: raise err
