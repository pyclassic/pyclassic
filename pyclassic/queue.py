"""
This is a queue system which can be used to build stuff. It uses a
job queue and threading to optimize the building speed as it is
slow using the asynchronous system of the event system.

It is designed to be used by an array of clients but can also be used
with only one client. If you want to build fast on a server with
anti-grief policies, this module is for you.

.. warning::
    Some servers may IP-ban you :) Make sure to only use it on
    unmoderated servers. Or maybe you can do a little trolling while
    no one is connected :troll:
"""
import pyclassic, threading, time
from dataclasses import dataclass

class QueueError(Exception): pass

@dataclass
class Block:
    """
    A single block.
    """
    x: int
    y: int
    z: int
    bid: int

class ThreadedQueue:
    """
    The class that does all the queue job.

    .. warning::
        To prevent Python from eventually doing a funny because
        threading while editing the job queue, please use the functions
        as they ensure the queue is not locked before modifying it.

    :param player: The array of bots to use, can also be a
                   :class:`pyclassic.PyClassic` instance, the class
                   will take the bot array from it.
    :param delay:  The delay, defaults to 0.03s (30ms) as it is the
                   usual delay to bypass the anti-grief system.
    
    :type player:  :class:`pyclassic.PyClassic` or a list of
                   :class:`pyclassic.client.Client` instances.
    :type delay:   float, optional
    :type map:     :class:`pyclassic.map.ClassicMap`, optional
    :raise pyclassic.queue.QueueError: The list is empty or the
                                       PyClassic instance has no
                                       bot array.
    """
    def __init__(self, player: pyclassic.PyClassic, map = None, delay = 0.03):
        self.current_queue = None
        self.queues = []
        self.thread = None
        self.thread_event = None
        self.delay = delay

        if type(player) is pyclassic.PyClassic:
            self.map = player.map
            print(player.map)
            print(self.map)

            if player.clones:
                self.bots = player.clones
            else:
                self.bots = [player.client]
            
            return
        elif type(player) is list:
            if not player: raise QueueError("Empty list.")
            self.bots = player
        else:
            self.bots = [player]
        self.map = None
    def is_active(self):
        """
        Checks if there is a running thread.

        :return: Thread running?
        :rtype:  bool
        """
        return self.thread != None
    
    def check_lock(self):
        """
        Checks if the block queue has been locked (it locks when the
        thread is running). It will raise an exception if it is. This
        is an helper function used in functions that edits the queue.

        :raise pyclassic.queue.QueueError: The queue is locked.
        """
        if self.thread:
            raise QueueError("Block queue has been locked. "
                             "Make sure to stop the thread first.")
    
    def add_queue(self, queue):
        """
        Adds a queue to the job queue.

        :param queue: Block queue
        :type queue:  list[:class:`pyclassic.queue.Block`]
        """
        self.check_lock()
        
        if self.map:
            self.queues.append([x for x in queue
                                if self.map[x.x, x.y, x.z] != x.bid])
        else:
            self.queues.append(queue.copy())
    def remove_queue(self, i):
        """
        Removes a queue from the job queue.

        :param i: Index
        :type i:  int
        """
        self.check_lock()
        if i > len(self.queues):
            raise QueueError("This queue does not exist.")
        self.queues.pop(i)

    def clear_queues(self):
        """
        Clear the whole job queue along with the current queue.
        """
        self.check_lock()
        self.queues = []
        self.current_queue = None

    def clear_current_queue(self):
        """
        Clears only the current queue.
        """
        self.check_lock()
        self.current_queue = None

    def do_blockqueue(self, threaded = True):
        """
        Pops a queue from the job queue and make the multibot run it.
        If there is already an unfinished current queue, continue it.
        Otherwise if it is empty, do nothing.

        .. warning::
            I do not recommend manually running as it breaks the whole
            point of this class but do as you wish.
            See :func:`pyclassic.queue.ThreadedQueue.start`.

        :param threaded: is it running in a thread?
        :type threaded:  bool, optional
        """
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
        """
        Do all queues from the job queue until there is nothing left.

        .. warning::
            I do not recommend manually running as it breaks the whole
            point of this class but do as you wish.
            See :func:`pyclassic.queue.ThreadedQueue.start_all`.
        """
        while self.queues != []:
            self.do_blockqueue(False)
            if self.thread and self.thread_event.is_set():
                return

        if self.thread:
            self.thread = None
            self.thread_event = None

    def make_thread(self, **kargs):
        """
        Helper function used internally to make and start a thread.
        """
        if not self.queues and not self.current_queue: return
        if self.thread: return
        t = threading.Thread(**kargs)
        self.thread_event = threading.Event()
        t.start()
        self.thread = t
        
    def start(self):
        """
        Starts a thread to execute one job in the queue. Does nothing
        if the thread is already running.
        """
        self.make_thread(target = self.do_blockqueue)
    def start_all(self):
        """
        Starts a thread to execute all jobs in the queue. Does nothing
        if the thread is already running.
        """
        self.make_thread(target = self.do_all_blockqueues)

    def stop(self):
        """
        Send a termination signal to the running thread if there is
        one and wait for it to stop.
        """
        if self.thread:
            self.thread_event.set()
            self.thread.join()
            
            self.thread = None
            self.thread_event = None
