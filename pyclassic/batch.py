"""
Queue batch system.

This is a very simple batch system to generate queues based on specific
commands. Positions must be relative. documentation soon:tm:
"""
from dataclasses import dataclass
import pyclassic.queue, pyclassic.extra

class BatchError(Exception): pass

@dataclass
class Batch:
    """
    The Batch class can generate queues on a given script.
    """
    fn: dict
    filterfn: dict

    current_queue = []

    def execute_line(self, line):
        cmd = line[0]
        args = [int(x) for x in line[1:]]

        print(cmd)
        if cmd in self.fn:
            self.current_queue += self.fn[cmd](*args)
        elif cmd in self.filterfn:
            f = self.filterfn[cmd](*args)
            self.current_queue = list(filter(f, self.current_queue))
        else:
            raise BatchError("Invalid command.")

    def generate_queue(self, script, ox=0, oy=0, oz=0):
        """
        Generates a queue from a script and a given offset.

        :param script: The script
        :type script: str
        :type ox: int, optional
        :type oy: int, optional
        :type oz: int, optional

        :return: The generated queue
        :rtype: list[:class:`pyclassic.queue.Block`]
        """
        self.current_queue = []
        script = [x.split() for x in script.split('\n')
                  if x.strip() != '']

        for line in script:
            if line[0].startswith("#"): continue
            self.execute_line(line)

        for block in self.current_queue:
            block.x += ox
            block.y += oy
            block.z += oz

        return self.current_queue

class DefaultBatchFunctions:
    """
    This is a static class with all the default batch functions.
    """

    
    def cuboid(ax, ay, az, bx, by, bz, bid):
        return pyclassic.extra.cuboid(ax,ay,az,bx,by,bz,bid)
    def wall(ax, ay, az, bx, by, bz, bid):
        return sum([pyclassic.extra.hollow(y, ax, az, bx, bz, bid)
                    for y in range(ay, by+1)], [])

    def filter_block(b):
        return lambda block: block.bid != b

    fn_dict = {
        "cuboid": cuboid, "wall": wall
    }
    filterfn_dict = {
        "fblock": filter_block
    }

    batch = Batch(fn_dict, filterfn_dict)

