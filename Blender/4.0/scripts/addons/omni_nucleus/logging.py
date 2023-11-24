# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import logging

from omniverse import client

from pathlib import Path

g_omni_logger = None
g_write_to_log_file = False

def get_omni_log_filepath(context):
    return Path().home() / ".nvidia-omniverse/logs/omni.blender.log"

def omni_log_callback(threadName, component, level, message):
    if level == client.LogLevel.ERROR:
       print (f"{__package__} ERROR: {message}.")

    global g_write_to_log_file
    if not g_write_to_log_file:
        return

    if g_omni_logger is None:
        print(f"{__package__} ERROR: Logger not initialized.")
        return

    g_omni_logger.info(message)

def init_logger(context):
    global g_omni_logger
    if g_omni_logger is not None:
        return

    g_omni_logger = logging.getLogger('omni_nucleus')
    if g_omni_logger is None:
        print(f"{__package__} ERROR: Couldn't create logger")

    log_file = get_omni_log_filepath(context)

    if not log_file:
        print(f"{__package__} ERROR: Empty log file path")

    g_omni_logger.setLevel(logging.DEBUG)
    # Create file handler with mode 'w' to overwrte log file
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    g_omni_logger.addHandler(fh)

def omni_log_level_updated(self, context):
    if self.omni_log_level == 'NONE':
        # We always want to get errors.
        # (A log level of 'NONE' means we won't
        # be writing errors to the log file,
        # but we will still report them in Blender.)
        client.set_log_level(client.LogLevel.ERROR)
    elif self.omni_log_level == 'ERROR':
        client.set_log_level(client.LogLevel.ERROR)
    elif self.omni_log_level == 'WARNING':
        client.set_log_level(client.LogLevel.WARNING)
    elif self.omni_log_level == 'INFO':
        client.set_log_level(client.LogLevel.INFO)
    elif self.omni_log_level == 'VERBOSE':
        client.set_log_level(client.LogLevel.VERBOSE)
    elif self.omni_log_level == 'DEBUG':
        client.set_log_level(client.LogLevel.DEBUG)

    global g_write_to_log_file
    g_write_to_log_file = self.omni_log_level != 'NONE'

    if g_write_to_log_file:
        try:
            init_logger(context)
        except BaseException as ex:
            print (f"{__package__} Exception initializing logger:")
            print(ex)

def reset_logger():
    global g_omni_logger
    g_omni_logger = None
    global g_write_to_log_file
    g_write_to_log_file = False
