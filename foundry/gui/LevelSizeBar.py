from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from foundry.game.File import ROM
from foundry.game.level.LevelRef import LevelRef


class LevelSizeBar(QWidget):
    def __init__(self, parent, level: LevelRef):
        super(LevelSizeBar, self).__init__(parent)

        self.level_ref = level

        self.level_ref.data_changed.connect(self.update)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.setWhatsThis(
            "<b>Level Size Bar</b><br/>"
            "The objects inside a level, like platforms and item blocks, are stored as bytes in the ROM. "
            "Since levels are stored one after another, saving a level with more objects, than it originally "
            "had, would overwrite another level and probably cause the game to crash, if you would enter it, "
            "while playing.<br/>"
            "This bar shows, how much of the available space for level objects is currently taken up. It will turn "
            "red, when too many level objects have been placed (or if the level objects would result in more bytes, "
            "than the level originally had)."
        )

        self.size_bar = SizeBar(self.level_ref)
        self.size_bar.value_color = self.value_color

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.size_bar)
        layout.addWidget(self.info_label)

    def update(self):
        original_value_string = "∞" if self.max_value == float("INF") else str(self.max_value)
        self.info_label.setText(f"{self.value_description}: {self.current_value}/{original_value_string} Bytes")

        self.size_bar.current_value = self.current_value
        self.size_bar.original_value = self.max_value

        return super(LevelSizeBar, self).update()

    @property
    def value_color(self):
        return QColor.fromRgb(0x58D858)

    @property
    def value_description(self):
        return "Objects"

    @property
    def max_value(self) -> float:
        level_size = self.level_ref.object_size_on_disk

        if not self.level_ref.level.attached_to_rom and level_size == 0:
            level_size = float("INF")

        elif ROM().additional_data.managed_level_positions:
            free_space_in_bank = ROM().additional_data.free_space_for_object_set(self.level_ref.level.object_set_number)
            level_size += free_space_in_bank

        return level_size

    @property
    def current_value(self) -> float:
        return self.level_ref.current_object_size()


class SizeBar(QWidget):
    DEFAULT_SIZE = QSize(10, 10)

    def __init__(self, level_ref: LevelRef):
        super(SizeBar, self).__init__()

        self.level = level_ref

        self.original_value: float = 1.0
        self.current_value: float = 1.0
        self.value_color = QColor.black

    def sizeHint(self) -> QSize:
        size = super(SizeBar, self).sizeHint()

        size.setHeight(self.DEFAULT_SIZE.height())

        return size

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        painter.fillRect(event.rect(), self.palette().base())

        if self.level.level is None:
            return

        total_length = max(self.current_value, self.original_value, 1)

        pixels_per_byte = event.rect().width() / total_length

        bar = QRect(event.rect())
        bar.setWidth(int(pixels_per_byte * self.current_value))

        if self.current_value > self.original_value:
            painter.fillRect(bar, Qt.red)
        else:
            painter.fillRect(bar, self.value_color)
