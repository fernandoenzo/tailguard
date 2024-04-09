#!/usr/bin/env python3
# encoding:utf-8


import json
import sys
from enum import IntEnum, StrEnum, auto, unique
from subprocess import CompletedProcess
from threading import get_ident
from typing import TYPE_CHECKING

from wirescale.communications.common import CONNECTION_PAIRS

if TYPE_CHECKING:
    from wirescale.vpn.wgconfig import WGConfig


@unique
class MessageFields(StrEnum):
    ADDRESSES = auto()
    AUTOREMOVE = auto()
    CODE = auto()
    CONFIG = auto()
    ERROR_CODE = auto()
    ERROR_MESSAGE = auto()
    HAS_PSK = auto()
    INTERFACE = auto()
    MESSAGE = auto()
    PEER_IP = auto()
    PSK = auto()
    PUBKEY = auto()
    RECOVER = auto()
    REMOTE_PUBKEY = auto()
    START_TIME = auto()
    SUFFIX = auto()


class ActionCodes(IntEnum):
    ACK = auto()
    INFO = auto()
    STOP = auto()
    SUCCESS = auto()
    UPGRADE = auto()
    UPGRADE_RESPONSE = auto()
    UPGRADE_GO = auto()


class ErrorCodes(IntEnum):
    CLOSED = auto()
    CONFIG_PATH_ERROR = auto()
    GENERIC = auto()
    FINAL_ERROR = auto()
    INTERFACE_EXISTS = auto()


class UnixMessages:
    STOP_MESSAGE = {MessageFields.CODE: ActionCodes.STOP, MessageFields.ERROR_CODE: None}

    @staticmethod
    def build_upgrade_option(args) -> dict:
        res = {
            MessageFields.CODE: ActionCodes.UPGRADE,
            MessageFields.ERROR_CODE: None,
            MessageFields.AUTOREMOVE: args.AUTOREMOVE,
            MessageFields.CONFIG: args.CONFIGFILE,
            MessageFields.INTERFACE: args.INTERFACE,
            MessageFields.PEER_IP: str(args.PAIR.peer_ip),
            MessageFields.SUFFIX: args.SUFFIX,
        }
        return res

    @staticmethod
    def build_upgrade_result(wgquick: CompletedProcess[str], interface: str) -> dict:
        res = {}
        if wgquick.returncode == 0:
            res[MessageFields.CODE] = ActionCodes.SUCCESS
            res[MessageFields.ERROR_CODE] = None
            res[MessageFields.INTERFACE] = interface
        else:
            res[MessageFields.CODE] = None
            res[MessageFields.ERROR_CODE] = ErrorCodes.FINAL_ERROR
            res[MessageFields.ERROR_MESSAGE] = wgquick.stdout.strip()
        return res


class TCPMessages:

    @staticmethod
    def build_upgrade(wgconfig: 'WGConfig') -> dict:
        res = {
            MessageFields.CODE: ActionCodes.UPGRADE,
            MessageFields.ERROR_CODE: None,
            MessageFields.ADDRESSES: [str(ip) for ip in wgconfig.addresses],
            MessageFields.PUBKEY: wgconfig.public_key,
            MessageFields.REMOTE_PUBKEY: wgconfig.remote_pubkey,
            MessageFields.HAS_PSK: wgconfig.has_psk,
            MessageFields.PSK: wgconfig.psk if not wgconfig.has_psk else None,
            MessageFields.START_TIME: wgconfig.start_time,
        }
        return res

    @staticmethod
    def build_upgrade_response(wgconfig) -> dict:
        res = {
            MessageFields.CODE: ActionCodes.UPGRADE_RESPONSE,
            MessageFields.ERROR_CODE: None,
            MessageFields.ADDRESSES: [str(ip) for ip in wgconfig.addresses],
            MessageFields.PUBKEY: wgconfig.public_key,
        }
        return res

    @staticmethod
    def build_upgrade_go() -> dict:
        res = {
            MessageFields.CODE: ActionCodes.UPGRADE_GO,
            MessageFields.ERROR_CODE: None,
        }
        return res


class Messages:
    CHECKING_ENDPOINT = "Checking that an endpoint is available for peer '{peer_name}' ({peer_ip})..."
    CONNECTING_UNIX = 'Connecting to local UNIX socket...'
    CONNECTED_UNIX = 'Connection to local UNIX socket established'
    ENQUEUEING_FROM = "Enqueueing upgrade request coming from peer '{peer_name}' ({peer_ip})..."
    ENQUEUEING_REMOTE = "Remote peer '{sender_name}' ({sender_ip}) has enqueued our upgrade request"
    ENQUEUEING_TO = "Enqueueing upgrade request to peer '{peer_name}' ({peer_ip})..."
    NEW_UNIX_INCOMING = 'New local UNIX connection incoming'
    REACHABLE = "Peer '{peer_name}' ({peer_ip}) is reachable"
    SHUTDOWN_SET = 'The server has been set to shut down'
    START_PROCESSING_FROM = "Starting to process the upgrade request coming from peer '{peer_name}' ({peer_ip})"
    START_PROCESSING_REMOTE = "Remote peer '{sender_name}' ({sender_ip}) has started to process our upgrade request"
    START_PROCESSING_TO = "Starting to process the upgrade request for the peer '{peer_name}' ({peer_ip})"
    SUCCESS = "Success! Now you have a new working P2P connection through interface '{interface}'"

    @staticmethod
    def build_info_message(info_message: str) -> dict:
        res = {
            MessageFields.CODE: ActionCodes.INFO,
            MessageFields.ERROR_CODE: None,
            MessageFields.MESSAGE: info_message
        }
        return res

    @classmethod
    def send_info_message(cls, local_message: str, remote_message: str = None):
        pair = CONNECTION_PAIRS[get_ident()]
        print(local_message, flush=True)
        if pair.local_socket is not None:
            local_message = cls.build_info_message(local_message)
            pair.local_socket.send(json.dumps(local_message))
        if remote_message is not None:
            remote_message = cls.build_info_message(remote_message)
            pair.remote_socket.send(json.dumps(remote_message))


class ErrorMessages:
    ALLOWED_IPS_MISMATCH = "Error: IPs from the 'Address' field of '{sender_name}' ({sender_ip}) are not fully covered in the 'AllowedIPs' field of '{my_name}' ({my_ip})"
    BAD_FORMAT_PRIVKEY = "Error: The private key has not the correct length or format in file '{config_file}'"
    BAD_FORMAT_PSK = "Error: The pre-shared key has not the correct length or format in file '{config_file}'"
    BAD_FORMAT_PUBKEY = "Error: The public key has not the correct length or format in file '{config_file}'"
    CLOSED = 'Error: Wirescale is shutting down and is no longer accepting new requests'
    FINAL_ERROR = 'Something went wrong and, finally, it was not possible to establish the P2P connection'
    INTERFACE_EXISTS = "Error: A network interface '{interface}' already exists and Wirescale was started with the --no-suffix option"
    MISSING_ADDRESS = "Error: 'Address' option missing in 'Interface' section of file '{config_file}'"
    MISSING_ALLOWEDIPS = "Error: 'AllowedIPs' option missing in 'Peer' section of file '{config_file}'"
    PSK_MISMATCH = ("Error: Peer '{name_without_psk}' ({ip_without_psk}) does not have a pre-shared key for '{name_with_psk}' ({ip_with_psk}), but '{name_with_psk}' has one configured for "
                    "'{name_without_psk}'. Ensure key consistency.")
    PUBKEY_MISMATCH = "Error: The public key provided by '{sender_name}' ({sender_ip}) is inconsistent with the one that '{receiver_name}' ({receiver_ip}) has on record for this peer."
    REMOTE_BAD_FORMAT_PRIVKEY = "Error: The private key has not the correct length or format in remote peer '{my_name}' ({my_ip}) configuration file for '{peer_name}'"
    REMOTE_BAD_FORMAT_PSK = "Error: The pre-shared key has not the correct length or format in remote peer '{my_name}' ({my_ip}) configuration file for '{peer_name}'"
    REMOTE_BAD_FORMAT_PUBKEY = "Error: The public key has not the correct length or format in remote peer '{my_name}' ({my_ip}) configuration file for '{peer_name}'"
    REMOTE_CLOSED = "Error: Wirescale instance at '{my_name}' ({my_ip}) has been set to stop receiving requests"
    REMOTE_CONFIG_ERROR = "Error: Remote peer '{my_name}' ({my_ip}) has a syntax error in its configuration file for '{peer_name}'"
    REMOTE_CONFIG_PATH_ERROR = "Error: Remote peer '{my_name}' ({my_ip}) cannot locate a configuration file for '{peer_name}'"
    REMOTE_INTERFACE_EXISTS = "Error: A network interface '{interface}' already exists on peer '{my_name}' ({my_ip}) and its Wirescale was started with the --no-suffix option"
    REMOTE_MISSING_ADDRESS = "Error: 'Address' option missing in remote peer '{my_name}' ({my_ip}) configuration file for '{peer_name}'"
    REMOTE_MISSING_ALLOWEDIPS = "Error: 'AllowedIPs' option missing in remote peer '{my_name}' ({my_ip}) configuration file for '{peer_name}'"
    REMOTE_MISSING_WIRESCALE = "Error: Remote peer '{peer_name}' ({peer_ip}) does not have Wirescale running"
    REMOTE_TAILSCALED_STOPPED = "Error: Tailscaled service is not running in remote peer `{peer_name}` ({peer_ip})"
    ROOT_SYSTEMD = "Error: Wirescale daemon must be managed by root's systemd"
    SUDO = 'Error: This program must be run as a superuser'
    TS_PEER_OFFLINE = "Error: Peer '{peer_name}' ({peer_ip}) is offline"
    TS_SYSTEMD_STOPPED = "Error: 'tailscaled.service' is stopped. Start the service with systemd"
    TS_STOPPED = "Error: Tailscale is stopped. Run 'sudo tailscale up'"
    TS_NO_ENDPOINT = "Sorry, it was impossible to find a public endpoint for peer `{peer_name}` ({peer_ip})"
    TS_NO_IP = "Error: No IPv4 found for peer '{peer_name}'"
    TS_NO_LOGGED = 'Error: Tailscale is logged out'
    TS_NO_PEER = "Error: No peer found matching the IP '{peer_ip}'"
    TS_NO_PORT = 'Error: No listening port for Tailscale was found'
    TS_NOT_RECOVERED = "Error: Either this tailscale instance or the other peer's has not fully recovered and cannot reestablish the connection"
    TS_NOT_RUNNING = 'Error: Tailscale is not running'
    UNIX_SOCKET = "Error: Couldn't connect to the local UNIX socket"

    @staticmethod
    def build_error_message(error_message: str, error_code: ErrorCodes = ErrorCodes.GENERIC) -> dict:
        res = {
            MessageFields.CODE: None,
            MessageFields.ERROR_CODE: error_code,
            MessageFields.ERROR_MESSAGE: error_message
        }
        return res

    @classmethod
    def send_error_message(cls, local_message: str = None, remote_message: str = None, error_code: ErrorCodes = ErrorCodes.GENERIC, always_send_to_remote: bool = True, exit_code: int | None = 1):
        pair = CONNECTION_PAIRS.get(get_ident())
        if local_message is not None:
            print(local_message, file=sys.stderr, flush=True)
        if pair is not None:
            if pair.local_socket is not None and local_message is not None:
                local_message = cls.build_error_message(local_message, error_code)
                pair.local_socket.send(json.dumps(local_message))
            if pair.remote_socket is not None and remote_message is not None and (always_send_to_remote or pair.running_in_remote):
                remote_message = cls.build_error_message(remote_message, error_code)
                pair.remote_socket.send(json.dumps(remote_message))
            if pair.local_socket is not None:
                pair.local_socket.close()
            if pair.remote_socket is not None:
                pair.remote_socket.close()
        if exit_code is not None:
            sys.exit(exit_code)
