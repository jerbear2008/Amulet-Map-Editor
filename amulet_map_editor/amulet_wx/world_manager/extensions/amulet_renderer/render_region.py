from OpenGL.GL import *
from typing import Dict, Tuple, Set, Union
import numpy
import queue
from .render_chunk import RenderChunk
from ..amulet_renderer import shaders


class ChunkManager:
    def __init__(self, identifier: str, region_size=16):
        self.identifier = identifier
        self.region_size = region_size
        self._regions: Dict[Tuple[int, int], RenderRegion] = {}
        # added chunks are put in here and then processed on the next call of draw
        # This is because add_render_chunk can be called from a different thread to draw
        # which causes issues due to dictionaries resizing
        self._chunk_temp: queue.Queue = queue.Queue()
        self._chunk_temp_set = set()

    def add_render_chunk(self, render_chunk: RenderChunk):
        self._chunk_temp.put(render_chunk)
        self._chunk_temp_set.add((render_chunk.cx, render_chunk.cz))

    def _merge_chunk_temp(self):
        for _ in range(self._chunk_temp.qsize()):
            render_chunk = self._chunk_temp.get()
            region_coords = self.region_coords(render_chunk.cx, render_chunk.cz)
            if region_coords not in self._regions:
                self._regions[region_coords] = RenderRegion(region_coords[0], region_coords[1], self.region_size, self.identifier)
            self._regions[region_coords].add_render_chunk(render_chunk)
        self._chunk_temp_set.clear()

    def __contains__(self, chunk_coords: Tuple[int, int]):
        region_coords = self.region_coords(*chunk_coords)
        return chunk_coords in self._chunk_temp_set or \
            region_coords in self._regions and chunk_coords in self._regions[region_coords]

    def region_coords(self, cx, cz):
        return cx // self.region_size, cz // self.region_size

    def draw(self, camera_transform):
        for region in self._regions.values():
            region.draw(camera_transform)
        self._merge_chunk_temp()

    def unload(self, safe_area: Tuple[int, int, int, int] = None):
        if safe_area is None:
            for _ in range(self._chunk_temp.qsize()):
                self._chunk_temp.get()
            self._chunk_temp_set.clear()
            for region in self._regions.values():
                region.unload()
            self._regions.clear()
        else:
            min_rx, min_rz = self.region_coords(*safe_area[:2])
            max_rx, max_rz = self.region_coords(*safe_area[2:])
            delete_regions = []
            for region in self._regions.values():
                if min_rx <= region.rx <= max_rx and min_rz <= region.rz <= max_rz:
                    region.merge()
                else:
                    region.unload()
                    delete_regions.append((region.rx, region.rz))

            for region in delete_regions:
                del self._regions[region]


class RenderRegion:
    def __init__(self, rx: int, rz: int, region_size: int, identifier: str):
        """A group of RenderChunks to minimise the number of draw calls"""
        self.identifier = identifier
        self.rx = rx
        self.rz = rz
        self._chunks: Dict[Tuple[int, int], RenderChunk] = {}
        self._manual_chunks = []
        self._shader = None
        self._trm_mat_loc = None
        self._vao = None
        self._vbo = None
        self._draw_count = 0

        self.region_transform = numpy.eye(4, dtype=numpy.float32)
        self.region_transform[3, [0, 2]] = numpy.array([rx, rz]) * region_size * 16

    def __repr__(self):
        return f'RenderRegion({self.rx}, {self.rz})'

    def __contains__(self, item):
        return item in self._chunks

    def add_render_chunk(self, render_chunk: RenderChunk):
        """Add a chunk to the region"""
        self._chunks[(render_chunk.cx, render_chunk.cz)] = render_chunk
        self._manual_chunks.append(render_chunk)

    def _setup(self):
        """Set up an empty VAO"""
        if self._vao is None:
            self._vao = glGenVertexArrays(1)
            glBindVertexArray(self._vao)
            self._vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
            glBufferData(GL_ARRAY_BUFFER, 0, numpy.zeros(0, dtype=numpy.float32), GL_DYNAMIC_DRAW)
            # vertex attribute pointers
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 40, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)
            # texture coords attribute pointers
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 40, ctypes.c_void_p(12))
            glEnableVertexAttribArray(1)
            # texture coords attribute pointers
            glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, 40, ctypes.c_void_p(20))
            glEnableVertexAttribArray(2)
            # tint value
            glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, 40, ctypes.c_void_p(36))
            glEnableVertexAttribArray(3)

            glBindVertexArray(0)

            self._shader = shaders.get_shader(self.identifier, 'render_chunk')
            self._trm_mat_loc = glGetUniformLocation(self._shader, "transformation_matrix")

    def merge(self):
        """If there are any chunks that have not been merged recreate the merged vertex table"""
        self._setup()
        if self._manual_chunks:
            glBindVertexArray(self._vao)
            glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
            verts = numpy.concatenate([chunk.chunk_lod0 for chunk in self._chunks.values()])
            self._draw_count = int(verts.size//10)
            glBufferData(GL_ARRAY_BUFFER, verts.size * 4, verts, GL_DYNAMIC_DRAW)
            for chunk in self._manual_chunks:
                chunk.unload()
            self._manual_chunks.clear()

    def unload(self):
        """Unload all chunks"""
        if self._vao is not None:
            glDeleteVertexArrays(1, self._vao)
            self._vao = None
        for chunk in self._chunks.values():
            chunk.unload()
        self._chunks.clear()

    def draw(self, transformation_matrix: numpy.ndarray):
        self._setup()
        glUseProgram(self._shader)
        transformation_matrix = numpy.matmul(self.region_transform, transformation_matrix)
        glUniformMatrix4fv(self._trm_mat_loc, 1, GL_FALSE, transformation_matrix)
        glBindVertexArray(self._vao)
        glDrawArrays(GL_TRIANGLES, 0, self._draw_count)
        for chunk in self._manual_chunks:
            chunk.draw(transformation_matrix)
