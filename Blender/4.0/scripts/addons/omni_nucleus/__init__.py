# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

bl_info = {
    "name": "Nucleus Connector",
    "author": "NVIDIA Corporation",
    "version": (1, 0, 1),
    "blender": (3, 5, 0),
    "location": "View3D > Toolbar > Omniverse",
    "description": "NVIDIA Omniverse tools for accessing Nucleus assts",
    "warning": "",
    "doc_url": "",
    "category": "Omniverse",
}

omniverse_module_loaded = True

try:
    import omniverse
except:
    omniverse_module_loaded = False

if omniverse_module_loaded:
    from .registration import (
        register_omni_nucleus,
        unregister_omni_nucleus
    )
else:
    from .ui_load_warning import (
        register_warning_panel,
        unregister_warning_panel
    )

## ======================================================================

def register():
    if omniverse_module_loaded:
        unregister()
        register_omni_nucleus()
    else:
        unregister()
        register_warning_panel()


## ======================================================================
def unregister():
    if omniverse_module_loaded:
        unregister_omni_nucleus()
    else:
        unregister_warning_panel()

