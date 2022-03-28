"""Render Queue

This process implements a render queue server. Clients can connect and add
render jobs to the queue, remove jobs, interrogate the queue, kill jobs 
etc.

Commands:

LIST:               List all jobs in the queue
ADD <params>        Adds a new job.
                    (params should match render_manager.py's BUILD cmd)
DEL <params>        Removes the job with the givens params

"""
from multiprocessing.connection import Listener, wait
from multiprocessing import Process, Manager
from array import array
import logging
import json
import collections
import time
import os

logging.basicConfig(level=logging.INFO)

###
### Handling clients
###
def list_queue(conn, render_queue):
    conn.send(render_queue)

#def add_job(conn, params, render_queue):
#    render_queue.append(params)
#    conn.send(["OK"])
#
#def del_job(conn, params, render_queue):
#    new_render_queue = [ x for x in render_queue if x != params]
#
#    n = len(render_queue) == len(new_render_queue)
#    if n == 0:
#        conn.send(["NOT FOUND"])
#    else:
#        # Tell the client how many we removed
#        conn.send(["OK", n])

def handle_command(conn, cmd, render_queue):
    try:
        c = str(cmd[0]).upper()
        if c == "LIST":
            list_queue(conn, render_queue)
#        elif c == "ADD":
#            add_job(conn, cmd[1:], render_queue)
#        elif c == "DEL":
#            del_job(conn, cmd[1:], render_queue)
        else:
            raise ValueError("Unknown command")
    except IndexError as e:
        raise ValueError("Invalid cmd") from e


def handle_connection(conn, render_queue):
    try:
        while True:
            # Wait for a command
            cmd = conn.recv()
            logging.info("Received command: %s", cmd)

            try:
                handle_command(conn, cmd, render_queue)
            except Exception:
                logging.exception("Error handling command: %s", cmd)

    except EOFError:
        pass # Exit

# familycould be 'AF_INET': TCP
#                'AF_UNIX': Unix domain socket
#                'AF_PIPE': Windows named pipe
address = r"\\.\pipe\RenderQ"

def client_request_handler(render_queue_state):

    # Convert from shared Python primatives to Python object wrappers.
    render_queue = RenderQueue.from_state(render_queue_state)

    with Listener(address, "AF_PIPE") as listener:
        while True:
            logging.info("Waiting for connection...")
            with listener.accept() as conn:
                logging.info('Accepted connection')
                handle_connection(conn, render_queue)
                logging.info("Client disconnected")

###
### The Queue
###

_Shot = collections.namedtuple("_Shot", "category,id,slate")

def shot_to_str(shot):
    return str(shot.category) + "/" + str(shot.id) + "/" + str(shot.slate)

class RenderQueue:
    Shot = _Shot

    @staticmethod
    def read_json_file(filepath):
        try:
            with open(filepath, "r") as file:
                return json.load(file)
        except Exception as e:
            raise IOError("Failed to read render queue file") from e


    @staticmethod
    def init_state_from_db(state, db):
        # Check that we have "quality" and "shots"
        if "quality" not in db:
            raise ValueError("Render queue file '%s' missing 'quality' key.")

        if "shots" not in db:
            raise ValueError("Render queue file '%s' missing 'shots' key.")

        """Create an instace of RenderQueue from a dict loaded from JSON"""
        state["quality"] = db["quality"]
        state["shots"] = [
            RenderQueue.Shot(shot["category"], shot["id"], shot["slate"])
            for shot in db["shots"]
        ]

    @classmethod
    def from_file(cls, manager, filepath):
        """Load the RenderQuene from a file

        manager:  A multiprocessing.Manager instance used to create the
                  shared state of the queue 
        """
        return cls.from_db(manager, 
                           cls.read_json_file(filepath),
                           filepath,
                           os.stat(filepath).st_mtime)

    @classmethod
    def from_db(cls, manager, db, filepath = None, file_timestamp = None):
        """Create an instace of RenderQueue from a dict loaded from JSON"""

        state = manager.dict()
        cls.init_state_from_db(state, db)
        state["filepath"] = filepath
        state["file_timestamp"] = file_timestamp

        return cls.from_state(state)

    @classmethod
    def from_state(cls, state):
        return cls(state)

    def __init__(self, state):
        self._state = state

    def refresh(self):
        """Poll the source file and update if necessary"""

        # Don't do anything if we weren't loaded from a file.
        if self.state["filepath"] is not None:
            timestamp = os.stat(self.state["filepath"]).st_mtime
            if timestamp != self.state["file_timestamp"]:
                logging.info("Change detected; reloading render queue...")
                try:
                    self.init_state_from_db(self.state, self.read_json_file(self.state["filepath"]))
                    self.state["file_timestamp"] = timestamp
                    logging.info("Reload successful")
                except Exception:
                    logging.exception("Reload FAILED.")

    @property
    def quality(self):
        return self._state["quality"]

    @property
    def shots(self):
        return self._state["shots"]

    # Get the internal state (to pass to a sub-process)
    @property
    def state(self):
        return self._state

#
# Do common initialization tasks of the renderer and compositor subprocesses
#
def setup_subprocess(subprocess_name, render_queue_state, current_shot_as_lst):
    logging.info("Starting " + subprocess_name)
    logging.info("*********" + ("*" * len(subprocess_name)))

    # Convert from shared Python primatives to Python object wrappers.
    render_queue = RenderQueue.from_state(render_queue_state)
    current_shot = RenderQueue.Shot(*current_shot_as_lst) # XXX This is, in fact, copying the data, which could be an issue.

    if len(render_queue.shots) == 0:
        logging.info("Queue empty; quitting")
        exit()

    # XXX Could be neater. It's a shame we have to do this here.
    shot_list_db = render_manager.ShotListDb.from_file(render_manager.SHOT_LIST_FILEPATH)

    return render_queue, shot_list_db, current_shot

#
# Get the index of the next shot in the queue.
# - Of course, typically, this will just be i + 1, where 'i' is the index of the current shot.
#   However, the user may edit the render queue while we are running and so, we cannot 
#   assume that the indicies always correspond to the same shot.
#
# - To resolve this, we search again to find the index of the current shot and then move to
#   the next one. Or, if the current shot has been removed form the queue, we start again
#   at the top of the queue.
#
def get_next_shot(render_queue, current_shot, end_of_queue_sleep_time):
    try:
        # Find current shot
        index = [ i for (i, shot) in enumerate(render_queue.shots) 
                      if shot.category == current_shot.category
                         and shot.id == current_shot.id 
                         and shot.slate == current_shot.slate][0]
    except IndexError:
        # Shot doesn't exist; so start again from the top
        logging.info("Shot \"" + shot_to_str(current_shot) + "\" missing from render queue; starting again from first shot.")
        index = -1

    try:
        new_shot = render_queue.shots[index+1]
    except IndexError:
        logging.info("Shot \"" + shot_to_str(current_shot) + "\" is the last in the queue.")

        # Sleep 30 seconds at the end of the queue, just to avoid going round in a hard
        # loop if all the shots have been built.
        logging.info("Sleeping for %d seconds..." % end_of_queue_sleep_time)
        time.sleep(end_of_queue_sleep_time)

        new_shot = render_queue.shots[0]

    return new_shot


###
### Process the queue
###
import render_manager
import time

# This is the main function of the render sub-process
def render_queue_main(render_queue_state, current_shot_as_lst):

    render_queue, shot_list_db, current_shot = setup_subprocess("render queue", render_queue_state, current_shot_as_lst)

    while True:

        # 
        # Call verify_render to see if current shot needs building
        # if it does, launch the build.
        # if it doesn't, update current_shot to the next shot
        # Loop back
        # Did we go through all the shots without building anything?
        # Yes -> sleep 1 minute
        # Loop

        is_render_complete = render_manager.verify_shot(shot_list_db, current_shot.category,
                                                        current_shot.id, 
                                                        render_queue.quality, 
                                                        current_shot.slate)
        if not is_render_complete:
            logging.info("Shot \""+ shot_to_str(current_shot) + "\" not rendered; launching Blender...")
            render_manager.build_shot(shot_list_db, current_shot.category,
                                                    current_shot.id, 
                                                    render_queue.quality, 
                                                    current_shot.slate,
                                                    in_separate_window = True)
        else:
            logging.info("Shot \"" + shot_to_str(current_shot) + "\" already built; trying next shot...")

            current_shot = get_next_shot(render_queue, current_shot, end_of_queue_sleep_time = 30)

        # Check for changes in the render queue file.
        render_queue.refresh()

        logging.info("Sleeping for 5 seconds...")
        time.sleep(5)

# This is the main function of the compositor sub-process
def compositor_queue_main(render_queue_state, current_shot_as_lst):

    # Do any setup of this sub-process; e.g. wrap 'render_queue_state' in a Python object.
    render_queue, shot_list_db, current_shot = setup_subprocess("compositor queue", render_queue_state, current_shot_as_lst)


    while True:
        shot_info = shot_list_db.get_shot_info(current_shot.category, current_shot.id)

        if shot_info.get("compositing_enabled", False):
            render_manager.composite_shot(shot_list_db,
                                          current_shot.category,
                                          current_shot.id, 
                                          render_queue.quality, 
                                          current_shot.slate,
                                          in_separate_window = True)

        logging.info("Shot \"" + shot_to_str(current_shot) + "\" composited; trying next shot...")

        current_shot = get_next_shot(render_queue, current_shot, end_of_queue_sleep_time = 300)

        # Check for changes in the render queue file.
        render_queue.refresh()

        logging.info("Sleeping for 5 seconds...")
        time.sleep(5)



#
# Note that we wrote this as a multi-processing script, so that one thread could
# listen to client requests and the other run the queue. But, in the end, we
# don't really need to listen to client requests; but, we might in the future,
# and, if we ever get two GPUs, we will need multiprocessing, so we leave
# it like that for now.
#

if __name__ == '__main__':
    with Manager() as manager:
        render_queue = RenderQueue.from_file(manager, r"render_queue.json")
        # Copy of category/id/slate identifies the current shot.
        current_shot = manager.list(render_queue.shots[0])

        children = []
       # children.append(Process(target=client_request_handler, args=(render_queue.state,)))
        children.append(Process(target=render_queue_main, args=(render_queue.state, current_shot)))
        children.append(Process(target=compositor_queue_main, args=(render_queue.state, current_shot)))

    
        [ c.start() for c in children ]
        [ c.join() for c in children ]
    print("EXITING")