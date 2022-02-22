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

logging.basicConfig(level=logging.INFO)

###
### Handling clients
###
def list_queue(conn, render_queue):
    conn.send(render_queue)

def add_job(conn, params, render_queue):
    render_queue.append(params)
    conn.send(["OK"])

def del_job(conn, params, render_queue):
    new_render_queue = [ x for x in render_queue if x != params]

    n = len(render_queue) == len(new_render_queue)
    if n == 0:
        conn.send(["NOT FOUND"])
    else:
        # Tell the client how many we removed
        conn.send(["OK", n])

def handle_command(conn, cmd, render_queue):
    try:
        c = str(cmd[0]).upper()
        if c == "LIST":
            list_queue(conn, render_queue)
        elif c == "ADD":
            add_job(conn, cmd[1:], render_queue)
        elif c == "DEL":
            del_job(conn, cmd[1:], render_queue)
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
# ...............'AF_PIPE': Windows named pipe
address = r"\\.\pipe\RenderQ"

def client_request_handler(render_queue):
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

class RenderQueue:
    Shot = collections.namedtuple("Job", "category,id,slate")

    @classmethod
    def from_file(cls, manager, filepath):
        """Load the RenderQuene from a file

        manager:  A multiprocessing.Manager instance used to create the
                  shared state of the queue 
        """
        try:
            with open(filepath, "r") as file:
                return cls.from_db(manager, db)
        except Exception as e:
            raise IOError("Failed to read shot list") from e

        # Check that we have "quality" and "shots"
        if "quality" not in db:
            raise ValueError("Render queue file '%s' missing 'quality' key." % filepath)

        if "shots" not in db:
            raise ValueError("Render queue file '%s' missing 'shots' key." % filepath)

        def from_state(cls, state):
            return cls(state)

    @classmethod
    def from_db(cls, manager, db):
        """Create an instace of RenderQueue from a dict loaded from JSON"""
        state = manager.dict()
        state["quality"] = db["quality"]
        state["shots"] = [
            RenderQueue.Shot(shot["category"], shot["id"], shot["slate"])
            for job in db["shots"]
        ]

        return cls(state)

    @classmethod
    def from_state(cls, state):
        return cls(state)

    def __init__(self, state):
        self._state = state

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


###
### Process the queue
###

def queue_processor(render_queue_state, current_shot_as_lst):
    import render_manager
    import time

    # Convert from shared Python primatives to Python object wrappers.
    render_queue = RenderQueue.from_state(render_queue_state)
    current_shot = RenderQueue.Shot(*current_shot_as_lst) # XXX This is, in fact, copying the data, which could be an issue.

    if len(render_queue.shots) == 0:
        exit()

    while True:

        # 
        # Call verify_render to see if current shot needs building
        # if it does, launch the build.
        # if it doesn't, update current_shot to the next shot
        # Loop back
        # Did we go through all the shots without building anything?
        # Yes -> sleep 1 minute
        # Loop

        is_render_complete = render_manager.verify_render(shot)
        if not is_render_complete:
            render_manager.build(shot.category, shot.id, render_queue.quality, shot.slate)
        else:
            try:
                i = [ for shot in enumerate(render_queue.shots) 
                      if shot.category == current_shot.category
                         and shot.id == current_shot.id 
                         and shot.slate == current_shot.slate][0][0]
            except IndexError:
                # Shot doesn't exist; so start again from the top
                logging.info("Shot \"" + str(shot) + "\" missing from render queue; starting again from first shot")
                i = -1

                # Sleep 30 seconds at the end of the queue, just to avoid going round in a hard
                # loop if all the shots have been built.
                time.sleep(30)

            try:
                current_shot = render_queue.shots[i+1]
            except IndexError:
                logging.info("Shot \"" + str(shot) + "\" is the only one in the queue")

        time.sleep(5)

if __name__ == '__main__':
    with Manager() as manager:
        render_queue = RenderQueue.from_file(r"render_queue.json")
        # Copy of category/id/slate identifies the current shot.
        current_shot = manager.list(render_queue.shots[0])

        children = []
        children.append(Process(target=client_request_handler, args=(render_queue,)))
        children.append(Process(target=queue_processor, args=(render_queue.state, current_shot)))
    
    [ c.start() for c in children ]
    [ c.join() for c in children ]