import bpy
import mathutils
import sys
import copy
import os


#
# Add a File Output node to the compositor which writes the requested render passes
#
def configure_render_passes(scene, render_passes_db, render_output_path):
    view_layer = scene.view_layers[0] # XXX Need to think about files with multiple scenes/view layers!!!

    # Make sure the compositor is "using nodes"
    scene.use_nodes = True

    # Setup a File Output node
    #
    output_node = scene.node_tree.nodes.new(type="CompositorNodeOutputFile")
    output_node.base_path = render_output_path + "/passes/"

    # This is how to set the output path of the first input, but we ignore it for the
    # sake of keeping the code more homogeneous.
    #bpy.data.scenes["Scene"].node_tree.nodes["File Output"].file_slots[0].path = "mist/mist_"

    # Get the "Render Layers" node
    render_layers_node = scene.node_tree.nodes["Render Layers"]

    # Move "File Output" node to be not too far from the Render Layers node
    output_node.location = render_layers_node.location + mathutils.Vector((render_layers_node.width + 100,-500))

    # Helper func to connect the last node of 'output_node' to the given output of 'rl_node'.
    def connect(rl_output_name):
        scene.node_tree.links.new(render_layers_node.outputs[rl_output_name], output_node.inputs[-1])

    def optional_connect_render_layer_output(db_prop_name,
                                             output_subpath,
                                             view_layer_prop_name,
                                             render_layer_output_name):
        """Connect the nodes to output the given render layer, if enabled.

        db_prop_name:   The name of the flag in the JSON file to enable render layer; e.g. "z"
        output_subpath: relative path in render output directory; e.g. mist/must_
        view_layer_prop_name:  VL property to set to true to enable this render layer
        render_layer_output_name: The output of the Render Layers node to conenct to

        """
        if render_passes_db.get(db_prop_name, False):
            output_node.file_slots.new(output_subpath)
            setattr(view_layer, view_layer_prop_name, True)
            connect(render_layer_output_name)

    #if render_passes_db.get("mist", False):
    #    output_node.file_slots.new("mist/mist_")
    #    view_layer.use_pass_mist = True
    #    connect("Mist")

    optional_connect_render_layer_output("mist", "mist/mist_", "use_pass_mist", "Mist")
    optional_connect_render_layer_output("z", "z/z_", "use_pass_z", "Mist")
    optional_connect_render_layer_output("position", "position/position_", "use_pass_position", "Position")
    optional_connect_render_layer_output("normal", "normal/normal_", "use_pass_normal", "Position")
    optional_connect_render_layer_output("vector", "vector/vector_", "use_pass_vector", "Vector")
    optional_connect_render_layer_output("uv", "uv/uv_", "use_pass_uv", "UV")

    # Denoise data is a but different from the other Render Layers.
    if render_passes_db.get("denoise_data", False):
        scene.view_layers[0].cycles.denoising_store_passes = True

        output_node.file_slots.new("denoise_albedo/denoise_albedo_")
        connect("Denoising Albedo")
        output_node.file_slots.new("denoise_normal/denoise_normal_")
        connect("Denoising Normal")
        output_node.file_slots.new("denoise_depth/denoise_depth_")
        connect("Denoising Depth")


# Find the directory where this file (render_manager.py) resides
# NOTE: This will break if os.chdir() is called before this line runs
render_script_py_path = os.path.dirname(os.path.realpath(__file__))

# Append this directory to path, so that we can find "shot_list_db.py"
sys.path.append(render_script_py_path)

import shot_list_db
from common import *

#def parse_resolution_string(resolution_string):
#    """Parse a string like "1920x1080" -> [1920, 1080]"""
#    try:
#        [x_str, y_str] = resolution_string.upper().split("X")
#        x = int(x_str)
#        y = int(y_str)
#    except ValueError as e:
#        raise ValueError("Invalid resolution string \"" + resolution_string + "\"")
#
#    return [x,y]

#def parse_boolean(b):
#    return str(b).upper() in ["TRUE", "1", "YES", "ON"]


# It's a problem for the compositor if we're not clear about which slate is being
# rendered. E.g. did the compositor start before the renderer, in which case it
# should use the next free slate number, or after, in which case it should use
# the highest numbered existing slate. Better just to insist that the user gives
# the exact slate number and don't try to guess.
#def find_next_slate_number(path):
#    """Find the next free slate_XXX directory"""
#    import re
#
#    pattern = re.compile("slate_([0-9]+)")
#
#    try:
#        max_index = -0
#        for candidate in os.listdir(path):
#            m = pattern.fullmatch(candidate)
#            if m:
#                index = int(m.group(1)) 
#                if index > max_index:
#                    max_index = index
#
#        return max_index + 1
#    except FileNotFoundError:
#        # If os.listdir() failed, because the render output directory doesn't 
#        # exist, then this is the first render, so the slate number is 1.
#        return 1





# Parse command line
#
argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all args after "--"

# Don' guess the slate number
#if len(argv) == 4:
#    [shot_list_db_filepath, shot_category, shot_id, quality] = argv
#    slate_number = None
if len(argv) == 5:
    [shot_list_db_filepath, shot_category, shot_id, quality, slate_number ] = argv
else:
    raise ValueError("Not enough command line parameters supplied to render_script.py")

# Index into lists in shot list file.
# - Parameters which are difference for low/medium/high quality renders are
#   given as arrays of three values; e.g.
#
#    "max_cycles_samples": [128, 1024, 4096], 
#
quality_index = get_quality_index(quality)

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

# Get the scene name from the shot info, but default to the first scene.
scene_name = shot_info.get("scene", bpy.data.scenes[0].name)
scene = bpy.data.scenes[scene_name]

scene.camera = bpy.data.objects[shot_info["camera"]]

# Frame start and end defaults to whatever is in the Blender file
if "frame_start" in shot_info:
    scene.frame_start = shot_info["frame_start"]
if "frame_end" in shot_info:
    scene.frame_end = shot_info["frame_end"]
    
scene.render.film_transparent = parse_boolean(shot_info.get("film_transparent", False)) 
scene.render.fps = shot_info.get("fps", 25) 
scene.render.use_motion_blur = parse_boolean(shot_info.get("use_motion_blur", True))


# Output settings
set_render_resolution(scene, shot_info, quality)
scene.render.image_settings.file_format = shot_info.get("render_file_format", "PNG")
scene.render.image_settings.color_mode = shot_info.get("render_color_mode", 'RGBA')
scene.render.image_settings.color_depth = shot_info.get("render_color_depth", "16")
scene.render.use_overwrite = False
scene.render.use_placeholder = False

# Use output path override given in the shot list, if given. Otherwise, fallback on eg. Renders/Title/slate_3/...
if shot_info.get("output_filepath_override"):
    render_filepath = shot_info.get("output_filepath_override")
    scene.render.filepath = render_filepath
else:
    output_path_base =  os.path.join(shot_list_db.render_root, shot_info["title"])

#    if slate_number is None:
#        slate_number = find_next_slate_number(output_path_base)


    filename =  shot_category + "_" + shot_id + "_" + slate_number + "_"
    render_filepath = os.path.join(output_path_base, "slate_%s/" % str(slate_number)) + filename 
    scene.render.filepath = render_filepath


# Map EEVEE -> BLENDER_EEVEE and WORKBENCH -> BLENDER_WORKBENCH. Otherwise, use whatever was specified in the shot list.
render_engine = shot_info.get("render_engine", "CYCLES")
scene.render.engine = {"EEVEE": "BLENDER_EEVEE", "WORKBENCH": "BLENDER_WORKBENCH"}.get(render_engine, render_engine)

# Cycles settings
scene.cycles.samples = shot_info.get("max_cycles_samples", [256, 1024, 1024, 4096])[quality_index] 
scene.cycles.use_adaptive_sampling = shot_info.get("use_adaptive_sampling", [True, True, False, False])[quality_index] 
scene.cycles.use_denoising = parse_boolean(shot_info.get("use_denoising", False))
scene.cycles.device = shot_info.get("rendering_device", 'GPU') 
scene.cycles.use_animated_seed = True

# If we're using Cycles; setup compositor to output render passes
render_passes_db = shot_info.get("render_passes")
if render_passes_db is not None and render_engine == "CYCLES":
    render_dir = os.path.dirname(render_filepath)
    configure_render_passes(scene, render_passes_db, render_dir)

# XXX We haven't thought about how rendering out render passes is going to work with 
# multiple render later (see below). Probably, we should duplicate the Render Layers
# node and File Output node for every view layer. We'd have to think about how
# to set render_filepath as well.

# Enable denoise data, vector and mist passes for all render layers.
#if shot_info.get("enable_all_layers", False):
#    for layer_name in bpy.context.scene.view_layers.keys():
#        bpy.context.scene.view_layers[layer_name].cycles.denoising_store_passes = True
#        bpy.context.scene.view_layers[layer_name].use_pass_vector = True
#        bpy.context.scene.view_layers[layer_name].use_pass_mist = True
#        bpy.context.scene.view_layers[layer_name].use_pass_z = True


# Object to hide in render
objects_to_hide = shot_info.get("objects_to_hide", [])
for obj_name in objects_to_hide:
    bpy.data.objects[obj_name].hide_render = True

# Collections to set as "indirect only"
indirect_collections = shot_info.get("indirect_collections", [])
for collection_name in indirect_collections:
    # XXX I think this only works for top-level collections; needs to extend this so that config file
    # takes full path in the tree to the collection.
    view_layer = scene.view_layers[0]
    view_layer.layer_collection.children["Collection"]
    layer_collection = view_layer.layer_collection.children[collection_name]
    view_layer.active_layer_collection = layer_collection
    view_layer.active_layer_collection.indirect_only = True

# Replace the world HDRI
def find_env_texture_node():
    if scene.world.use_nodes == False:
        return None

    for node in scene.world.node_tree.nodes:
        if type(node) is bpy.types.ShaderNodeTexEnvironment:
            return node

    return None

world_hdri_filepath = shot_info.get('world_hdri', None)
if world_hdri_filepath:
    # Find the environment texture node
    env_texture_node = find_env_texture_node()
    if env_texture_node is None:
        print("Couldn't set world HDRI; environment texture node not found or nodes not enabled.")
    else:
        try:
            node.image = bpy.data.images.load(world_hdri_filepath, check_existing = True)
        except RuntimeError as e:
            print("FAILED to set world HDRI: %s" % str(e))

bpy.ops.render.render(animation=True)
    
