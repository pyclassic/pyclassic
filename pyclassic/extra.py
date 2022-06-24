# Cool extras.
from pyclassic.queue import Block
from pyclassic.client import Client
from pyclassic.auth import SimpleAuth

def throwaway(username, clientname = None, **kargs):
    """
    Makes a "throw-away" account. This can only be used on servers that
    does not check user authentication.
    It uses :class:`pyclassic.auth.SimpleAuth` as auth object.

    :param username:   Username of the throwaway, will also be the
                       specified salt
    :param clientname: The name of the client :troll:
    :param kargs:      Arguments to pass to the auth object on
                       connection

    :type username:   str
    :type clientname: str or None, optional
    
    :return: The freshly new client that has been created just for you
    :rtype:  :class:`pyclassic.client.Client`
    """
    player = Client(SimpleAuth(username, username), client_name = clientname)
    player.connect(**kargs)
    return player

def download_map(bot):
    """
    Hacky function to download the map from a server. I would not
    recommend using it unless you're doing hacky automated shit like
    I do.

    :param bot: The client to receive data with
    :type bot:  :class:`pyclassic.client.Client`

    :return: The downloaded, decompressed and parsed map.
    :rtype:  :class:`pyclassic.map.ClassicMap`
    """
    m = b''
    while True:
        info, packet = bot.recv()
        if info.pid == 3:
            m += packet[1][:packet[0]]
        elif info.pid == 4:
            x, y, z = packet
            break
    return pyclassic.map.ClassicMap(m, x, y, z)

def hollow(y, x1, z1, x2, z2, bid):
    (ax, bx), (az, bz) = sorted((x1, x2)), sorted((z1, z2))
    result = [Block(x, y, az, bid) for x in range(ax, bx+1)] + \
        [Block(x, y, bz, bid) for x in range(ax, bx+1)] + \
        [Block(ax, y, z, bid) for z in range(az, bz+1)] + \
        [Block(bx, y, z, bid) for z in range(az, bz+1)]
    return result

def pyramid(size, ox, oy, oz, bid):
    q = []
    for y in range(0, size//2):
        sz = size-y
        q += hollow(oy+y, y+ox, y+oz, sz+ox, sz+oz, bid)
    return q

def cuboid(x1, y1, z1, x2, y2, z2, blockid):
    ax, ay, az = min(x1, x2), min(y1, y2), min(z1, z2)
    bx, by, bz = max(x1, x2), max(y1, y2), max(z1, z2)

    queue = []
    for x in range(ax, bx+1):
        for y in range(ay, by+1):
            for z in range(az, bz+1):
                queue.append(Block(x, y, z, blockid))
    return queue
