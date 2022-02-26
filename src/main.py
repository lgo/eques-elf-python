import argparse
import json
from typing import List
import logging

from eques_elf.eques_local import (
    discover_command,
    on_command,
    off_command,
    status_command,
)
from eques_elf.device import Device

logger = logging.getLogger(__name__)


def discover_cli(args: argparse.Namespace):
    logger.debug("executing discover")
    discover_command()


def send_cli(args: argparse.Namespace):
    logger.debug("executing send")
    device = Device(
        ip=args.ip,
        mac=args.mac,
        password=args.password,
        state=None,
    )

    result: List[Device] = []

    if args.cmd == "status":
        result = status_command(device)
    elif args.cmd == "toggle":
        result = status_command(device)
        if len(result) == 0:
            logger.error("no response from status and cannot toggle. Try again?")
            return
        device = result[0]
        if device.state is None:
            pass
        elif device.state:
            result = off_command(device)
        else:
            result = on_command(device)
    elif args.cmd == "set_on":
        result = on_command(device)
    elif args.cmd == "set_off":
        result = off_command(device)
    else:
        # TODO(joey): Return help message.
        pass

    print(json.dumps([device.as_dict() for device in result]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executes Eques Elf smart plug commands on the local network."
    )
    subparsers = parser.add_subparsers()

    discover = subparsers.add_parser(
        "discover",
        help="Discovers devices.",
        description="Broadcasts a discover command and lists all discovered Eques Elf devices on the local network.",
    )
    discover.set_defaults(func=discover_cli)

    command = subparsers.add_parser(
        "send",
        help="Sends a device command.",
        description="Sends a command to a specific Eques Elf device.",
    )
    command.set_defaults(func=send_cli)
    command.add_argument(
        "--cmd",
        metavar="COMMAND",
        type=str,
        choices=["status", "toggle", "set_on", "set_off"],
        help="the command to execute (status, toggle, set_on, set_off)",
    )
    command.add_argument(
        "--mac",
        metavar="MAC",
        type=str,
        help="MAC address of the device to send a command",
    )
    command.add_argument(
        "--ip",
        metavar="IP",
        type=str,
        help="IP address of the device to send a command (optional: MAC is used to find the IP if unspecified)",
    )
    command.add_argument(
        "--password",
        metavar="PASS",
        type=str,
        help="password of the device to send a command (optional: discovery command is initiated to find the password if unspecified)",
    )

    parser.add_argument(
        "-d",
        "--debug",
        help="Print debugging statements",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Print verbose (info) statements",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    args = parser.parse_args()
    # Set loglevel.
    logging.basicConfig(
        level=args.loglevel,
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    # Execute the CLI entry-points.
    args.func(args)
