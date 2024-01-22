import bpy
from bpy.types import CompositorNodeAntiAliasing
from bpy.utils import time_from_frame
from .. utils.ui import get_mouse_pos, warp_mouse, get_window_space_co2d
from .. utils.system import printd
from .. utils.registration import get_prefs
from .. utils.workspace import is_fullscreen, get_assetbrowser_space
from .. utils.asset import get_asset_import_method, get_asset_library_reference, set_asset_import_method, set_asset_library_reference
from .. colors import red, yellow


supress_assetbrowser_toggle = False

class ToggleVIEW3DRegion(bpy.types.Operator):
    bl_idname = "machin3.toggle_view3d_region"
    bl_label = "MACHIN3: Toggle 3D View Region"
    bl_description = "Toggle 3D View Region based on Mouse Position"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):

        # init asset_browser_prefs dict
        self.initiate_asset_browser_area_settings(context, debug=False)

        # find_areas directly above or below the active area
        areas = self.get_areas(context, debug=False)

        # get regions
        regions = self.get_regions(context.area, debug=False)

        # get mouse pos
        get_mouse_pos(self, context, event, hud=False)

        # get the region type to toggle
        region_type = self.get_region_type_from_mouse(context, debug=False)

        # then toggle it
        area = self.toggle_region(context, areas, regions, region_type, debug=False)

        # warp the mouse to the region border, so it can be adjusted right away if the user choses so
        if area and get_prefs().region_warp_mouse_to_asset_border:
            self.warp_mouse_to_border(context, area, region_type)

        # context.area.tag_redraw()
        return {'FINISHED'}


    # UTILS

    def get_areas(self, context, debug=False):
        '''
        check the screen for areas exactly above or below the active area
        so they have to have the same x coord and width!
        '''

        active_area = context.area

        if debug:
            print()
            print("active area:", active_area.x, active_area.y, active_area.width, active_area.height)

        areas = {'TOP': None,
                 'BOTTOM': None,
                 'ACTIVE': active_area}

        for area in context.screen.areas:
            if area == active_area:
                # if debug:
                #     print(">", area.type)
                continue
            else:
                if debug:
                    print(" ", area.type)
                    print("  ", area.x, area.y, area.width, area.height)

                if area.x == active_area.x and area.width == active_area.width:
                    location = 'BOTTOM' if area.y < active_area.y else 'TOP'

                    if debug:
                        print(f"   area is in the same 'column' and located at the {location}")

                    # replace existing location, if it is closer to the active one, compared to the previously stored region above or below the active
                    if areas[location]:
                        if location == 'BOTTOM' and area.y > areas[location].y:
                            areas[location] = area

                        elif location == 'TOP' and area.y < areas[location].y:
                            areas[location] = area

                    else:
                        areas[location] = area

        if debug:
            for location, area in areas.items():
                print(location)

                if area:
                    print("", area.type)

        return areas

    def get_regions(self, area, debug=False):
        '''
        collect toolbar, sidebar, redo panel and asset shelf regions in a dict
        ignore others like WINDOW, HEADER
        '''
        
        regions = {}

        for region in area.regions:
            if region.type in ['TOOLS', 'TOOL_HEADER', 'TOOL_PROPS', 'UI', 'HUD', 'ASSET_SHELF', 'ASSET_SHELF_HEADER']:
                regions[region.type] = region

        if debug:
            printd(regions)

        return regions

    def get_region_type_from_mouse(self, context, debug=False):
        '''
        from the mouse position, get the type of the region you want to toggle
        unless it's over a non-WINDOW region already, then just toggle this one
        '''

        prefer_left_right = get_prefs().region_prefer_left_right
        close_range = get_prefs().region_close_range

        if context.region.type in ['WINDOW', 'HEADER', 'TOOL_HEADER']:
            area = context.area

            # get mouse position expresed in percentages
            x_pct = (self.mouse_pos.x / area.width) * 100
            y_pct = (self.mouse_pos.y / area.height) * 100

            is_left = x_pct < 50
            is_bottom = y_pct < 50


            # check left/right sides first, and only choose bottom/top if within close range
            if prefer_left_right:
                side = 'LEFT' if is_left else 'RIGHT'

                if y_pct <= close_range:
                    side = 'BOTTOM'

                elif y_pct >= 100 - close_range:
                    side = 'TOP'

            # check bottom/top sides first, and only choose left/right if within close range
            else:
                side = 'BOTTOM' if is_bottom else 'TOP'

                if x_pct <= close_range:
                    side = 'LEFT'

                elif x_pct >= 100 - close_range:
                    side = 'RIGHT'


            if debug:
                # print()
                # print("area")
                # print(f" width x height: {area.width} x {area.height}")
                #
                # print()
                # print("mouse")
                # # print(f" x x y: {self.mouse_pos.x} x {self.mouse_pos.y}")
                # print(f" x x y: {x_pct}% x {y_pct}%")
                #
                # print()
                # print("sides")
                # print(" is left:", is_left)
                # print(" is bottom:", is_bottom)

                print()
                print(f"side: {side}")


            if side == 'LEFT':
                return 'TOOLS'

            elif side == 'RIGHT':
                return 'UI'

            elif side == 'BOTTOM':
                return 'ASSET_BOTTOM'

            elif side == 'TOP':
                return 'ASSET_TOP'

        else:
            return context.region.type

    def get_asset_shelf(self, regions, debug=False):
        '''
        check if there actually are asset shelf regions
        and if so, wether it's at the BOTTOM or TOP
        '''

        shelf = regions.get('ASSET_SHELF', None)
        header = regions.get('ASSET_SHELF_HEADER', None)

        # the regions should always exist (in Blender 4.0), but that doesn't mean they are available to the user
        if shelf and header:
            if debug:
                print()

            if header.height > 1:
                if debug:
                    print("asset shelf available!")

                if shelf.height > 1:
                    if debug:
                        print(" shelf is open")

                else:
                    if debug:
                        print(" shelf is collapsed")

                # NOTE: in 4.0 you can flip the shelf using F5, but you can't flip the shelf header yet
                if debug:
                    print(" alignment:", shelf.alignment)

                return shelf

            else:
                if debug:
                    print("asset shelf not available!")

        else:
            if debug:
                print("asset shelf not supported in this Blender version")

    def is_close_area_of_type(self, area, area_type='ASSET_BROWSER'):  
        '''
        compare passed in area with area_type arg
        note, that for ASSET_BROWSER you hace to check the ui_type to, as it's still just a FILE_BROWSER as of Blender 4

        we do this check to eunsure we only close an area that would would open too, so we don't want to close a time line for instance, until we support opening timelines
        '''

        if area_type == 'ASSET_BROWSER':
            return area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS'

        else:
            return area.type == area_type

    def get_area_split_factor(self, context, total_height, stored_asset_browser_height, is_bottom, debug=False):
        '''
        calculate asset split factor, from stored height in pixels divided by the total height of the current pre-split area
        NOTE, depending of the percentage and depending on the general UI scale it needs to be compensated by a few pixels
        also it needs to be capped at less than 50%, I chose 45%, or the new region will be current one
        '''

        if debug:
            print()
            print("total height:", total_height)
            print("  percentage:", stored_asset_browser_height / total_height)

        if is_bottom:
            if debug:
                print("bottom split")

            if context.preferences.system.ui_scale >= 2:
                if debug:
                    print(" big ui scale")

                if stored_asset_browser_height / total_height <= 0.12:
                    area_height = stored_asset_browser_height + 3

                    if debug:
                        print("  smaller than 37.5%, compensating with", 3, "pixels")

                elif stored_asset_browser_height / total_height <= 0.375:
                    area_height = stored_asset_browser_height + 2

                    if debug:
                        print("  smaller than 37.5%, compensating with", 2, "pixels")

                else:
                    area_height = stored_asset_browser_height + 1

                    if debug:
                        print("  bigger than 37.5% compensating with", 1, "pixels, capped at 45%")

            else:
                if debug:
                    print(" normal ui scale")

                if stored_asset_browser_height / total_height <= 0.25:
                    area_height = stored_asset_browser_height + 1

                    if debug:
                        print("  smaller than 25%, compensating with", 1, "pixels")

                else:
                    area_height = stored_asset_browser_height

                    if debug:
                        print("  using original height, capped at 45%")

        else:
            if context.preferences.system.ui_scale >= 2:
                if debug:
                    print(" big ui scale")

                if stored_asset_browser_height / total_height <= 0.12:
                    area_height = stored_asset_browser_height + 4

                    if debug:
                        print("  smaller than 12%, compensating with", 4, "pixels")

                elif stored_asset_browser_height / total_height <= 0.375:
                    area_height = stored_asset_browser_height + 3

                    if debug:
                        print("  smaller than 37.5%, compensating with", 3, "pixels")

                else:
                    area_height = stored_asset_browser_height + 2

                    if debug:
                        print("  bigger than 37.5% compensating with", 2, "pixels, capped at 45%")

            else:
                if debug:
                    print(" normal ui scale")

                if stored_asset_browser_height / total_height <= 0.25:
                    area_height = stored_asset_browser_height + 2

                    if debug:
                        print("  smaller than 25%, compensating with", 2, "pixels")

                else:
                    area_height = stored_asset_browser_height + 1

                    if debug:
                        print("  bigger than 25% compensating with", 1, "pixels, capped at 45%")

        area_split_factor = min(0.45, area_height / total_height)

        return area_split_factor, area_height 

    def warp_mouse_to_border(self, context, area, region_type):
        '''
        note, unfortunately my attempts to invoke screen.area_move() failed due to wrong context, even with various overrides
        so positioning the mouse on the area border is all I can do for now
        '''
        
        if area and region_type in ['ASSET_BOTTOM', 'ASSET_TOP']:
            mouse = get_window_space_co2d(context, self.mouse_pos)
            if region_type == 'ASSET_BOTTOM':
                mouse.y = area.y + area.height

            else:
                mouse.y = area.y

            warp_mouse(self, context, mouse, region=False)


    # ASSET BROWSER SETTINGS - stored on scene.M3['asset_browser_prefs']

    def initiate_asset_browser_area_settings(self, context, debug=False):
        '''
        1. ensure the asset browser prefs are stored on the scene level in a dict
        2. and reference it on the op via self.prefs
        3. then add the current screen to it, if it's not stored already
        '''

        if not context.scene.M3.get('asset_browser_prefs', False):
            context.scene.M3['asset_browser_prefs'] = {}

            if debug:
                print("initiating asset browser prefs on scene object")

        self.prefs = context.scene.M3.get('asset_browser_prefs')

        # ensure the curretn screen is in the asset browser presf
        if context.screen.name not in self.prefs:
            if debug:
                print("initiating asset browser prefs for screen", context.screen.name)

            empty = {'area_height': 250,

                     'libref': 'ALL',
                     'catalog_id': '00000000-0000-0000-0000-000000000000',
                     'import_method': 'FOLLOW_PREFS',
                     'display_size': 96 if bpy.app.version >= (4, 0, 0) else 'SMALL',

                     'header_align': 'TOP',

                     'show_region_toolbar': True,
                     'show_region_tool_props': False,

                     'filter_search': '',
                     'filter_action': True,
                     'filter_group': True,
                     'filter_material': True,
                     'filter_node_tree': True,
                     'filter_object': True,
                     'filter_world': True,
                     }

            self.prefs[context.screen.name] = {'ASSET_TOP': empty,
                                               'ASSET_BOTTOM': empty.copy()}

        # if True:
        if debug:
            printd(self.prefs.to_dict())

    def store_asset_browser_area_settings(self, context, area, region_type, screen_name):
        '''
        store the passed in area settings on the scene

        NOTE: All and Unassigned catagories can't be read out, but Unassigned can be set by setting '00000000-0000-0000-0000-000000000000', or potentially any other invalid one
        '''

        for space in area.spaces:
            if space.type == 'FILE_BROWSER':
                if space.params:
                    libref = get_asset_library_reference(space.params)
                    import_method = get_asset_import_method(space.params)

                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['area_height'] = area.height

                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['libref'] = libref
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['import_method'] = import_method
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['catalog_id'] = space.params.catalog_id
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['display_size'] = space.params.display_size

                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['show_region_toolbar'] = space.show_region_toolbar
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['show_region_tool_props'] = space.show_region_tool_props

                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_search'] = space.params.filter_search
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_action'] = space.params.filter_asset_id.filter_action
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_group'] = space.params.filter_asset_id.filter_group
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_material'] = space.params.filter_asset_id.filter_material
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_node_tree'] = space.params.filter_asset_id.filter_node_tree
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_object'] = space.params.filter_asset_id.filter_object
                    context.scene.M3['asset_browser_prefs'][screen_name][region_type]['filter_world'] = space.params.filter_asset_id.filter_world

        for region in area.regions:
            if region.type == 'HEADER':
                context.scene.M3['asset_browser_prefs'][screen_name][region_type]['header_align'] = region.alignment

        # print()
        # print("storing")
        # printd(context.scene.M3['asset_browser_prefs'].to_dict())

    def apply_asset_browser_area_settings(self, context, area, space, params, screen_name, region_type):
        '''
        apply the stored asset browsr settings on the newly created area/space/params for the given screen_name and region_type
        '''

        if screen_name in self.prefs:

            # fetch them
            libref = self.prefs[screen_name][region_type]['libref']
            import_method = self.prefs[screen_name][region_type]['import_method']
            catalog_id = self.prefs[screen_name][region_type]['catalog_id']
            display_size = self.prefs[screen_name][region_type]['display_size']

            # reset display size to a default value when encounterign wrong type, such as when openeing 3.6 file in 4.0 or the other way around
            if bpy.app.version >= (4, 0, 0) and isinstance(display_size, str):
                print("WARNING: discovered legacy string value of asset browser display_size prop, resetting to size 96")
                display_size = 96

            elif bpy.app.version < (4, 0, 0) and isinstance(display_size, int):
                print("WARNING: discovered new string value of asset browser display_size prop, in legacy Blender version, resetting to size SMALL")
                display_size = 'SMALL'

            show_region_toolbar = self.prefs[screen_name][region_type]['show_region_toolbar']
            show_region_tool_props = self.prefs[screen_name][region_type]['show_region_tool_props']

            filter_search = self.prefs[screen_name][region_type]['filter_search']
            filter_action = self.prefs[screen_name][region_type]['filter_action']
            filter_group = self.prefs[screen_name][region_type]['filter_group']
            filter_material = self.prefs[screen_name][region_type]['filter_material']
            filter_node_tree = self.prefs[screen_name][region_type]['filter_node_tree']
            filter_object = self.prefs[screen_name][region_type]['filter_object']
            filter_world = self.prefs[screen_name][region_type]['filter_world']

            # then set them
            set_asset_library_reference(params, libref)
            set_asset_import_method(params, import_method)
            params.catalog_id = catalog_id
            params.display_size = display_size

            # NOTE: some very odd behavior here, show_region_toolbar needs to be negated to maintain whatever was set, but even that may not always work
            # new_space.show_region_toolbar = not show_region_toolbar
            # NOTE: I think it was due to the T key still being passed through, so the normal toggle took over!
            # ####: it's no longer happening now, that the ToggleASSETBROWSERRegion() takes over in that region
            space.show_region_toolbar = show_region_toolbar

            # set the 'N panel' too, which in the FILE_BROWSER is called show_region_tool_props, not show_region_UI like in the 3d view!
            space.show_region_tool_props = show_region_tool_props

            params.filter_search = filter_search
            params.filter_asset_id.filter_action = filter_action
            params.filter_asset_id.filter_group = filter_group
            params.filter_asset_id.filter_material = filter_material
            params.filter_asset_id.filter_node_tree = filter_node_tree
            params.filter_asset_id.filter_object = filter_object
            params.filter_asset_id.filter_world = filter_world

            # finalyl flip the HEADER region if necessary
            for region in area.regions:
                if region.type == 'HEADER':
                    if region.alignment != self.prefs[screen_name][region_type]['header_align']:
                        with context.temp_override(area=area, region=region):
                            bpy.ops.screen.region_flip()


    # TOGGLE

    def toggle_region(self, context, areas, regions, region_type='TOOLS', debug=False):
        '''
        toggle region based on type arg
        '''

        # if debug:
        #     print()
        #     print("toggling:", region_type)

        # get context
        space = context.space_data
        region = regions[region_type] if region_type in regions else None
        screen_name = context.screen.name

        # get settings
        toggle_asset_shelf = get_prefs().region_toggle_assetshelf
        toggle_asset_top = get_prefs().region_toggle_assetbrowser_top
        toggle_asset_bottom = get_prefs().region_toggle_assetbrowser_bottom

        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale


        # Toolbar

        if region_type == 'TOOLS':
            space.show_region_toolbar = not space.show_region_toolbar


        # Sidebar

        elif region_type == 'UI':
            space.show_region_ui = not space.show_region_ui

            if region:

                # it's possible the region can't be toggled because there is not enough space, in which case the width will be 1
                if region.width == 1:
                    coords = (context.region.width / 2, 100 * scale)
                    bpy.ops.machin3.draw_label(text="Can't Toggle the Sidebar", coords=coords, color=red, alpha=1, time=1.2)

                    coords = (context.region.width / 2, (100 - 20) * scale)
                    bpy.ops.machin3.draw_label(text="Insufficient view space", coords=coords, color=red, alpha=1, time=1.5)


        # Redo Panel / Adjust Last Operation

        elif region_type == 'HUD':
            space.show_region_hud = not space.show_region_hud


        # Disable Asset Shelf (as mouse is position on it)

        elif region_type in ['ASSET_SHELF', 'ASSET_SHELF_HEADER']:
            space.show_region_asset_shelf = not space.show_region_asset_shelf


        # Asset Browser

        elif region_type in ['ASSET_BOTTOM', 'ASSET_TOP']:

            shelf = self.get_asset_shelf(regions)


            # TOGGLE ASSET SHELF, if available and the prefs are set accordingly

            if shelf and toggle_asset_shelf:

                # only toggle the shelf if it's actually aligned with the region_type
                # because in addition to the shelf we still want to be albe to toggle the browser as well, just on the oder side of the
                if region_type == 'ASSET_BOTTOM' and shelf.alignment == 'BOTTOM' or region_type == 'ASSET_TOP' and shelf.alignment == 'TOP':
                    space.show_region_asset_shelf = not space.show_region_asset_shelf

                    return

            # TOGGLE ASSET BROWSER aka SPLIT or CLOSE AREA 

            if is_fullscreen(context.screen):
                coords = (context.region.width / 2, 100 * scale if region_type == 'ASSET_BOTTOM' else context.region.height - 100 * scale)
                bpy.ops.machin3.draw_label(text="You can't Split this area in Fullscreen", coords=coords, color=red, alpha=1, time=2)

            else:
                if region_type == 'ASSET_BOTTOM' and  toggle_asset_bottom or region_type == 'ASSET_TOP' and toggle_asset_top:
                    return self.toggle_area(context, areas, region_type, screen_name, scale)

        # TODO?
        # show_region_header True
        # show_region_tool_header True

    def toggle_area(self, context, areas, region_type, screen_name, scale):
        '''
        "toggle" area, by splitting the current area or closing the one above or below the current one
        '''

        # print(f"splitting the area to create assetbrowser at {'BOTTOM' if is_bottom else 'TOP'}")

        # get settings
        below_area_split = 'ASSET_BROWSER'
        top_area_split = 'ASSET_BROWSER'
        is_bottom = region_type == 'ASSET_BOTTOM'


        # CLOSE EXISTING AREA at the BOTTOM or TOP, if present, and before you do, fetch it's properties and store them, for later restoration

        close_area = areas['BOTTOM' if is_bottom else 'TOP']

        if close_area and self.is_close_area_of_type(close_area, 'ASSET_BROWSER'):
            self.store_asset_browser_area_settings(context, close_area, region_type, screen_name)

            with context.temp_override(area=close_area):
                bpy.ops.screen.area_close()


        # OPEN NEW AREA at BOTTOM or TOP

        else:

            total_height = areas['ACTIVE'].height
            area_height = self.prefs[screen_name][region_type]['area_height']

            # calculate the area split factor
            area_split_factor, _ = self.get_area_split_factor(context, total_height, area_height, is_bottom)

            # NOTE: supress automatic invokation of ToggleASSETBROWSERRegion()
            # ####: for some reason this happens due to the split op I think, but not sure actually
            # ####: and we only do this if the mouse will end up in the new area, as otherwise you will have a dead keypress when you enter the new area and try to toggle something
            global supress_assetbrowser_toggle

            if is_bottom:
                if self.mouse_pos.y <= area_height:
                    supress_assetbrowser_toggle = True

            else:
                if self.mouse_pos.y >= total_height - area_height:
                    supress_assetbrowser_toggle = True

            # fetch all currently existing areas
            all_areas = [area for area in context.screen.areas]

            # do the split
            bpy.ops.screen.area_split(direction='HORIZONTAL', factor=area_split_factor if is_bottom else 1 - area_split_factor)

            # find the new area by comparison
            new_areas = [area for area in context.screen.areas if area not in all_areas]

            # and turn it into an asset browser
            if new_areas:
                new_area = new_areas[0]
                new_area.type = 'FILE_BROWSER'
                new_area.ui_type = 'ASSETS'

                for new_space in new_area.spaces:
                    if new_space.type == 'FILE_BROWSER':

                        # apply stored settings to new asset browser area
                        if new_space.params:
                            self.apply_asset_browser_area_settings(context, new_area, new_space, new_space.params, screen_name, region_type)

                        # NOTE: space.params can be None, so we can't set Library, or any other of the spaces settings
                        # ####: however, if you manually turn the 3d view into an asset browser and back into a 3d view again, then params will be available!
                        else:
                            coords = (context.region.width / 2, 100 * scale if region_type == 'ASSET_BOTTOM' else context.region.height - (80 * scale + context.region.height * area_split_factor))
                            bpy.ops.machin3.draw_label(text="WARNING: Assetbrowser couldn't be set up yet, due to Blender shenanigans.", coords=coords, color=red, alpha=1, time=5)

                            coords = (context.region.width / 2, 80 * scale if region_type == 'ASSET_BOTTOM' else context.region.height - (100 * scale + context.region.height * area_split_factor))
                            bpy.ops.machin3.draw_label(text="This is normal on a new 3D View!", coords=coords, color=red, alpha=1, time=5)

                            coords = (context.region.width / 2, 60 * scale if region_type == 'ASSET_BOTTOM' else context.region.height - (120 * scale + context.region.height * area_split_factor))
                            bpy.ops.machin3.draw_label(text="TO FIX IT, DO THIS: Change THIS 3D View into an Asset browser, and back again", coords=coords, color=yellow, alpha=1, time=5)

                            coords = (context.region.width / 2, 40 * scale if region_type == 'ASSET_BOTTOM' else context.region.height - (140 * scale + context.region.height * area_split_factor))
                            bpy.ops.machin3.draw_label(text="Then save the blend file, for the change to stick", coords=coords, color=yellow, alpha=1, time=5)

                return new_area


class ToggleASSETBROWSERRegion(bpy.types.Operator):
    bl_idname = "machin3.toggle_asset_browser_region"
    bl_label = "MACHIN3: Toggle Asset Browser Region"
    bl_description = "Toggle Asset Browser Region based on Mouse Position"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER' and context.area.ui_type == 'ASSETS'

    def invoke(self, context, event):
        global supress_assetbrowser_toggle

        if supress_assetbrowser_toggle:
            supress_assetbrowser_toggle = False
            # print("supressing")

            return {'CANCELLED'}

        # init asset_browser_prefs dict
        ToggleVIEW3DRegion.initiate_asset_browser_area_settings(self, context, debug=False)

        # find_areas directly above or below the active area
        areas = ToggleVIEW3DRegion.get_areas(self, context, debug=False)

        # find out of there is a 3d view above or below the asset browser
        self.view3d_above =  areas['TOP'] if areas['TOP'] and areas['TOP'].type == 'VIEW_3D' else None
        self.view3d_below =  areas['BOTTOM'] if areas['BOTTOM'] and areas['BOTTOM'].type == 'VIEW_3D' else None

        # if there is a 3dview above or below, then you can in fact close the curretn asset browsr
        can_close = bool(self.view3d_above or self.view3d_below)
        # print("can close:", can_close)

        # get mouse pos
        get_mouse_pos(self, context, event, hud=False)

        # get the region type to toggle
        region_type = self.get_region_type_from_mouse(context, can_close, debug=False)

        # then toggle it
        self.toggle_region(context, areas, region_type, debug=False)

        # context.area.tag_redraw()
        return {'FINISHED'}

    def get_region_type_from_mouse(self, context, can_close, debug=False):
        '''
        from the mouse position, get the type of the region you want to toggle
        unless it's over a non-WINDOW region already, then just toggle this one
        '''

        close_range = get_prefs().region_close_range if can_close else 50

        # print()
        # print(context.region.type)
        # print(self.mouse_pos)

        if context.region.type in ['WINDOW', 'HEADER']:
            area = context.area
            region_width = 0

            # in the asset browser, the TOOLS region will the mouse to the right, but the area.width stays unaffected
            # bui only for when in th WINDOW region, not when over the HEADER!
            for region in area.regions:
                if region.type == 'TOOLS':
                    if context.region.type == 'WINDOW':
                        region_width = region.width

                    break

            # get mouse position expresed in percentages, and consider the TOOLS header width too, which pushes the mouse to the right, while keeping the area width unaffected
            # x_pct = (self.mouse_pos.x / area.width) * 100
            x_pct = ((self.mouse_pos.x + region_width)/ area.width) * 100

            if x_pct <= close_range:
                side = 'LEFT'

            elif x_pct >= 100 - close_range:
                side = 'RIGHT'

            else:
                side = 'CENTER'

            if debug:
                print()
                print("area width:", area.width)
                print("tools region width:", region_width)
                # print("mouse pos:", self.mouse_pos.x)
                print("mouse pos, corrected:", self.mouse_pos.x + region_width)

                print()
                print("mouse.x in %", x_pct)

                print()
                print(f"side: {side}")

            if side == 'LEFT':
                return 'TOOLS'

            elif side == 'RIGHT':
                return 'TOOL_PROPS'

            elif side == 'CENTER':
                return 'CLOSE'

        else:
            return context.region.type

    def toggle_region(self, context, areas, region_type='TOOLS', debug=False):
        '''
        toggle region based on type arg
        '''

        # if debug:
        #     print()
        #     print("toggling:", region_type)


        # CLOSE ASSET BROWSER

        if region_type == 'CLOSE':

            # store the props before closing
            area = areas['ACTIVE']
            region_type = 'ASSET_BOTTOM' if self.view3d_above else 'ASSET_TOP'
            screen_name = context.screen.name

            ToggleVIEW3DRegion.store_asset_browser_area_settings(self, context, area, region_type, screen_name)

            # then close
            bpy.ops.screen.area_close()


        # TOGGLE TOOLS (library and catalog slection) or ACTIVE ASSET info panel
        else:
            space = context.space_data

            if region_type == 'TOOLS':
                space.show_region_toolbar = not space.show_region_toolbar

            elif region_type == 'TOOL_PROPS':
                space.show_region_tool_props = not space.show_region_tool_props


class AreaDumper(bpy.types.Operator):
    bl_idname = "machin3.area_dumper"
    bl_label = "MACHIN3: Area Dumper"
    bl_description = "description"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # return True
        return False

    def execute(self, context):

        print()
        print("spaces")
        for space in context.area.spaces:
            if space.type == 'FILE_BROWSER':
                for d in dir(space):
                    print("", d, getattr(space, d))

                if space.params:
                    print()
                    print("params")

                    for d in dir(space.params):
                        print("", d, getattr(space.params, d))


        return {'FINISHED'}
