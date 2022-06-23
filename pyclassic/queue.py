import pyclassic, threading, time
from dataclasses import dataclass

class QueueError(Exception): pass

@dataclass
class Block:
    x: int
    y: int
    z: int
    bid: int

    def place(self, player):
        player.set_block(self.x, self.y, self.z, self.bid)


class ThreadedQueue:
    def __init__(self, player: pyclassic.PyClassic, delay = 0.03):
        self.current_queue = None
        self.queues = []
        self.thread = None
        self.thread_event = None
        self.delay = delay
        if type(player) is pyclassic.PyClassic:
            if player.clones:
                self.bots = player.clones
            else:
                self.bots = [player.client]
        elif type(player) is list:
            if not player: raise QueueError("Empty list.")
            self.bots = player
        else:
            self.bots = [player]

    def is_active(self):
        return self.thread != None
    
    def check_lock(self):
        if self.thread:
            raise QueueError("Block queue has been locked. "
                             "Make sure to stop the thread first.")
    
    def add_queue(self, queue):
        self.check_lock()
        self.queues.append(queue)

    def remove_queue(self, i):
        self.check_lock()
        if i > len(self.queues):
            raise QueueError("This queue does not exist.")
        self.queues.pop(i)

    def clear_queues(self):
        self.check_lock()
        self.queues = []
        self.current_queue = None

    def clear_current_queue(self):
        self.check_lock()
        self.current_queue = None

    def do_blockqueue(self, threaded = True):
        if not self.current_queue:
            if not self.queues: return
            else:
                self.current_queue = self.queues.pop(0)

        delay = self.delay # / len(self.bots)
        bot_id = 0
        while self.current_queue != []:
            if self.thread_event != None and \
               self.thread_event.is_set():
                break
            if bot_id == 0:
                time.sleep(delay)
            block = self.current_queue.pop(0)
            x, y, z, bid = block.x, block.y, block.z, block.bid
            self.bots[bot_id].set_block(x, y, z, bid)
            bot_id = (bot_id+1)%len(self.bots)

        if threaded and self.thread and not self.thread_event.is_set():
            self.thread = None
            self.thread_event = None

    def do_all_blockqueues(self):
        while self.queues != []:
            self.do_blockqueue(False)
            if self.thread and self.thread_event.is_set():
                return

        if self.thread:
            self.thread = None
            self.thread_event = None

    def make_thread(self, **kargs):
        if not self.queues and not self.current_queue: return
        if self.thread: return
        t = threading.Thread(**kargs)
        self.thread_event = threading.Event()
        t.start()
        self.thread = t
        
    def start(self):
        self.make_thread(target = self.do_blockqueue)
    def start_all(self):
        self.make_thread(target = self.do_all_blockqueues)

    def stop(self):
        if self.thread:
            self.thread_event.set()
            self.thread.join()
            
            self.thread = None
            self.thread_event = None
