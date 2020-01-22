import termcolor

def hexformat(i, pos):
    pos = hex(pos)[2:]

    '''
    if i % 16 == 0:
        print('')
    '''
    if i % 32 == 0:
        print(termcolor.colored('\n{}:'.format(pos.zfill(8)),
                                'white'), end='')
    elif i % 4 == 0:
        print(' ', end='')
    return i + 1

# PoC, refactor
def view_slackobject(image_io, blocksize, slackobjects):
    for slackobj in slackobjects:
        start_block = slackobj.block_id * blocksize
        start_slack = start_block + blocksize - len(slackobj.slack_bytes)
        obj_size = abs(start_block - start_slack)

        print('\nType: {} in block {}:'.format(slackobj.slack_type.name, slackobj.block_id))

        image_io.seek(start_block)
        i = 1

        print(termcolor.colored('{}:'.format(hex(start_block)[2:].zfill(8)),
                                'white'), end='')
        for obj_byte in image_io.read(obj_size):
            print(termcolor.colored(
                hex(obj_byte)[2:].zfill(2),
                'blue'), end='')
            i = hexformat(i, start_block+i)
        for obj_byte in image_io.read(len(slackobj.slack_bytes)):
            if obj_byte == 0x0:
                print(termcolor.RESET + '00', end='')
            else:
                print(termcolor.colored(
                    hex(obj_byte)[2:].zfill(2),
                    'white', 'on_red'), end='')

            if i == blocksize:
                print('')
                break
            i = hexformat(i, start_block+i)

'''
def print_ascii():
    for byte in slackobj.slack_bytes:
        if byte != 0x00:
            print('Found non-empty slackspace.')
            print('Type: {} in block {}.'.format(type, slackobj.block_id))
            ascii = '??'
            if str(byte) in string.printable:
                ascii = str(byte)
                print('{} - value: {}'.format(ascii, hex(byte)))
'''