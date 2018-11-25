""" carve file system

Carve NXSB:
- Iterate all blocks and search for magic bytes
    -> parse from 1.

Carve APSB:
- Iterate all block and search for magic bytes
    -> parse from 6.

Carve nodes:
- Iterate all block and search for patterns
    -> parse from 9.
"""
import logging

from kaitaistruct import KaitaiStream, BytesIO

from . import libapfs, parse, checksum, block

LOGGER = logging.getLogger(__name__)


def nxsb(image_io, blocksize):
    return carve(image_io, blocksize, 'nxsb', match_magic_func(b'NXSB'), parse.parse_nxsb)


def apsb(image_io, blocksize):
    return carve(image_io, blocksize, 'apsb', match_magic_func(b'APSB'), parse.parse_apsb)


def nodes(image_io, blocksize):
    return carve(image_io, blocksize, 'nodes', match_nodes, parse.parse_node)


def match_magic_func(magic):

    def match_magic(data):
        return data[32:36] == magic and checksum.check_checksum(data)

    return match_magic


def match_nodes(data):
    obj_type = int.from_bytes(data[24:26], byteorder='little')
    subtype = int.from_bytes(data[28:30], byteorder='little')

    return (obj_type in (2, 3)) and subtype == 14 and checksum.check_checksum(data)


def carve(image_io, blocksize, name, magic, get_file_entries_func):
    """ parse image and print files """

    # get file entries
    apfs = libapfs.Apfs(KaitaiStream(image_io))
    file_entries = dict()
    i = 0
    while True:
        data = block.get_block(i, blocksize, image_io)
        if not data:
            break
        elif magic(data):
            LOGGER.info('Found %s in block %i', name, i)
            try:
                obj = apfs.Obj(KaitaiStream(BytesIO(data)), apfs, apfs)
                carved_file_entries = get_file_entries_func(obj, apfs)
                for xid in carved_file_entries:
                    file_entries.setdefault(xid, dict())
                    for volume in carved_file_entries[xid]:
                        file_entries[xid].setdefault(volume, list())
                        file_entries[xid][volume] += carved_file_entries[xid][volume]
            except Exception as err:
                LOGGER.info(err)
        i += 1

    LOGGER.debug(file_entries)
    return file_entries
