#!/usr/bin/env python3
# encoding:utf-8


import re
import subprocess
from argparse import ArgumentTypeError
from ipaddress import IPv4Address
from pathlib import Path

from wirescale.communications.common import file_locker
from wirescale.communications.messages import ErrorMessages
from wirescale.vpn.tsmanager import TSManager


def check_peer(value) -> IPv4Address:
    value = value.strip()
    if not value:
        raise ArgumentTypeError('you provided an empty peer')
    print(f"Checking peer '{value}' is correct. This might take some minutes...")
    with file_locker():
        print(f"Start checking peer '{value}'")
        try:
            ip = IPv4Address(value)
        except Exception:
            ip = TSManager.peer_ip(value)
        if ip == TSManager.my_ip():
            raise ArgumentTypeError('you should not connect to your own machine')
        TSManager.peer(ip)  # Checks the IP belongs to somebody
        TSManager.peer_endpoint(ip)  # Checks an endpoint is available
    return ip


def check_existing_conf(value) -> Path:
    res = Path(f'/run/wirescale/{value}.conf')
    if not res.exists():
        raise ArgumentTypeError(f"file '{res}' does not exist")
    return res.resolve()


def check_existing_wg_interface(value):
    res = subprocess.run(['wg', 'show', value, 'listen-port'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    if res != 0:
        error = ErrorMessages.WG_INTERFACE_MISSING.format(interface=value)
        raise ArgumentTypeError(error)
    return value


def check_existing_conf_and_systemd(value) -> str:
    check_existing_wg_interface(value)
    check_existing_conf(value)
    is_active = subprocess.run(['systemctl', 'is-active', f'autoremove-{value}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    if is_active != 0:
        error = ErrorMessages.MISSING_AUTOREMOVE.format(interface=value)
        raise ArgumentTypeError(error)
    return value


def interface_name_validator(value):
    regex = r'([a-zA-Z0-9_=+.-]{1,15})'
    if not re.fullmatch(regex, value):
        error = f"'{value}' is not a valid name for a WireGuard interface"
        raise ArgumentTypeError(error)
    return value
