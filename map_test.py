#!/usr/bin/env python3
import pyclassic, pyclassic.map, config, asyncio
from pyclassic.utils import sanitize

v1, v2, selpid, in_mem, todocmd = None, None, None, None, None

player = pyclassic.PyClassic(pyclassic.ClassiCubeAuth(
    config.username, config.password))

@player.event
async def on_level_finalize(ctx, *args):
    await ctx.message("ayo the pizza here")

@player.event
async def on_set_block(ctx, x, y, z, bid):
    global v1, v2, in_mem, todocmd
    if not todocmd: return

    if todocmd == "copy":
        if not v1:
            v1 = (x, y, z)
            await ctx.message(f"#1 {v1}")
        elif not v2:
            v2 = (x, y, z)
            await ctx.message(f"#2 {v2}")
            in_mem = ctx.map[v1:v2]
            v1, v2 = None, None
            await ctx.message(f"Saved!")
            todocmd = None
    elif todocmd == "paste":
        if not v1:
            print("eeee")
            todocmd = None

            for idx, block in enumerate(in_mem.blocks):
                xx, yy, zz = in_mem.getpos(idx)
                await ctx.set_block(x+xx,y+yy,z+zz, block)

            await ctx.message("Built!")

@player.event
async def on_message(ctx, pid, message):
    global selpid, todocmd
    msg = message.split(':', maxsplit=1)[-1].strip()
    msg = sanitize(msg).split()

    if msg == ['hi', 'bot']:
        await ctx.message("Hi")
    elif msg == ['do', '1984']:
        await ctx.message("removing all bookshelves...")
        # Look for bookshelves
        for idx in (i for i, _ in enumerate(ctx.map.blocks) if _ == 47):
            await asyncio.sleep(0.1)
            await ctx.set_block(*ctx.map.getpos(idx), 0)
        await ctx.message("now this is literally 1984")
    elif msg[0] in ['copy', 'paste']:
        await ctx.message("Select where you wanna do that")
        selpid = pid
        todocmd = msg[0]
        v1, v2 = None, None
    elif msg[0] == "getblock" and len(msg) == 4:
        v = [int(x) for x in msg[1:]]
        await ctx.message(f"Block #{ctx.get_block(*v)}")

player.run(name = "Matthilde's Private Server")
