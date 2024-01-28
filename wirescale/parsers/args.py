#!/usr/bin/env python3
# encoding:utf-8


from functools import cached_property
from ipaddress import IPv4Address

from websockets.sync.client import ClientConnection
from websockets.sync.server import ServerConnection

from wirescale.parsers.parsers import top_parser
from wirescale.vpn import TSManager


class ConnectionPair:
    def __init__(self, caller: IPv4Address, receiver: IPv4Address):
        self.caller = caller
        self.receiver = receiver
        self.caller_name, self.receiver_name
        self.tcp_socket: ClientConnection | ServerConnection = None
        self.unix_socket: ServerConnection = None

    @cached_property
    def my_ip(self) -> IPv4Address:
        return TSManager.my_ip()

    @cached_property
    def my_name(self) -> str:
        return TSManager.my_name()

    @cached_property
    def peer_ip(self) -> IPv4Address:
        return self.caller if self.running_in_remote else self.receiver

    @cached_property
    def peer_name(self) -> str:
        return TSManager.peer_name(self.peer_ip)

    @cached_property
    def caller_name(self) -> str:
        return self.peer_name if self.running_in_remote else self.my_name

    @cached_property
    def receiver_name(self) -> str:
        return self.my_name if self.running_in_remote else self.peer_name

    @cached_property
    def running_in_remote(self) -> bool:
        return self.receiver == self.my_ip

    @property
    def remote_socket(self):
        return self.tcp_socket

    @property
    def local_socket(self):
        return self.unix_socket

    @cached_property
    def websockets(self):
        return (self.remote_socket,) if self.running_in_remote else (self.remote_socket, self.local_socket)


class ARGS:
    AUTOREMOVE: bool = None
    CONFIGFILE: str = None
    DAEMON: bool = None
    INTERFACE: str = None
    PAIR: ConnectionPair = None
    START: bool = None
    STOP: bool = None
    SUFFIX: bool = None
    UPGRADE: bool = None


def parse_args():
    args = vars(top_parser.parse_args())
    ARGS.DAEMON = args.get('opt') == 'daemon'
    ARGS.UPGRADE = args.get('opt') == 'upgrade'
    if ARGS.DAEMON:
        ARGS.START = args.get('start')
        ARGS.STOP = args.get('stop')
        ARGS.SUFFIX = not args.get('no_suffix')
    elif ARGS.UPGRADE:
        ARGS.AUTOREMOVE = not args.get('disable_autoremove')
        peer_ip = args.get('peer')
        ARGS.PAIR = ConnectionPair(caller=TSManager.my_ip(), receiver=peer_ip)
        ARGS.CONFIGFILE = args.get('config') if args.get('config') is not None and args.get('config').split() else f'/etc/wirescale/{ARGS.PAIR.peer_name}.conf'
        ARGS.INTERFACE = args.get('interface') or ARGS.PAIR.peer_name
