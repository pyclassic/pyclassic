import re
from dataclasses import dataclass

######################################################################
class PyClassicError(Exception): pass

_packet_fmt_types = {
    "BYTE": 1, "SBYTE": 1, "SHORT": 2, "STRING": 64, "ARRAY": 1024
}

_cc_api = "http://www.classicube.net/api"
######################################################################

enc = lambda n: n.encode('us-ascii')
encstr = lambda n: enc(n) + bytes([0x20 for x in range(64-len(enc(n)))])
decstr = lambda n: n[:64].decode('us-ascii').strip()
decint = lambda n, s = True: int.from_bytes(n, byteorder='big',
                                     signed=s)
encint = lambda n, l = 2: n.to_bytes(l, 'big')
api_url = lambda n: _cc_api + n
def sanitize(msg):
    return re.sub('\&.', '', msg)
def contains_all(needle, haystack):
    for el in needle:
        if el not in haystack:
            return False
        elif needle[el] != haystack[el]:
            return False
    return True

# BYTE, SBYTE, SHORT, ARRAY, STRING
@dataclass
class PacketFormat:
    pid: int
    name: str
    content: list[str]

    def __len__(self):
        return sum(_packet_fmt_types[x] for x in self.content)
    def __bool__(self):
        return True

def find_packet_id(t):
    for c, i in enumerate(packet_id_s):
        if t == packet_id_s[i].name:
            return packet_id_s[i].pid
    return -1
def encode_packet(fmt, *args):
    if len(args) != len(fmt.content): return

    packet = b''
    for f, a in zip(fmt.content, args):
        if   f == "BYTE":   packet += bytes([a & 0xff])
        elif f == "SBYTE":  packet += encint(a, 1)
        elif f == "SHORT":  packet += encint(a&0xffff, 2)
        elif f == "STRING": packet += encstr(a[:64])
        elif f == "ARRAY":  packet += a[:1024]
    return packet
def decode_packet(fmt, packet: bytes):
    if len(fmt) != len(packet): return

    args = []
    for f in fmt.content:
        if   f == "BYTE":   args.append(packet[0])
        elif f == "SBYTE":  args.append(decint(packet[:1]))
        elif f == "SHORT":  args.append(decint(packet[:2]))
        elif f == "STRING": args.append(decstr(packet[:64]))
        elif f == "ARRAY":  args.append(packet[:1024])
        packet = packet[_packet_fmt_types[f]:]

    return args

packet_id_s = {
    0x0: PacketFormat(0, "AUTH", ['BYTE', 'STRING', 'STRING', 'BYTE']),
    0x1: PacketFormat(1, "PING", []),
    0x2: PacketFormat(2, "LEVEL_INIT", []),
    0x3: PacketFormat(3, "LEVEL_DATA_CHUNK", ['SHORT', 'ARRAY', 'BYTE']),
    0x4: PacketFormat(4, "LEVEL_FINALIZE", ['SHORT'] * 3),
    0x6: PacketFormat(6, "SET_BLOCK", ['SHORT']*3 + ['BYTE']),
    0x7: PacketFormat(7, "SPAWN", ['SBYTE', 'STRING'] + \
                       ['SHORT']*3 + ['BYTE']*2),
    0x8: PacketFormat(8, "TELEPORT", ['SBYTE'] + ['SHORT']*3 + ['BYTE']*2),
    0x9: PacketFormat(9, "POS_ORI", ['SBYTE']*4 + ['BYTE']*2),
    0xa: PacketFormat(10, "POS", ['SBYTE']*4),
    0xb: PacketFormat(11, "ORI", ['SBYTE'] + ['BYTE']*2),
    0xc: PacketFormat(12, "DESPAWN", ['BYTE']),
    0xd: PacketFormat(13, "MESSAGE", ['SBYTE', 'STRING']),
    0xe: PacketFormat(14, "DISCONNECT", ['STRING']),
    0xf: PacketFormat(15, "USERTYPE", ['BYTE'])
}
packet_id_c = {
    0x0: PacketFormat(1, "AUTH", ['BYTE', 'STRING', 'STRING', 'BYTE']),
    0x5: PacketFormat(5, "SET_BLOCK", ['SHORT']*3 + ['BYTE']*2),
    0x8: PacketFormat(8, "POS_ORI", ['BYTE'] + ['SHORT']*3 + ['BYTE']*2),
    0xd: PacketFormat(13, "MESSAGE", ['BYTE', 'STRING'])
}
