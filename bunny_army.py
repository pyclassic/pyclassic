#!/usr/bin/env python3
import pyclassic, pyclassic.map
import time, asyncio

ip, port = "51.89.42.211", 39999

def throwaway(username):
    p = pyclassic.PyClassic(pyclassic.SimpleAuth(username, username))
    p.connect(ip = ip, port = port)
    return p

def connect_bunnies(amount, prefix):
    bots = [(throwaway(f"{prefix}{n}"), time.sleep(0.5))[0]
             for n in range(amount)]
    return bots

def disconnect_bunnies(bots):
    [bot.disconnect() for bot in bots]

def download_map(bot):
    m = b''
    while True:
        info, packet = bot.recv()
        if info.pid == 3:
            m += packet[1][:packet[0]]
        elif info.pid == 4:
            x, y, z = packet
            break
    return pyclassic.map.ClassicMap(m, x, y, z)

def make_queue(cmap, fn):
    return [cmap.getpos(idx) for idx, bid in enumerate(cmap.blocks)
            if fn(idx, bid)]

async def do_blockqueue(bots, queue, blockid):
    blocks = queue.copy()
    i = 0
    while blocks != []:
        x, y, z = blocks.pop()
        i = (i+1)%len(bots)
        await bots[i].set_block(x, y, z, blockid)
        time.sleep(0.03/len(bots))

async def wipemap():
    print("Connecting bots...")
    bots = connect_bunnies(8, "sussybaka")
    print("Downloading map...")
    m = download_map(bots[0])
    print("Generating block queue...")
    # queue = make_queue(m, lambda i, b: b not in [0, 42] and i%512 != 511)
    queue = []
    for x in range(512):
        for y in range(512):
            if m[x, 63, y] != 2:
                queue.append((x, 63, y))
    print("Causing chaos...")
    await do_blockqueue(bots, queue, 2)

if __name__ == "__main__":
    asyncio.run(wipemap())
