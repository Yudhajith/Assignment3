import colorlog
import enum
import logging
import sys
import pickledb



class Log:
    main = logging.getLogger('MAIN')
    transport = logging.getLogger('TRANSPORT')
    server = logging.getLogger('SERVER')
    consensus = logging.getLogger('CONSENSUS')
    ballot = logging.getLogger('BALLOT')
    storage = logging.getLogger('STORAGE')

    log_format = '%(msecs)f - %(name)s - [%(filename)s:%(lineno)d] - %(message)s'
    if sys.stdout.isatty():
        colorlog_format = '%(log_color)s' + log_format
    else:
        colorlog_format = log_format

    def __init__(self):
        logging.basicConfig(
            format='%(msecs)f - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
        )

        if sys.stdout.isatty():
            log_handler = colorlog.StreamHandler()
            log_handler.setFormatter(
                colorlog.ColoredFormatter(
                    self.colorlog_format,
                    reset=True,
                    log_colors={
                        'DEBUG': 'white',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    },
                ),
            )
            logging.root.handlers = [log_handler]

    def set_level(self, level):
        self.main.setLevel(level)
        self.server.setLevel(level)
        self.server.setLevel(level)
        self.consensus.setLevel(level)
        self.ballot.setLevel(level)
        self.storage.setLevel(level)

        return


log = Log()


class BaseEnum(enum.Enum):
    @classmethod
    def from_value(cls, value):
        for i in cls:
            if i.value == value:
                return i

        return None

    @classmethod
    def from_name(cls, name):
        return getattr(cls, name)



class Message():
    
    def __init__(self, sock, address = None, port = None):
    
        self.port = port
        self.sock = sock
        self.address = (address, self.port)

    def sendMessage(self, message):
        try:
            # Send data
            print ('sending "%s"' % message)
            sent = self.sock.sendto(str.encode(message), self.address)
            return sent
        except Exception as e:
            print ('Sending error {}'.format(e))

    def receiveMessage(self):
        # Receive response
        data, address = self.sock.recvfrom(4096)
        return data.decode()


class PickleDB():

    def __init__(self, port):
        self.db = pickledb.load('assignment3_%s.db' %port, False)

    def setValue(self, key, value):
        self.db.set(key, value)
    
    def getValue(self, key):
        return self.db.get(key)
    
    def is_exists(self, key):
        return self.db.exists(key)
    
    def appendValue(self, data):
        key, value = data.split(':$')
        val = self.getValue(key)
        if val:
            value = int(val) + int(value)
        self.setValue(key, value)
    
    def dump(self):
        self.db.dump()


