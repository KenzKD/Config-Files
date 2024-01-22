import bpy
from bpy.props import StringProperty, BoolProperty
import os
from .. utils.system import abspath, open_folder
from .. utils.property import step_list
from .. utils.asset import get_asset_library_reference, set_asset_library_reference, get_asset_import_method, set_asset_import_method, get_asset_details_from_space, get_asset_ids
from .. utils.workspace import get_window_region_from_area, get_3dview_area
from .. utils.registration import get_prefs
from .. colors import red


class Open(bpy.types.Operator):
    bl_idname = "machin3.filebrowser_open"
    bl_label = "MACHIN3: Open in System's filebrowser"
    bl_description = "Open the current location in the System's own filebrowser\nALT: Open .blend file"

    path: StringProperty(name="Path")
    blend_file: BoolProperty(name="Open .blend file")

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER'

    def execute(self, context):
        space = context.space_data
        params = space.params

        directory = abspath(params.directory.decode())
        active_file = context.active_file

        active, id_type, local_id = get_asset_ids(context)

        if self.blend_file:
            if active_file.asset_data:

                if not get_asset_ids(context)[2]:
                    bpy.ops.asset.open_containing_blend_file()

                else:


                    area = get_3dview_area(context)

                    if area:
                        region, region_data = get_window_region_from_area(area)
                        print(area, region, region_data)

                        with context.temp_override(area=area, region=region, region_data=region_data):
                            scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale
                            coords = (context.region.width / 2, 100 * scale)
                            bpy.ops.machin3.draw_label(text="The blend file containing this asset is already open.", coords=coords, color=red, alpha=1, time=5)


            else:
                path = os.path.join(directory, active_file.relative_path)
                bpy.ops.machin3.open_library_blend(blendpath=path)

        else:

            # for the asset browser, fetch the library location via the custom get_asset_details_from_space() function
            if active_file.asset_data:
                _, libpath, _, _ = get_asset_details_from_space(context, space, debug=False)

                if libpath:
                    open_folder(libpath)


            # for the filebrowser, you can just fetch it from params.directory
            else:
                open_folder(directory)

        return {'FINISHED'}


class Toggle(bpy.types.Operator):
    bl_idname = "machin3.filebrowser_toggle"
    bl_label = "MACHIN3: Toggle Filebrowser"
    bl_description = ""

    type: StringProperty()

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER'

    def execute(self, context):
        params = context.space_data.params

        # 1

        if self.type == 'SORT':

            # FILEBROWSER - toggle sorting by name or time
            if context.area.ui_type == 'FILES':
                if params.sort_method == 'FILE_SORT_ALPHA':
                    params.sort_method = 'FILE_SORT_TIME'

                else:
                    params.sort_method = 'FILE_SORT_ALPHA'

            # ASSETBROWSER - cycle asset liraries
            elif context.area.ui_type == 'ASSETS':
                base_libs = ['LOCAL']

                # TODO: make ALL and ESSENTIALS optional via addon prefs
                if bpy.app.version >= (3, 5, 0):
                    base_libs.insert(0, 'ALL')
                    base_libs.append('ESSENTIALS')

                asset_libraries = base_libs + [lib.name for lib in context.preferences.filepaths.asset_libraries]

                current = get_asset_library_reference(params)
                next = step_list(current, asset_libraries, 1)
                set_asset_library_reference(params, next)


        # 2

        elif self.type == 'DISPLAY_TYPE':

            # FILEBROWSER - toggle display type
            if context.area.ui_type == 'FILES':
                if params.display_type == 'LIST_VERTICAL':
                    params.display_type = 'THUMBNAIL'

                else:
                    params.display_type = 'LIST_VERTICAL'

            # ASSETBROWSER - cycle import methods
            elif context.area.ui_type == 'ASSETS':

                # only cycle importy types when you aren't in the LOCAL lib, in that case the prop is not used and is hidden in the UI, so you may end up changing it accidentally
                current = get_asset_library_reference(params)

                if current != 'LOCAL':
                    import_methods = ['LINK', 'APPEND', 'APPEND_REUSE']

                    if bpy.app.version >= (3, 5, 0):
                        import_methods.insert(0, 'FOLLOW_PREFS')

                    current = get_asset_import_method(params)
                    next = step_list(current, import_methods, 1)
                    set_asset_import_method(params, next)


        # 4 toggle hidden files in file browser

        elif self.type == 'HIDDEN':
            if context.area.ui_type == 'FILES':
                params.show_hidden = not params.show_hidden
                params.use_filter_backup = params.show_hidden

        return {'FINISHED'}


class CycleThumbs(bpy.types.Operator):
    bl_idname = "machin3.filebrowser_cycle_thumbnail_size"
    bl_label = "MACHIN3: Cycle Thumbnail Size"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    reverse: BoolProperty(name="Reverse Cycle Diretion")

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER' and context.space_data.params.display_type == 'THUMBNAIL'

    # 3  

    def execute(self, context):
        params = context.space_data.params

        if bpy.app.version >= (4, 0, 0):
            if params.display_size == 256 and not self.reverse:
                params.display_size = 16

            elif params.display_size == 16 and self.reverse:
                params.display_size = 256

            else:
                params.display_size += -20 if self.reverse else 20

        else:
            sizes = ['TINY', 'SMALL', 'NORMAL', 'LARGE']
            params.display_size = step_list(params.display_size, sizes, -1 if self.reverse else 1, loop=True)


        return {'FINISHED'}
