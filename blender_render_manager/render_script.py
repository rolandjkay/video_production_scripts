import bpy
import sys
import copy
import os

# Find the directory where this file (render_manager.py) resides
# NOTE: This will break if os.chdir() is called before this line runs
render_script_py_path = os.path.dirname(os.path.realpath(__file__))

# Append this directory to path, so that we can find "shot_list_db.py"
sys.path.append(render_script_py_path)

import shot_list_db

def parse_resolution_string(resolution_string):
    """Parse a string like "1920x1080" -> [1920, 1080]"""
    try:
        [x_str, y_str] = resolution_string.upper().split("X")
        x = int(x_str)
        y = int(y_str)
    except ValueError as e:
        raise ValueError("Invalid resolution string \"" + resolution_string + "\"")

    return [x,y]

def parse_boolean(b):
    return str(b).upper() in ["TRUE", "1", "YES", "ON"]


def find_next_slate_number(path):
    """Find the next free slate_XXX directory"""
    import re

    pattern = re.compile("slate_([0-9]+)")

    try:
        max_index = -0
        for candidate in os.listdir(path):
            m = pattern.fullmatch(candidate)
            if m:
                index = int(m.group(1)) 
                if index > max_index:
                    max_index = index

        return max_index + 1
    except FileNotFoundError:
        # If os.listdir() failed, because the render output directory doesn't 
        # exist, then this is the first render, so the slate number is 1.
        return 1

# Parse command line
#
argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all args after "--"

if len(argv) == 4:
    [shot_list_db_filepath, shot_category, shot_id, quality] = argv
    slate_number = None
elif len(argv) == 5:
    [shot_list_db_filepath, shot_category, shot_id, quality, slate_number ] = argv
else:
    raise ValueError("Not enough command line parameters supplued to render_script.py")

# Index into lists in shot list file.
# - Parameters which are difference for low/medium/high quality renders are
#   given as arrays of three values; e.g.
#
#    "max_cycles_samples": [128, 1024, 4096], 
#
quality_index = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(quality.upper(), 2)

shot_list_db = shot_list_db.ShotListDb.from_file(shot_list_db_filepath)

# Look up the shot using category + ID.
shot_info = shot_list_db.get_shot_info(shot_category, shot_id)

# Output job details
s = ("Rendering shot: %s/%s" % (shot_category, shot_id))
print(s)
print("=" * len(s))
width = max([ len(x) for x in shot_info.keys()])
for key, value in shot_info.items():
    print(key + ":", (width - len(key)) * ".",value)
print()

bpy.context.scene.camera = bpy.data.objects[shot_info["camera"]]

# Frame start and end defaults to whatever is in the Blender file
if "frame_start" in shot_info:
    bpy.context.scene.frame_start = shot_info["frame_start"]
if "frame_end" in shot_info:
    bpy.context.scene.frame_end = shot_info["frame_end"]
    
bpy.context.scene.render.film_transparent = parse_boolean(shot_info.get("film_transparent", False)) 
bpy.context.scene.render.fps = shot_info.get("fps", 25) 
bpy.context.scene.render.use_motion_blur = parse_boolean(shot_info.get("use_motion_blur", True))


# Output settings
bpy.context.scene.render.resolution_percentage = shot_info.get("resolution_percentage", [50, 50, 100])[quality_index]
bpy.context.scene.render.resolution_x = parse_resolution_string(shot_info.get("target_resolution", "1920x1080"))[0];
bpy.context.scene.render.resolution_y = parse_resolution_string(shot_info.get("target_resolution", "1920x1080"))[1];
bpy.context.scene.render.image_settings.file_format = shot_info.get("output_file_format", "PNG")
bpy.context.scene.render.image_settings.color_mode = shot_info.get("output_color_mode", 'RGBA')
bpy.context.scene.render.use_overwrite = False
bpy.context.scene.render.use_placeholder = False

# Use output path override given in the shot list, if given. Otherwise, fallback on eg. Renders/Title/slate_3/...
if shot_info.get("output_filepath_override"):
    bpy.context.scene.render.filepath = shot_info.get("output_filepath_override")
else:
    output_path_base =  os.path.join(shot_list_db.render_root, shot_info["title"])

    if slate_number is None:
        slate_number = find_next_slate_number(output_path_base)


    bpy.context.scene.render.filepath = os.path.join(output_path_base, "slate_%d/" % slate_number)


# Map EEVEE -> BLENDER_EEVEE and WORKBENCH -> BLENDER_WORKBENCH. Otherwise, use whatever was specified in the shot list.
render_engine = shot_info.get("render_engine", "CYCLES")
bpy.context.scene.render.engine = {"EEVEE": "BLENDER_EEVEE", "WORKBENCH": "BLENDER_WORKBENCH"}.get(render_engine, render_engine)

# Cycles settings
bpy.context.scene.cycles.samples = shot_info.get("max_cycles_samples", [256, 1024, 4096])[quality_index] 
bpy.context.scene.cycles.use_denoising = parse_boolean(shot_info.get("use_denoising", False))

# Object to hide in render
objects_to_hide = shot_info.get("objects_to_hide", [])
for obj_name in objects_to_hide:
    bpy.data.objects[obj_name].hide_render = True

# Collections to set as "indirect only"
indirect_collections = shot_info.get("indirect_collections", [])
for collection_name in indirect_collections:
    # XXX I think this only works for top-level collections; needs to extend this so that config file
    # takes full path in the tree to the collection.
    layer_collection = bpy.context.view_layer.layer_collection.children[collection_name]
    bpy.context.view_layer.active_layer_collection = layer_collection
    bpy.context.view_layer.active_layer_collection.indirect_only = True


bpy.ops.render.render(animation=True)
    
