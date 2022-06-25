"""
This module take care of doing all the map stuff for you. It features
map data decoding (including gzip decompression), and can also be
edited which has been useful for the event system.

We are also considering supporting other formats such as schematic
or ClassicWorld (.cw) files

.. note::
    Concerning map loading and saving, the format it uses is essentially
    just the same as the data downloaded on a regular Classic server with
    6 shorts (12 bytes) prepended. The 3 first being the offset of the map
    and the 3 last being the size of the map. All of it gzipped. It is
    quite trivial to parse.
"""
# Map stuff
import gzip, pyclassic
from pyclassic.utils import decint, encint

class ClassicMapError(Exception): pass

def load(filename):
    """
    Loads a map.

    :param filename: File name
    :type filename:  str

    :return: The offset and the generate map object.
    :rtype:  (int, int, int), :class:`pyclassic.map.ClassicMap`
    """
    with gzip.open(filename) as f:
        offset = f.read(6)
        x, y, z = [decint(offset[x:x+2]) for x in range(0,6,2)]
        size = f.read(6)
        width, height, length = [decint(size[x:x+2]) for x in range(0,6,2)]
        data = f.read()
    return (x, y, z), ClassicMap(data,
                                 width, height, length,
                                 compressed = False)

class ClassicMap:
    """
    This ClassicMap class is used to store map data which can also be
    modified and saved in a file with the format mentionned at the
    beginning of the module documentation. It can also be sliced into
    a region.

    Getting and setting blocks can be done like on an array.
    For example, `map[3, 1, 2] = 1` sets a stone block at the position
    (3, 1, 2) of the stored map.

    :param data: Raw data downloaded from the server, compressed or not
    :param compressed: If true, it will decompress the data using gzip

    :type data:   bytes
    :type width:  int
    :type height: int
    :type length: int
    :type compressed: bool, optional
    """
    # NOTE: Maybe we could add offset in the class.
    def __init__(self, data: bytes, width, height, length,
                 compressed = True):
        self.data = bytearray(
            gzip.decompress(data) if compressed else data)
        magic = decint(self.data[:2])

        self.blocks = self.data[4:]
        self.width = width
        self.height = height
        self.length = length
        
    def __getitem__(self, vector):
        if type(vector) == slice:
            return self.slice_down(vector)
        if len(vector) != 3: raise ClassicMapError("not a vector")
        x, y, z = vector
        if x > self.width or y > self.height or z > self.length:
            raise ClassicMapError("Position outside of map boundaries.")

        idx = x+(z*self.width)+(y*self.width*self.length)
        block = self.blocks[idx]

        return block

    def slice_down(self, vectors):
        start = vectors.start
        if not start: return None
        stop = vectors.stop
        if not stop: return None

        v1 = [min(a,b) for a, b in zip(start, stop)]
        v2 = [max(a,b) for a, b in zip(start, stop)]
        
        w, h, l = v2[0]-v1[0]+1, v2[1]-v1[1]+1, v2[2]-v1[2]+1
        n = b'\0\0\0\0'
        for y in range(v1[1], v2[1]+1):
            y *= self.width*self.length
            for z in range(v1[2], v2[2]+1):
                z *= self.width
                n += self.blocks[v1[0]+y+z:v2[0]+y+z+1]

        return ClassicMap(n, w, h, l, compressed = False)

    def __setitem__(self, vector, bid):
        if len(vector) != 3: raise ClassicMapError("not a vector")
        x, y, z = vector

        idx = x+(z*self.width)+(y*self.width*self.length)
        self.blocks[idx] = bid

    def getpos(self, idx):
        """
        Calculate the x, y, z position of a specified index.

        :param idx: Index in the map
        :type idx:  int

        :return: Calculated position
        :rtype:  (int, int, int)
        """
        x = (idx % self.width)
        y = (idx // self.width) // self.length
        z = (idx // self.width) % self.length
        return x, y, z

    def save(self, filename, compresslevel = 9, ox=0,oy=0,oz=0):
        """
        Saves the map in a file.

        :param filename:      Name of the file to save.
        :param compresslevel: Level of gzip compression.
        :param ox: X offset
        :param oy: Y offset
        :param oz: Z offset

        :type filename:      str
        :type compresslevel: int, optional
        :type ox: int, optional
        :type oy: int, optional
        :type oz: int, optional
        """
        with gzip.open(filename, "wb") as f:
            f.write(encint(ox) + encint(oy) + encint(oz))
            f.write(encint(self.width) + encint(self.height) + \
                    encint(self.length))
            f.write(self.data)

    def get_queue(self, ox = 0, oy = 0, oz = 0):
        """
        Turns a map into a queue, a list of
        :class:`pyclassic.queue.Block` to be used with
        :class:`pyclassic.queue.ThreadedQueue`

        :param ox: X offset
        :param oy: Y offset
        :param oz: Z offset

        :type ox: int, optional
        :type oy: int, optional
        :type oz: int, optional

        :return: The queue converted from the map.
        :rtype:  list[:class:`pyclassic.queue.ThreadedQueue`]
        """
        return [pyclassic.queue.Block(
            *[x+y for x, y in zip(self.getpos(idx),(ox,oy,oz))], bid)
                for idx, bid in enumerate(self.blocks)]

    def get_queue_from_region(self, x1, y1, z1, x2, y2, z2,
                              ox = 0, oy = 0, oz = 0):

        ax, ay, az = [min(a,b) for a, b in zip((x1,y1,z1), (x2,y2,z2))]
        bx, by, bz = [max(a,b) for a, b in zip((x1,y1,z1), (x2,y2,z2))]

        queue = []
        for x in range(ax, bx+1):
            for y in range(ay, by+1):
                for z in range(az, bz+1):
                    if x >= self.width or \
                       y >= self.height or \
                       z >= self.length:
                        continue
                    queue.append(pyclassic.queue.Block(ox+x, oy+y, oz+z,
                                        self[x,y,z]))

        return queue
