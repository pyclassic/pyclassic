#!/usr/bin/env python3
import pyclassic, pyclassic.queue, config
from pyclassic.utils import sanitize

player = pyclassic.PyClassic(pyclassic.ClassiCubeAuth(config.username,
                                                      config.password))

@player.event
async def on_level_finalize(ctx, *_):
    ctx.log("Ready!")
    await ctx.message("[#] Ready!")

@player.event
async def on_message(ctx, pid, message):
    msg = sanitize(message.split(':',maxsplit=1)[-1].strip())

    if msg == "hi bot":
        await ctx.message("Hello, World!")

player.run(name = "Matthilde's Private Server")
