import pyclassic
from dataclasses import dataclass

class QueueException(Exception): pass

class Job:
    def __init__(self, name, iterable):
        self.name = name
        self.iterable = iter(iterable)
        self.complete = 0

    async def next(self, player):
        f = next(self.iterable)
        self.complete = f(player)
        return self.complete != None

    def is_done(self):
        return self.complete == None

@dataclass
class Block:
    x: int
    y: int
    z: int
    bid: int

    async def place(self, player):
        await player.set_block(self.x, self.y, self.z, self.bid)
        
class BlockJob(Job):
    def __init__(self, name, iterable):
        if type(iterable) != list:
            raise QueueException("Must be a list.")
        self.name     = name
        self.iterable = iterable
        self.length   = len(iterable)
        self.complete = 0

    async def next(self, player):
        if self.iterable:
            block = self.iterable.pop(0)
            complete = ((self.length-len(self.iterable)) / self.length)*100

            await block.place(player)
        else:
            self.complete = None
        return complete

class JobQueue:
    def __init__(self, player, delay = 0.1):
        self.delay = delay
        assert type(player) == pyclassic.PyClassic
        self.queue = []
        self.current = Non
        self.player = player

    def running(self):
        return self.current != None

    def run_queue(self):
        self.current = self.queue.pop(0)
        if not self.current:
            raise QueueException("Nothing left in queue.")

    async def do_next(self):
        complete = self.current.next(self.player)
        if complete == None:
            pass

    # First In First Out
    def push(self, q):
        if type(q) != Job:
            raise QueueException("Only a queue can be pushed.")
        self.queue.append(q)
    def pop(self):
        return self.queue.pop(0) if len(self.queue)>0 else None
