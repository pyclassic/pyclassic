"""
PyClassic - Minecraft Classic Protocol implementation in Python.
"""
# PyClassic - Minecraft Classic client
import socket, json, requests, time, asyncio, re
import pyclassic.auth, pyclassic.map, pyclassic.client
from dataclasses import dataclass
from pyclassic.utils import *

__version__ = "dev-2022"
PYCLASSIC_VERSION = __version__ 

@dataclass
class Player:
    name: str
    x: int
    y: int
    z: int
    pitch: int
    yaw: int


######################################################################

class PyClassic:
    """
    The PyClassic class is the "main" class. It handles the event
    system which the core design of this library. However you do not
    have to use this class. See client.Client.

    It supports event handling of course but also multibot which can
    be useful for building stuff using queue.ThreadedQueue.
    """
    def __init__(self, client, multibot = [], client_name = None):
        """
        :param client: the client that will be used
        :param multibot: array of clients or auth objects for multibots
        :param client_name: name of the client, defaults to pyclassic if None

        :type client:  pyclassic.auth.SimpleAuth or pyclassic.client.Client
        :type multibot: list[pyclassic.auth.SimpleAuth or pyclassic.client.Client]
        :type client_name: str or None

        :raise pyclassic.PyClassicError: if the client parameter is invalid.
        """
        # self.auth = auth
        if type(client) is pyclassic.auth.SimpleAuth:
            # For backward compatibility but to also keep it
            # concise.
            self.client = pyclassic.client.Client(
                client, client_name = client_name)
        elif type(client) is pyclassic.client.Client:
            self.client = client
        else:
            raise PyClassicError("Invalid client argument "
                                 "(must be Client or Auth)")

        # Invalid elements will be ignored.
        self.clones = [
            x if type(x) is pyclassic.client.Client else
            pyclassic.client.Client(x, client_name = client_name)
            for x in multibot]

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
        """
        Logs stuff
        """
        print("[#]", ' '.join(msg))
    def die(self, *msg):
        """
        Logs stuff but more dramatically
        """
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

    def recv(self): return self.client.recv()

    def send(self, pid, *args): return self.client.send(pid, *args)
    ##################################################################

    async def asend(self, pid, *args):
        self.send(pid, *args)
    def get_block(self, x, y, z):
        if self.map:
            return self.map[x, y, z]
        else:
            raise PyClassicError("Map must be loaded first.")
    # Backward compat
    async def move(self, *args):
        return self.client.move(*args)
    async def set_block(self, x, y, z, bid):
        r = self.client.set_block(x, y, z, bid)
        if self.map:
            self.map[x, y, z] = bid
    async def message(self, *args):
        return self.client.message(*args)

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
        return self.client.disconnect()
    def connect(self, **kargs):
        return self.client.connect(**kargs)

    def connect_multibot(self, delay = 4, **kargs):
        for bot in self.clones:
            time.sleep(delay)
            bot.connect(**kargs)
    def disconnect_multibot(self):
        for bot in self.clones: bot.disconnect()
        
    ##################################################################
    ##################################################################


    async def event_loop(self):
        def run_event(name, *args):
            fn = self.event_functions.get(name)
            if fn:
                task = asyncio.ensure_future(fn(*args))

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
                    if self.players.get(packet[0]):
                        del self.players[packet[0]]

                elif info.name == "TELEPORT":
                    run_event("move", info.name, *packet)
                    if packet[0] == -1:
                        await self.move(packet[1]//32,
                                        packet[2]//32 + 2,
                                        packet[3]//32)
                    self.update_player(packet[0], None, *packet[1:])
                elif info.name in ["POS", "ORI", "POS_ORI"]:
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

                    run_event("move", info.name, pid, *(newpos+newangle))
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

    def run(self, delay = 4, **kargs): # TODO: finish
        err = None
        self.connect(**kargs)
        if self.clones:
            self.connect_multibot(delay = delay, **kargs)
            
        self.loop = asyncio.get_event_loop()
        # self.loop.create_task(self.event_loop())
        try:
            self.loop.run_until_complete(self.event_loop())
        except Exception as e:
            err = e

        self.loop = None

        self.disconnect()
        if err: raise err
