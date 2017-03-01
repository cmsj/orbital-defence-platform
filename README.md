# Orbital Defence Platform
by Chris Jones <cmsj@tenshu.net>

## Licence
Released under the MIT licence.

## Introduction
This is a simple tool for remote execution. You send a message with Pushbullet, from a trusted device, and a corresponding command is executed.

## Installation
 * The `requirements.txt` file describes the Python dependencies required, you can cause them to be installed with `pip install -r requirements.txt`
 * Copy `odp.py` somewhere useful
 * Copy `sample-config.json` to `/etc/odp.json` and edit it
  * Insert your Pushbullet API key
  * Add one or more Pushbullet identifiers for your trusted devices. You can find these identifiers by running `odp.py` with `-s` after adding your API key
  * Add one or more commands to the configuration
 * Arrange for `odp.py` to be running on your machine, it will create a new device in your Pushbullet account called `ODP`
 * Send one of your pre-defined commands from a trusted source device, to your `ODP` device
 * If you want to, you can choose a different name for the odp device, by adding an `odp_device_name` entry in the JSON configuration.

## Security
Obviously there are huge potential risks in exposing a machine to a third party service, when command execution is involved.

For this reason, ODP will never include any part of the remote message, in the command that is executed. Commands must be strictly pre-defined in the configuration file.

You are strongly encouraged to run ODP as an unprivileged user, with its configuration file not writeable by that user. To execute privileged commands, create static, passwordless `sudoers` entries which tightly control the privileged commands that can be executed (the correct ways to do this are beyond the scope of this README, you are encouraged to seek out the many tutorials for writing locked-down `sudoers` entries)

## Troubleshooting
You can run `odp.py` with `-d` to get fairly comprehensive logging.

The process will poll Pushbullet for new messages, every 30 seconds, which may cause you to get ratelimited if you're not a Pushbullet Pro subscriber. You can change the polling interval with the `-t` command line option.
