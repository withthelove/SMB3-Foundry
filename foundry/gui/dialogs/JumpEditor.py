from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)

from foundry.game.gfx.objects import Jump
from foundry.gui.dialogs.CustomDialog import CustomDialog
from foundry.gui.Spinner import Spinner

JUMP_ACTIONS = [
    "Downward Pipe 1",
    "Upward Pipe",
    "Downward Pipe 2",
    "Right Pipe",
    "Left Pipe",
    "?",
    "?",
    "Jump on Noteblock",
    "Door",
    "?",
    "?",
    "?",
    "?",
    "?",
    "?",
    "?",
]

VERT_POSITIONS = [
    "00",
    "05",
    "08",
    "12",
    "16",
    "20",
    "23",
    "24",
    "00 (Vertical)",
    "05 (Vertical)",
    "08 (Vertical)",
    "12 (Vertical)",
    "16 (Vertical)",
    "20 (Vertical)",
    "23 (Vertical)",
    "24 (Vertical)",
]

MAX_SCREEN_INDEX = 0x0F
MAX_HORIZ_POSITION = 0xFF


class JumpEditor(CustomDialog):
    def __init__(self, parent: Optional[QWidget], jump: Jump):
        super(JumpEditor, self).__init__(parent, "Jump Editor")

        self.jump = jump

        self.screen_spinner = Spinner(parent=self, maximum=MAX_SCREEN_INDEX, base=10)

        position_layout = QFormLayout()
        position_layout.addRow("Jump on screen:", self.screen_spinner)

        level_group_box = QGroupBox("Level position")
        level_group_box.setLayout(position_layout)

        self.exit_action = QComboBox(self)
        self.exit_action.addItems(JUMP_ACTIONS)

        self.exit_horizontal = Spinner(parent=self, maximum=MAX_HORIZ_POSITION, base=10)

        self.exit_vertical = QComboBox(self)
        self.exit_vertical.addItems(VERT_POSITIONS)

        exit_layout = QFormLayout()
        exit_layout.addRow("Exit action:", self.exit_action)
        exit_layout.addRow("Exit position x:", self.exit_horizontal)
        exit_layout.addRow("Exit position y:", self.exit_vertical)

        exit_group_box = QGroupBox("Exit options")
        exit_group_box.setLayout(exit_layout)

        button_box = QDialogButtonBox()
        self.ok_button = button_box.addButton(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.on_ok)
        button_box.addButton(QDialogButtonBox.Cancel).clicked.connect(self.close)

        main_layout = QVBoxLayout()
        main_layout.addWidget(level_group_box)
        main_layout.addWidget(exit_group_box)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

        self._set_widget_values()

    def _set_widget_values(self):
        self.screen_spinner.setValue(self.jump.screen_index)

        self.exit_action.setCurrentIndex(self.jump.exit_action)
        self.exit_horizontal.setValue(self.jump.exit_horizontal)
        self.exit_vertical.setCurrentIndex(self.jump.exit_vertical)

    @staticmethod
    def edit_jump(parent: Optional[QWidget], jump: Jump):
        jump_editor = JumpEditor(parent, jump)

        jump_editor.exec()

        return jump_editor.jump

    def on_ok(self):
        self.jump = Jump.from_properties(
            self.screen_spinner.value(),
            self.exit_action.currentIndex(),
            self.exit_horizontal.value(),
            self.exit_vertical.currentIndex(),
        )

        self.close()
