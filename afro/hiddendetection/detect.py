import logging
import sys

from kaitaistruct import KaitaiStream, BytesIO

from .. import libapfs, block, log, offsetbufferedreader, carve, process, parse
from . import slack_object, hexdump

LOGGER = logging.getLogger(__name__)


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

    #nxsb_slacks = [x for x in slacks_found if x.slack_type is SlackType.NXSB]
    #apsb_slacks = [x for x in slacks_found if x.slack_type is SlackType.APSB]
    return check_slacks(slacks_found)


def inode(file_entries, apfs):
    """ Search for nonzero data in j_inode_valt_t pad1 and pad2 """

    extentmap = dict()
    itemmap = dict()

    # xid = The identifier of the most recent transaction that this object was modified in ??
    for xid in file_entries:

        extentmap[xid] = dict()
        itemmap[xid] = dict()

        for volume in file_entries[xid]:

            extentmap[xid][volume] = dict()
            itemmap[xid][volume] = dict()

            for file_entry in file_entries[xid][volume]:
                #File extent (fext) entries contain information about the position and size of file content.
                if file_entry.j_key_t.obj_type == apfs.JObjTypes.apfs_type_file_extent and \
                        isinstance(file_entry.val, libapfs.Apfs.JExtentValT):

                    extentmap[xid][volume].setdefault(file_entry.j_key_t.obj_id, list())
                    extentmap[xid][volume][file_entry.j_key_t.obj_id].append({
                        'start': file_entry.val.phys_block_num,
                        'length': file_entry.val.len,
                        'offset': file_entry.key.offset
                    })

                # inode
                elif file_entry.j_key_t.obj_type == apfs.JObjTypes.apfs_type_inode and \
                        isinstance(file_entry.val, libapfs.Apfs.JInodeValT):

                    item = process.Item()
                    for index, xf_h in enumerate(file_entry.val.xfields.xf_data):
                        if xf_h.x_type == apfs.InoExtType.ino_ext_type_name:
                            item.name = file_entry.val.xfields.xf[index].name
                        elif xf_h.x_type == apfs.InoExtType.ino_ext_type_dstream:
                            item.file_size = file_entry.val.xfields.xf[index].size
                    if item.name is None:
                        raise Exception("name not found")
                    item.node_id = file_entry.j_key_t.obj_id
                    item.parent = file_entry.val.parent_id
                    item.private_id = file_entry.val.private_id
                    item.creationtime = file_entry.val.change_time
                    item.accesstime = file_entry.val.access_time
                    item.modificationtime = file_entry.val.mod_time

                    item.pad1 = file_entry.val.pad1
                    item.pad2 = file_entry.val.pad2

                    if file_entry.val.xfields.xf_num_exts == 1:
                        item.type = 'folder'
                    else:
                        item.type = 'file'

                    itemmap[xid][volume][file_entry.j_key_t.obj_id] = item

    candidates = []

    for xid in file_entries:
        for volume in file_entries[xid]:
            for item in sorted(itemmap[xid][volume].values(), key=lambda item: item.parent):
                if item.pad1 != 0 or item.pad2 != 0:
                    candidate = {
                        'xid': xid,
                        'volume': volume,
                        'item': item,
                    }

                    candidates.append(candidate)

    if len(candidates) != 0:
        LOGGER.info("nonzero pads detected!")
        for candidate in candidates:
            suspect = "xid:{}, volume:{}, item:{}".format(candidate['xid'],
                                                          candidate['volume'],
                                                          candidate['item'])
            LOGGER.info(suspect)
    else:
        LOGGER.info('No data detected within inodepads!')

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

    try:
        with open(args.image, 'rb') as image_io:
            image_io = offsetbufferedreader.OffsetBufferedReader(image_io, args.offset * 512)

            apfs = libapfs.Apfs(KaitaiStream(image_io))
            block_size = apfs.block_size
            image_io.seek(0)

            if hiding_technique == 'slack':
                non_empty_slacks = slack(image_io, block_size)
                hexdump.view_slackobject(image_io, block_size, non_empty_slacks, args)
            elif hiding_technique == 'inode_pad':
                file_entries = carve.carve(image_io, block_size, 'apsb', carve.match_magic_func(b'APSB'), parse.parse_apsb)
                inode(file_entries, apfs)
                #TODO extend inode() that it supports multiple hiding techniques
            else:
                print('Detection method unknown')
                sys.exit(2)
    except AttributeError:
        print(AttributeError)
        print('Maybe wrong offset?')
    except FileNotFoundError:
        print('Could not find file: ' + args.image)
