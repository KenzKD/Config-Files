# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import bpy

from .icons import (
    g_preview_collections,
    register_icons,
    unregister_icons
)

## ======================================================================
class OMNI_PT_NucleusLoadWarningPanel(bpy.types.Panel):
    bl_idname = 'OMNI_PT_NucleusLoadWarningPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Omniverse"
    bl_label = "NUCLEUS"
    version = "0.0.0"

    def draw_header(self, context):
        self.layout.label(text="", icon_value=g_preview_collections["main"]["OMNI"].icon_id)

    # draw the panel
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="WARNING: Couldn't import 'omniverse' module.", icon='ERROR')
        col.label(text="Please run Blender from the Omniverse Launcher to use the Nucleus Connector.")

def register_warning_panel():
    unregister_warning_panel()
    register_icons()
    bpy.utils.register_class(OMNI_PT_NucleusLoadWarningPanel)

def unregister_warning_panel():
    unregister_icons()
    try:
        bpy.utils.unregister_class(OMNI_PT_NucleusLoadWarningPanel)
    except:
        pass
