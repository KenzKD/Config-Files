# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import bpy
from bpy.props import (BoolProperty, IntProperty, CollectionProperty, StringProperty, EnumProperty)

from .list_updates import (
    update_location_list_index,
    update_file_list_index,
    filename_updated,
    directory_updated,
)

from .logging import (
    omni_log_level_updated,
)

from .ui_lists import (
    OMNI_FileListItem,
    OMNI_LocationListItem,
    OMNI_ConnectionListItem,
)

class OmniNucleusSettings(bpy.types.PropertyGroup):
    location_list: CollectionProperty(
        type=OMNI_LocationListItem,
        name="Locations",
        description="List of Omniverse servers or local file system drives",
    )

    location_list_index: IntProperty(
        name="Location List Index",
        description="Index of the currently selected location list item",
        default=0,
        update=update_location_list_index
    )

    location_list_initialized: BoolProperty(
        name="Location List Initialized",
        description="Whether or not the location list has been initialized",
        default=False
    )

    file_list: CollectionProperty(
        type=OMNI_FileListItem,
        name="Files",
        description="List of files in the current directory",
    )

    file_list_index: IntProperty(
        name="File List Index",
        description="Index of the currently selected file list item",
        default=0,
        update=update_file_list_index
    )

    connection_list: CollectionProperty(
        type=OMNI_ConnectionListItem,
        name="Connections",
        description="List of open Nucleus connections",
    )

    connection_list_index: IntProperty(
        name="Connection Index",
        description="Index of the currently selected connection",
        default=0
    )

    connection_list_initialized: BoolProperty(
        name="Connection List Initialized",
        description="Whether or not the collection list has been initialized",
        default=False
    )

    filepath: StringProperty(
        name="File Path",
        description="Path of the currently selected file",
        default=""
    )

    directory: StringProperty(
        name="Directory",
        description="Currently selected directory",
        default="",
        update=directory_updated
    )

    filename: StringProperty(
        name="File Name",
        description="Name of the currently selected file",
        default="",
        update=filename_updated
    )

    file_select_mode: EnumProperty(
        name="File Select Mode",
        description="File selection mode",
        items=(
            ('IMPORT', "Import", ""),
            ('EXPORT', "Export", ""),
        ),
        default='IMPORT',
    )

    omni_log_level: EnumProperty(
        name="Log Level",
        description="Omniverse Client library logging level",
        items=(
            ('NONE', "None", "No logging"),
            ('ERROR', "Error", "Definite problem"),
            ('WARNING', "Warning", "Potential problem"),
            ('INFO', "Info", "Not a problem"),
            ('VERBOSE', "Verbose", "Chatty"),
            ('DEBUG', "Debug", "Extra chatty"),
        ),
        default='ERROR',
        update=omni_log_level_updated
    )

    expand_import_general: BoolProperty(
        name="Expand Import General",
        description="Whether to expand the General box in the import options UI layout",
        default=False
    )

    expand_import_types: BoolProperty(
        name="Expand Import Types",
        description="Whether to expand the Import Types box in the import options UI layout",
        default=False
    )

    expand_import_geometry: BoolProperty(
        name="Expand Import Geometry",
        description="Whether to expand the Geometry box in the import options UI layout",
        default=False
    )

    expand_import_materials: BoolProperty(
        name="Expand Import Materials",
        description="Whether to expand the Materials box in the import options UI layout",
        default=False
    )

    expand_import_textures: BoolProperty(
        name="Expand Import Textures",
        description="Whether to expand the Textures box in the import options UI layout",
        default=False
    )

    expand_import_lights: BoolProperty(
        name="Expand Import Lights",
        description="Whether to expand the Lights box in the import options UI layout",
        default=False
    )

    expand_import_rigging: BoolProperty(
        name="Expand Import Rigging",
        description="Whether to expand the Rigging box in the import options UI layout",
        default=False
    )

    expand_import_animation: BoolProperty(
        name="Expand Import Animation",
        description="Whether to expand the Animation box in the import options UI layout",
        default=False
    )

    expand_import_particles_and_instancing: BoolProperty(
        name="Expand Import Particles and Instancing",
        description="Whether to expand the Particles and Instancing box in the import options UI layout",
        default=False
    )

    expand_export_general: BoolProperty(
        name="General",
        description="Whether to expand the General box in the export options UI layout",
        default=False
    )

    expand_export_stage: BoolProperty(
        name="Stage",
        description="Whether to expand the Stage box in the export options UI layout",
        default=False
    )

    expand_export_types: BoolProperty(
        name="Export Types",
        description="Whether to expand the Export Types box in the export options UI layout",
        default=False
    )

    expand_export_geometry: BoolProperty(
        name="Export Geometry",
        description="Whether to expand the Geometry box in the export options UI layout",
        default=False
    )

    expand_export_materials: BoolProperty(
        name="Export Materials",
        description="Whether to expand the Materials box in the export options UI layout",
        default=False
    )

    expand_export_lights: BoolProperty(
        name="Export Lights",
        description="Whether to expand the Lights box in the export options UI layout",
        default=False
    )

    expand_export_rigging: BoolProperty(
        name="Export Rigging",
        description="Whether to expand the Rigging box in the export options UI layout",
        default=False
    )

    expand_export_animation: BoolProperty(
        name="Export Animation",
        description="Whether to expand the Animation box in the export options UI layout",
        default=False
    )

    expand_export_particles_and_instancing: BoolProperty(
        name="Export Particles and Instancing",
        description="Whether to expand the Particles and Instancing box in the export options UI layout",
        default=False
    )

    set_checkpoint_message: BoolProperty(
        name="Set Checkpoint Message",
        description="Whether to set the checkpoint message when exporting to Nucleus",
        default=False
    )

    checkpoint_message: StringProperty(
        name="Checkpoint Message",
        description="Checkpoint message for files exported to Nucleus",
        default="Exported from Blender",
    )

    async_texture_upload: BoolProperty(
        name="Async Texture Upload",
        description="Whether to asynchronously copy exported textures to Nucleus",
        default=False
    )

    always_allow_file_overwrite: BoolProperty(
        name="Always Allow File Overwrite",
        description="If True, always allow overwriting files, without asking",
        default=False
    )

    confirm_texture_import_options: BoolProperty(
        name="Confirm Texture Import Options",
        description="If True, prompt the user to confirm texture import options",
        default=True
    )

    import_textures_directory: StringProperty(
        name="Import Textures Directory",
        description="Local directory where textures will be downloaded from Nucleus",
        default="",
        subtype='DIR_PATH'
    )

    connection_status_report: StringProperty(
        name="Connection Status Report",
        description="Report of the latest Nucleus connection status received",
        default="",
    )

    connection_status_report_type: EnumProperty(
        name="Connection Status Report Type",
        description="Type of the Nucleus status report",
        items=(
            ('INFO', "Info", ""),
            ('WARNING', "Warning", ""),
            ('ERROR', "Error", ""),
        ),
        default='INFO',
    )
