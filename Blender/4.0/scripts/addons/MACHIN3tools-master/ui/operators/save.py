import bpy
from bpy.props import BoolProperty, StringProperty
import os
import time
import subprocess
import shutil
from ... utils.registration import get_addon, get_prefs
from ... utils.system import add_path_to_recent_files, get_incremented_paths, get_next_files, get_temp_dir
from ... utils.ui import popup_message, get_icon
from ... colors import green


class New(bpy.types.Operator):
    bl_idname = "machin3.new"
    bl_label = "Current file is unsaved. Start a new file anyway?"
    bl_description = "Start new .blend file"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # TODO: passing the app_template arg seems to cause Blender to crash, when calling the op from the Sculpting template for instance
        # ####: the same op (with app_template arg) does seem to work in Blender however, but I've had it crash once as well

        # bpy.ops.wm.read_homefile(app_template="", load_ui=True)
        bpy.ops.wm.read_homefile(load_ui=True)

        return {'FINISHED'}

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event)
        else:
            # bpy.ops.wm.read_homefile(app_template="", load_ui=True)
            bpy.ops.wm.read_homefile(load_ui=True)
            return {'FINISHED'}


# TODO: file size output

class Save(bpy.types.Operator):
    bl_idname = "machin3.save"
    bl_label = "Save"
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        currentblend = bpy.data.filepath

        if currentblend:
            return f"Save {currentblend}"
        return "Save unsaved file as..."

    def execute(self, context):
        currentblend = bpy.data.filepath

        if currentblend:
            bpy.ops.wm.save_mainfile()

            t = time.time()
            localt = time.strftime('%H:%M:%S', time.localtime(t))
            print("%s | Saved blend: %s" % (localt, currentblend))
            self.report({'INFO'}, 'Saved "%s"' % (os.path.basename(currentblend)))

        else:
            bpy.ops.wm.save_mainfile('INVOKE_DEFAULT')

        return {'FINISHED'}


class SaveAs(bpy.types.Operator):
    bl_idname = "machin3.save_as"
    bl_label = "MACHIN3: Save As"
    bl_description = "Save the current file in the desired location\nALT: Save as Copy\nCTRL: Save as Asset"
    bl_options = {'REGISTER', 'UNDO'}

    copy: BoolProperty(name="Save as Copy", default=False)
    asset: BoolProperty(name="Save as Asset", default=False)

    def draw(self, context):
        layout = self.layout
        column = layout.column()

    def invoke(self, context, event):
        self.asset = event.ctrl
        self.copy = event.alt
        return self.execute(context)

    def execute(self, context):
        assets = [obj for obj in bpy.data.objects if obj.asset_data]

        if self.asset and assets:
            print(f"\nINFO: Saving as Asset!")
            print(f"      Found {len(assets)} root Object/Assembly Assets in the current file")

            keep = set()
            self.get_asset_objects_recursively(assets, keep)

            # print()
            # print("keep")

            # for obj in keep:
                # print(obj.name)

            remove = [obj for obj in bpy.data.objects if obj not in keep]

            # print()
            # print("remove")

            for obj in remove:
                print(f"WARNING: Removing {obj.name}")
                bpy.data.objects.remove(obj, do_unlink=True)

            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT', copy=True)

        elif self.copy:
            print("\nINFO: Saving as Copy")
            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT', copy=True)

        else:
            # print("INFO: Saving as Current")
            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')

        return {'FINISHED'}

    def get_asset_objects_recursively(self, assets, keep, depth=0):
        '''
        go over passed in asset objects
        if an asset is a collection instance, go deeper and look recursively for all contained objects
        '''

        for obj in assets:
            # print(depth * " ", obj.name)
            keep.add(obj)

            if obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' and obj.instance_collection:
                self.get_asset_objects_recursively(obj.instance_collection.objects, keep, depth + 1)


class SaveIncremental(bpy.types.Operator):
    bl_idname = "machin3.save_incremental"
    bl_label = "Incremental Save"
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        currentblend = bpy.data.filepath

        if currentblend:
            incrpaths = get_incremented_paths(currentblend)

            if incrpaths:
                return f"Save {currentblend} incrementally to {os.path.basename(incrpaths[0])}\nALT: Save to {os.path.basename(incrpaths[1])}"

        return "Save unsaved file as..."

    def invoke(self, context, event):
        currentblend = bpy.data.filepath

        if currentblend:
            incrpaths = get_incremented_paths(currentblend)
            savepath = incrpaths[1] if event.alt else incrpaths[0]

            if os.path.exists(savepath):
                self.report({'ERROR'}, "File '%s' exists already!\nBlend has NOT been saved incrementally!" % (savepath))
                return {'CANCELLED'}

            else:

                # add it to the recent files list
                add_path_to_recent_files(savepath)

                bpy.ops.wm.save_as_mainfile(filepath=savepath)

                t = time.time()
                localt = time.strftime('%H:%M:%S', time.localtime(t))
                print(f"{localt} | Saved {os.path.basename(currentblend)} incrementally to {savepath}")
                self.report({'INFO'}, f"Incrementally saved to {os.path.basename(savepath)}")

        else:
            bpy.ops.wm.save_mainfile('INVOKE_DEFAULT')

        return {'FINISHED'}


class SaveVersionedStartupFile(bpy.types.Operator):
    bl_idname = "machin3.save_versioned_startup_file"
    bl_label = "Save Versioned Startup File"
    bl_options = {'REGISTER'}

    def execute(self, context):
        config_path = bpy.utils.user_resource('CONFIG')
        startup_path = os.path.join(config_path, 'startup.blend')

        if os.path.exists(startup_path):
            indices = [int(f.replace('startup.blend', '')) for f in os.listdir(bpy.utils.user_resource('CONFIG')) if 'startup.blend' in f and f != 'startup.blend']
            biggest_idx = max(indices) if indices else 0

            # create latest versioned startup file from current one
            os.rename(startup_path, os.path.join(config_path, f'startup.blend{biggest_idx + 1}'))

            # save current file as startup file
            bpy.ops.wm.save_homefile()

            self.report({'INFO'}, f'Versioned Startup File saved: {biggest_idx + 1}')

        else:
            # save current file as startup file
            bpy.ops.wm.save_homefile()

            self.report({'INFO'}, f'Initial Startup File saved')

        return {'FINISHED'}


class LoadMostRecent(bpy.types.Operator):
    bl_idname = "machin3.load_most_recent"
    bl_label = "Load Most Recent"
    bl_description = "Load most recently used .blend file"
    bl_options = {"REGISTER"}

    def execute(self, context):
        recent_path = bpy.utils.user_resource('CONFIG', path="recent-files.txt")

        try:
            with open(recent_path) as file:
                recent_files = file.read().splitlines()
        except (IOError, OSError, FileNotFoundError):
            recent_files = []

        if recent_files:
            most_recent = recent_files[0]

            if os.path.exists(most_recent):
                bpy.ops.wm.open_mainfile(filepath=most_recent, load_ui=True)
                self.report({'INFO'}, 'Loaded most recent "%s"' % (os.path.basename(most_recent)))

            else:
                popup_message("File %s does not exist" % (most_recent), title="File not found")

        return {'FINISHED'}


class LoadPrevious(bpy.types.Operator):
    bl_idname = "machin3.load_previous"
    bl_label = "MACHIN3: Load previous file"
    bl_options = {'REGISTER'}

    load_ui: BoolProperty()
    include_backups: BoolProperty()

    @classmethod
    def poll(cls, context):
        if bpy.data.filepath:
            _, prev_file, prev_backup_file = get_next_files(bpy.data.filepath, next=False, debug=False)
            return prev_file or prev_backup_file

    @classmethod
    def description(cls, context, properties):
        folder, prev_file, prev_backup_file = get_next_files(bpy.data.filepath, next=False, debug=False)

        if not prev_file and not prev_backup_file:
            desc = "Your are at the beginning of the folder. There are no previous files to load."

        else:
            desc = f"Load Previous .blend File in Current Folder: {prev_file}"

            if prev_backup_file and prev_backup_file != prev_file:
                desc += f"\nCTRL: including Backups: {prev_backup_file}"

            desc += "\n\nALT: Keep current UI"
        return desc

    def invoke(self, context, event):
        self.load_ui = not event.alt
        self.include_backups = event.ctrl
        return self.execute(context)

    def execute(self, context):
        # print()
        # print("load UI:", self.load_ui)
        # print("include backups:", self.include_backups)

        folder, prev_file, prev_backup_file = get_next_files(bpy.data.filepath, next=False, debug=False)

        is_backup = self.include_backups and prev_backup_file
        file = prev_backup_file if is_backup else prev_file if prev_file else None

        if file:
            filepath = os.path.join(folder, file)
            # print("loading:", filepath)

            # add the path to the recent files list, for some reason it's not done automatically
            add_path_to_recent_files(filepath)

            bpy.ops.wm.open_mainfile(filepath=filepath, load_ui=self.load_ui)
            self.report({'INFO'}, f"Loaded previous {'BACKUP ' if is_backup else ''}file '{file}'")
            return {'FINISHED'}

        # NOTE: unlike LoadNext(), if you are at the beginning, then you truely are at the beginning, there won't be any previous backup files

        return {'CANCELLED'}


class LoadNext(bpy.types.Operator):
    bl_idname = "machin3.load_next"
    bl_label = "MACHIN3: Load next file"
    bl_options = {'REGISTER'}

    load_ui: BoolProperty()
    include_backups: BoolProperty()

    @classmethod
    def poll(cls, context):
        if bpy.data.filepath:
            _, next_file, next_backup_file = get_next_files(bpy.data.filepath, next=True, debug=False)
            return next_file or next_backup_file

    @classmethod
    def description(cls, context, properties):
        folder, next_file, next_backup_file = get_next_files(bpy.data.filepath, next=True, debug=False)

        if not next_file and not next_backup_file:
            desc = "You have reached the end of the folder. There are no next files to load."

        else:
            desc = f"Load Next .blend File in Current Folder: {next_file}"

            if next_backup_file and next_backup_file != next_file:
                desc += f"\nCTRL: including Backups: {next_backup_file}"

            desc += "\n\nALT: Keep current UI"
        return desc

    def invoke(self, context, event):
        self.load_ui = not event.alt
        self.include_backups = event.ctrl
        return self.execute(context)

    def execute(self, context):
        # print()
        # print("load UI:", self.load_ui)
        # print("include backups:", self.include_backups)

        folder, next_file, next_backup_file = get_next_files(bpy.data.filepath, next=True, debug=False)

        is_backup = self.include_backups and next_backup_file
        file = next_backup_file if is_backup else next_file if next_file else None

        if file:
            filepath = os.path.join(folder, file)
            # print("loading:", filepath)

            # add the path to the recent files list, for some reason it's not done automatically
            add_path_to_recent_files(filepath)

            bpy.ops.wm.open_mainfile(filepath=filepath, load_ui=self.load_ui)

            self.report({'INFO'}, f"Loaded next {'BACKUP ' if is_backup else ''}file '{file}'")
            return {'FINISHED'}

        # if both files are None, then the poll will prevent execution of the op
        # so the only case where the filepath is None is if you have reched the end of main .blend files, but backups are still available
        else:
            popup_message([f"You have reached the end of blend files in '{folder}'", "There are still some backup files though, which you can load via CTRL"], title="End of folder reached")

        return {'CANCELLED'}


class OpenTemp(bpy.types.Operator):
    bl_idname = "machin3.open_temp_dir"
    bl_label = "Open"
    bl_description = "Open System's Temp Folder, which is used to Save Files on Quit, Auto Saves and Undo Saves"
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    # filename: StringProperty(options={'HIDDEN'})
    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    filter_blender: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_backup: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})

    load_ui: BoolProperty(name="Load UI", default=True)

    def execute(self, context):
        bpy.ops.wm.open_mainfile(filepath=self.filepath, load_ui=self.load_ui)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.directory = get_temp_dir(context)

        if self.directory:

            # Opens a file selector with an operator. The string properties ‘filepath’, ‘filename’, ‘directory’ and a ‘files’ collection are assigned when present in the operator
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}


decalmachine = None

class Purge(bpy.types.Operator):  
    bl_idname = "machin3.purge_orphans"
    bl_label = "MACHIN3: Purge Orphans"
    bl_options = {'REGISTER', 'UNDO'}

    recursive: BoolProperty(name="Recursive Purge", default=False)

    @classmethod
    def description(cls, context, properties):
        return "Purge Orphans\nALT: Purge Orphans Recursively"

    def invoke(self, context, event):
        global decalmachine
        
        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        self.recursive = event.alt

        before_meshes_count = len(bpy.data.meshes)
        before_curves_count = len(bpy.data.curves)
        before_objects_count = len(bpy.data.objects)
        before_materials_count = len(bpy.data.materials)
        before_images_count = len(bpy.data.images)
        before_nodegroups_count = len(bpy.data.node_groups)
        before_collections_count = len(bpy.data.collections)
        before_scenes_count = len(bpy.data.scenes)
        before_worlds_count = len(bpy.data.worlds)

        # with decalmachine install run it's decal orphan op as well
        if decalmachine:
            bpy.ops.machin3.remove_decal_orphans()

        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=self.recursive)

        after_meshes_count = len(bpy.data.meshes)
        after_curves_count = len(bpy.data.curves)
        after_objects_count = len(bpy.data.objects)
        after_materials_count = len(bpy.data.materials)
        after_images_count = len(bpy.data.images)
        after_nodegroups_count = len(bpy.data.node_groups)
        after_collections_count = len(bpy.data.collections)
        after_scenes_count = len(bpy.data.scenes)
        after_worlds_count = len(bpy.data.worlds)

        meshes_count = before_meshes_count - after_meshes_count
        curves_count = before_curves_count - after_curves_count
        objects_count = before_objects_count - after_objects_count
        materials_count = before_materials_count - after_materials_count
        images_count = before_images_count - after_images_count
        nodegroups_count = before_nodegroups_count - after_nodegroups_count
        collections_count = before_collections_count - after_collections_count
        scenes_count = before_scenes_count - after_scenes_count
        worlds_count = before_worlds_count - after_worlds_count

        # print("meshes:", meshes_count)
        # print("curves:", curves_count)
        # print("objects:", objects_count)
        # print("materials:", materials_count)
        # print("images:", images_count)
        # print("nodegroups:", nodegroups_count)
        # print("collections:", collections_count)
        # print("scenes:", scenes_count)
        # print("worlds:", worlds_count)

        if any([meshes_count, curves_count, objects_count, materials_count, images_count, nodegroups_count, collections_count, scenes_count, worlds_count]):
            total_count = meshes_count + curves_count + objects_count + materials_count + images_count + nodegroups_count + collections_count + scenes_count + worlds_count

            msg = [f"Removed {total_count} data blocks!"]

            if meshes_count:
                msg.append(f" • {meshes_count} meshes")

            if curves_count:
                msg.append(f" • {curves_count} curves")

            if objects_count:
                msg.append(f" • {objects_count} objects")

            if materials_count:
                msg.append(f" • {materials_count} materials")

            if images_count:
                msg.append(f" • {images_count} images")

            if nodegroups_count:
                msg.append(f" • {nodegroups_count} node groups")

            if scenes_count:
                msg.append(f" • {scenes_count} scenes")

            if worlds_count:
                msg.append(f" • {worlds_count} worlds")

            popup_message(msg, title="Recursive Purge" if event.alt else "Purge")

        else:
            bpy.ops.machin3.draw_label(text="Nothing to purge.", coords=(context.region.width / 2, 200), color=green)

        return {'FINISHED'}


class Clean(bpy.types.Operator):
    bl_idname = "machin3.clean_out_blend_file"
    bl_label = "Clean out .blend file!"
    bl_options = {'REGISTER', 'UNDO'}

    remove_custom_brushes: BoolProperty(name="Remove Custom Brushes", default=False)
    has_selection: BoolProperty(name="Has Selected Objects", default=False)

    @classmethod
    def poll(cls, context):
        return bpy.data.objects or bpy.data.materials or bpy.data.images

    @classmethod
    def description(cls, context, properties):
        desc = "Clean out entire .blend file"

        if context.selected_objects:
            desc += " (except selected objects)"

        desc += '\nALT: Remove non-default Brushes too'

        return desc

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        text = "This will remove everything in the current .blend file"

        if self.remove_custom_brushes:
            text += ", including custom Brushes"

        if self.has_selection:
            if self.remove_custom_brushes:
                text += ", but except the selected objects"
            else:
                text += ", except the selected objects"

        text += "!"

        column.label(text=text, icon_value=get_icon('error'))

    def invoke(self, context, event):
        self.has_selection = True if context.selected_objects else False
        self.remove_custom_brushes = event.alt

        width = 600 if self.has_selection and self.remove_custom_brushes else 450 if self.has_selection or self.remove_custom_brushes else 300

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=width)

    def execute(self, context):

        # remove Objects
        sel = [obj for obj in context.selected_objects]
        remove_objs = [obj for obj in bpy.data.objects if obj not in sel]
        bpy.data.batch_remove(remove_objs)

        # prevent selected objects only being in collections, that will be removed
        if sel:
            mcol = context.scene.collection

            for obj in sel:
                if obj.name not in mcol.objects:
                    mcol.objects.link(obj)
                    print(f"WARNING: Adding {obj.name} to master collection to ensure visibility/accessibility")

        # remove Scenes (all but current)
        remove_scenes = [scene for scene in bpy.data.scenes if scene != context.scene]
        bpy.data.batch_remove(remove_scenes)

        # remove Materials
        bpy.data.batch_remove(bpy.data.materials)

        # remove Images
        bpy.data.batch_remove(bpy.data.images)
        
        # remove collections
        bpy.data.batch_remove(bpy.data.collections)

        # remove text
        bpy.data.batch_remove(bpy.data.texts)

        # remove actions
        bpy.data.batch_remove(bpy.data.actions)

        # all but default brushes
        if self.remove_custom_brushes:
            print("WARNING: Removing Custom Brushes")
            default_brushes_names = ['Add', 'Airbrush', 'Average', 'Blob', 'Blur', 'Boundary', 'Clay', 'Clay Strips', 'Clay Thumb', 'Clone', 'Clone Stroke', 'Cloth', 'Crease', 'Darken', 'Draw', 'Draw Face Sets', 'Draw Sharp', 'Draw Weight', 'Elastic Deform', 'Eraser Hard', 'Eraser Point', 'Eraser Soft', 'Eraser Stroke', 'Fill', 'Fill Area', 'Fill/Deepen', 'Flatten/Contrast', 'Grab', 'Grab Stroke', 'Inflate/Deflate', 'Ink Pen', 'Ink Pen Rough', 'Layer', 'Lighten', 'Marker Bold', 'Marker Chisel', 'Mask', 'Mix', 'Multi-plane Scrape', 'Multiply', 'Multires Displacement Eraser', 'Nudge', 'Paint', 'Pen', 'Pencil', 'Pencil Soft', 'Pinch Stroke', 'Pinch/Magnify', 'Pose', 'Push Stroke', 'Randomize Stroke', 'Rotate', 'Scrape/Peaks', 'SculptDraw', 'Simplify', 'Slide Relax', 'Smear', 'Smooth', 'Smooth Stroke', 'Snake Hook', 'Soften', 'Strength Stroke', 'Subtract', 'TexDraw', 'Thickness Stroke', 'Thumb', 'Tint', 'Twist Stroke', 'Vertex Average', 'Vertex Blur', 'Vertex Draw', 'Vertex Replace', 'Vertex Smear']
            remove_brushes = [brush for brush in bpy.data.brushes if brush.name not in default_brushes_names]
            bpy.data.batch_remove(remove_brushes)

        # remove worlds
        bpy.data.batch_remove(bpy.data.worlds)

        # purge recursively
        bpy.ops.outliner.orphans_purge(do_recursive=True)

        # remove left over Meshes (fake users)
        if bpy.data.meshes:
            selmeshes = [obj.data for obj in sel if obj.type == 'MESH']
            remove_meshes = [mesh for mesh in bpy.data.meshes if mesh not in selmeshes]

            if remove_meshes:
                print("WARNING: Removing leftover meshes")
                bpy.data.batch_remove(remove_meshes)

        # go out of local view, if in it
        if context.space_data.local_view:
            bpy.ops.view3d.localview(frame_selected=False)

        return {'FINISHED'}


class ReloadLinkedLibraries(bpy.types.Operator):
    bl_idname = "machin3.reload_linked_libraries"
    bl_label = "MACHIN3: Reload Linked Liraries"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.data.libraries

    def execute(self, context):
        reloaded = []

        for lib in bpy.data.libraries:
            lib.reload()
            reloaded.append(lib.name)
            print(f"Reloaded Library: {lib.name}")

        self.report({'INFO'}, f"Reloaded {'Library' if len(reloaded) == 1 else f'{len(reloaded)} Libraries'}: {', '.join(reloaded)}")

        return {'FINISHED'}


has_skribe = None
has_screencast_keys = None

class ScreenCast(bpy.types.Operator):
    bl_idname = "machin3.screen_cast"
    bl_label = "MACHIN3: Screen Cast"
    bl_description = "Screen Cast Operators"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        screencast_keys = get_addon('Screencast Keys')[0]

        if screencast_keys:
            return "Screen Cast recent Operators and Keys"
        return "Screen Cast Recent Operators"

    def execute(self, context):
        global has_skribe, has_screencast_keys

        debug = False
        # debug = True

        if has_skribe is None:
            has_skribe = bool(shutil.which('skribe'))

        if has_screencast_keys is None:
            enabled, foldername, _, _ = get_addon('Screencast Keys')

            # print("screencastkeys enabled:", enabled)
            # print("screencastkeys folder name:", foldername)

            # enable if it's installed but not enabled
            if foldername:
                if not enabled and get_prefs().screencast_use_screencast_keys:
                    print("INFO: Enabling Screencast Keys Addon")
                    bpy.ops.preferences.addon_enable(module=foldername)

                has_screencast_keys = True
            else:
                has_screencast_keys = False

        if debug:
            print("skribe exists:", has_skribe)
            print("screncast keys exists:", has_screencast_keys)

        use_skribe = has_skribe and get_prefs().screencast_use_skribe
        use_screencast_keys = has_screencast_keys and get_prefs().screencast_use_screencast_keys

        # toggle screencast wm prop, which will cause the drawing handler to draw the last used ops
        wm = context.window_manager
        setattr(wm, 'M3_screen_cast', not wm.M3_screen_cast)

        # fetch current casting state now
        is_casting = wm.M3_screen_cast

        # toggle skribe sreencast keys
        if use_skribe:

            # turn skribe on
            if is_casting:
                if debug:
                    print("turning skribe ON!")

                try:
                    subprocess.Popen('skribe', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print("WARNING: SKRIBE not found?")
                    print(e)

            # turn skribe off
            else:
                if debug:
                    print("turning skribe OFF!")

                try:
                    subprocess.Popen('pkill -f SKRIBE'.split())

                except Exception as e:
                    print("WARNING: something went wrong")
                    print(e)

        elif use_screencast_keys:
            screencast_keys = get_addon('Screencast Keys')[0]

            if screencast_keys:

                # switch workspaces back and forth
                # this prevents "internal error: modal gizmo-map handler has invalid area" errors when maximizing the view

                current = context.workspace
                other = [ws for ws in bpy.data.workspaces if ws != current]

                if other:
                    context.window.workspace = other[0]
                    context.window.workspace = current

                # this op will toggle the keys, so you don't even need to check the state of screencasting, although it's possible that both get out of sync of course
                bpy.ops.wm.sk_screencast_keys('INVOKE_DEFAULT')

        # force handler update via selection event
        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

        return {'FINISHED'}
