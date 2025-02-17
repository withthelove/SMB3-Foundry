from typing import Optional, TYPE_CHECKING

from smb3parse import OFFSET_BY_OBJECT_SET_A000
from smb3parse.constants import (
    BASE_OFFSET,
    OFFSET_SIZE,
)
from smb3parse.data_points.util import DataPoint, _IndexedMixin, _PositionMixin
from smb3parse.levels import (
    FIRST_VALID_ROW,
    WORLD_MAP_BASE_OFFSET,
    WORLD_MAP_SCREEN_SIZE,
    WORLD_MAP_SCREEN_WIDTH,
)
from smb3parse.util.rom import PRG_BANK_SIZE, Rom

if TYPE_CHECKING:
    from smb3parse.data_points.world_map_data import WorldMapData


class LevelPointerData(_PositionMixin, _IndexedMixin, DataPoint):
    """
    Levels are defined by the memory location of the level header and level object data, the memory location of the
    enemy and item data and the Object Set of the Level, necessary to interpret the level object data correctly.

    Since there is no look up table for these values in the ROM itself, levels can be found in two ways, either by a
    level pointer on a World Map, or by their memory locations and object set being part of another level's header.

    This class deals with the former method. It stores the memory locations and object set of the Level, as well as a
    reference to the World Map it is located in and the position it is at in said World Map.
    """

    SIZE = 2 * OFFSET_SIZE + 2  # object offset, enemy offset, 2 bytes for position in map

    def __init__(self, world_map_data: "WorldMapData", index: int):
        self.world = world_map_data
        """A reference to the WorldMapData object for the Overworld this LevelPointer was found in."""
        self.index = index

        self.object_set_address = 0x0
        self.object_set = 0
        """The Object Set to be used, when parsing and generating the Level Objects of the Level."""

        self.level_offset_address = 0x0
        self.level_offset = 0
        """
        The PRG Bank with the level data will be loaded into RAM at location 0xA000, so every level offset will be
        between 0xA000 and 0xBFFF. Points to the Level Header.
        """

        self.enemy_offset_address = 0x0
        self.enemy_offset = 0
        """The offset into the ROM, that the enemy data can be found."""

        super(LevelPointerData, self).__init__(self.world._rom)

    def calculate_addresses(self):
        self.x_address = self.screen_address = self.world.x_pos_list_start + self.index
        self.y_address = self.object_set_address = self.world.y_pos_list_start + self.index

        self.level_offset_address = (
            WORLD_MAP_BASE_OFFSET
            + self._rom.little_endian(self.world.level_offset_list_offset_address)
            + OFFSET_SIZE * self.index
        )
        self.enemy_offset_address = (
            WORLD_MAP_BASE_OFFSET
            + self._rom.little_endian(self.world.enemy_offset_list_offset_address)
            + OFFSET_SIZE * self.index
        )

    @property
    def level_address(self):
        return BASE_OFFSET + self.object_set_offset + self.level_offset

    @level_address.setter
    def level_address(self, value):
        self.level_offset = (value - BASE_OFFSET - self.object_set_offset) & 0xFFFF

    @property
    def enemy_address(self):
        return BASE_OFFSET + self.enemy_offset

    @enemy_address.setter
    def enemy_address(self, value):
        self.enemy_offset = value - BASE_OFFSET

    @property
    def object_set_offset(self):
        """
        Returns the offset, based on the level pointers object set, that needs to be added to its level header offset in
        order to get the actual memory location of the level in the ROM.
        """
        return self._rom.int(OFFSET_BY_OBJECT_SET_A000 + self.object_set) * PRG_BANK_SIZE - 0xA000

    def read_values(self):
        self.screen, self.x = self._rom.nibbles(self.screen_address)

        self.y, self.object_set = self._rom.nibbles(self.y_address)

        self.level_offset = self._rom.little_endian(self.level_offset_address)
        self.enemy_offset = self._rom.little_endian(self.enemy_offset_address)

    def clear(self):
        self.screen = 0
        self.x = 0
        self.y = FIRST_VALID_ROW

        self.object_set = 1
        self.level_offset = 0x0
        self.enemy_offset = 0x0

    def write_back(self, rom: Optional[Rom] = None):
        if rom is None:
            rom = self._rom

        rom.write_nibbles(self.screen_address, self.screen, self.x)
        rom.write_nibbles(self.y_address, self.y, self.object_set)

        rom.write_little_endian(self.level_offset_address, self.level_offset)
        rom.write_little_endian(self.enemy_offset_address, self.enemy_offset)

    def __eq__(self, other):
        if not isinstance(other, LevelPointerData):
            return NotImplemented

        if self.pos != other.pos:
            return False

        if self.level_offset != other.level_offset:
            return False

        if self.enemy_offset != other.enemy_offset:
            return False

        if self.object_set != other.object_set:
            return False

        if self.screen_address != other.screen_address:
            return False

        if self.y_address != other.y_address:
            return False

        if self.level_offset_address != other.level_offset_address:
            return False

        if self.enemy_offset_address != other.enemy_offset_address:
            return False

        return True

    def __lt__(self, other):
        self_result = self.screen * WORLD_MAP_SCREEN_SIZE + self.y * WORLD_MAP_SCREEN_WIDTH + self.x
        other_result = other.screen * WORLD_MAP_SCREEN_SIZE + other.y * WORLD_MAP_SCREEN_WIDTH + other.x

        return self_result < other_result
