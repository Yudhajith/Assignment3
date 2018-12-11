import logging
import sys
import json  
import collections  
import argparse
import asyncio
import time
from uuid import uuid1

from src.fba_consensus import Consensus
from src.network import (
    BaseServer,
    LocalTransport,
    Message,
    Node,
    Quorum,
)
from src.util import (
    log,
)

MESSAGES = []

async def check_message(node):
    global MESSAGE_COUNT

    if check_message.is_running:
        return

    check_message.is_running = True
    for MESSAGE in MESSAGES:
        found = list()
            
        log.main.info('%s: checking if input was stored: %s', node.name, MESSAGE)
        while len(found) < len(servers):
            for node_name, server in servers.items():
                if node_name in found:
                    continue

                storage = server.consensus.storage

                is_exists = storage.is_exists(MESSAGE)
                is_exists = True
                if is_exists:
                    log.main.critical(
                        '> %s: is_exists=%s state=%s ballot=%s',
                        node_name,
                        is_exists,
                        server.consensus.ballot.state,
                        '', 
                    )
                    found.append(node_name)
                await asyncio.sleep(0.01)
    check_message.is_running = False
    return  

check_message.is_running = False


class Server(BaseServer):
    consensus = None
    node = None

    def __init__(self, node, consensus, *a, **kw):
        assert isinstance(node, Node)
        assert isinstance(consensus, Consensus)

        super(Server, self).__init__(*a, **kw)

        self.consensus = consensus
        self.node = node


    def __repr__(self):
        return '<Server: node=%(node)s consensus=%(consensus)s>' % self.__dict__

    def message_receive(self, data_list):
        super(Server, self).message_receive(data_list)

        for i in data_list:
            log.server.debug('%s: hand over to consensus: %s', self.name, i)
            self.consensus.receive(i)

        return


class TestConsensus(Consensus):
    def reached_all_confirm(self, ballot_message):
        asyncio.ensure_future(check_message(self.node))
        return


NodeConfig = collections.namedtuple(
    'NodeConfig',
    (
        'name',
        'endpoint',
        'threshold',
    ),
)


def check_threshold(v):
    v = int(v)
    if v < 1 or v > 100:
        raise argparse.ArgumentTypeError(
            '%d is invalid, must be 0 < trs <= 100' % v,
        )

    return v


parser = argparse.ArgumentParser()
parser.add_argument('-s', dest='silent', action='store_true', help='turn off debug messages')
parser.add_argument('-trs', type=check_threshold, default=80, help='threshold; 0 < trs <= 100')
parser.add_argument('-nodes', nargs='+', type=int, default=[3000, 3001, 3002, 3003], help='endpoints of nodes as list -nodes 3000 3001 3002 3003')

if __name__ == '__main__':
    log_level = logging.DEBUG
    if '-s' in sys.argv[1:]:
        log_level = logging.INFO
    
    log.set_level(log_level)
    
    loop = asyncio.get_event_loop()

    options = parser.parse_args()
    log.main.debug('options: %s', options)

    name = 'client%d' %options.nodes[0]
    endpoint = 'http://localhost:%d' %options.nodes[0]
    client0_config = NodeConfig(name, endpoint, None)
    transport = LocalTransport(client0_config.name, client0_config.endpoint, loop)
    client0_node = Node(client0_config.name, client0_config.endpoint, None)    
    
    nodes_config = dict()
    for i in options.nodes:
        name = 'server%d' % i
        endpoint = 'http://localhost:%d' % i
        nodes_config[name] = NodeConfig(name, endpoint, options.trs)

    log.main.debug('node configs are created: %s', nodes_config)

    quorums = dict()
    for name, config in nodes_config.items():
        validator_configs = filter(lambda x: x.name != name, nodes_config.values())

        quorums[name] = Quorum(
            config.threshold,
            list(map(lambda x: Node(x.name, x.endpoint, None), validator_configs)),
        )
    log.main.debug('quorums slices are created: %s', quorums)

    nodes = dict()
    transports = dict()
    consensuses = dict()
    servers = dict()

    for name, config in nodes_config.items():
        servers[name] = Server(nodes[name], consensuses[name], name, transport=transports[name])
        log.main.debug('servers are created: %s', servers)
        
        nodes[name] = Node(name, config.endpoint, quorums[name])
        log.main.debug('nodes are created: %s', nodes)

        consensuses[name] = TestConsensus(nodes[name], quorums[name], transports[name])
        log.main.debug('consensuses are created: %s', consensuses)

        transports[name] = LocalTransport(name, config.endpoint, loop)
        log.main.debug('transports are created: %s', transports)
        
        

    for server in servers.values():
        server.start()

    data = ['alice:$30','bob:$60','alice:$40','bob:$50','alice:$50','bob:$40']

    for message in data:
        MESSAGE = Message.new(message)
        MESSAGES.append(MESSAGE)
       
        transport.send(client0_node.endpoint, MESSAGE.serialize(client0_node))
        log.main.info('send message %s -> node0: %s', client0_node.name, MESSAGE)

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        log.main.debug('exit')
        sys.exit(1)
    finally:
        loop.close()
