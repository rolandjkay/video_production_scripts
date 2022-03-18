"""Common Code

"""
import bpy

IMAGE_FILE_EXTENSIONS = {
    "PNG": "png",
    'OPEN_EXR_MULTILAYER': "exr",
    'OPEN_EXR': "exr",
    "TIFF": "tiff",
    "JPEG": "jpeg",
    "JPEG2000": "jpeg"
}

def get_quality_index(quality):
    """Map a quality string to an index into the arrays in the JSON file"""
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "FINAL": 3}.get(quality.upper(), 3)


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


def print_table(table):
    """Pretty print a table of data"""
    column_widths = [0] * len(table[0])

    def elementwise_max(lst1, lst2):
        return [ max(x,y) for (x,y) in zip(lst1, lst2)]

    for row in table:
        widths = [ len(str(x)) for x in row]

        if len(widths) != len(column_widths):
            raise ValueError("Input table not square")

        column_widths = elementwise_max(column_widths, widths)

    for row in table:
        print("  ".join( 
                 [
                  "{0:{1}}".format(str(cell), column_width)
                  for cell, column_width in zip(row, column_widths)
                 ]
               )
             )


def set_render_resolution(shot_info, quality):
    """Set Blender's render resolution to match that specified in 'shot_info'"""
    quality_index = get_quality_index(quality)

    bpy.context.scene.render.resolution_percentage = shot_info.get("resolution_percentage", [50, 50, 100, 100])[quality_index]
    bpy.context.scene.render.resolution_x = parse_resolution_string(shot_info.get("target_resolution", "1920x1080"))[0];
    bpy.context.scene.render.resolution_y = parse_resolution_string(shot_info.get("target_resolution", "1920x1080"))[1];
