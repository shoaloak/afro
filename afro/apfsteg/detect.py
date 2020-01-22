import logging
import sys

from kaitaistruct import KaitaiStream, BytesIO

from .. import libapfs, block, log, offsetbufferedreader, carve
from . import slack_object, hexdump

def find_omap(superblock):
    """ get entries of superblock """
    target = None

    if hasattr(superblock.body, 'apfs_magic'):
        target = superblock.body.apfs_omap_oid.target
    elif hasattr(superblock.body, 'nx_magic'):
        target = superblock.body.nx_omap_oid.target

    if target.hdr.o_type == 11:
        return target
    return None

def iterate_superblocks(apfs, image_io, blocksize, magic, slacks_found, slack_type: slack_object.SlackType):
    i = 0
    while True:
        data = block.get_block(i, blocksize, image_io)
        if not data:
            break
        elif magic(data):
            try:
                obj = apfs.Obj(KaitaiStream(BytesIO(data)), apfs, apfs)

                # find superblock slackspace (usually 3112 bytes, but can vary?)
                slacks_found.append(slack_object.SlackObject(slack_type, obj.body.cstm_slack, i))

                # find container omap
                omap = find_omap(obj)
                if omap is None:
                    i += 1
                    continue

                slacks_found.append(slack_object.SlackObject(slack_type.omap, omap.body.cstm_slack, i))

            except Exception as err:
                print(err)
        i += 1

def check_slacks(slackobjects):
    non_empty = []

    for slackobj in slackobjects:
        if set(slackobj.slack_bytes) != {0}:
            non_empty.append(slackobj)
    
    return non_empty
        

def slack(image_io, blocksize):
    """ Find suspicious slackspace in NXSB, APSB, and their omaps """

    apfs = libapfs.Apfs(KaitaiStream(image_io))
    slacks_found = []

    # NXSB slackspace, usually 3488 bytes but can vary (?)
    magic = carve.match_magic_func(b'NXSB')
    iterate_superblocks(apfs, image_io, blocksize, magic, slacks_found, slack_object.SlackType.NXSB)

    # APSB slackspace, usually 3112 bytes but can vary (?)
    image_io.seek(0)
    magic = carve.match_magic_func(b'APSB')
    iterate_superblocks(apfs, image_io, blocksize, magic, slacks_found, slack_object.SlackType.APSB)

    non_empty_slacks = check_slacks(slacks_found)
    #nxsb_slacks = [x for x in slacks_found if x.slack_type is SlackType.NXSB]
    #apsb_slacks = [x for x in slacks_found if x.slack_type is SlackType.APSB]
    
    hexdump.view_slackobject(image_io, blocksize, non_empty_slacks)


def inodepad(file_entries, apfs, blocksize, file_io):
    """ Search for nonzero data in j_inode_valt_t pad1 and pad2 """
    #TODO

    
def detect(args):
    """ Detect steganography in APFS """

    if args.log:
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.log)

        log.set_logging(args.log)

    hiding_technique = args.detect
    if not hiding_technique:
        print('No detection method selected, using slack detection.')
        hiding_technique = 'slack'

    with open(args.image, 'rb') as image_io:
        image_io = offsetbufferedreader.OffsetBufferedReader(image_io, args.offset * 512)

        apfs = libapfs.Apfs(KaitaiStream(image_io))
        block_size = apfs.block_size
        image_io.seek(0)

        if hiding_technique == 'slack':
            slack(image_io, block_size)
        elif hiding_technique == 'inode_pad':
            #TODO
            inodepad(None, apfs, block_size, image_io)
        else:
            print('Detection method unknown')
            sys.exit(2)
