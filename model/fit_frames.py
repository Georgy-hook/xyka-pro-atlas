"""A rigid measuring frame. Project BReps, not the corners of their world boxes."""

from dataclasses import dataclass
from functools import cached_property

from fit_geometry import bounds, vec, xyz


@dataclass
class LocalSolid:
    shape: object

    @cached_property
    def box(self):
        return bounds(self.shape, True)


class Frame:
    def __init__(self, obj):
        self.to_world = obj.getGlobalPlacement()
        self.to_local = self.to_world.inverse()

    def solid(self, leaf):
        shape = leaf.shape.copy()  # The input is the already installed world BRep.
        shape.Placement = self.to_local.multiply(shape.Placement)
        return LocalSolid(shape)

    def local_point(self, point):
        return xyz(self.to_local.multVec(vec(point)))

    def point(self, local):
        return xyz(self.to_world.multVec(vec(local)))

    def direction(self, local):
        # Do not translate a normal/direction, including on a displaced cassette.
        return None if local is None else xyz(self.to_world.Rotation.multVec(vec(local)))
