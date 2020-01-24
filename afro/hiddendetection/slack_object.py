import enum

class SlackType(enum.Enum):
    NXSB = enum.auto()
    NXSB_OMAP = enum.auto()
    APSB = enum.auto()
    APSB_OMAP = enum.auto()

    def omap(self):
        if self == SlackType.NXSB:
            return SlackType.NXSB_OMAP
        elif self == SlackType.APSB:
            return SlackType.APSB_OMAP
        else:
            raise ValueError('No superblock supplied.')

class SlackObject():
    def __init__(self, slack_type: SlackType, slack_bytes, block_id):
        self.slack_type = slack_type
        self.slack_bytes = slack_bytes
        self.block_id = block_id