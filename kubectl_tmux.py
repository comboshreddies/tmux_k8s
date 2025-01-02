#!/usr/bin/env python3
""" kubectl plugin for tmux_k8s """ 

import argparse
import os


def main():
    """ kubectl tmux plugin wrapper for tmux_k8s.py """
    accepted_objects = ['po', 'pod', 'pods']

    parser = argparse.ArgumentParser(description='kubectl tmux helper')

    parser.add_argument('--context', type=ascii, help="context")
    parser.add_argument('--namespace', '-n', type=ascii, help="namespace")
    parser.add_argument('--selector', '-l', type=ascii, help='label selector')

    parser.add_argument('sequence', type=ascii, help='sequence')
    parser.add_argument('get', type=ascii, help='get')
    parser.add_argument('object', type=ascii, help='object')

    args = parser.parse_args()

    if args.get[1:-1] != 'get':
        parser.error("arg.get should be get")

    if args.object[1:-1] not in accepted_objects:
        line = ""
        for obj in accepted_objects:
            line.join(f"{obj} ")
        parser.error("arg object should be one of: " + line)

    arg_list = ""

    value = getattr(args, 'context', None)
    if value:
        arg_list += " " + value[1:-1]

    value = getattr(args, 'namespace', None)
    if value:
        arg_list += " " + value[1:-1]

    value = getattr(args, 'selector', None)
    if value:
        arg_list += " " + value[1:-1]

    os.system(f"tmux_k8s {args.sequence[1:-1]} {arg_list}")


if __name__ == '__main__':
    main()
