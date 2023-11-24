# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

## ======================================================================

import os

import bpy.utils.previews

from .scene_props import (
    OmniNucleusSettings
)

from .ui import (
    OMNI_PT_NucleusPanel,
    OMNI_PT_ConnectionsPanel,
    OMNI_PT_ProjectPanel,
    OMNI_PT_LoggingPanel,
)

from .ui_lists import (
    OMNI_FileListItem,
    OMNI_LocationListItem,
    OMNI_UL_FileList,
    OMNI_UL_LocationList,
    OMNI_ConnectionListItem,
    OMNI_UL_ConnectionList
)

from .preferences import (
    NucleusConnectionPreferences
)

from .logging import (
    reset_logger
)

from .icons import (
    register_icons,
    unregister_icons
)

from .operators import (
    OMNI_OT_FileSelect,
    OMNI_OT_ExportFileSelect,
    OMNI_OT_ImportFileSelect,
    OMNI_OT_OpenParentDirectory,
    OMNI_OT_CreateDirectory,
    OMNI_OT_RefreshDirectory,
    OMNI_OT_OpenConnection,
    OMNI_OT_CloseConnection,
    OMNI_OT_ImportUSD,
    OMNI_OT_ExportUSD,
    OMNI_OT_AddBookmark,
    OMNI_OT_ClearConnectionStatus
)

from .usd_io_options import (
    USDImportProps,
    USDExportProps
)

from .omni_init import (
    register_omniverse,
    unregister_omniverse
)


## ======================================================================
classes = (
    NucleusConnectionPreferences,
    OMNI_ConnectionListItem,
    OMNI_LocationListItem,
    OMNI_FileListItem,
    OmniNucleusSettings,
    OMNI_PT_NucleusPanel,
    OMNI_PT_ConnectionsPanel,
    OMNI_PT_ProjectPanel,
    OMNI_PT_LoggingPanel,
    OMNI_UL_ConnectionList,
    OMNI_UL_LocationList,
    OMNI_UL_FileList,
    OMNI_OT_FileSelect,
    OMNI_OT_ExportFileSelect,
    OMNI_OT_ImportFileSelect,
    OMNI_OT_OpenParentDirectory,
    OMNI_OT_CreateDirectory,
    OMNI_OT_RefreshDirectory,
    OMNI_OT_OpenConnection,
    OMNI_OT_CloseConnection,
    OMNI_OT_ImportUSD,
    OMNI_OT_ExportUSD,
    OMNI_OT_AddBookmark,
    OMNI_OT_ClearConnectionStatus,
    USDImportProps,
    USDExportProps
)


def register_omni_nucleus():
    unregister_omni_nucleus()

    register_omniverse()

    for item in classes:
        bpy.utils.register_class(item)

    bpy.types.Scene.omni_nucleus = bpy.props.PointerProperty(type=OmniNucleusSettings)
    bpy.types.Scene.omni_usd_import_props = bpy.props.PointerProperty(type=USDImportProps)
    bpy.types.Scene.omni_usd_export_props = bpy.props.PointerProperty(type=USDExportProps)

    register_icons()


## ======================================================================
def unregister_omni_nucleus():

    unregister_omniverse()

    for item in classes:
        try:
            bpy.utils.unregister_class(item)
        except:
            continue

    if hasattr(bpy.types.Scene, "omni_nucleus"):
        del bpy.types.Scene.omni_nucleus
    if hasattr(bpy.types.Scene, "omni_usd_import_props"):
        del bpy.types.Scene.omni_usd_import_props
    if hasattr(bpy.types.Scene, "omni_usd_export_props"):
        del bpy.types.Scene.omni_usd_export_props

    reset_logger()

    unregister_icons()

