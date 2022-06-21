# Map stuff
import gzip, pyclassic
from pyclassic.utils import decint

class ClassicMapError(Exception): pass

class ClassicMap:
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
        x = (idx % self.width)
        y = (idx // self.width) // self.length
        z = (idx // self.width) % self.length
        return x, y, z