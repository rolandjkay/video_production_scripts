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
from shot_list_db import ShotListDb, print_table

SHOT_LIST_FILEPATH = "blender_shot_list.json"
BLENDER_ROOT = r"C:\Program Files\Blender Foundation\Blender 3.0"
RENDER_SCRIPT = "render_script.py"

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


def build_shot(shot_list_db, shot_category, shot_id, quality):
    shot_info = shot_list_db.get_shot_info(shot_category, shot_id)

    # Look up the blend file pattern from the shot list db and resolve to an actual file.
    #

    try:
        blend_file = find_latest_blend_file(shot_info["blend_file"])
    except KeyError as e:
        raise FileError("Shot list didn't specify blend file for shot %s/%s" % (shot_category, shot_id))


    build_cmd = " ".join(['"' + os.path.join(BLENDER_ROOT, "blender") + '"', 
                          "-b", '"' + blend_file + '"', 
                          "--python", '"' + os.path.join(render_manager_py_path, RENDER_SCRIPT) + '"', 
                          "--",
                          SHOT_LIST_FILEPATH,
                          shot_category,
                          shot_id,
                          quality])

    print("Launching blender")
    print("#################")
    print()
    print(build_cmd)
    print()

    res = subprocess.call(build_cmd, shell = True)

    print("Returned Value: ", res)

def main():
    cmd_name = sys.argv.pop(0) # Discard command name
    try:
        command = sys.argv.pop(0).upper()
    except IndexError:
        print("Nothing to do")
        return

    shot_list_db = ShotListDb.from_file(SHOT_LIST_FILEPATH)

    if command == "LIST":
        list_shots(shot_list_db)
    elif command == "BUILD":
        try:
            [shot_category, shot_id, quality] = sys.argv

            if quality.upper() not in ["LOW", "MEDIUM", "HIGH"]:
                raise ValueError
        except ValueError:
            print("Usage:", "render_manager.py", "BUILD", "<category>", "<id>", "<quality: LOW|MEDIUM|HIGH>", "[slate number]") 
            return
         
        build_shot(shot_list_db, shot_category, shot_id, quality) 
    else:
        print("Unknown command:", command)
        print("Usage:", "render_manager.py", "[LIST|BUILD]")
        

try:
    main()
except Exception:
    logging.exception("Quitting")

input("Press [ENTER] to quit")
