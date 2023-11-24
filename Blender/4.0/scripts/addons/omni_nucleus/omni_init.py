# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import bpy

from .list_updates import (
    init_connection_list,
    init_location_list
)

from .logging import omni_log_callback

from .omni_globals import g_open_connections

from omniverse import client

import queue

g_connection_status_subscription = None
g_omni_initialized = False
g_connection_updates = queue.Queue()

g_connection_status_messages = {
    client.ConnectionStatus.CONNECTING : "Attempting to connect",
    client.ConnectionStatus.CONNECTED : "Successfully connected",
    client.ConnectionStatus.CONNECT_ERROR : "Connection error",
    client.ConnectionStatus.DISCONNECTED : "Disconnected",
    client.ConnectionStatus.SIGNED_OUT : "Signed out",
    client.ConnectionStatus.NO_USERNAME : "No username was provided and no auth server found",
    client.ConnectionStatus.AUTH_ABORT : "Application requested auth abort",
    client.ConnectionStatus.AUTH_CANCELLED : "User or application request authentication cancelled",
    client.ConnectionStatus.AUTH_ERROR : "Internal error while trying to authenticate",
    client.ConnectionStatus.AUTH_FAILED : "Authentication failed",
    client.ConnectionStatus.SERVER_INCOMPATIBLE : "The server is not compatible with this version of the client library",
    client.ConnectionStatus.INVALID_HOST : "The host name is invalid" }

def connection_status_callback(url, connection_status):
    global g_connection_updates

    print(f"{__package__}: Connection status: {url} {connection_status}")

    g_connection_updates.put((url, connection_status))

def get_connection_status_report(url, status):

    status_msg = (g_connection_status_messages[status]
                  if status in g_connection_status_messages
                  else str(status))

    is_info_status = (status == client.ConnectionStatus.CONNECTING or
                      status == client.ConnectionStatus.CONNECTED or
                      status == client.ConnectionStatus.SIGNED_OUT)

    type = "INFO" if is_info_status else "WARNING"

    return (type, f"{url}: {status_msg}")

def process_queued_connection_updates():
    global g_open_connections

    if not bpy.context:
        return

    omni_nucleus = bpy.context.scene.omni_nucleus
    update_location_list = not g_connection_updates.empty()
    while not g_connection_updates.empty():
        update = g_connection_updates.get()
        url = update[0]
        status = update[1]
        if status == client.ConnectionStatus.CONNECTED:
            g_open_connections.add(url)
        elif url in g_open_connections:
            g_open_connections.remove(url)

        report = get_connection_status_report(url, status)
        omni_nucleus.connection_status_report_type = report[0]
        omni_nucleus.connection_status_report = report[1]

    if update_location_list:
        init_location_list(bpy.context)
        init_connection_list(bpy.context)
    elif bpy.context.scene:
        if (omni_nucleus is not None and
            not omni_nucleus.connection_list_initialized):
            init_connection_list(bpy.context)

    return 4.0

def register_omniverse():
    global g_omni_initialized
    global g_connection_status_subscription

    bpy.app.timers.register(process_queued_connection_updates,  persistent=True)

    if g_omni_initialized:
        return

    client.set_log_callback(omni_log_callback)

    if not client.initialize():
        print ("omni_nucleus WARNING: couldn't initialize client")
        return

    g_omni_initialized = True

    g_connection_status_subscription = client.register_connection_status_callback(connection_status_callback)


def unregister_omniverse():
    g_connection_status_subscription = None

    if bpy.app.timers.is_registered(process_queued_connection_updates):
        bpy.app.timers.unregister(process_queued_connection_updates)
