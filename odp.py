#!/usr/bin/env python
"""Orbital Defence Platform v1.0 by Chris Jones <cmsj@tenshu.net>"""

import argparse
import docker
import json
import logging
import os
import pushbullet
import subprocess
import sys
import time


DEFAULT_DEVICE_NAME = "ODP"


def parse_options(args=None):
    """Parse command line options"""
    formatter = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description='Orbital Defence Platform',
                                     formatter_class=formatter)
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        help='Enable debugging', default=False)
    parser.add_argument('-c', '--config', action='store', dest='config',
                        help='Config file', default='/etc/odp.json')
    parser.add_argument('-e', '--envconfig', action='store_true',
                        dest='envconf',
                        help='Load config from $ODP_CONFIG instead of a file',
                        default=False)
    parser.add_argument('-s', '--show-devices', action='store_true',
                        dest='show_devices',
                        help='Show Pushbullet devices and exit', default=False)
    parser.add_argument('-t', '--poll-interval', action='store', type=int,
                        dest='polling_interval', default=30,
                        help='Pushbullet polling interval, in seconds')
    options = parser.parse_args(args)
    return options


class ODP:
    config = None
    logger = None
    options = None
    pb = None
    pb_listener = None
    pb_device = None
    time_cursor = None

    def __init__(self, options):
        self.logger = logging.getLogger("ODP")
        self.options = options

        if self.options.debug:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Command line options: %s" % self.options)
        else:
            self.logger.setLevel(logging.INFO)

        # Set a timestamp for our time cursor \
        self.time_cursor = time.time()

        # Load our config
        if self.options.envconf:
            self.config = json.loads(os.getenv("ODP_CONFIG"))
        else:
            with open(self.options.config, 'r') as config_file:
                self.config = json.load(config_file)
                self.logger.debug("Loaded config: %s" % self.config)

        # Validate the config contains some minimally useful things
        if "odp_device_name" not in self.config:
            self.config["odp_device_name"] = DEFAULT_DEVICE_NAME

        # Create our PushBullet object and find our device within it
        self.pb = pushbullet.Pushbullet(self.config["api_key"])
        try:
            self.pb_device = self.pb.get_device(self.config["odp_device_name"])
        except pushbullet.errors.InvalidKeyError:
            self.pb_device = self.pb.new_device(self.config["odp_device_name"])
        self.logger.debug("Our device: %s" % self.pb_device)

        # Check if we're doing a one-shot action, or going into server mode
        if self.options.show_devices:
            self.logger.info("Pushbullet devices:")
            for device in self.pb.devices:
                print("  %s: %s" % (device.nickname, device.device_iden))
            sys.exit(0)

        # Create our listener
        self.pb_listener = pushbullet.Listener(account=self.pb,
                                               on_push=self.newEvent)

        # Run the listener
        try:
            self.pb_listener.run_forever()
        except KeyboardInterrupt:
            self.pb_listener.close()

    def deviceNameFromIden(self, iden):
        """Figure out a device name from its iden"""
        for device in self.pb.devices:
            if iden == device.device_iden:
                return device.nickname

    def newEvent(self, event):
        """Process an event from the Pushbullet listener"""
        self.logger.debug("Received new listener event: %s" % event)
        if event["type"] == "tickle" and event["subtype"] == "push":
            self.updatePushes()

    def updatePushes(self):
        """Poll Pushbullet and trigger processing of them"""
        self.logger.debug("Refreshing pushes since %d..." % self.time_cursor)
        allPushes = self.pb.get_pushes(modified_after=self.time_cursor)
        self.logger.debug("Found %d pushes in total" % len(allPushes))

        # Update our time cursor to the latest one in our pushes
        for push in allPushes:
            self.time_cursor = max(self.time_cursor, push.get("modified"))

        # Find pushes specifically for ODP
        our_pushes = [x for x in allPushes
                      if x.get("target_device_iden",
                               None) == self.pb_device.device_iden and
                      x.get("source_device_iden",
                            None) in self.config["authorised_src_idens"]]
        self.processPushes(our_pushes)

    def processPushes(self, pushes):
        """Process any push messages that have been found"""
        self.logger.debug("Found %d pushes for ODP" % len(pushes))
        for push in pushes:
            self.logger.debug("Found relevant push: %s" % push)
            msg = ""
            # Attempt execution of the defined command
            try:
                result = self.executeCommand(push["body"]) \
                         and "Failed" or "Success"
                msg = "Command: '%s'. Result: %s" % (push["body"], result)
            except:
                self.logger.error("executeCommand failed for command: %s" %
                                  push["body"])
                msg = "Command '%s' exploded" % push["body"]
            src_name = self.deviceNameFromIden(push["source_device_iden"])
            src_device = self.pb.get_device(src_name)
            # Send a reply back to the source of this push
            self.pb.push_note(msg, time.strftime("%c"), device=src_device)

    def executeCommand(self, command):
        """Fish a command out of our config and execute it"""
        try:
            exec_cmd = self.config["commands"][command]
        except KeyError:
            self.logger.error("Command: '%s' not found" % command)
            # Raise another exception so this failure bubbles up
            raise ValueError

        if exec_cmd.starts_with("docker-start:"):
            return self.dockerStart(exec_cmd[13:])
        elif exec_cmd.starts_with("docker-stop:"):
            return self.dockerStop(exec_cmd[12:])
        else:
            self.logger.debug("Executing command: '%s':'%s'" % (
                              command, exec_cmd))
            return subprocess.call(exec_cmd.split(), shell=False)

    def dockerStart(self, container):
        """Start a docker container"""
        client = docker.Client(base_url="unix://var/run/docker.sock")
        client.start(container)

    def dockerStop(self, container):
        """Stop a docker container"""
        client = docker.Client(base_url="unix://var/run/docker.sock")
        client.stop(container)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    options = parse_options()
    odp = ODP(options)
