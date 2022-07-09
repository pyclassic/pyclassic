"""
PyClassic - Minecraft Classic Protocol implementation in Python.

This is the main classes of the module.
"""
# PyClassic - Minecraft Classic client
import socket, json, requests, time, asyncio, re
import pyclassic
import pyclassic.queue, pyclassic.auth, pyclassic.map, pyclassic.client
__version__ = "dev-2022"
PYCLASSIC_VERSION = __version__ 

from .pyclassic import PyClassic

__all__ = ["PyClassic"]
