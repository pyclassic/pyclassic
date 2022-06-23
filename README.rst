=========
PyClassic
=========

**PyClassic** is a Python implementation of the Minecraft Classic Protocol with
CPE (Classic Protcol Extension). It implements a block queue, an event system,
map loader, and much more.

Features
--------

Currently, here are the features

 - Minecraft Classic Protocol fully implemented, with map download and parsing
   support.
 - Classic Protocol Extension (CPE) partially implemented such as EXT_INFO.
 - Map object which can be sliced and saved/loaded with a simple custom map
   format.
 - Threaded queue system that can work along with the event system.
 - Multibot support for faster building in rate-limited servers (lol)
 - ClassiCube authentication support with usage of API to retrieve the server
   list and join by the server name or other available info.
 - discord.py-like event system with some useful stuff going on under the hood
    - automatic map download, keeping track of changes
    - detection of player join/leave and keep a list of players
    - responsive to /summon


