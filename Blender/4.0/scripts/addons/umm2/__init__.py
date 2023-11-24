# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

bl_info = {
    "name": "Universal Material Mapper 2.0",
    "author": "NVIDIA Corporation",
    "version": (201, 1, 3),
    "blender": (4, 0, 0),
    "description": "For converting materials using Nvidia Omniverse Universal Material Mapper",
    "warning": "",
    "tracker_url": "",
    "category": "Omniverse",
}


import os
import sys

import bpy

UMM2_PLUGIN_PATH = os.environ.get("UMM2_PLUGIN_PATH")
if UMM2_PLUGIN_PATH is None:
    UMM2_PLUGIN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../blender_umm2_plugin"))
else:
    UMM2_PLUGIN_PATH = os.path.abspath(UMM2_PLUGIN_PATH)

UMM_PYTHON_PATH = os.path.join(UMM2_PLUGIN_PATH, "python")
UMM_CONNECTOR_PATH = os.path.join(UMM2_PLUGIN_PATH, "connector")


class UmmPreferences(bpy.types.AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    tags: bpy.props.StringProperty(name="Tags", default="default")
    collapsed_conversion: bpy.props.BoolProperty(
        name="Collapsed conversions",
        default=False,
    )
    uncollapsed_fallback: bpy.props.BoolProperty(
        name="Fallback to node conversions for uncollapsed inputs",
        default=True,
    )

    def draw(self, context_):
        layout = self.layout
        layout.label(text="Universal Material Mapper Global Preferences")
        layout.prop(self, "tags")
        layout.prop(self, "collapsed_conversion")
        layout.prop(self, "uncollapsed_fallback")


# =========================================================================
# Registration:
# =========================================================================


def register():
    bpy.utils.register_class(UmmPreferences)
    sys.path.append(UMM_PYTHON_PATH)
    sys.path.append(UMM_CONNECTOR_PATH)


def unregister():
    sys.path.remove(UMM_CONNECTOR_PATH)
    sys.path.remove(UMM_PYTHON_PATH)
    bpy.utils.unregister_class(UmmPreferences)


if __name__ == "__main__":
    register()
