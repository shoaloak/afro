import io

class OffsetBufferedReader(io.BufferedReader):
    """docstring for OffsetBytesIO"""

    def __init__(self, raw, offset):
        super().__init__(raw)
        self.offset = offset
        self.seek(0)

    def seek(self, offset, whence=0):
        if whence == 0:
            super().seek(self.offset + offset, whence)
        else:
            super().seek(offset, whence)