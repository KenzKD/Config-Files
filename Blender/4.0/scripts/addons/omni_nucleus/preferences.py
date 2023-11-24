# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import bpy
from bpy.props import (StringProperty)

from omniverse import client

class NucleusConnectionPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    nucleus_bookmarks: StringProperty(
        name="Nucleus Bookmarks",
        description="Space delimited list of bookmarked Nucleus file browser locations",
        default="omniverse://localhost"
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'nucleus_bookmarks')


def get_bookmarks_preferences(context) :
    bookmarks = set()
    try:
        bookmarks_str = context.preferences.addons[__package__].preferences.nucleus_bookmarks
        if bookmarks_str:
            bookmarks_list = bookmarks_str.split()
            for item in bookmarks_list:
                path = client.normalize_url(item)
                # Strip out the trailing slash, if necessary
                if path.endswith("/"):
                    path = path[:-1]
                bookmarks.add(path)
    except BaseException as ex:
        print("Exception accessing nucleus bookmarks:")
        print(ex)

    return bookmarks


def add_bookmark(context, new_bookmark) :
    bookmarks = get_bookmarks_preferences(context)
    if new_bookmark in bookmarks:
        return False

    try:
        context.preferences.addons[__package__].preferences.nucleus_bookmarks += f" {new_bookmark}"
        context.preferences.use_preferences_save = True

    except BaseException as ex:
        print("Exception adding bookmark:")
        print(ex)
        return False

    return True
