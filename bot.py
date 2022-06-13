#!/usr/bin/env python3
import config
import pyclassic, re, time, asyncio
from pyclassic import sanitize

# server_name = "Matthilde's Private Server"
server_name = "+cope's experimental server"

auth = pyclassic.ClassiCubeAuth(config.username, config.password)
player = pyclassic.PyClassic(auth)

@player.event
async def on_connect(ctx):
    ctx.log("Connected to the server!")

@player.event
async def on_message(ctx, pid, message):
    username = "user"
    if pid in ctx.players:
        username = ctx.players[pid].name
    command = sanitize(message.split(':', maxsplit=1)[-1].strip())
    cmds = command.split()
    
    if command == "hi bot":
        ctx.log("Got a message!")
        await ctx.message(f"Hello, {username}")
    elif len(cmds) == 3 and cmds[0] == "cube":
        size, bid = cmds[1:]
        s = ctx.players[-1]
        ctx.log("Gotta build a cube")
        await ctx.message("Got it!")

        size = int(size)
        for x in range(size):
            x += s.x//32
            for y in range(size):
                y += s.y//32
                for z in range(size):
                    z += s.z//32
                    await ctx.set_block(x, y, z, int(bid))

        print("I am done.")

@player.event
async def on_move(ctx, t, pid, *args):
    return
    p = ctx.players[pid]
    username = p.name
    await ctx.message(f"{t} {p.x//32} {p.y//32} {p.z//32}")
    
player.run(name = server_name)
