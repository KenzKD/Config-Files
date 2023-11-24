# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

from typing import *

import bpy
from bpy.props import (StringProperty)
from bpy.types import (Context)

from omniverse import (client)
from omniverse import (usd_resolver)

from pxr import Ar

import os.path

from .preferences import (
    add_bookmark
)

from .list_updates import (
	init_location_list,
    open_parent_directory,
    refresh_current_directory,
    create_directory,
)

from .usd_io_options import (
    OMNI_USDImportOptions,
    OMNI_USDExportOptions
)

## ======================================================================

class OMNI_OT_ClearConnectionStatus(bpy.types.Operator):
    """Clear the connection status message property"""
    bl_idname = "omni.clear_connection_status"
    bl_label = "Clear Connection Status"

    @classmethod
    def poll(cls, context):
        omni_nucleus = context.scene.omni_nucleus
        if omni_nucleus is None:
            return False
        return omni_nucleus.connection_status_report

    def execute(self, context:Context) -> Set[str]:
        omni_nucleus = context.scene.omni_nucleus
        omni_nucleus.connection_status_report = ""

        return {'FINISHED'}

class OMNI_OT_OpenConnection(bpy.types.Operator):
    """Open a Nucleus connection"""
    bl_idname = "omni.open_connection"
    bl_label = "Open Connection"

    server_name: StringProperty(
        name="Connect to Server",
        description="Name of the server to which we should connect",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return context.scene.omni_nucleus

    def draw(self, context:Context):
        layout = self.layout
        layout.prop(self, "server_name")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def execute(self, context:Context) -> Set[str]:
        if self.server_name:
            input_host = self.server_name

            # Handle the case where the user input
            # is an omniverse URI, as opposed to a
            # server name.
            parsed_url = client.break_url(input_host)
            if parsed_url.scheme == "omniverse" and parsed_url.host:
                input_host = parsed_url.host

            url = client.make_url(scheme="omniverse",
                                  host=input_host)
            client.reconnect(url)
        return {'FINISHED'}

class OMNI_OT_CloseConnection(bpy.types.Operator):
    """Close a Nucleus connection"""
    bl_idname = "omni.close_connection"
    bl_label = "Close Connection"

    @classmethod
    def poll(cls, context):
        omni_nucleus = context.scene.omni_nucleus
        if omni_nucleus is None:
            return False
        list = omni_nucleus.connection_list
        idx = omni_nucleus.connection_list_index
        if list is None or idx is None:
            return False
        return (idx >= 0 and idx < len(list))

    def execute(self, context:Context) -> Set[str]:
        omni_nucleus = context.scene.omni_nucleus
        list = omni_nucleus.connection_list
        idx = omni_nucleus.connection_list_index
        if (idx >= 0 and idx < len(list)):
            server = list[idx].name
            url = f"omniverse://{server}"
            client.sign_out(url)

        return {'FINISHED'}

class OMNI_OT_AddBookmark(bpy.types.Operator):
    """Add current directory to the bookmarks in the addon preferences"""
    bl_idname = "omni.add_bookmark"
    bl_label = "Add to Bookmarks"

    @classmethod
    def poll(cls, context):
        return context.scene.omni_nucleus and context.scene.omni_nucleus.directory

    def execute(self, context:Context) -> Set[str]:
        dir = context.scene.omni_nucleus.directory
        if add_bookmark(context, dir):
            init_location_list(context)

        return {'FINISHED'}

class OMNI_OT_CreateDirectory(bpy.types.Operator):
    """Create a directory"""
    bl_idname = "omni.create_directory"
    bl_label = "Create a Directory"

    new_directory_name: StringProperty(
        name="New Folder Name",
        description="Name of the directory to create",
        default="NewFolder"
    )

    @classmethod
    def poll(cls, context):
        return context.scene.omni_nucleus and context.scene.omni_nucleus.directory

    def draw(self, context:Context):
        layout = self.layout
        layout.prop(self, "new_directory_name")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def execute(self, context:Context) -> Set[str]:
        create_directory(self.new_directory_name, context)
        return {'FINISHED'}

class OMNI_OT_RefreshDirectory(bpy.types.Operator):
    """Refresh the contents of the current directory"""
    bl_idname = "omni.refresh_directory"
    bl_label = "Refresh the Current Directory"

    @classmethod
    def poll(cls, context):
        return context.scene.omni_nucleus and context.scene.omni_nucleus.directory

    def execute(self, context:Context) -> Set[str]:
        refresh_current_directory(context)
        return {'FINISHED'}

class OMNI_OT_OpenParentDirectory(bpy.types.Operator):
    """Opent the parent of the current directory"""
    bl_idname = "omni.open_parent_directory"
    bl_label = "Open Parent Directory"

    @classmethod
    def poll(cls, context):
        return context.scene.omni_nucleus and context.scene.omni_nucleus.directory

    def execute(self, context:Context) -> Set[str]:
        open_parent_directory(context)
        return {'FINISHED'}

class OMNI_OT_FileSelect(bpy.types.Operator):
    """Omniverse file selection"""
    bl_idname = "omni.file_select"
    bl_label = "File Selection"

    def __init__(self):

        self.draw_left_column = getattr(self, "draw_left_column", None)
        if not callable(self.draw_left_column):
            self.draw_left_column = None

        self.draw_right_column = getattr(self, "draw_right_column", None)
        if not callable(self.draw_right_column):
            self.draw_right_column = None


    def draw(self, context:Context):
        scene = context.scene
        layout = self.layout

        main_row = layout.row()
        lcol = main_row.column()
        rcol = main_row.column()
        rcol.scale_x = 1.6

        col = lcol.column()
        col.label(text="Locations")
        col.template_list("OMNI_UL_LocationList", "", scene.omni_nucleus, "location_list",
            scene.omni_nucleus, "location_list_index")

        row = col.row()
        row.prop(scene.omni_nucleus, "directory")
        row.operator("omni.open_parent_directory", text="", icon='FILE_PARENT')
        row.operator("omni.refresh_directory", text="", icon='FILE_REFRESH')
        row.operator("omni.create_directory", text="", icon='NEWFOLDER')
        row.operator("omni.add_bookmark", text="", icon='ADD')

        col = lcol.column()
        row = col.row()
        name_col = row.column()
        name_col.scale_x = 2.0
        name_col.label(text="Name")
        date_col = row.column()
        date_col.scale_x = 1.25
        date_col.label(text="Date Modified")
        size_col = row.column()
        size_col.scale_x = 1.0
        size_col.label(text="Size")
        col.template_list("OMNI_UL_FileList", "", scene.omni_nucleus, "file_list",
            scene.omni_nucleus, "file_list_index")

        lcol.prop(context.scene.omni_nucleus, "filename")

        if self.draw_left_column is not None:
            self.draw_left_column(lcol, context)

        if self.draw_right_column is not None:
            self.draw_right_column(rcol, context)

    def invoke(self, context, event):
        scene = context.scene
        if not scene.omni_nucleus.location_list_initialized:
            init_location_list(context)

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=950)

    def execute(self, context:Context) -> Set[str]:
        return {'FINISHED'}


class OMNI_OT_ImportFileSelect(OMNI_OT_FileSelect):
    """Omniverse import file selection"""
    bl_idname = "omni.import_file_select"
    bl_label = "USD Import"

    import_options = OMNI_USDImportOptions()

    def draw_right_column(self, layout, context):
        self.import_options.draw(layout, context)

    def draw_left_column(self, layout, context):
        pass

    def invoke(self, context, event):
        self.import_options.init(context)
        return super().invoke(context, event)

    def execute(self, context:Context) -> Set[str]:
        bpy.ops.omni.import_usd('INVOKE_DEFAULT')
        return {'FINISHED'}


class OMNI_OT_ExportFileSelect(OMNI_OT_FileSelect):
    """Omniverse export file selection"""
    bl_idname = "omni.export_file_select"
    bl_label = "USD Export"

    export_options = OMNI_USDExportOptions()

    def draw_right_column(self, layout, context):
        self.export_options.draw(layout, context)

    def draw_left_column(self, layout, context):
        omni_nucleus = context.scene.omni_nucleus
        row = layout.row()
        col = row.column()
        col.prop(omni_nucleus, "set_checkpoint_message", icon_only=True)
        col.scale_x = .2
        col = row.column()
        col.prop(omni_nucleus, "checkpoint_message")
        col.enabled = omni_nucleus.set_checkpoint_message

    def invoke(self, context, event):
        self.export_options.init(context)
        return super().invoke(context, event)

    def execute(self, context:Context) -> Set[str]:
        bpy.ops.omni.export_usd('INVOKE_DEFAULT')
        return {'FINISHED'}

class OMNI_OT_ImportUSD(bpy.types.Operator):
    """Import USD"""
    bl_idname = "omni.import_usd"
    bl_label = "Import USD"
    bl_options =  {"REGISTER", "UNDO"}

    def validate_import_textures_options(self, context:Context):
        if not self.should_import_textures(context):
            return True

        import_props = context.scene.omni_usd_import_props

        if import_props.import_textures_mode != "IMPORT_COPY":
            # We only validate when copying textures, so we
            # trivially consider the options valid.
            return True

        tex_dir = import_props.import_textures_dir

        if not tex_dir:
            self.report({"ERROR"},
                         f"{self.bl_label}: Empty import textures directory path. Operation Cancelled")
            return False

        if (import_props.import_textures_dir.startswith("//") and
            not bpy.data.is_saved):
            self.report({"ERROR"},
                         f"{self.bl_label}: the textures directory is a relative path, "
                         "but the Blender file hasn't been saved.  Please save the "
                         "Blender file prior to USD import.  Operation Cancelled")
            return False

        return True

    def should_import_textures(self, context:Context):
        import_props = context.scene.omni_usd_import_props
        omni_nucleus = context.scene.omni_nucleus

        filepath = omni_nucleus.filepath

        if not filepath:
            return False

        if not import_props.import_materials:
            return False

        if import_props.import_textures_mode == "IMPORT_NONE":
            return False

        return (client.break_url(filepath).scheme == "omniverse" or
                os.path.splitext(filepath)[1].lower() == ".usdz")


    def draw(self, context:Context):
        omni_nucleus = context.scene.omni_nucleus
        import_props = context.scene.omni_usd_import_props
        layout = self.layout
        col = layout.column()
        col.label(text=f"Confirm Texture Import Options for '{omni_nucleus.filepath}'")
        col.prop(import_props, "import_textures_mode")

        col = layout.column()
        col.prop(import_props, "import_textures_dir")
        col.prop(import_props, "tex_name_collision_mode")
        col.enabled = import_props.import_textures_mode == "IMPORT_COPY"

        col = layout.column()
        if import_props.import_textures_mode == "IMPORT_PACK":
            col.label(text="WARNING: importing packed textures may be slow!",
                      icon='ERROR')
        elif (import_props.import_textures_mode == "IMPORT_COPY" and
              not bpy.data.is_saved and
              import_props.import_textures_dir.startswith("//")):
            col.label(text="WARNING: the textures directory is a relative path, "
                           "but the Blender file hasn't been saved!",
                      icon='ERROR')
            col.label(text="Please provide an absolute texture directory path.")

        col = layout.column()
        col.prop(omni_nucleus, "confirm_texture_import_options",
                 text="Don't ask again", invert_checkbox=True)

    def modal(self, context, event):
        self.execute(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        omni_nucleus = context.scene.omni_nucleus
        if (omni_nucleus.confirm_texture_import_options and
            self.should_import_textures(context)):
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=600)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context:Context) -> Set[str]:
        omni_nucleus = context.scene.omni_nucleus

        if not self.validate_import_textures_options(context):
            return {'CANCELLED'}

        props = {}
        for key in bpy.ops.wm.usd_import.get_rna_type().properties.keys():
            if key in ["rna_type"]:
                continue
            if hasattr(bpy.context.scene.omni_usd_import_props, key):
                props[key] = getattr(bpy.context.scene.omni_usd_import_props, key)

        props["filepath"] = omni_nucleus.filepath
        bpy.ops.wm.usd_import(**props)
        return {'FINISHED'}

class OMNI_OT_ExportUSD(bpy.types.Operator):
    """Export USD"""
    bl_idname = "omni.export_usd"
    bl_label = "Export USD"

    def draw(self, context:Context):
        omni_nucleus = context.scene.omni_nucleus
        layout = self.layout
        col = layout.column()
        col.label(text=f"Overwrite existing file '{omni_nucleus.filepath}'?")
        col.prop(omni_nucleus, "always_allow_file_overwrite", text="Don't ask again")

    def modal(self, context, event):
        self.execute(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        omni_nucleus = context.scene.omni_nucleus
        if (not omni_nucleus.always_allow_file_overwrite and
            Ar.GetResolver().Resolve(omni_nucleus.filepath).GetPathString()):
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=600)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context:Context) -> Set[str]:
        omni_nucleus = context.scene.omni_nucleus

        ar = Ar.GetResolver()
        resolved_path = ar.ResolveForNewAsset(omni_nucleus.filepath)
        can_write = ar.CanWriteAssetToPath(resolved_path)

        if not can_write[0]:
            self.report({"ERROR"},
                         f"{self.bl_label}: Can't write to {omni_nucleus.filepath}: {can_write[1]}. Operation Cancelled")
            return {'CANCELLED'}

        export_props = context.scene.omni_usd_export_props

        props = {}
        for key in bpy.ops.wm.usd_export.get_rna_type().properties.keys():
            if key in ["rna_type"]:
                continue
            if hasattr(export_props, key):
                props[key] = getattr(export_props, key)

        props["filepath"] = omni_nucleus.filepath

        if omni_nucleus.set_checkpoint_message:
            usd_resolver.set_checkpoint_message(omni_nucleus.checkpoint_message)
        bpy.ops.wm.usd_export(**props)
        if omni_nucleus.set_checkpoint_message:
            usd_resolver.set_checkpoint_message("")
        return {'FINISHED'}

