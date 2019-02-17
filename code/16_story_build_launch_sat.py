from __future__ import division
import sys, os
import math
import random
import time
import copy

# custom classes in other files
# -----------------------------
import AI_class
import sensors
# -----------------------------

from collections import deque
from pyglet import image
from pyglet.gl import *
from pyglet.graphics import TextureGroup
from pyglet.window import key, mouse


TICKS_PER_SEC = 60

# Size of sectors used to ease block loading.
SECTOR_SIZE = 16

WALKING_SPEED = 5
FLYING_SPEED = 15

GRAVITY = 20.0
MAX_JUMP_HEIGHT = 1.0 # About the height of a block.
# To derive the formula for calculating jump speed, first solve
#    v_t = v_0 + a * t
# for the time at which you achieve maximum height, where a is the acceleration
# due to gravity and v_t = 0. This gives:
#    t = - v_0 / a
# Use t and the desired MAX_JUMP_HEIGHT to solve for v_0 (jump speed) in
#    s = s_0 + v_0 * t + (a * t^2) / 2
JUMP_SPEED = math.sqrt(2 * GRAVITY * MAX_JUMP_HEIGHT)
TERMINAL_VELOCITY = 50

PLAYER_HEIGHT = 2

if sys.version_info[0] >= 3:
    xrange = range

def cube_vertices(x, y, z, n):
    """ Return the vertices of the cube at position x, y, z with size 2*n.

    """
    return [
        x-n,y+n,z-n, x-n,y+n,z+n, x+n,y+n,z+n, x+n,y+n,z-n,  # top
        x-n,y-n,z-n, x+n,y-n,z-n, x+n,y-n,z+n, x-n,y-n,z+n,  # bottom
        x-n,y-n,z-n, x-n,y-n,z+n, x-n,y+n,z+n, x-n,y+n,z-n,  # left
        x+n,y-n,z+n, x+n,y-n,z-n, x+n,y+n,z-n, x+n,y+n,z+n,  # right
        x-n,y-n,z+n, x+n,y-n,z+n, x+n,y+n,z+n, x-n,y+n,z+n,  # front
        x+n,y-n,z-n, x-n,y-n,z-n, x-n,y+n,z-n, x+n,y+n,z-n,  # back
    ]


# changed n=4 to n=8 to allow for more textures
def tex_coord(x, y, n=8):
    """ Return the bounding vertices of the texture square.

    """
    m = 1.0 / n
    dx = x * m
    dy = y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m


def tex_coords(top, bottom, side):
    """ Return a list of the texture squares for the top, bottom and side.

    """
    top = tex_coord(*top)
    bottom = tex_coord(*bottom)
    side = tex_coord(*side)
    result = []
    result.extend(top)
    result.extend(bottom)
    result.extend(side * 4)
    return result


TEXTURE_PATH = 'story_textures.png'

#                   top,   bottom,  side
# basic blocks
GRASS = tex_coords((1, 0), (0, 1), (0, 0))
SAND = tex_coords((1, 1), (1, 1), (1, 1))
BRICK = tex_coords((2, 0), (2, 0), (2, 0))
STONE = tex_coords((2, 1), (2, 1), (2, 1))
MOB_STATE1 = tex_coords((2, 1), (2, 1), (0, 3))
MOB_STATE2 = tex_coords((2, 1), (2, 1), (1, 3))
SAT_PIECE = tex_coords((2, 1), (2, 1), (2, 3))
HEART_1 = tex_coords((2,1), (2,1), (3,2))
HEART_2 = tex_coords((2,1), (2,1), (3,3))

# composite blocks
COMPOSITE_RED = tex_coords((3, 1), (3, 1), (3, 1))
COMPOSITE_BLUE = tex_coords((3, 0), (3, 0), (3, 0))
COMPOSITE_BLACK = tex_coords((0, 2), (0, 2), (0, 2))
COMPOSITE_GREY = tex_coords((1, 2), (1, 2), (1, 2))
COMPOSITE_GREEN = tex_coords((2, 2), (2, 2), (2, 2))

# green creeper blocks
CREEPER_HEAD = tex_coords((4, 1), (4, 1), (4, 0))
CREEPER_BODY = tex_coords((4, 1), (4, 1), (4, 1))

# red creeper coutdown blocks
CR_HEAD = tex_coords((4, 4), (4, 4), (4, 2))
CR_1 = tex_coords((4, 4), (4, 4), (0, 4))
CR_2 = tex_coords((4, 4), (4, 4), (1, 4))
CR_3 = tex_coords((4, 4), (4, 4), (2, 4))
CR_4 = tex_coords((4, 4), (4, 4), (3, 4))
CR_5 = tex_coords((4, 4), (4, 4), (4, 3))

# neutralized creeper blocks
NC_HEAD = tex_coords((5, 1), (5, 1), (5, 0))
NC_BODY = tex_coords((5, 1), (5, 1), (5, 1))

# circuit blocks
CABLE = tex_coords((1, 5), (1, 5), (1, 5))
ELECH = tex_coords((2, 5), (2, 5), (2, 5))
ELECT = tex_coords((0, 5), (0, 5), (0, 5))

# sensor blocks
SENSOR_ACTIVE = tex_coords((4, 5), (4, 5), (4, 5))
SENSOR_RED = tex_coords((3, 5), (3, 5), (3, 5))

# all textures possible
ALL_TEXTURE = [GRASS, SAND, BRICK, STONE, MOB_STATE1, MOB_STATE2, SAT_PIECE, HEART_1, HEART_2,
COMPOSITE_RED, COMPOSITE_BLUE, COMPOSITE_BLACK, COMPOSITE_GREY, COMPOSITE_GREEN,
CREEPER_HEAD, CREEPER_BODY, CR_HEAD, CR_1, CR_2, CR_3, CR_4, CR_5, CABLE, ELECH, ELECT, 
SENSOR_ACTIVE, SENSOR_RED]

# all composite blocks
COMPOSITE = [COMPOSITE_RED, COMPOSITE_BLUE, COMPOSITE_BLACK, COMPOSITE_GREY, COMPOSITE_GREEN]

# all creeper blocks
CREEPER = [CREEPER_HEAD, CREEPER_BODY, CR_HEAD, CR_1, CR_2, CR_3, CR_4, CR_5,
NC_HEAD, NC_BODY]

FACES = [
    ( 0, 1, 0),
    ( 0,-1, 0),
    (-1, 0, 0),
    ( 1, 0, 0),
    ( 0, 0, 1),
    ( 0, 0,-1),
]


def normalize(position):
    """ Accepts `position` of arbitrary precision and returns the block
    containing that position.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    block_position : tuple of ints of len 3

    """
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y, z)


def sectorize(position):
    """ Returns a tuple representing the sector for the given `position`.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    sector : tuple of len 3

    """
    x, y, z = normalize(position)
    x, y, z = x // SECTOR_SIZE, y // SECTOR_SIZE, z // SECTOR_SIZE
    return (x, 0, z)


class Model(object):

    def __init__(self):

        # A Batch is a collection of vertex lists for batched rendering.
        self.batch = pyglet.graphics.Batch()

        # A TextureGroup manages an OpenGL texture.
        self.group = TextureGroup(image.load(TEXTURE_PATH).get_texture())

        # A mapping from position to the texture of the block at that position.
        # This defines all the blocks that are currently in the world.
        self.world = {}

        self.circuit = {}

        self.sensors = []

        self.added_elech = False

        # Same mapping as `world` but only contains blocks that are shown.
        self.shown = {}

        # Mapping from position to a pyglet `VertextList` for all shown blocks.
        self._shown = {}

        # Mapping from sector to a list of positions inside that sector.
        self.sectors = {}

        # Simple function queue implementation. The queue is populated with
        # _show_block() and _hide_block() calls
        self.queue = deque()

        self.rocket_loaded = False
        self.rocket_health_red = pyglet.resource.image("rocket_health_red.png")
        self.rocket_health_red = pyglet.sprite.Sprite(self.rocket_health_red, 60, 75)
        self.rocket_health_red.scale_y = 0.5
        self.rocket_health_outline = pyglet.resource.image("rocket_health_outline.png")
        self.rocket_health_outline = pyglet.sprite.Sprite(self.rocket_health_outline, 60, 75)
        self.rocket_health_outline.scale = 0.5

        self.rocket_health = 1

        self.mob_loaded = False

        self.mob_mode = "1"

        self.mob_x_position = 0

        self.mob_z_position = 0

        #need for when jumping
        self.mob_y_position = -1

        self.mob_update_count = 0

        self.mob_frames = 33

        # AI for running or following
        self.ai = AI_class.AI()

        # satellite pieces
        self.sat_pieces = []

        self.trapped = False

        # health blocks
        self.health_map_icons = {}

        self.rocket_launched = False
        self.rocket_count = 0
        self.rocket_altitude = 0

        self._initialize()

    def _initialize(self):
        """ Initialize the world by placing all the blocks.

        """
        n = 80  # 1/2 width and height of world
        s = 1  # step size
        y = 0  # initial y height
        for x in xrange(-n, n + 1, s):
            for z in xrange(-n, n + 1, s):
                # create a layer stone an grass everywhere.
                self.add_block((x, y - 2, z), GRASS, immediate=False)
                self.add_block((x, y - 3, z), STONE, immediate=False)
                if x in (-n, n) or z in (-n, n):
                    # create outer walls.
                    for dy in xrange(-2, 3):
                        self.add_block((x, y + dy, z), STONE, immediate=False)

        # generate the hills randomly
        o = n - 10
        for _ in xrange(120):
            a = random.randint(-o, o)  # x position of the hill
            b = random.randint(-o, o)  # z position of the hill
            c = -1  # base of the hill
            h = random.randint(1, 6)  # height of the hill
            s = random.randint(4, 8)  # 2 * s is the side length of the hill
            d = 1  # how quickly to taper off the hills
            t = random.choice([GRASS, SAND, BRICK])
            for y in xrange(c, c + h):
                for x in xrange(a - s, a + s + 1):
                    for z in xrange(b - s, b + s + 1):
                        if (x - a) ** 2 + (z - b) ** 2 > (s + 1) ** 2:
                            continue
                        if (x - 0) ** 2 + (z - 0) ** 2 < 5 ** 2:
                            continue
                        self.add_block((x, y, z), t, immediate=False)
                s -= d  # decrement side lenth so hills taper off

        # randomly place pieces of satellite around map
        for i in xrange(6):
            x = random.randint(-75, 75)
            z = random.randint(-75, 75)
            y = -1
            pos = (x, y, z)
            while pos in self.world:
                y += 1
                pos = (x, y, z)
            self.add_block(pos, SAT_PIECE, immediate=False)
            self.sat_pieces.append(pos)

    def mob_move_right(self):
        """ Function to move the mob right
        """
        self.remove_block((self.mob_x_position, self.mob_y_position, self.mob_z_position))
        self.mob_x_position += 1

        if self.mob_mode == "1":
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)
        else:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE2)

    def mob_move_left(self):
        """ Function to move the mob left
        """
        self.remove_block((self.mob_x_position, self.mob_y_position, self.mob_z_position))
        self.mob_x_position -= 1

        if self.mob_mode == "1":
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)
        else:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE2)

    def mob_move_forward(self):
        """ Function to move the mob forward
        """
        self.remove_block((self.mob_x_position, self.mob_y_position, self.mob_z_position))
        self.mob_z_position += 1

        if self.mob_mode == "1":
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)
        else:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE2)

    def mob_move_backward(self):
        """ Function to move the mob backward
        """
        self.remove_block((self.mob_x_position, self.mob_y_position, self.mob_z_position))
        self.mob_z_position -= 1

        if self.mob_mode == "1":
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)
        else:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE2)

    #jump functions
    def mob_move_up(self):
        self.remove_block((self.mob_x_position, self.mob_y_position, self.mob_z_position))
        self.mob_y_position += 1

        if self.mob_mode == "1":
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)
        else:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE2)

    def mob_move_down(self):
        self.remove_block((self.mob_x_position, self.mob_y_position, self.mob_z_position))
        self.mob_y_position -= 1

        if self.mob_mode == "1":
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)
        else:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE2)

    def load_mob(self):
        if not self.mob_loaded:
            self.add_block((self.mob_x_position, self.mob_y_position, self.mob_z_position), MOB_STATE1)

    def launch_mob(self):
        if not self.mob_loaded:
            self.add_block((self.mob_x_position, -1, self.mob_z_position), MOB_STATE1)
            self.mob_loaded = True

    def stop_mob(self):
        if self.mob_loaded:
            self.mob_loaded = False

    def process_mob(self):
        """
            This function will process the mob and decide if it should
            move left, right, forward, or backward
        """

        if self.mob_loaded and self.mob_update_count >= 128:
            # adjust the mob
            if self.mob_mode == "1":
                self.mob_mode = "2"
            elif self.mob_mode == "2":
                self.mob_mode = "1"
            self.mob_move_left()

            self.mob_update_count = 0
        else:
            self.mob_update_count += 1

        if self.mob_loaded and self.mob_update_count >= 128:
            # adjust the mob
            if self.mob_mode == "1":
                self.mob_mode = "2"
            elif self.mob_mode == "2":
                self.mob_mode = "1"
            self.mob_move_backward()

            self.mob_update_count = 0
        else:
            self.mob_update_count += 1

        if self.mob_loaded and self.mob_update_count >= 128:
            # adjust the mob
            if self.mob_mode == "1":
                self.mob_mode = "2"
            elif self.mob_mode == "2":
                self.mob_mode = "1"
            self.mob_move_right()

            self.mob_update_count = 0
        else:
            self.mob_update_count += 1

        if self.mob_loaded and self.mob_update_count >= 128:
            # adjust the mob
            if self.mob_mode == "1":
                self.mob_mode = "2"
            elif self.mob_mode == "2":
                self.mob_mode = "1"
            self.mob_move_forward()

            self.mob_update_count = 0
        else:
            self.mob_update_count += 1

    def hit_test(self, position, vector, max_distance=8):
        """ Line of sight search from current position. If a block is
        intersected it is returned, along with the block previously in the line
        of sight. If no block is found, return None, None.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check visibility from.
        vector : tuple of len 3
            The line of sight vector.
        max_distance : int
            How many blocks away to search for a hit.

        """
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in xrange(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None, None

    def neighbor(self, position):
        x, y, z = position
        local = set()
        for dx in [-1, 0, 1]:  #if (dx is within [-1,0,1]) is true
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:  #if (dz is within [-1,0,1]) is true then key = (x+dx,y,z+dz)
                    key = (x + dx, y + dy, z + dz)
                    local.add(key)
        return(local)

    def circuit_change(self):
        count_h = {}
        to_cable = set()
        to_elect = set()
        to_elech = set()
        elech_safe = set()
        check_elech = False
        for position in self.circuit:
            if self.circuit[position] == ELECH:
                check_elech = True
            if position not in count_h:
                count_h[position] = 0
            if self.circuit[position] is ELECT:
                to_cable.add(position)
            elif self.circuit[position] is ELECH:
                local = self.neighbor(position)
                for pos in local:
                    if pos in self.circuit and self.circuit[pos] is CABLE:
                        if pos not in count_h:
                            count_h[pos] = 0
                        count_h[pos] += 1
                        if count_h[pos] <= 2:
                            to_elech.add(pos)
                        elif pos in to_elech:
                            to_elech.remove(pos)
                to_elect.add(position)
        for position in to_elect:
            self.add_block(position, ELECT)
        for position in to_elech:
                self.add_block(position, ELECH)
        for position in to_cable:
            self.add_block(position, CABLE)

        if not check_elech:
            self.added_elech = False

    def exposed(self, position):
        """ Returns False is given `position` is surrounded on all 6 sides by
        blocks, True otherwise.

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
        return False

    def add_block(self, position, texture, immediate=True):
        """ Add a block with the given `texture` and `position` to the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to add.
        texture : list of len 3
            The coordinates of the texture squares. Use `tex_coords()` to
            generate.
        immediate : bool
            Whether or not to draw the block immediately.

        """
        if position in self.world:
            self.remove_block(position, immediate)
        self.world[position] = texture
        self.sectors.setdefault(sectorize(position), []).append(position)
        if immediate:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)
        if texture in [ELECH, CABLE, ELECT]:
            self.circuit[position] = texture

    def remove_block(self, position, immediate=True):
        """ Remove the block at the given `position`.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to remove.
        immediate : bool
            Whether or not to immediately remove block from canvas.

        """
        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if immediate:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)
        if position in self.circuit:
            del self.circuit[position]

    def check_neighbors(self, position):
        """ Check all blocks surrounding `position` and ensure their visual
        state is current. This means hiding blocks that are not exposed and
        ensuring that all exposed blocks are shown. Usually used after a block
        is added or removed.

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block(key)
            else:
                if key in self.shown:
                    self.hide_block(key)

    def show_block(self, position, immediate=True):
        """ Show the block at the given `position`. This method assumes the
        block has already been added with add_block()

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        immediate : bool
            Whether or not to show the block immediately.

        """
        texture = self.world[position]
        self.shown[position] = texture
        if immediate:
            self._show_block(position, texture)
        else:
            self._enqueue(self._show_block, position, texture)

    def _show_block(self, position, texture):
        """ Private implementation of the `show_block()` method.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        texture : list of len 3
            The coordinates of the texture squares. Use `tex_coords()` to
            generate.

        """
        x, y, z = position
        vertex_data = cube_vertices(x, y, z, 0.5)
        texture_data = list(texture)
        # create vertex list
        # FIXME Maybe `add_indexed()` should be used instead
        self._shown[position] = self.batch.add(24, GL_QUADS, self.group,
            ('v3f/static', vertex_data),
            ('t2f/static', texture_data))

    def hide_block(self, position, immediate=True):
        """ Hide the block at the given `position`. Hiding does not remove the
        block from the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to hide.
        immediate : bool
            Whether or not to immediately remove the block from the canvas.

        """
        self.shown.pop(position)
        if immediate:
            self._hide_block(position)
        else:
            self._enqueue(self._hide_block, position)

    def _hide_block(self, position):
        """ Private implementation of the 'hide_block()` method.

        """
        self._shown.pop(position).delete()

    def show_sector(self, sector):
        """ Ensure all blocks in the given sector that should be shown are
        drawn to the canvas.

        """
        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)

    def hide_sector(self, sector):
        """ Ensure all blocks in the given sector that should be hidden are
        removed from the canvas.

        """
        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)

    def change_sectors(self, before, after):
        """ Move from sector `before` to sector `after`. A sector is a
        contiguous x, y sub-region of world. Sectors are used to speed up
        world rendering.

        """
        before_set = set()
        after_set = set()
        pad = 4
        for dx in xrange(-pad, pad + 1):
            for dy in [0]:  # xrange(-pad, pad + 1):
                for dz in xrange(-pad, pad + 1):
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)

    def _enqueue(self, func, *args):
        """ Add `func` to the internal queue.

        """
        self.queue.append((func, args))

    def _dequeue(self):
        """ Pop the top function from the internal queue and call it.

        """
        func, args = self.queue.popleft()
        func(*args)

    def process_queue(self):
        """ Process the entire queue while taking periodic breaks. This allows
        the game loop to run smoothly. The queue contains calls to
        _show_block() and _hide_block() so this method should be called if
        add_block() or remove_block() was called with immediate=False

        """
        start = time.process_time()
        while self.queue and time.process_time() - start < 1.0 / TICKS_PER_SEC:
            self._dequeue()

    def process_entire_queue(self):
        """ Process the entire queue with no breaks.

        """
        while self.queue:
            self._dequeue()

    def code_load(self, num="", type=""):
        """
        If given a number (num), returns composite block at that index.
        If given a composite block type (type), returns the index of that type.
        """
        if not isinstance(num, str):
            return COMPOSITE[int(num)]
        elif not isinstance(type, str):
            for i in xrange(0, len(COMPOSITE)):
                if type == COMPOSITE[i]:
                    return i
        print("Invalid Call")

    def load_txt(self):
        """
        Load composite blocks from a .txt file
        """
        if not self.rocket_loaded:
            for x in xrange(1, 21):
                for z in xrange(-8, 13):
                    for y in xrange(-1, 6):
                        pos = (x, y, z)
                        if pos in self.world:
                            self.remove_block(pos)

            with open('rocket.txt', 'r') as file:
                line = file.readline()
                while line:
                    line = line.split(" ")
                    x, y, z = int(line[0]), int(line[1]), int(line[2])
                    block_type = self.code_load(num=int(line[3]))
                    self.add_block((x, y, z), block_type)
                    line = file.readline()
                self.rocket_loaded = True

class Window(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        # Whether or not the window exclusively captures the mouse.
        self.exclusive = False

        # When flying gravity has no effect and speed is increased.
        self.flying = False

        # Strafing is moving lateral to the direction you are facing,
        # e.g. moving to the left or right while continuing to face forward.
        #
        # First element is -1 when moving forward, 1 when moving back, and 0
        # otherwise. The second element is -1 when moving left, 1 when moving
        # right, and 0 otherwise.
        self.strafe = [0, 0]

        # Current (x, y, z) position in the world, specified with floats. Note
        # that, perhaps unlike in math class, the y-axis is the vertical axis.
        self.position = (0, 0, 0)

        # First element is rotation of the player in the x-z plane (ground
        # plane) measured from the z-axis down. The second is the rotation
        # angle from the ground plane up. Rotation is in degrees.
        #
        # The vertical plane rotation ranges from -90 (looking straight down) to
        # 90 (looking straight up). The horizontal rotation range is unbounded.
        self.rotation = (-45, 0)

        # Which sector the player is currently in.
        self.sector = None

        # The crosshairs at the center of the screen.
        self.reticle = None

        # Velocity in the y (upward) direction.
        self.dy = 0

        # A list of blocks the player can place. Hit num keys to cycle.
        self.inventory = [BRICK, GRASS, SAND, CABLE, ELECH, ELECT]

        # The current block the user can place. Hit num keys to cycle.
        self.block = self.inventory[0]

        # Convenience list of num keys.
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]

        # Instance of the model that handles the world.
        self.model = Model()

        # The label that is displayed in the top left of the canvas.
        self.label = pyglet.text.Label('', font_name='Arial', font_size=18,
            x=10, y=self.height - 10, anchor_x='left', anchor_y='top',
            color=(0, 0, 0, 255))

        # This call schedules the `update()` method to be called
        # TICKS_PER_SEC. This is the main game event loop.
        pyglet.clock.schedule_interval(self.update, 1.0 / TICKS_PER_SEC)

        #health bar setup: initally full health
        self.health = []
        for i in xrange(0,10):
            self.health.append(pyglet.resource.image("heart_2.png"))
        self.health_value = 10
        self.fell_height = False
        self.max_vel = 0

        self.count_injure = 91

        # map objects
        self.map = pyglet.resource.image("black_map.png")
        self.map = pyglet.sprite.Sprite(self.map, self.width - 150,
                                        self.height - 150)
        self.map.scale = 0.275

        # player icon
        self.steve_dot = pyglet.resource.image("steve_dot.png")
        self.steve_dot = pyglet.sprite.Sprite(self.steve_dot, self.width - 85,
                                              self.height - 85)
        self.steve_dot.scale = 0.025

        # mob icon
        self.mob_dot = pyglet.resource.image("mob_dot.png")
        self.mob_dot = pyglet.sprite.Sprite(self.mob_dot, self.width - 85,
                                            self.height - 85)
        self.mob_dot.scale = 0.025

        # satellite pieces
        self.sat_dot = pyglet.resource.image("sat_dot.png")
        # draw locations on map
        self.sat_pieces = copy.deepcopy(self.model.sat_pieces)
        for i in xrange(0, len(self.sat_pieces)):
            self.sat_pieces[i] = pyglet.sprite.Sprite(self.sat_dot,
                           self.width - 85 + 137*(self.sat_pieces[i][0]/160),
                           self.height - 85 - 137*(self.sat_pieces[i][2]/160))
            self.sat_pieces[i].scale = 0.025

        self.count_sat = 0
        self.sat_label = pyglet.text.Label('', font_name='Arial', font_size=18,
            x=self.width - 15, y=10, anchor_x='right', anchor_y='bottom',
            color=(0, 0, 0, 255))

        # creeper
        self.creeper = [AI_class.Creeper(self.model.world),
                        AI_class.Creeper(self.model.world),
                        AI_class.Creeper(self.model.world),
                        AI_class.Creeper(self.model.world),
                        AI_class.Creeper(self.model.world)]
        for i in range(0, 5):
            	for j in range(i + 1, 5):
            		pos_i = (self.creeper[i].pos_x,
                   			 self.creeper[i].pos_y,
                   			 self.creeper[i].pos_z)
            		pos_j = (self.creeper[j].pos_x,
                   			 self.creeper[j].pos_y,
                   			 self.creeper[j].pos_z)
            		dist = 0.0
            		for k in range(0, 3):
            			dist += (pos_j[k] - pos_i[k])**2
            		dist = math.sqrt(dist)
            		if dist < 5:
            			self.creeper[j] = AI_class.Creeper(self.model.world)
            			j -= 1
        self.creeper_temp = pyglet.resource.image("mob_dot.png")
        self.creeper_icon = []
        for i in xrange(0, 5):
            self.creeper_icon.append(pyglet.sprite.Sprite(self.creeper_temp,
                            self.width - 85 + 137*(self.creeper[i].pos_x/160),
                            self.height - 85 - 137*(self.creeper[i].pos_z/160)))
            self.creeper_icon[i].scale = 0.025
        self.creeper_count = 0

    def set_exclusive_mouse(self, exclusive):
        """ If `exclusive` is True, the game will capture the mouse, if False
        the game will ignore the mouse.

        """
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """ Returns the current line of sight vector indicating the direction
        the player is looking.

        """
        x, y = self.rotation
        # y ranges from -90 to 90, or -pi/2 to pi/2, so m ranges from 0 to 1 and
        # is 1 when looking ahead parallel to the ground and 0 when looking
        # straight up or down.
        m = math.cos(math.radians(y))
        # dy ranges from -1 to 1 and is -1 when looking straight down and 1 when
        # looking straight up.
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90)) * m
        dz = math.sin(math.radians(x - 90)) * m
        return (dx, dy, dz)

    def get_motion_vector(self):
        """ Returns the current motion vector indicating the velocity of the
        player.

        Returns
        -------
        vector : tuple of len 3
            Tuple containing the velocity in x, y, and z respectively.

        """
        if any(self.strafe):
            x, y = self.rotation
            strafe = math.degrees(math.atan2(*self.strafe))
            y_angle = math.radians(y)
            x_angle = math.radians(x + strafe)
            if self.flying:
                m = math.cos(y_angle)
                dy = math.sin(y_angle)
                if self.strafe[1]:
                    # Moving left or right.
                    dy = 0.0
                    m = 1
                if self.strafe[0] > 0:
                    # Moving backwards.
                    dy *= -1
                # When you are flying up or down, you have less left and right
                # motion.
                dx = math.cos(x_angle) * m
                dz = math.sin(x_angle) * m
            else:
                dy = 0.0
                dx = math.cos(x_angle)
                dz = math.sin(x_angle)
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0
        return (dx, dy, dz)

    def update(self, dt):
        """ This method is scheduled to be called repeatedly by the pyglet
        clock.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        self.model.process_queue()
        sector = sectorize(self.position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue()
            self.sector = sector
        m = 8
        dt = min(dt, 0.2)
        for _ in xrange(m):
            self._update(dt / m)

        #self.model.process_mob()
        self.move_mob()

    def _update(self, dt):
        """ Private implementation of the `update()` method. This is where most
        of the motion logic lives, along with gravity and collision detection.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        # walking
        speed = FLYING_SPEED if self.flying else WALKING_SPEED
        d = dt * speed # distance covered this tick.
        dx, dy, dz = self.get_motion_vector()
        # New position in space, before accounting for gravity.
        dx, dy, dz = dx * d, dy * d, dz * d
        # gravity
        if not self.flying:
            # Update your vertical speed: if you are falling, speed up until you
            # hit terminal velocity; if you are jumping, slow down until you
            # start falling.
            self.dy -= dt * GRAVITY
            self.dy = max(self.dy, -TERMINAL_VELOCITY)
            dy += self.dy * dt
        # collisions
        x, y, z = self.position
        x, y, z = self.collide((x + dx, y + dy, z + dz), PLAYER_HEIGHT)
        self.position = (x, y, z)

    def collide(self, position, height):
        """ Checks to see if the player at the given `position` and `height`
        is colliding with any blocks in the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check for collisions at.
        height : int or float
            The height of the player.

        Returns
        -------
        position : tuple of len 3
            The new position of the player taking into account collisions.

        """
        # How much overlap with a dimension of a surrounding block you need to
        # have to count as a collision. If 0, touching terrain at all counts as
        # a collision. If .49, you sink into the ground, as if walking through
        # tall grass. If >= .5, you'll fall through the ground.
        pad = 0.25
        p = list(position)
        np = normalize(position)
        for face in FACES:  # check all surrounding blocks
            for i in xrange(3):  # check each dimension independently
                if not face[i]:
                    continue
                # How much overlap you have with this dimension.
                d = (p[i] - np[i]) * face[i]
                if d < pad:
                    continue
                for dy in xrange(height):  # check each height
                    op = list(np)
                    op[1] -= dy
                    op[i] += face[i]
                    if tuple(op) not in self.model.world:
                        continue
                    p[i] -= (d - pad) * face[i]
                    if face == (0, -1, 0) or face == (0, 1, 0):
                        # You are colliding with the ground or ceiling, so stop
                        # falling / rising.
                        self.dy = 0
                    break
        return tuple(p)

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called when a mouse button is pressed. See pyglet docs for button
        amd modifier mappings.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        button : int
            Number representing mouse button that was clicked. 1 = left button,
            4 = right button.
        modifiers : int
            Number representing any modifying keys that were pressed when the
            mouse button was clicked.

        """
        if self.exclusive:
            vector = self.get_sight_vector()
            block, previous = self.model.hit_test(self.position, vector)
            if (button == mouse.RIGHT) or \
                    ((button == mouse.LEFT) and (modifiers & key.MOD_CTRL)):
                # ON OSX, control + left click = right click.
                if previous:
                    if self.block != ELECH or not self.model.added_elech:
                        if self.block == ELECH:
                            self.model.added_elech = True
                            for i in self.model.sensors:
                                i.status = False
                                self.model.add_block(i.location, SENSOR_RED)
                        self.model.add_block(previous, self.block)
            elif button == pyglet.window.mouse.LEFT and block:
                texture = self.model.world[block]
                if texture == HEART_1:
                    self.health_value += 0.5
                    h = self.health_value
                    self.update_health(h)
                    del self.model.health_map_icons[block]
                elif texture == HEART_2:
                    self.health_value += 1.0
                    h = self.health_value
                    self.update_health(h)
                    del self.model.health_map_icons[block]
                if texture not in [STONE, MOB_STATE1, MOB_STATE2,
                SAT_PIECE, SENSOR_ACTIVE, SENSOR_RED] and texture not in COMPOSITE and texture not in CREEPER:
                    self.model.remove_block(block)
                if texture == ELECH:
                    self.model.added_elech = False
                    for i in self.model.sensors:
                        i.activated = False
                        self.model.add_block(i.location, SENSOR_RED)
        else:
            self.set_exclusive_mouse(True)

    def on_mouse_motion(self, x, y, dx, dy):
        """ Called when the player moves the mouse.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        dx, dy : float
            The movement of the mouse.

        """
        if self.exclusive:
            m = 0.15
            x, y = self.rotation
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.rotation = (x, y)

    def on_key_press(self, symbol, modifiers):
        """ Called when the player presses a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[1] -= 1
        elif symbol == key.D:
            self.strafe[1] += 1
        elif symbol == key.SPACE:
            if self.dy == 0:
                self.dy = JUMP_SPEED
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
        #elif symbol == key.TAB: #disable flying
        #    self.flying = not self.flying
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0]) % len(self.inventory)
            self.block = self.inventory[index]
        elif symbol == key.F:
            if not self.model.mob_loaded:
                self.set_exclusive_mouse(True)
                self.model.mob_x_position = -5
                self.model.mob_z_position = -5
                self.model.mob_y_position = -1
                pos = (self.model.mob_x_position,
                       self.model.mob_y_position,
                       self.model.mob_z_position)
                while pos in self.model.world:
                    self.model.mob_y_position += 1
                    pos = (self.model.mob_x_position,
                       self.model.mob_y_position,
                       self.model.mob_z_position)
                self.model.load_mob()
                self.model.ai.mode = "follow"
                self.model.ai.status = True
                self.model.mob_loaded = True
        elif symbol == key.T and self.count_sat == 6 and not self.model.trapped:
            self.draw_trap()
        elif symbol == key.N and self.model.rocket_loaded:
            self.neut_creeper()
        elif symbol == key.L and self.model.trapped and not self.model.rocket_loaded:
            self.model.load_txt()
            for i in xrange(0, 3):
                self.load_creeper()
        elif symbol == key.C:
            self.model.circuit_change()

    def neut_creeper(self):
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.position, vector)[0]
        if block:
            x, y, z = block
            pos = (-5, -5, -5)
            if self.model.world[block] in [CR_HEAD, CREEPER_HEAD]:
                # have head selected
                pos = (x, y - 1, z)
            elif self.model.world[block] in CREEPER:
                # have body selected
                pos = (x, y, z)
            if pos != (-5, -5, -5):
                for i in self.creeper:
                    p = (i.pos_x, i.pos_y, i.pos_z)
                    if pos == p:
                        i.status = False
                        self.model.add_block(pos, NC_BODY)
                        pos = (pos[0], pos[1] + 1, pos[2])
                        self.model.add_block(pos, NC_HEAD)
                        self.load_creeper()


    def on_key_release(self, symbol, modifiers):
        """ Called when the player releases a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[1] += 1
        elif symbol == key.D:
            self.strafe[1] -= 1

    def on_resize(self, width, height):
        """ Called when the window is resized to a new `width` and `height`.

        """
        # label
        self.label.y = height - 10
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = self.width // 2, self.height // 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
        )

    def set_2d(self):
        """ Configure OpenGL to draw in 2d.

        """
        width, height = self.get_size()
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_3d(self):
        """ Configure OpenGL to draw in 3d.

        """
        width, height = self.get_size()
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65.0, width / float(height), 0.1, 60.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        x, y = self.rotation
        glRotatef(x, 0, 1, 0)
        glRotatef(-y, math.cos(math.radians(x)), 0, math.sin(math.radians(x)))
        x, y, z = self.position
        glTranslatef(-x, -y, -z)

    def draw_map(self):
        temp = (self.width - 150, self.height - 150)
        self.map.position = temp
        self.map.draw()
        self.steve_dot.x = int(self.width - 85 + 137*(self.position[0]/160))
        self.steve_dot.y = int(self.height - 85 - 137*(self.position[2]/160))
        self.steve_dot.draw()

        if self.model.ai.status:
            self.mob_dot.x = int(self.width - 85 + 137*(self.model.mob_x_position/
                                                        160))
            self.mob_dot.y = int(self.height - 85 - 137*(self.model.mob_z_position/
                                                         160))
            self.mob_dot.draw()
            self.collect_sat()

        for i in xrange(0, len(self.sat_pieces)):
            self.sat_pieces[i].position = (self.width - 85 + 137*(self.model.sat_pieces[i][0]/160),
                           self.height - 85 - 137*(self.model.sat_pieces[i][2]/160))
            self.sat_pieces[i].draw()

        if self.model.trapped:
            for i in self.model.health_map_icons:
                self.model.health_map_icons[i].draw()

        for i in xrange(0, 5):
            if self.creeper[i].status:
                self.creeper_icon[i].x = self.width - 85 + 137*(self.creeper[i].pos_x/160)
                self.creeper_icon[i].y = self.height - 85 - 137*(self.creeper[i].pos_z/160)
                self.creeper_icon[i].draw()

    def collect_sat(self):
        # make satellite piece dispear from map and from world
        index = 0
        for i in self.model.sat_pieces:
            dist = (self.position[0] - i[0])**2 + (self.position[1] - i[1])**2 + (self.position[2] - i[2])**2
            if dist < 1.56:
                self.model.remove_block(i)
                del self.model.sat_pieces[index]
                del self.sat_pieces[index]
                self.count_sat += 1
                self.model.mob_frames -= 3
            index += 1

    def check_height(self):
        if abs(self.dy) > 12:
            self.fell_height = True
            self.max_vel = max(self.max_vel, abs(self.dy))

    def update_health(self, h):
        self.health = []
        full = int(math.floor(h))
        #fill full hearts
        for i in xrange(0, full):
            self.health.append(pyglet.resource.image("heart_2.png"))

        #border case: could be empty, half, or full
        if float(h - full) < 0.35:
            self.health.append(pyglet.resource.image("heart_0.png"))
            self.health_value = float(full)
        elif float(h - full) < 0.65:
            self.health.append(pyglet.resource.image("heart_1.png"))
            self.health_value = float(full) + 0.5
        else:
            self.health.append(pyglet.resource.image("heart_2.png"))
            self.health_value = float(full) + 1.0

        #remaining hearts are empty
        for i in xrange(full + 1, 10):
            self.health.append(pyglet.resource.image("heart_0.png"))

    def draw_health(self):
        # check if health should be lost
        self.check_height()
        # change in health value when hit ground
        if self.fell_height == True and self.dy == 0:
            # get new health value and reset variables
            self.fell_height = False
            self.health_value = max(0, self.health_value - (self.max_vel/9.0))
            self.max_vel = 0
            # update displayed health
            self.update_health(self.health_value)

        #check for injury due to mob
        self.check_mob_dist()

        # draw the health bar
        for i in xrange(0,10):
            heart = pyglet.sprite.Sprite(self.health[i], 50 + i * 40, 20)
            heart.scale = 0.05
            heart.draw()

        if self.model.trapped:
            for icon in self.model.health_map_icons:
                temp_x, temp_y = icon[0], icon[2]
                temp_x = int(self.width - 85 + 137*(temp_x/160))
                temp_y = int(self.height - 85 - 137*(temp_y/160))
                self.model.health_map_icons[icon].position = (temp_x, temp_y)

        # rocket has health once it's loaded
        if self.model.rocket_loaded:
            self.model.rocket_health_red.scale_x = 0.5 * self.model.rocket_health
            self.model.rocket_health_red.draw()
            self.model.rocket_health_outline.draw()

    def check_game_over(self):
        if self.health_value == 0 or self.model.rocket_health == 0:
            message = pyglet.text.Label('GAME OVER', font_name='Arial', font_size=75,
            x=self.width/2, y=self.height/2, anchor_x='center', anchor_y='center',
            color=(255, 0, 0, 255))
            message.draw()
            self.set_exclusive_mouse(False)

    def check_mob_dist(self):
        if self.model.mob_loaded and not self.model.trapped:
            dist = [abs(self.position[0] - self.model.mob_x_position),
                abs(self.position[2] - self.model.mob_z_position),
                abs(self.position[1] - self.model.mob_y_position)]
            if not any(d > 1.25 for d in dist):
                s = dist[0]**2 + dist[1]**2 + dist[2]**2
                if s < 2.25 and self.count_injure > 90:
                    self.health_value = max(0, self.health_value - 2)
                    self.update_health(self.health_value)
                    self.count_injure = 0
                elif s > 2.25:
                    self.count_injure = 91
                else:
                    self.count_injure += 1

    # returns whether or not a position is available
    # returns true if available, false if not
    def check_avail(self, pos):
        if pos in self.model.world and self.model.world[pos] in ALL_TEXTURE:
            return False
        return True

    def move_mob(self):
        moved_up = False
        if self.model.ai.status and self.model.ai.count >= self.model.mob_frames:
            # forward backward left right
            if self.model.ai.mode == "follow":
                out = self.model.ai.follow(self.model.mob_x_position,
                                           self.model.mob_z_position,
                                           self.position[0],
                                           self.position[2])
            elif self.model.ai.mode == "run":
                out = self.model.ai.run_away(self.model.mob_x_position,
                                           self.model.mob_z_position,
                                           self.position[0],
                                           self.position[2])
            if out[0]:
                pos = (self.model.mob_x_position,
                       self.model.mob_y_position,
                       self.model.mob_z_position+1)
                # check if square in front not available
                if not self.check_avail(pos):
                    # check if one square up avaiable
                    pos = (pos[0], pos[1]+1, pos[2])
                    # if yes
                        # go there
                    if self.check_avail(pos):
                        self.model.mob_move_up()
                        self.model.mob_move_forward()
                        moved_up = True
                    # else
                        # don't move
                else:
                    self.model.mob_move_forward()
            elif out[1]:
                pos = (self.model.mob_x_position,
                       self.model.mob_y_position,
                       self.model.mob_z_position-1)
                if not self.check_avail(pos):
                    pos = (pos[0], pos[1]+1, pos[2])
                    if self.check_avail(pos):
                        self.model.mob_move_up()
                        self.model.mob_move_backward()
                        moved_up = True
                else:
                    self.model.mob_move_backward()
            if out[2]:
                pos = (self.model.mob_x_position-1,
                       self.model.mob_y_position,
                       self.model.mob_z_position)
                if not self.check_avail(pos):
                    pos = (pos[0], pos[1]+1, pos[2])
                    if self.check_avail(pos):
                        self.model.mob_move_up()
                        self.model.mob_move_left()
                        moved_up = True
                else:
                    self.model.mob_move_left()
            elif out[3]:
                pos = (self.model.mob_x_position+1,
                       self.model.mob_y_position,
                       self.model.mob_z_position)
                if not self.check_avail(pos):
                    pos = (pos[0], pos[1]+1, pos[2])
                    if self.check_avail(pos):
                        self.model.mob_move_up()
                        self.model.mob_move_right()
                        moved_up = True
                else:
                    self.model.mob_move_right()

            # make sure mob isn't floating
            pos = (self.model.mob_x_position,
                       self.model.mob_y_position-1,
                       self.model.mob_z_position)

            while (self.check_avail(pos) and pos[1] >= -2 and not moved_up):
                self.model.mob_move_down()
                pos = (self.model.mob_x_position,
                       self.model.mob_y_position-1,
                       self.model.mob_z_position)

            self.model.ai.count = 0
        else:
            self.model.ai.count += 1

    def draw_creeper(self, creeper):
        at_target = False
        dist = (creeper.pos_x - creeper.target[0])**2 + \
        (creeper.pos_z - creeper.target[2])**2
        if dist <= 3.125:
            at_target = True
        if creeper.count >= creeper.frames and creeper.status \
        and not at_target:
            # if at target position then need to continue or start countdown
            # remove from previous position
            pos_body = (copy.copy(creeper.pos_x),
                        copy.copy(creeper.pos_y),
                        copy.copy(creeper.pos_z))
            pos_head = (pos_body[0], pos_body[1] + 1, pos_body[2])

            # add to new position
            creeper.follow(self.model.world)
            pos = (creeper.pos_x, creeper.pos_y, creeper.pos_z)
            # if the creeper moved
            if pos != pos_body:
                # remove blocks from previous position
                self.model.remove_block(pos_body)
                self.model.remove_block(pos_head)
                # add blocks to new position
                self.model.add_block(pos, CREEPER_BODY)
                pos = (pos[0], pos[1] + 1, pos[2])
                self.model.add_block(pos, CREEPER_HEAD)
            creeper.count = 0
        else:
            creeper.count += 1

        #check for explosion
        if at_target:
            type = creeper.explode()
            pos = (creeper.pos_x, creeper.pos_y, creeper.pos_z)
            pos_head = (pos[0], pos[1] + 1, pos[2])
            if type == "boom":
                print(type)
                self.model.rocket_health = round(self.model.rocket_health - 0.2, 1)
                self.model.rocket_health = max(0, self.model.rocket_health)
                pos = (creeper.pos_x, creeper.pos_y, creeper.pos_z)
                self.model.remove_block(pos)
                self.model.remove_block((pos[0], pos[1] + 1, pos[2]))
                creeper.status = False
                if self.creeper_count < 5:
                    self.creeper[self.creeper_count].status = True
                    pos = (self.creeper[self.creeper_count].pos_x,
                           self.creeper[self.creeper_count].pos_y,
                           self.creeper[self.creeper_count].pos_z)
                    self.creeper_count += 1
                    self.model.add_block(pos, CREEPER_BODY)
                    pos = (pos[0], pos[1] + 1, pos[2])
                    self.model.add_block(pos, CREEPER_HEAD)
                dist = (self.position[0] - creeper.pos_x)**2 + (self.position[1]
                        - creeper.pos_y)**2 + (self.position[2] - creeper.pos_z)**2
                if dist < 25:
                    self.health_value -= 3
                    self.health_value = max(0, self.health_value)
                    self.update_health(self.health_value)
            elif type == "5":
                self.model.add_block(pos, CR_5)
                self.model.add_block(pos_head, CR_HEAD)
            elif type == "4":
                self.model.add_block(pos, CR_4)
            elif type == "3":
                self.model.add_block(pos, CR_3)
            elif type == "2":
                self.model.add_block(pos, CR_2)
            elif type == "1":
                self.model.add_block(pos, CR_1)

    def on_draw(self):
        """ Called by pyglet to draw the canvas.

        """

        self.clear()
        self.set_3d()
        glColor3d(1, 1, 1)
        self.model.batch.draw()
        self.draw_focused_block()
        self.set_2d()
        self.draw_label()
        self.draw_reticle()
        self.draw_health()
        self.draw_map()
        self.check_game_over()

        if not self.model.mob_loaded:
            self.set_exclusive_mouse(False)
            label = pyglet.text.Label('', font_name='Arial', font_size=30,
            x=self.width/2, y=self.height/2, anchor_x='center', anchor_y='center',
            color=(255, 255, 255, 255))
            label.text = "PRESS F TO LAUNCH MOB AND BEGIN"
            label.draw()
        for i in self.creeper:
            if i.status:
                self.draw_creeper(i)

    def draw_focused_block(self):
        """ Draw black edges around the block that is currently under the
        crosshairs.

        """
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.position, vector)[0]
        if block:
            x, y, z = block
            vertex_data = cube_vertices(x, y, z, 0.51)
            glColor3d(0, 0, 0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            pyglet.graphics.draw(24, GL_QUADS, ('v3f/static', vertex_data))
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def draw_label(self):
        """ Draw the label in the top left of the screen.

        """
        # determines the current block selected
        if (self.block == BRICK):
            blockSelectedString = "Brick"
        elif (self.block == GRASS):
            blockSelectedString = "Grass"
        elif (self.block == SAND):
            blockSelectedString = "Sand"
        elif (self.block == ELECH):
            blockSelectedString = "ELECH"
        elif (self.block == ELECT):
            blockSelectedString = "ELECT"
        elif (self.block == CABLE):
            blockSelectedString = "Cable"

        x, y, z = self.position
        self.label.text = '%02d (%.2f, %.2f, %.2f) %d / %d Block: %s' % (
            pyglet.clock.get_fps(), x, y, z,
            len(self.model._shown), len(self.model.world),
            blockSelectedString)
        self.label.draw()

        # text for satellite
        #self.count_sat = 6 #TODO TESTING
        if self.count_sat < 6:
            self.sat_label.text = 'Satellite Pieces Collected: %01d' % (
                self.count_sat)
        elif self.count_sat >= 6 and not self.model.trapped:
            self.sat_label.text = "Trap the Mob! 'T' builds trap."
        elif self.model.trapped and not self.model.rocket_loaded:
            self.sat_label.text = "Mob Trapped! Load Rocket (L)"
        elif self.model.rocket_loaded and self.creeper_count != 5:
            self.sat_label.text = "Neutralize Creepers (N)"
            #self.creeper_count = 5 # TODO TESTING
        elif self.creeper_count == 5:
            safe = True
            for i in self.creeper:
                if i.status:
                    safe = False
                    #safe = True # TODO TESTING
            if safe:
                self.sat_label.text = "Activate Sensors to Launch"
                if len(self.model.sensors) < 4:
                    self.model.sensors.append(sensors.Sensor((10, -1, -6)))
                    self.model.add_block((10, -1, -6), SENSOR_RED)
                    self.model.sensors.append(sensors.Sensor((18, -1, 2)))
                    self.model.add_block((18, -1, 2), SENSOR_RED)
                    self.model.sensors.append(sensors.Sensor((10, -1, 10)))
                    self.model.add_block((10, -1, 10), SENSOR_RED)
                    self.model.sensors.append(sensors.Sensor((2, -1, 2)))
                    self.model.add_block((2, -1, 2), SENSOR_RED)
                count_active = 0
                for i in self.model.sensors:
                    i.check_status(self.model.circuit, ELECH)
                    if i.activated:
                        count_active += 1
                        if self.model.world[i.location] != SENSOR_ACTIVE:
                            self.model.add_block(i.location, SENSOR_ACTIVE)
                    if count_active == 4:
                        self.launch_rocket()
                if self.model.rocket_launched:
                    self.sat_label.text = "Launching Rocket"
                    message = pyglet.text.Label('SUCCESS', font_name='Arial', font_size=75,
                    x=self.width/2, y=self.height/2, anchor_x='center', anchor_y='center',
                    color=(0, 255, 0, 255))
                    message.draw()
                    self.set_exclusive_mouse(False)
        self.sat_label.draw()

    def launch_rocket(self):
        if not self.model.rocket_launched:
            self.model.rocket_launched = True
            # place steve at top of rocket
        if self.model.rocket_count > 8:
            self.model.rocket_count = 0
            self.move_rocket_up()
            self.position = (10, self.model.rocket_altitude + 19, 2)
        self.model.rocket_count += 1

    def move_rocket_up(self):
        """
            0) find all the composite blocks and add to composite_world
            dictionary.  At the same time erase all the composite blocks from the world
            1) loop through composite_world dictionary and add blocks with y + 1
            to add each block to the world.
        """
        #self.position = (position(0), position(1)+1, position(2))
        composite_world = {}
        for world_key, world_value in list(self.model.world.items()):
            if world_value in COMPOSITE:
                composite_world[world_key] = world_value
                self.model.remove_block(world_key, True)

        for composite_key, composite_value in composite_world.items():
             if composite_value in COMPOSITE:
                new_x = composite_key[0]
                new_y = composite_key[1] + 1
                new_z = composite_key[2]
                self.model.add_block((new_x, new_y, new_z), composite_value)
        self.model.rocket_altitude += 1

    def draw_trap(self):
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.position, vector)[0]
        if block:
            x, y, z = block # coordinates of currently selected block
            for i in range(-3, 4): # x coordinate loop
                for j in range(-3, 4): # z coordinate loop
                    if (i == -3 or i == 3 or j == -3 or j == 3): # if i or j is +/- 3
                        for k in range(-1, y + 3): # y loop
                            if (x + i, k, z + j) not in self.model.world:
                            # add block if nothing there
                                "TODO"
                                # coordinates in call to add_block
                                # X = x + i
                                # Y = k
                                # Z = z + j
                                # block type: SAND
                    # add roof
                    "TODO"
                    # coordinates in call to add_block
                    # X = x + i
                    # Y = y + 3
                    # Z = z + j
                    # block type: SAND
        # make this true to acknowledge you edited the code
        drew_trap = False

        "recall call form: self.model.add_block((X, Y, Z), texture)"

        # --------------------------- #
        # DO NOT EDIT BELOW THIS LINE #
        # --------------------------- #

        # check mob inside trap
        in_x, in_y, in_z = False, False, False
        if self.model.mob_x_position in range(x-3, x+4):
            in_x = True
        if self.model.mob_z_position in range(z-3, z+4):
            in_z = True
        if self.model.mob_y_position < y + 3:
            in_y = True
        # if trapped, stop the mob from moving and attacking
        # and place blocks of health
        if in_x and in_y and in_z and drew_trap:
            self.model.trapped = True
            self.model.ai.status = False
            self.model.remove_block((self.model.mob_x_position,
                                     self.model.mob_y_position,
                                     self.model.mob_z_position))
            self.place_health()

    def load_creeper(self):
        if self.creeper_count < 5:
            self.creeper[self.creeper_count].status = True
            pos = (self.creeper[self.creeper_count].pos_x,
                   self.creeper[self.creeper_count].pos_y,
                   self.creeper[self.creeper_count].pos_z)
            self.model.add_block(pos, CREEPER_BODY)
            pos = (pos[0], pos[1] + 1, pos[2])
            self.model.add_block(pos, CREEPER_HEAD)
            self.creeper_count += 1
            self.draw_creeper(self.creeper[self.creeper_count - 1])

    def place_health(self):
        for i in xrange(3):
            x = random.randint(-60, 60)
            z = random.randint(-60, 60)
            y = -1
            while (x, y, z) in self.model.world:
                y += 1
            temp = str(random.randint(1, 2))
            if temp == "1":
                block_type = HEART_1
            else:
                block_type = HEART_2
            self.model.add_block((x, y, z), block_type)
            self.model.health_map_icons[(x, y, z)] = pyglet.resource.image(
                "heart_" + temp + ".png")
            self.model.health_map_icons[(x, y, z)] = pyglet.sprite.Sprite(
                self.model.health_map_icons[(x, y, z)], self.width - 85,
                self.height - 85)
            self.model.health_map_icons[(x, y, z)].scale = 0.02
            self.model.health_map_icons[(x, y, z)].x = int(self.width - 
                                                       85 + 137*(x/160))
            self.model.health_map_icons[(x, y, z)].y = int(self.height - 
                                                       85 - 137*(z/160))

    def draw_reticle(self):
        """ Draw the crosshairs in the center of the screen.

        """
        glColor3d(0, 0, 0)
        self.reticle.draw(GL_LINES)


def setup_fog():
    """ Configure the OpenGL fog properties.

    """
    # Enable fog. Fog "blends a fog color with each rasterized pixel fragment's
    # post-texturing color."
    glEnable(GL_FOG)
    # Set the fog color.
    glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.5, 0.69, 1.0, 1))
    # Say we have no preference between rendering speed and quality.
    glHint(GL_FOG_HINT, GL_DONT_CARE)
    # Specify the equation used to compute the blending factor.
    glFogi(GL_FOG_MODE, GL_LINEAR)
    # How close and far away fog starts and ends. The closer the start and end,
    # the denser the fog in the fog range.
    glFogf(GL_FOG_START, 20.0)
    glFogf(GL_FOG_END, 60.0)


def setup():
    """ Basic OpenGL configuration.

    """
    # Set the color of "clear", i.e. the sky, in rgba.
    glClearColor(0.5, 0.69, 1.0, 1)
    # Enable culling (not rendering) of back-facing facets -- facets that aren't
    # visible to you.
    glEnable(GL_CULL_FACE)
    # Set the texture minification/magnification function to GL_NEAREST (nearest
    # in Manhattan distance) to the specified texture coordinates. GL_NEAREST
    # "is generally faster than GL_LINEAR, but it can produce textured images
    # with sharper edges because the transition between texture elements is not
    # as smooth."
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    setup_fog()


def main():
    window = Window(width=800, height=600, caption='Sensor Craft', resizable=True)
    try:
        # Hide the mouse cursor and prevent the mouse from leaving the window.
        window.set_exclusive_mouse(True)
        setup()
        pyglet.app.run()
    except:
        # variation on error handling code taken from stack overflow:
        # https://stackoverflow.com/questions/1278705/python-when-i-catch-an-exception-how-do-i-get-the-type-file-and-line-number

        # get information about error
        exc_type, exc_object, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

        # free the mouse and close the window
        window.set_exclusive_mouse(False)
        window.close()

        # print error message
        print("Error Type: ", exc_type, '\n', "File Name: ", fname,'\n',
              "Line Number: ", exc_tb.tb_lineno, '\n',
              "Message: ", exc_object, sep='')


if __name__ == '__main__':
    main()
