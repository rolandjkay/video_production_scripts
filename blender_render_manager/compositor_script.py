"""Blender script to composite shots built with render_manager

To test:

"C:\Program Files\Blender Foundation\Blender 3.0\blender" -b "D:\Assets\Models\Mine\compositor recipes\defaullt_compositor_chain.blend" --python compositor_script.py -- "D:\Projects\Sitting Duck\Blender\blender_shot_list.json" film 1 1 .png


"""
import bpy
import sys
import copy
import os
import functools
import logging

# Find the directory where this file (render_manager.py) resides
# NOTE: This will break if os.chdir() is called before this line runs
render_script_py_path = os.path.dirname(os.path.realpath(__file__))

# Append this directory to path, so that we can find "shot_list_db.py"
sys.path.append(render_script_py_path)

import shot_list_db

# XXX Duplicated with render_manager.py
IMAGE_FILE_EXTENSIONS = {
    "OPEN_EXR_MULTILAYER": "EXR",
    "PNG": "PNG",
}

# DEFAULT_COMPOSITOR_CHAIN_BLEND_FILE = "D:\\Assets\\Models\\Mine\\compositor recipes\\default_compositor_chain.blend"

def configure_compositor_chain(compositor_chain_db):
    """Configure the compositor chain to match the requirements for current shot

    compositor_chain_db:  Sub-db of the shot list JSON file

    Example:

        "compositor_chain": {
            "Denoise": {
                "mute": true,
                "prefilter": "ACCURATE",
                "use_hdr": true
            },
            "Vector Blur": {
                "mute": true,
                "samples": 32,
                "factor": 1.0,
                "speed_min": 0,
                "speed_max": 0,
                "use_curved": false
            },
            "Glare": {
                "mute": false,
                "glare_type": "FOG_GLOW",
                "quality": "MEDIUM",
                "mix": 0.0,
                "threshold": 1.0,
                "size": 8
            },
            "Lens Distortion": {
                "mute": false,
                "use_projector": false,
                "use_jitter": false,
                "use_fit": true,
                "distortion": 0.005,
                "dispersion": 0.01
            },
            "Filter": {
                "mute": true,
        "filter_type": "SOFTEN",
                "factor": 0.0
            },
            "Blur": {
                "mute": true,
                "filter_type": "GAUSS",
                "use_variable_size": false,
                "use_bokeh": false,
                "use_gamma_correction": false,
                "use_relative": false,
                "size_x": 1,
                "size_y": 1,
                "use_extended_bounds": false,
                "size": 2
            }
        }

    """

    ## We mostly just use the Python attribute names in the JSON file.
    ## However, in some cases, this is not possible and so we need
    ## custom setter functions.

    def set_node_input_default_value(index, node, prop, value):
        """Set the default value of the node's index'th input"""
        node.inputs[index].default_value = value

    attribute_setters = {
        # XXX Maybe we should, in fact, search through the inputs for one with the given name?
        # Distort node has distortion and dispersion in its inputs (not properties)
        ("Lens Distortion", "distortion"): functools.partial(set_node_input_default_value, 1),
        ("Lens Distortion", "dispersion"): functools.partial(set_node_input_default_value, 2),
        ("Filter", "factor"): functools.partial(set_node_input_default_value, 0),
        ("Blur", "size"): functools.partial(set_node_input_default_value, 1),
    }

    # Loop through the nodes that we expect in the chain
    for node_name, node_properties in compositor_chain_db.items():
        for node_property, property_value in node_properties.items():
            try:
                attribute_setter = attribute_setters.get((node_name, node_property), setattr)
                attribute_setter(bpy.data.scenes["Scene"].node_tree.nodes[node_name], node_property, property_value)
            except KeyError:
                logging.exception("Compositor config specified node \"%s\" which is missing from blend file." % node_name)
            except AttributeError:
                logging.exception("Compositor config specified non-existant property \"%s\" for node \"%s\"." % (node_property, node_name))

# WIP
def setup_compositor_source_image(src_filepath):

    # First we have to load the source image sequence into Blender's data object tree
#    result = bpy.ops.image.open(
#                            filepath=os.path.join(src_path, (src_filename_stub + "%04d" % frame_start),
#                            directory=src_path, 
#                            files=[ {"name": src_filename_stub + ("%04d" % i) + src_filename_ext} 
#                                    for i in range(frame_start, frame_end + 1)
#                                  ], 
#                            show_multiview=False)
#                        )

    # First we have to load the source imageinto Blender's data object tree
    result = bpy.ops.image.open(
                            directory=os.path.dirname(src_filepath), 
                            files=[ {"name": os.path.basename(src_filepath)} ],
                            show_multiview=False
                        )

    if result != {'FINISHED'}:
        raise FileNotFoundError("Failed to load source image sequence for composition")

    try:
        image = bpy.data.images[os.path.basename(src_filepath)]
    except KeyError as e:
        raise ValueError("Source image loaded, but not available.")

    # We expect the compositor node setup to have an Image Sequenece node called "Source Image"
    try:
        source_image_node = bpy.data.scenes["Scene"].node_tree.nodes["Source Image"]
    except KeyError as e:
        raise ValueError("Compositor missing 'Source Image' node.")

    source_image_node.image = image
    image.colorspace_settings.name = 'Filmic Log'
    image.source = 'FILE'



    # XXX Need to set frame start and end, and output file resolution to match the source footage
    # and set the output path.

## This is a Blender python script. It should
## 1. Get from the command line
##   a. the directory to monitor
##   b. the output directoy and filename pattern
## 2. Set up the compositor nodes as specified in the JSON
## 3. Do any configuration of standard Blender settings, render engine etc. needed for compositing.
## 4. Monitor the incoming directory for frames that have not yet been composited
## 5. Setup the Source Image node to point to the incoming frame
## 6. Setup the output resolution to match the incoming frame
## 7. Render to write the composite frame
## 8. Loop back to 4


# Parse command line
#
argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all args after "--"

print(len(argv))
if len(argv) == 5:
    [shot_list_db_filepath, shot_category, shot_id, slate_number, outgoing_file_extension] = argv
else:
    raise ValueError("Not enough command line parameters supplied to compositor_script.py")

##
## Load the shot list, which contains the compositor chain configuration
##
shot_list_db = shot_list_db.ShotListDb.from_file(shot_list_db_filepath)

# Look up the shot using category + ID.
shot_info = shot_list_db.get_shot_info(shot_category, shot_id)

##
## Figure out the incoming filestub from the shot list DB settings
##

# Use output path override given in the shot list, if given. Otherwise, fallback on eg. Renders/Title/slate_3/...
# XXX Duplicate code
if shot_info.get("output_filepath_override"):
    incoming_filestub = shot_info.get("output_filepath_override")
else:
    output_path_base =  os.path.join(shot_list_db.render_root, shot_info["title"])

    if slate_number is None:
        slate_number = find_next_slate_number(output_path_base)

    filename =  shot_category + "_" + shot_id + "_" + slate_number + "_"
    incoming_filestub = os.path.join(output_path_base, "slate_%s/" % str(slate_number)) + filename 

incoming_file_format = shot_list_db.get_shot_info(shot_category, shot_id).get("output_file_format", "PNG")
incoming_file_extension = IMAGE_FILE_EXTENSIONS[incoming_file_format]

outgoing_filestub = os.path.join(output_path_base, "slate_%s_composite/" % str(slate_number)) + filename 

##
## Setup the nodes in the compositor chain.
##
compositor_chain_db = shot_info.get("compositor_chain", None)
if compositor_chain_db:
    configure_compositor_chain(compositor_chain_db)

##
## Set render settings
##
bpy.context.scene.render.engine = 'CYCLES'

##
## Some helper functions
##
frame_filepath = lambda filestub, file_extension, frame_number: filestub + ("%04d" % frame_number) + "." + file_extension
incoming_frame_filepath = functools.partial(frame_filepath, incoming_filestub, incoming_file_extension)
outgoing_frame_filepath = functools.partial(frame_filepath, outgoing_filestub, outgoing_file_extension)

##
## Define a function to composite a single frame.
##
def composite_frame(frame_number):
    """Composite a single frame"""
    setup_compositor_source_image(incoming_frame_filepath(frame_number))

    ## Set output
    bpy.context.scene.render.filepath = outgoing_filestub

    bpy.context.scene.frame_start = frame_number
    bpy.context.scene.frame_end = frame_number
    bpy.ops.render.render(animation=True)


##
## Monitor incoming 
##

# render_script.py defaults frame_start and frame_end to whatever is in the blend file. However,
# we don't want to have to read the blend file here, so you need to specify them if you want to 
# composite
#
try:
    frame_start = shot_info['frame_start']
    frame_end = shot_info['frame_end']
except KeyError as e:
    raise Exception("For compositing, 'frame_start' and 'frame_end' must be specified in the JSON shot-info file") from e

print("INCOMING FRAME PATH:", incoming_frame_filepath(0))
print("OUTGOING FRAME PATH:", outgoing_frame_filepath(0))

num_frames = (frame_end - frame_start + 1)
while True:
    composited_frames = set(
        frame_number
        for frame_number in range(frame_start, frame_end + 1)
        if os.path.exists(outgoing_frame_filepath(frame_number))
     )

    incoming_frames = set(
        frame_number 
        for frame_number in range(frame_start, frame_end + 1)
        if os.path.exists(incoming_frame_filepath(frame_number))
    )

    print("INCOMING:", incoming_frames)
    print("FRAMES ALREADY COMPOSITED:", composited_frames)

    # Quit when we have composited all frames
    if len(composited_frames) == num_frames:
        logging.info("Composited %d of %d frames; exiting"% (num_frames, num_frames))
        exit()

    frames_waiting_to_be_composited = incoming_frames - composited_frames

    for frame in frames_waiting_to_be_composited:
        composite_frame(frame)

    if len(frames_waiting_to_be_composited) == 0:
        logging.info("No frames waiting to be composited; sleeping 30s")
        sleep(30)