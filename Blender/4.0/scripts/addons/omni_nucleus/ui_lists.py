# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import bpy
from bpy.props import (BoolProperty, StringProperty)
from bpy.types import (PropertyGroup, UIList)

from .icons import (
    g_preview_collections,
)

class OMNI_ConnectionListItem(PropertyGroup):
    """A connection list item (i.e., a Nucleus server name)."""

    name: StringProperty(
           name="Name",
           description="Nucleus server name",
           default="")

class OMNI_UL_ConnectionList(UIList):
    """List Omniverse connections."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        custom_icon = 'NONE'
        custom_icon_value = 0

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = custom_icon, icon_value = custom_icon_value)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon, icon_value = custom_icon_value)

class OMNI_LocationListItem(PropertyGroup):
    """A file browser location list item (e.g., a Nucleus server or disk drive name)."""

    name: StringProperty(
           name="Name",
           description="File base location",
           default="Untitled")

    is_omni_uri: BoolProperty(
           name="IsOmniUri",
           description="True if location is an Omniverse URI",
           default=False)


class OMNI_UL_LocationList(UIList):
    """List file location bases (Nucleus URLS and file system drives)."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        custom_icon = 'NONE'
        custom_icon_value = 0

        if item.is_omni_uri:
            # Use the Omniverse icon for URIs.
            custom_icon_value = g_preview_collections["main"]["OMNI"].icon_id
        else:
            custom_icon = 'DISK_DRIVE'

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = custom_icon, icon_value = custom_icon_value)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon, icon_value = custom_icon_value)

class OMNI_FileListItem(PropertyGroup):
    """A file browser file name list item."""

    name: StringProperty(
           name="Name",
           description="File name",
           default="Untitled")

    is_directory: BoolProperty(
		name="Is Directory Flag",
        description="Whether or not the file is a directory",
		default=False
	)

    modified_time: StringProperty(
		name="Modified Time",
        description="File modification time",
		default=""
	)

    size: StringProperty(
		name="Size",
        description="File size formatted string",
		default=""
	)

    is_accessible: BoolProperty(
		name="Is Accessible Flag",
        description="Whether the containing directory is accessible",
		default=True
	)

    is_writable: BoolProperty(
		name="Is Writable",
        description="Whether the current user has write access to the file",
		default=True
	)


class OMNI_UL_FileList(UIList):
    """List file names in the current directory."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        if not item.is_accessible:
            layout.label(text="Directory is inaccessible", icon='ERROR')
            return

        # We could write some code to decide which icon to use here...
        if item.is_directory:
            custom_icon = 'FILEBROWSER'
        else:
            if not item.is_writable:
                custom_icon = 'LOCKED'
            else:
                custom_icon = 'NONE'

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            col = layout.column()
            col.scale_x = 2.0
            col.label(text=item.name, icon = custom_icon)
            col = layout.column()
            col.scale_x = 1.25
            col.label(text=item.modified_time, icon = 'NONE')
            col = layout.column()
            col.scale_x = 1.0
            col.label(text=item.size, icon = 'NONE')

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)