# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

from os.path import join, dirname
import bpy.utils.previews

# We can store multiple preview collections here,
# however in this example we only store "main"
g_preview_collections = {}


def get_icons_directory():
    icons_directory = join(dirname(__file__), "icons")
    return icons_directory


def register_icons():
    # Note that preview collections returned by bpy.utils.previews
    # are regular py objects - you can use them to store custom data.
    pcoll = bpy.utils.previews.new()

    # path to the folder where the icon is
    # the path is calculated relative to this py file inside the addon folder
    my_icons_dir = get_icons_directory()

    # load a preview thumbnail of a file and store in the previews collection
    pcoll.load("OMNI", join(my_icons_dir, "omni_icon.png"), 'IMAGE')

    g_preview_collections["main"] = pcoll


def unregister_icons():
    for pcoll in g_preview_collections.values():
        bpy.utils.previews.remove(pcoll)

    g_preview_collections.clear()
