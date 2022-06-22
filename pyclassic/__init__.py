#!/usr/bin/env python3
# PyClassic - Minecraft Classic client
import socket, json, requests, time, asyncio, re
import pyclassic.map
from dataclasses import dataclass
from pyclassic.utils import *

PYCLASSIC_VERSION = "dev-2022"

@dataclass
class Player:
    name: str
    x: int
    y: int
    z: int
    pitch: int
    yaw: int

class SimpleAuth:
    def __init__(self, username, mppass):
        self.session = mppass
        self.username = username

    def connect(self, **kargs):
        assert "ip" in kargs and "port" in kargs
        ip, port = kargs['ip'], kargs['port']
        return ip, port, self.username, self.session
    
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

    def connect(self, **kargs):
        serverlist = self.server_list()
        server = [x for x in serverlist
                  if contains_all(kargs, x)]
        if len(server) == 0:
            raise PyClassicError("Server not found")
        server = server[0]

        ip, port = server['ip'], server['port']
        username = self.username
        mppass = server.get('mppass')
        if not mppass:
            raise PyClassicError("mppass not found, is the user authenticated?")

        return ip, port, username, mppass

######################################################################

class PyClassic:
    def __init__(self, auth, client_name = None):
        self.auth = auth
        self.players = {}
        self.event_functions = {}
        self.socket = None
        self.loop = None
        self.map = None
        self.map_cache = b''
        if not client_name:
            self.client_name = f"pyclassic {PYCLASSIC_VERSION}"
        else:
            self.client_name = client_name

    ##################################################################
    def log(self, *msg):
        print("[#]", ' '.join(msg))
    def die(self, *msg):
        print("[!]", ' '.join(msg))

    ##################################################################
    def event(self, fn):
        packetpref, pref = "on_packet_", "on_"
        n = fn.__name__
        if n.startswith(packetpref):
            t = find_packet_id(n[len(packetpref):].upper())
            if t == -1: return
            self.event_functions[t] = fn
        elif n.startswith(pref):
            t = n[len(pref):].lower()
            if t in ['recv', 'connect', 'move', 'set_block']:
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
        if self.map:
            self.map[x, y, z] = block_id
    def get_block(self, x, y, z):
        if self.map:
            return self.map[x, y, z]
        else:
            raise PyClassicError("Map must be loaded first.")

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

    ##################################################################
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
    def connect(self, **kargs):
        if self.socket:
            raise PyClassicError("The socket is not null, plase disconnect.")

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
                raise PyClassicError(f"Kicked! {auth_or_cpe[1]}")

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
                        await self.move(packet[1]//32,
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

                elif info.name == 'LEVEL_INIT':
                    self.map_cache = b''
                elif info.name == 'LEVEL_DATA_CHUNK':
                    sz = packet[0]
                    self.map_cache += packet[1][:sz]
                elif info.name == 'LEVEL_FINALIZE':
                    w, h, l = packet
                    self.map = pyclassic.map.ClassicMap(
                        self.map_cache, w, h, l)
                    self.map_cache = b''
                elif info.name == 'SET_BLOCK' and self.map:
                    x, y, z, block_id = packet
                    run_event("set_block", x, y, z, block_id,
                              self.map[x, y, z])
                    self.map[x, y, z] = block_id
                elif info.name == "CUSTOM_BLOCK_LEVEL":
                    self.send(0x13, 1)
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
            # Putting the run function as async does not make sense
            # at all and adds some useless boilerplate to code.

            # I don't even know why you did that
            # .run_until_complete is pretty much the same thing as await.
            self.loop.run_until_complete(self.event_loop())
        except Exception as e:
            err = e

        self.loop = None

        self.disconnect()
        if err: raise err
