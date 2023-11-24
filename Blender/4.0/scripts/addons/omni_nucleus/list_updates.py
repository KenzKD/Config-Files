# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import os
import os.path
from pathlib import Path
from string import ascii_uppercase
from typing import *

from omniverse import client

from .omni_globals import (
    g_open_connections
)

from .preferences import get_bookmarks_preferences

import platform


def format_filesize(size):
    KB = 1024
    MB = KB * KB
    if size < KB:
        return f"{size:3.1f} B"
    if size < MB:
        size /= KB
        return f"{size:3.1f} KB"
    size /= MB
    return f"{size:3.1f} MB"

def normalize_path(path):
    url = client.break_url(path.replace('\\', '/'))

    if url.scheme:
        uri = url.scheme + '://'
        if url.host:
            uri += url.host
        if url.path:
            uri += url.path
        if url.query:
            uri += f"?{url.query}"
        return uri

    return url.path

def is_absolute_path(path):
    url = client.break_url(path)

    if url.scheme:
        return True

    is_windows = platform.system() == "Windows"

    if ((is_windows and ':' in url.path) or
        (not is_windows and url.path.startswith('/'))):
            return True

    return False


def is_valid_file(path):
    result = client.stat(path)

    if result[0] != client.Result.OK:
        return False

    return True

def is_directory(dir):
    result = client.stat(dir)

    if result[0] != client.Result.OK:
        return False

    if (result[1].flags & client.ItemFlags.CAN_HAVE_CHILDREN) == 0:
        return False

    return True

def populate_file_list(dir, context):
    list = context.scene.omni_nucleus.file_list
    list.clear()
    context.scene.omni_nucleus.file_list_index = -1

    if not dir:
        return

    result = client.list(dir)

    if result[0] != client.Result.OK:
        # Add a dummy entry to signal that the
        # current directory isn't accessible so
        # that an error message can be displayed
        # in the file list.
        placeholder_entry = list.add()
        placeholder_entry.is_accessible = False
        return

    dirs = []
    files = []

    for item in result[1]:
        if ((item.flags & client.ItemFlags.CAN_HAVE_CHILDREN) != 0):
            dirs.append(item)
        else:
            files.append(item)

    for dir in dirs:
        new_file = list.add()
        new_file.name = dir.relative_path
        new_file.is_directory = True
        new_file.modified_time = dir.modified_time.strftime('%Y-%m-%d %I:%M %p')
        new_file.is_writable = (dir.access & client.AccessFlags.WRITE) != 0

    for file in files:
        if Path(file.relative_path).suffix not in ['.usd', '.usda', '.usdz', '.usdc', '.live']:
            continue
        new_file = list.add()
        new_file.name = file.relative_path
        new_file.modified_time = file.modified_time.strftime('%Y-%m-%d %I:%M %p')
        new_file.size = format_filesize(file.size)
        new_file.is_writable = (file.access & client.AccessFlags.WRITE) != 0

def refresh_current_directory(context):
    dir = context.scene.omni_nucleus.directory
    if dir:
        populate_file_list(dir, context)

def create_directory(new_dir_name, context):
    new_dir_path = context.scene.omni_nucleus.directory

    if not new_dir_path.endswith(("/", "\\")):
        new_dir_path += "/"
    new_dir_path += new_dir_name

    if is_valid_file(new_dir_path):
        path_base = new_dir_path
        idx = 1
        while idx <= 100:
            new_dir_path = f"{path_base}{idx}"
            if not is_valid_file(new_dir_path):
                break
            idx += 1
        if idx > 100:
            print(f"Path {new_dir_path} already exists.  Please specify a unique directory name.")
            return False

    result = client.create_folder(new_dir_path)

    success = result == client.Result.OK

    if not success:
        print(f"Couldn't create directory {new_dir_path}")

    context.scene.omni_nucleus.directory = new_dir_path

    return success

def update_location_list_index(self, context):
    list = self.location_list
    idx = self.location_list_index
    if idx >= 0 and idx < len(list):
        self.directory = list[idx].name

def update_file_list_index(self, context):
    list = self.file_list
    idx = self.file_list_index
    if idx >= 0 and idx < len(list):
        item = list[idx]
        if not item.is_accessible:
            # This is a placeholder entry signalling
            # that the directory is inaccessible, so
            # we ignore it.
            return

        if item.is_directory:
            new_dir = self.directory
            if not new_dir.endswith(("/", "\\")):
                new_dir += '/'
            new_dir += item.name
            self.directory = new_dir
        else:
            self.filename = item.name

def open_parent_directory(context):
    omni_nucleus = context.scene.omni_nucleus
    parent_dir = omni_nucleus.directory + "/.."
    parent_dir = client.normalize_url(parent_dir)

    if not is_directory(parent_dir):
        return

    if parent_dir == omni_nucleus.directory:
        return

    omni_nucleus.directory = parent_dir


def init_location_list(context):
    global g_open_connections

    omni_nucleus = context.scene.omni_nucleus
    list = omni_nucleus.location_list
    list.clear()

    bookmarks = get_bookmarks_preferences(context)
    omni_urls = bookmarks.union(g_open_connections)

    for url in omni_urls:
        item = list.add()
        item.name = url
        item.is_omni_uri = (client.break_url(url).scheme == "omniverse")

    home_dir = Path().home().as_posix()
    if home_dir and is_directory(home_dir):
        item = list.add()
        item.name = home_dir

    if platform.system() == "Windows":
        for c in ascii_uppercase:
            drive = f"{c}:"
            if os.path.isdir(drive):
                item = list.add()
                item.name = drive

    omni_nucleus.location_list_index = -1

    if not omni_nucleus.location_list_initialized:
        omni_nucleus.location_list_initialized = True


def init_connection_list(context):
    global g_open_connections

    if context is None:
        return

    if context.scene is None:
        return

    omni_nucleus = context.scene.omni_nucleus
    list = omni_nucleus.connection_list
    list.clear()

    hosts = set()

    for url in g_open_connections:
        host = client.break_url(url).host
        if host:
            hosts.add(host)

    for host in hosts:
        item = list.add()
        item.name = host

    omni_nucleus.connection_list_index = -1

    if not omni_nucleus.connection_list_initialized:
        omni_nucleus.connection_list_initialized = True


def update_filepath(context):
    omni_nucleus = context.scene.omni_nucleus
    filename = omni_nucleus.filename

    if not filename:
        omni_nucleus.filepath = omni_nucleus.directory
        return

    if is_absolute_path(filename):
        omni_nucleus.filepath = filename
        return

    new_filepath = omni_nucleus.directory + '/' + filename
    omni_nucleus.filepath = normalize_path(new_filepath)


def filename_updated(self, context):
    filename = self.filename

    if not filename:
        update_filepath(context)
        return

    filename = normalize_path(filename)

    # Use simple heuristics to ensure that the file
    # name has an extension:
    # If the file name doesn't end with a slash
    # and has no extension, append the '.usd' extension.
    # However, we also want to allow checkpoint query syntax
    # (e.g., 'foo.usd?&2'), so we don't append the extension
    # if the file name contains the '?' query character.
    if (not filename.endswith("/")
        and filename.find('?') == -1
        and not os.path.splitext(filename)[1]):
        self.filename = f"{filename}.usd"
        return

    if is_absolute_path(filename):
        is_dir = is_directory(filename)
        if is_dir and not filename.endswith('/'):
            filename += '/'
        self.directory = filename
        if is_dir:
            self.filename = ""
            return

    update_filepath(context)

def directory_updated(self, context):
    dir = self.directory
    dir = normalize_path(dir)

    if not dir.endswith('/'):
        if is_directory(dir):
            dir += '/'
        else:
            split_path = dir.rsplit("/", 1)
            if len(split_path) > 1:
                dir = split_path[0]
                if not dir.endswith('/'):
                    dir += '/'
                self.filename = split_path[1]

    if self.directory != dir:
        self.directory = dir

    populate_file_list(self.directory, context)

    update_filepath(context)

