"""ShotListDB

A shot list DB object that encapsulates serialization to JSON and other 
operations on the data, such as handling inheritence and resolving
filepath short cuts.

"""
import copy
import json
import os

class ShotListDb:
    @classmethod
    def from_file(cls, filepath):
       try:
           with open(filepath, "r") as file:
               return cls(json.load(file), filepath)
       except Exception as e:
           raise IOError("Failed to read shot list") from e

    def __init__(self, db, filepath = None):
        # Check that we have "project_root" and "render_root"
        if "project_root" not in db:
           raise ValueError("Shot list db '%s' missing 'project_root' key." % filepath)

        if "render_root" not in db:
           raise ValueError("Shot list db '%s' missing 'render_root' key." % filepath)

        self._filepath = filepath
        self._db = db

    @property
    def project_root(self):
        return self._db["project_root"]

    @property
    def render_root(self):
        # If 'render_root' starts with "//" then replace with the project root.
        render_root = self._db["render_root"]
        if render_root[:2] == "//":
            return os.path.join(self.project_root, render_root[2:])
        else:
            return render_root

    def get_shot_info(self, shot_category, shot_id):
        """Read shot info from database, taking account of inheritance"""

        # Inner function to wrap the recursion, so we can do any necessary
        # post-processing afterwards once we've got the final result.
        def inner(shot_category, shot_id):
            # Look up the shot using category + ID.
            try:
                shot_info = [ shot for shot in self._db["shots"] 
                             if shot["category"] == shot_category and str(shot["id"]) == str(shot_id)
                            ][0]
            except IndexError as e:
                raise ValueError("No shot found with ID " + shot_category + "/" + str(shot_id)) from e 

            if "parent" not in shot_info:
                return shot_info

            # Recurse
            (parent_category, parent_id) = shot_info["parent"]
            parent_shot_info = copy.deepcopy(inner(parent_category, parent_id))

            parent_shot_info.update(shot_info)

            return parent_shot_info

        # Call 'inner' to get the raw shot_info without any post-processing.
        shot_info = inner(shot_category, shot_id)

        # Automatically resolve the blend file to a full path and filename
        #
        if "blend_file" in shot_info:
            shot_info["blend_file"] = self.get_blend_file_from_shot_info(shot_info)

        return shot_info


    @property
    def shot_ids(self):
        return [ (shot_info["category"], shot_info["id"]) 
                 for shot_info in self._db["shots"] 
               ]

    def get_blend_file(self, shot_category, shot_id):
        shot_info = self.get_shot_info(shot_category, shot_id)

        return self.get_blend_file_from_shot_info(shot_info)

    def get_blend_file_from_shot_info(self, shot_info):
        project_root = shot_info.get("project_root", None)
        blend_file = shot_info["blend_file"]

        if blend_file[:2] == "//":
            if project_root:
                return os.path.join(project_root, blend_file[2:])
            else:
                return blend_file[2:]
        else:
            return blend_file

    def refresh(self):
        """Update from original file; if loaded from file"""
        if self._filepath:
           with open(self._filepath, "r") as file:
               db = json.load(file)