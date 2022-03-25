"""Render manager

Python script for batch rendering.

"""
import json
import argparse
import sys
import os
import logging
import subprocess
import copy

from shot_list_db import ShotListDb
from common import *


SHOT_LIST_FILEPATH = "blender_shot_list.json"
BLENDER_ROOT = r"C:\Program Files\Blender Foundation\Blender 3.0"
RENDER_SCRIPT = "render_script.py"
COMPOSITOR_SCRIPT = "compositor_script.py"

# Find the directory where this file (render_manager.py) resides
# NOTE: This will break if os.chdir() is called before this line runs
render_manager_py_path = os.path.dirname(os.path.realpath(__file__))

#parser = argparse.ArgumentParser(description='Build script for Blender shots')
##parser.add_argument('integers', metavar='N', type=int, nargs='+',
#                            help='an integer for the accumulator')
#parser.add_argument('--list', dest='list', action='store_const',
#                    const=True, default=False,
#                    help='list ')

#args = parser.parse_args()
#print(args.accumulate(args.integers))

def list_shots(shot_list_db):

    print_table(
        [["Title", "Category", "ID", "Frame Start", "End", "Blend File"]]
        +
        [
            [
                shot_list_db.get_shot_info(shot_category, shot_id)["title"],
                shot_list_db.get_shot_info(shot_category, shot_id)["category"],
                shot_list_db.get_shot_info(shot_category, shot_id)["id"],
                shot_list_db.get_shot_info(shot_category, shot_id).get("frame_start", "UNSET"),
                shot_list_db.get_shot_info(shot_category, shot_id).get("frame_end", "UNSET"),
                shot_list_db.get_shot_info(shot_category, shot_id).get("blend_file")
            ]
            for (shot_category, shot_id) in shot_list_db.shot_ids
        ]
    )
 
def find_latest_blend_file(filepath):
    """If 'filepath' contains the pattern '[X]', replace with the number
    of the most uptodate version

    """
    import re

    if '[X]' in filepath:
        pattern = re.compile(os.path.basename(filepath).replace('[X]', "([0-9]+)", 1))
    else:
        # If the '[X]' pattern isn't found, just return the given filename.
        return filepath

    max_index = -1
    dir_name = os.path.dirname(filepath)
    for candidate in os.listdir(dir_name if dir_name else "."):
        m = pattern.fullmatch(candidate)
        if m:
            index = int(m.group(1)) 
            if index > max_index:
                max_index = index

    if max_index == -1:
        raise FileError("No blend file found matching pattern '" + filepath + "'")
    else:
        return filepath.replace('[X]', str(max_index))


def build_shot(shot_list_db, shot_category, shot_id, quality, slate, in_separate_window = False):
    shot_info = shot_list_db.get_shot_info(shot_category, shot_id)

    # Look up the blend file pattern from the shot list db and resolve to an actual file.
    #

    try:
        blend_file = find_latest_blend_file(shot_info["blend_file"])
    except KeyError as e:
        raise FileError("Shot list didn't specify blend file for shot %s/%s" % (shot_category, shot_id))


    build_cmd = " ".join((["start", '"Renderer"', '/wait'] if in_separate_window else [])
                         +
                         ['"' + os.path.join(BLENDER_ROOT, "blender") + '"', 
                          "-b", '"' + blend_file + '"', 
                          "--python", '"' + os.path.join(render_manager_py_path, RENDER_SCRIPT) + '"', 
                          "--",
                          SHOT_LIST_FILEPATH,
                          str(shot_category),
                          str(shot_id),
                          quality,
                          str(slate)])

    print("Launching Blender Renderer")
    print("##########################")
    print()
    print(build_cmd)
    print()

    res = subprocess.call(build_cmd, shell = True)

    print("Returned Value: ", res)


def composite_shot(shot_list_db, shot_category, shot_id, quality, slate, in_separate_window = False):
    shot_info = shot_list_db.get_shot_info(shot_category, shot_id)

    # Look up the blend file pattern from the shot list db and resolve to an actual file.
    #

    DEFAULT_COMPOSITOR_CHAIN = "D:\\Assets\\Models\\Mine\\compositor recipes\\default_compositor_chain.blend"

    compositor_cmd = " ".join((["start", '"Compositor"', '/wait'] if in_separate_window else [])
                              +
                              ['"' + os.path.join(BLENDER_ROOT, "blender") + '"', 
                               "-b", '"' + DEFAULT_COMPOSITOR_CHAIN + '"', 
                               "--python", '"' + os.path.join(render_manager_py_path, COMPOSITOR_SCRIPT) + '"', 
                               "--",
                               SHOT_LIST_FILEPATH,
                               str(shot_category),
                               str(shot_id),
                               quality,
                               str(slate)])

    print("Launching Blender compositor")
    print("############################")
    print()
    print(compositor_cmd)
    print()

    res = subprocess.call(compositor_cmd, shell = True)

    print("Returned Value: ", res)

def verify_shot(shot_list_db, shot_category, shot_id, quality, slate):
    ### XXX We have the same code in render_script.py :/
    shot_info = shot_list_db.get_shot_info(shot_category, shot_id)

    # Use output path override given in the shot list, if given. Otherwise, fallback on eg. Renders/Title/slate_3/...
    if shot_info.get("output_filepath_override"):
        bpy.context.scene.render.filepath = shot_info.get("output_filepath_override")
    else:
        output_path_base =  os.path.join(shot_list_db.render_root, shot_info["title"])

#        if slate is None:
#            slate = find_next_slate_number(output_path_base)

    filename =  str(shot_category) + "_" + str(shot_id) + "_" + str(slate) + "_"
    render_path = os.path.join(output_path_base, "slate_%d\\" % slate) + filename

    ### If the frame range isn't specified, all we can do is check for at least one frame.
    if 'frame_start' in shot_info and 'frame_end' in shot_info:
        ext = IMAGE_FILE_EXTENSIONS[shot_info.get("output_file_format", "PNG")]
        
        for frame in range(shot_info["frame_start"], shot_info["frame_end"]):
            filename = "%04d" % frame + "." + ext
            if not os.path.exists(render_path + filename):
                return False
        return True
    else:
        return len(os.listdir(render_path)) > 0



def main(*_args):
    args = list(_args)

    try:
        cmd_name = args.pop(0) # Discard command name
        command = args.pop(0)
    except IndexError:
        print("Nothing to do")
        return

    shot_list_db = ShotListDb.from_file(SHOT_LIST_FILEPATH)

    if command == "LIST":
        list_shots(shot_list_db)
    elif command == "BUILD":
        try:
 #           if len(args) == 3:
 #               [shot_category, shot_id, quality] = args
 #               slate_number = None
            if len(args) == 4:
                [shot_category, shot_id, quality, slate_number] = args
            else:
                raise ValueError("Not enough args")

            if quality.upper() not in ["LOW", "MEDIUM", "HIGH", "FINAL"]:
                raise ValueError
        except ValueError:
            print("Usage:", "render_manager.py", "BUILD", "<category>", "<id>", "<quality: LOW|MEDIUM|HIGH|FINAL>", "[slate number]") 
            return
         
        build_shot(shot_list_db, shot_category, shot_id, quality, slate_number) 
    elif command == "COMPOSITE":
        try:
            #f len(args) == 3:
            #   [shot_category, shot_id, quality] = args
            #   slate_number = None
            if len(args) == 4:
                [shot_category, shot_id, quality, slate_number] = args
            else:
                raise ValueError("Not enough args")

            if quality.upper() not in ["LOW", "MEDIUM", "HIGH", "FINAL"]:
                raise ValueError
        except ValueError:
            print("Usage:", "render_manager.py", "COMPOSITE", "<category>", "<id>", "<quality: LOW|MEDIUM|HIGH|FINAL>", "slate number") 
            return
         
        composite_shot(shot_list_db, shot_category, shot_id, quality, slate_number) 
    else:
        print("Unknown command:", command)
        print("Usage:", "render_manager.py", "[LIST|BUILD]")
        

if __name__ == '__main__':
    try:
        main(*sys.argv)
    except Exception:
        logging.exception("Quitting")

    input("Press [ENTER] to quit")
