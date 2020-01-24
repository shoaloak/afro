class Color:
    END = '\33[0m'
    BG_RED = '\33[41m'
    BG_BLUE = '\33[44m'
    FG_WHITE = '\33[37m'
    FG_BLACK = '\33[30m'

def output(display, _s, _bg, _fg):
    if display is 'print':
        return _bg + _fg + _s + Color.END

    return _s

def hexformat(i, pos, display):
    if i % 32 == 0:
        _s = '\n{}:'.format(byte2hex(pos, 8))
        return output(display, _s, Color.END, Color.END)
    elif i % 4 == 0:
        return ' '
    return ''

def byte2hex(_b, fill):
    return hex(_b)[2:].upper().zfill(fill)

def view_slackobject(image_io, blocksize, slackobjects, args):
    display = args.print
    buf = ['Non-empty slack found, ',
           'if printed, blue shows datastructure, red non-empty slack.\n\n']

    for slackobj in slackobjects:
        start_block = slackobj.block_id * blocksize
        start_slack = start_block + blocksize - len(slackobj.slack_bytes)
        obj_size = abs(start_block - start_slack)

        _s = 'Type: {} in block {}:\n'.format(slackobj.slack_type.name, slackobj.block_id)
        buf.append(output(display, _s, Color.END, Color.END))

        image_io.seek(start_block)
        i = 1

        _s = '{}:'.format(byte2hex(start_block, 8))
        buf.append(output(display, _s, Color.END, Color.END))

        # datastructure
        for obj_byte in image_io.read(obj_size):
            _s = byte2hex(obj_byte, 2)
            buf.append(output(display, _s, Color.BG_BLUE, Color.FG_WHITE))
            buf.append(hexformat(i, start_block+i, display))
            i += 1
        
        # slack
        for obj_byte in image_io.read(len(slackobj.slack_bytes)):
            if obj_byte == 0x0:
                buf.append(output(display, '00', Color.END, Color.END))
            else:
                _s = byte2hex(obj_byte, 2)
                buf.append(output(display, _s, Color.BG_RED, Color.FG_WHITE))
            if i == blocksize:
                buf.append('\n\n')
                break
            buf.append(hexformat(i, start_block+i, display))
            i += 1

    # remove newlines
    del buf[-1]

    if display is 'print':
        print(''.join(buf))
    else:
        with open(args.image + '_slack.hex', 'w') as _f:
            _f.write(''.join(buf))

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