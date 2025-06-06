# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import getpass
import logging
import os
import shutil
import sys
import tempfile

import bpy

from . import daemon_lib, global_vars, reports, utils


bk_logger = logging.getLogger(__name__)

BLENDERKIT_API = f"{global_vars.SERVER}/api/v1"
BLENDERKIT_OAUTH_LANDING_URL = f"{global_vars.SERVER}/oauth-landing"
BLENDERKIT_PLANS_URL = f"{global_vars.SERVER}/plans/pricing"
BLENDERKIT_REPORT_URL = f"{global_vars.SERVER}/usage_report"
BLENDERKIT_USER_ASSETS_URL = f"{global_vars.SERVER}/my-assets"
BLENDERKIT_MANUAL_URL = "https://youtu.be/0P8ZjfbUjeA"
BLENDERKIT_MODEL_UPLOAD_INSTRUCTIONS_URL = f"{global_vars.SERVER}/docs/upload/"
BLENDERKIT_MATERIAL_UPLOAD_INSTRUCTIONS_URL = (
    f"{global_vars.SERVER}/docs/uploading-material/"
)
BLENDERKIT_BRUSH_UPLOAD_INSTRUCTIONS_URL = f"{global_vars.SERVER}/docs/uploading-brush/"
BLENDERKIT_HDR_UPLOAD_INSTRUCTIONS_URL = f"{global_vars.SERVER}/docs/uploading-hdr/"
BLENDERKIT_SCENE_UPLOAD_INSTRUCTIONS_URL = f"{global_vars.SERVER}/docs/uploading-scene/"
BLENDERKIT_LOGIN_URL = f"{global_vars.SERVER}/accounts/login"
BLENDERKIT_SIGNUP_URL = f"{global_vars.SERVER}/accounts/register"


def cleanup_old_folders():
    """function to clean up any historical folders for BlenderKit. By now removes the temp folder."""
    orig_temp = os.path.join(os.path.expanduser("~"), "blenderkit_data", "temp")
    if os.path.isdir(orig_temp):
        try:
            shutil.rmtree(orig_temp)
        except Exception as e:
            bk_logger.error(f"could not delete old temp directory: {e}")


def find_in_local(text=""):
    fs = []
    for p, d, f in os.walk("."):
        for file in f:
            if text in file:
                fs.append(file)
    return fs


def get_author_gallery_url(author_id):
    return f"{global_vars.SERVER}/asset-gallery?query=author_id:{author_id}"


def get_asset_gallery_url(asset_id):
    return f"{global_vars.SERVER}/asset-gallery-detail/{asset_id}/"


def default_global_dict():
    home = os.path.expanduser("~")
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home != None:
        home = data_home
    return home + os.sep + "blenderkit_data"


def get_categories_filepath():
    tempdir = get_temp_dir()
    return os.path.join(tempdir, "categories.json")


dirs_exist_dict = {}  # cache these results since this is used very often


# this causes the function to fail if user deletes the directory while blender is running,
# but comes back when blender is restarted.
def get_temp_dir(subdir=None):
    user_preferences = bpy.context.preferences.addons["blenderkit"].preferences
    # first try cached results
    if subdir is not None:
        d = dirs_exist_dict.get(subdir)
        if d is not None:
            return d
    else:
        d = dirs_exist_dict.get("top")
        if d is not None:
            return d
    username = getpass.getuser()
    safe_username = "".join(c for c in username if c.isalnum())
    tempdir = os.path.join(tempfile.gettempdir(), f"bktemp_{safe_username}")
    if tempdir.startswith("//"):
        tempdir = bpy.path.abspath(tempdir)
    try:
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        dirs_exist_dict["top"] = tempdir

        if subdir is not None:
            tempdir = os.path.join(tempdir, subdir)
            if not os.path.exists(tempdir):
                os.makedirs(tempdir)
            dirs_exist_dict[subdir] = tempdir

        cleanup_old_folders()
    except Exception as e:
        reports.add_report("Cache directory not found. Resetting Cache folder path.")
        bk_logger.warning(f"due to exception: {e}")

        p = default_global_dict()
        if p == user_preferences.global_dir:
            message = "Global dir was already default, plese set a global directory in addon preferences to a dir where you have write permissions."
            reports.add_report(message)
            return None
        user_preferences.global_dir = p
        tempdir = get_temp_dir(subdir=subdir)
    return tempdir


def get_download_dirs(asset_type):
    """get directories where assets will be downloaded"""
    subdmapping = {
        "brush": "brushes",
        "texture": "textures",
        "model": "models",
        "scene": "scenes",
        "material": "materials",
        "hdr": "hdrs",
    }

    dirs = []
    if global_vars.PREFS["directory_behaviour"] in ("BOTH", "GLOBAL"):
        ddir = global_vars.PREFS["global_dir"]
        if ddir.startswith("//"):
            ddir = bpy.path.abspath(ddir)
        if not os.path.exists(ddir):
            os.makedirs(ddir)

        subd = subdmapping[asset_type]
        subdir = os.path.join(ddir, subd)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        dirs.append(subdir)
    if (
        global_vars.PREFS["directory_behaviour"] == "BOTH"
        or global_vars.PREFS["directory_behaviour"] == "LOCAL"
    ) and bpy.data.is_saved:  # it's important local get's solved as second, since for the linking process only last filename will be taken. For download process first name will be taken and if 2 filenames were returned, file will be copied to the 2nd path.
        ddir = global_vars.PREFS["project_subdir"]
        if ddir.startswith("//"):
            ddir = bpy.path.abspath(ddir)
            if not os.path.exists(ddir):
                os.makedirs(ddir)

        subd = subdmapping[asset_type]

        subdir = os.path.join(ddir, subd)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        dirs.append(subdir)

    return dirs


def slugify(slug):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import re

    slug = slug.lower()

    characters = '<>:"/\\|?\*., ()#'
    for ch in characters:
        slug = slug.replace(ch, "_")
    # import re
    # slug = unicodedata.normalize('NFKD', slug)
    # slug = slug.encode('ascii', 'ignore').lower()
    slug = re.sub(r"[^a-z0-9]+.- ", "-", slug).strip("-")
    slug = re.sub(r"[-]+", "-", slug)
    slug = re.sub(r"/", "_", slug)
    slug = re.sub(r"\\\'\"", "_", slug)
    if len(slug) > 50:
        slug = slug[:50]
    return slug


def extract_filename_from_url(url):
    if url is not None:
        imgname = url.split("/")[-1]
        imgname = imgname.split("?")[0]
        return imgname
    return ""


resolution_suffix = {
    "blend": "",
    "resolution_0_5K": "_05k",
    "resolution_1K": "_1k",
    "resolution_2K": "_2k",
    "resolution_4K": "_4k",
    "resolution_8K": "_8k",
}
resolutions = {
    "resolution_0_5K": 512,
    "resolution_1K": 1024,
    "resolution_2K": 2048,
    "resolution_4K": 4096,
    "resolution_8K": 8192,
}


def round_to_closest_resolution(res):
    rdist = 1000000
    #    while res/2>1:
    #        p2res*=2
    #        res = res/2
    for rkey in resolutions:
        d = abs(res - resolutions[rkey])
        if d < rdist:
            rdist = d
            p2res = rkey

    return p2res


def get_res_file(asset_data, resolution, find_closest_with_url=False):
    """
    Returns closest resolution that current asset can offer.
    If there are no resolutions, return orig file.
    If orig file is requested, return it.
    params
    asset_data
    resolution - ideal resolution
    find_closest_with_url:
        returns only resolutions that already containt url in the asset data, used in scenes where asset is/was already present.
    Returns:
        resolution file
        resolution, so that other processess can pass correctly which resolution is downloaded.
    """
    orig = None
    res = None
    closest = None
    target_resolution = resolutions.get(resolution)
    mindist = 100000000

    for f in asset_data["files"]:
        if f["fileType"] == "blend":
            orig = f
            if resolution == "blend":
                # orig file found, return.
                return orig, "blend"

        if f["fileType"] == resolution:
            # exact match found, return.
            return f, resolution
        # find closest resolution if the exact match won't be found.
        rval = resolutions.get(f["fileType"])
        if rval and target_resolution:
            rdiff = abs(target_resolution - rval)
            if rdiff < mindist:
                closest = f
                mindist = rdiff
    if not res and not closest:
        return orig, "blend"
    return closest, closest["fileType"]


def server_2_local_filename(asset_data, filename):
    """
    Convert file name on server to file name local.
    This should get replaced
    """

    fn = filename.replace("blend_", "")
    fn = fn.replace("resolution_", "")
    n = slugify(asset_data["name"]) + "_" + fn
    return n


def get_texture_directory(asset_data, resolution="blend"):
    tex_dir_path = f"//textures{resolution_suffix[resolution]}{os.sep}"
    return tex_dir_path


def get_download_filepaths(asset_data, resolution="blend", can_return_others=False):
    """Get all possible paths of the asset and resolution. Usually global and local directory."""
    windows_path_limit = 250
    dirs = get_download_dirs(asset_data["assetType"])
    res_file, resolution = get_res_file(
        asset_data, resolution, find_closest_with_url=can_return_others
    )
    name_slug = slugify(asset_data["name"])
    if len(name_slug) > 16:
        name_slug = name_slug[:16]
    asset_folder_name = f"{name_slug}_{asset_data['id']}"

    file_names = []

    if not res_file:
        return file_names
    # fn = asset_data['file_name'].replace('blend_', '')
    if res_file.get("url") is not None:
        # Tweak the names a bit:
        # remove resolution and blend words in names
        #
        fn = extract_filename_from_url(res_file["url"])
        n = server_2_local_filename(asset_data, fn)
        for d in dirs:
            asset_folder_path = os.path.join(d, asset_folder_name)
            if sys.platform == "win32" and len(asset_folder_path) > windows_path_limit:
                reports.add_report(
                    "The path to assets is too long, "
                    "only Global folder can be used. "
                    "Move your .blend file to another "
                    "folder with shorter path to "
                    "store assets in a subfolder of your project.",
                    60,
                    "ERROR",
                )
                continue
            if not os.path.exists(asset_folder_path):
                os.makedirs(asset_folder_path)

            file_name = os.path.join(asset_folder_path, n)
            file_names.append(file_name)

    utils.p("file paths", file_names)
    for f in file_names:
        if len(f) > windows_path_limit:
            reports.add_report(
                "The path to assets is too long, "
                "only Global folder can be used. "
                "Move your .blend file to another "
                "folder with shorter path to "
                "store assets in a subfolder of your project.",
                60,
                "ERROR",
            )
            file_names.remove(f)
    return file_names


def delete_asset_debug(asset_data):
    """TODO fix this for resolutions - should get ALL files from ALL resolutions."""
    user_preferences = bpy.context.preferences.addons["blenderkit"].preferences
    api_key = user_preferences.api_key

    _, asset_data = daemon_lib.get_download_url(
        asset_data, utils.get_scene_id(), api_key
    )

    file_names = get_download_filepaths(asset_data)
    for f in file_names:
        asset_dir = os.path.dirname(f)

        if os.path.isdir(asset_dir):
            try:
                bk_logger.info(f"{asset_dir}")
                shutil.rmtree(asset_dir)
            except:
                e = sys.exc_info()[0]
                bk_logger.error(f"{e}")


def get_clean_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    subpath = "blendfiles" + os.sep + "cleaned.blend"
    cp = os.path.join(script_path, subpath)
    return cp


def get_thumbnailer_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    subpath = "blendfiles" + os.sep + "thumbnailer.blend"
    return os.path.join(script_path, subpath)


def get_material_thumbnailer_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    subpath = "blendfiles" + os.sep + "material_thumbnailer_cycles.blend"
    return os.path.join(script_path, subpath)
    """
    for p in bpy.utils.script_paths():
        testfname= os.path.join(p, subpath)#p + '%saddons%sobject_fracture%sdata.blend' % (s,s,s)
        if os.path.isfile( testfname):
            fname=testfname
            return(fname)
    return None
    """


def get_addon_file(subpath=""):
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    return os.path.join(script_path, subpath)


script_path = os.path.dirname(os.path.realpath(__file__))


def get_addon_thumbnail_path(name):
    global script_path
    # fpath = os.path.join(p, subpath)
    ext = name.split(".")[-1]
    next = ""
    if not (ext == "jpg" or ext == "png"):  # already has ext?
        next = ".jpg"
    subpath = f"thumbnails{os.sep}{name}{next}"
    return os.path.join(script_path, subpath)


def get_config_dir_path() -> str:
    """Get the path to the config directory in global_dir."""
    global_dir = bpy.context.preferences.addons["blenderkit"].preferences.global_dir
    directory = os.path.join(global_dir, "config")
    return os.path.abspath(directory)


def ensure_config_dir_exists():
    """Ensure that the config directory exists."""
    config_dir = get_config_dir_path()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return config_dir
