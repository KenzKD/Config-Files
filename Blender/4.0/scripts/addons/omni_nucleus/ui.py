
# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

from typing import *

import bpy

from .icons import (
    g_preview_collections,
)


## ======================================================================
class OMNI_PT_NucleusPanel(bpy.types.Panel):
    bl_idname = 'OMNI_PT_NucleusPanel'
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
        col = layout.column(align=True)
        col.operator('omni.import_file_select', text='Import USD')
        col.operator('omni.export_file_select', text='Export USD')



class OMNI_PT_ConnectionsPanel(bpy.types.Panel):
    bl_idname = 'OMNI_PT_ConnectionsPanel'
    bl_parent_id = 'OMNI_PT_NucleusPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'CONNECTIONS'

    def draw(self, context):
        omni_nucleus = context.scene.omni_nucleus
        layout = self.layout

        layout = self.layout
        col = layout.column()
        col.template_list("OMNI_UL_ConnectionList", "", omni_nucleus, "connection_list",
                          omni_nucleus, "connection_list_index")

        row = col.row()
        row.operator("omni.open_connection", text="", icon='ADD')
        row.operator("omni.close_connection", text="", icon='REMOVE')

        if omni_nucleus.connection_status_report:
            row = row.row()
            report_icon = "INFO" if omni_nucleus.connection_status_report_type == "INFO" else "ERROR"
            report = f"{omni_nucleus.connection_status_report}"
            row.label(text=report, icon=report_icon)
            row.operator("omni.clear_connection_status", text="", icon='X')



class OMNI_PT_ProjectPanel(bpy.types.Panel):
    bl_idname = 'OMNI_PT_ProjectPanel'
    bl_parent_id = 'OMNI_PT_NucleusPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'PROJECT'
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        omni_nucleus = context.scene.omni_nucleus
        layout = self.layout
        col = layout.column(align=True)
        col.prop(omni_nucleus, "import_textures_directory", text="Textures Directory")

class OMNI_PT_LoggingPanel(bpy.types.Panel):
    bl_idname = 'OMNI_PT_LoggingPanel'
    bl_parent_id = 'OMNI_PT_NucleusPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'LOGGING'
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        omni_nucleus = context.scene.omni_nucleus
        layout = self.layout
        col = layout.column(align=True)
        col.prop(omni_nucleus, "omni_log_level")
