import asyncio, time
import pyclassic.queue as pqueue
import pyclassic.map as pmap
import pyclassic.client as pclient
import pyclassic.auth as pauth
from .utils import *
from dataclasses import dataclass

@dataclass
class Player:
    """
    This is a simple class to store player data such as their position,
    their username and their head direction.
    """
    name: str
    x: int
    y: int
    z: int
    pitch: int
    yaw: int

class PyClassic:
    """
    The PyClassic class is the "main" class. It handles the event
    system which the core design of this library. However you do not
    have to use this class. See :class:`pyclassic.client.Client`.

    It supports event handling of course but also multibot which can
    be useful for building stuff using
    :class:`pyclassic.queue.ThreadedQueue`.

    :param client: The main client that will be used for event
                   handling
    :param multibot: array of clients or auth objects for multibot
    :param client_name: name of the client, defaults to
                        "pyclassic <VERSION>" if None
    :param build_delay: Block placing delay for multibot building

    :type client:  :class:`pyclassic.auth.SimpleAuth` or
                   :class:`pyclassic.client.Client`
    :type multibot: list[:class:`pyclassic.auth.SimpleAuth` or
                         :class:`pyclassic.client.Client`], optional
    :type client_name: str or None, optional
    :type build_delay: float, optional

    :raise pyclassic.PyClassicError: if the client parameter is invalid.
    """
    def __init__(self, client, multibot = [], client_name = None,
                 build_delay = 0.03, mainbot_as_worker = False):
        # self.auth = auth
        if isinstance(client, pauth.SimpleAuth):
            # For backward compatibility but to also keep it
            # concise.
            self.client = pclient.Client(
                client, client_name = client_name)
        elif type(client) is client.Client:
            self.client = client
        else:
            raise PyClassicError("Invalid client argument "
                                 "(must be Client or Auth)")

        # Invalid elements will be ignored.
        #: Queue object for multibot, None if there are no multibot.
        self.queue: pqueue.ThreadedQueue = None
        self.clones = [
            x if type(x) is pclient.Client else
            pclient.Client(x, client_name = client_name)
            for x in multibot]

        #: List of players, dynamically updated with the event system.
        self.players: dict = {}
        self.event_functions = {}
        self.socket = None
        self.loop = None
        #: Map object that stores the downloaded map.
        self.map: pmap.ClassicMap = None
        self.map_cache = b''
        if not client_name:
            self.client_name = f"pyclassic {PYCLASSIC_VERSION}"
        else:
            self.client_name = client_name

        if self.clones != []:
            if mainbot_as_worker: self.clones.append(self.client)
            self.queue = pqueue.ThreadedQueue(self,
                                               delay = build_delay)

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
        """
        Decorator to define an event.

        :param fn: Event function. The function must be named as the
                   wanted event.
        :type fn: function
        """
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
        """
        see :func:`pyclassic.client.Client.recv`
        """
        return self.client.recv()

    def send(self, pid, *args):
        """
        see :func:`pyclassic.client.Client.send`
        """
        return self.client.send(pid, *args)
    ##################################################################

    async def asend(self, pid, *args):
        """
        Actually not very useful, sends stuff but asynchronously.

        see :func:`pyclassic.PyClassic.send`
        """
        self.send(pid, *args)
    def get_block(self, x, y, z):
        """
        Retrieve a block from `self.map`

        :param x: X position
        :param y: Y position
        :param z: Z position

        :type x: int
        :type y: int
        :type z: int

        :raise pyclassic.PyClassicError: The map has not been loaded.

        :return: The ID of the wanted block.
        :rtype: int
        """
        if self.map:
            return self.map[x, y, z]
        else:
            raise PyClassicError("Map must be loaded first.")
    # Backward compat
    async def move(self, *args):
        """
        Moves the main client.
        see :func:`pyclassic.client.Client.move`
        """
        return self.client.move(*args)
    async def set_block(self, x, y, z, bid):
        """
        Makes the main client place a block and updates the map if
        there is one.

        See :func:`pyclassic.client.Client.set_block`

        :type x: int
        :type y: int
        :type z: int

        :param bid: Block ID to place
        :type bid: int
        """
        r = self.client.set_block(x, y, z, bid)
        if self.map:
            self.map[x, y, z] = bid
    async def message(self, *args):
        """
        Send a message from the main client.

        See :func:`pyclassic.client.Client.message`
        """
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
        dtz = lambda n: 0 if None else n
        x, y, z, pitch, yaw = [dtz(_) for _ in (x,y,z,pitch,yaw)]
        if playerid not in self.players:
            self.players[playerid] = Player(name,x,y,z,pitch,yaw)
            return
        p = self.players[playerid]
        
        if name: p.name = name
        if x: p.x = p.x+x if relative and p.x else x
        if y: p.y = p.y+y if relative and p.y else y
        if z: p.z = p.z+z if relative and p.z else z
        if pitch: p.pitch = pitch
        if yaw: p.yaw = yaw

    ##################################################################
    def disconnect(self):
        """
        Disconnects the main client.
        
        see :func:`pyclassic.client.Client.disconnect`
        """
        return self.client.disconnect()
    def connect(self, **kargs):
        """
        Connects the main client to a server.

        see :func:`pyclassic.client.Client.connect`
        """
        return self.client.connect(**kargs)

    def connect_multibot(self, delay = 4, **kargs):
        """
        Connects the multibot army to a server.

        see :func:`pyclassic.client.Client.connect`
        """
        for bot in self.clones:
            if not bot.socket:
                time.sleep(delay)
                bot.connect(**kargs)
    def disconnect_multibot(self):
        """
        Disconnects the whole bot army.

        see :func:`pyclassic.client.Client.disconnect`
        """
        for bot in self.clones: bot.disconnect()
        
    ##################################################################
    ##################################################################

    async def event_loop(self):
        """
        Runs the asynchronous event loop.

        .. warning::
            This function **SHOULD NOT** be run manually unless you
            are doing cursed shit.
            See :func:`pyclassic.PyClassic.run`
        """
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
                    self.map = pmap.ClassicMap(
                        self.map_cache, w, h, l)
                    self.map_cache = b''
                    if self.queue:
                        self.queue.map = self.map
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
        """
        Connects all clients and run the event loop.

        :param delay: Delay of connection between each multibot
                      connection.
        :param kargs: Arguments such as the IP address, port, etc.
                      It depends of the :class:`pyclassic.auth`
                      class.
        """
        err = None
        if self.client.socket: self.connect(**kargs)
        if self.clones: self.connect_multibot(delay = delay, **kargs)
            
        self.loop = asyncio.get_event_loop()
        # self.loop.create_task(self.event_loop())
        try:
            self.loop.run_until_complete(self.event_loop())
        except Exception as e:
            err = e

        self.loop = None

        self.disconnect()
        if err: raise err
