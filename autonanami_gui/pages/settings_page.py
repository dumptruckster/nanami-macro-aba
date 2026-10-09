from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QComboBox,
)

from autonanami_gui.widgets import KeybindBox, ToggleRow, ToggleSwitch, SliderRow


class SettingsPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        root.addWidget(self.build_the_keybind_panel(), 1)
        root.addWidget(self.build_the_success_rate_panel(), 1)

    def make_a_keybind_row(self, label, sub, initial, on_change):
        row = QHBoxLayout()
        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        label_widget = QLabel(label)
        label_widget.setObjectName("KbLabel")
        sub_widget = QLabel(sub)
        sub_widget.setObjectName("KbSub")
        text_column.addWidget(label_widget)
        text_column.addWidget(sub_widget)
        row.addLayout(text_column)
        row.addStretch()
        box = KeybindBox(initial)
        box.keyChanged.connect(on_change)
        row.addWidget(box)
        return row, box

    def build_the_keybind_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        title = QLabel("Keybinds and toggles")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        layout.addSpacing(10)

        macro_row, self.macro_keybind = self.make_a_keybind_row(
            "Macro keybind", "Click, then press a key",
            "F1", self.macro_key_was_chosen,
        )
        layout.addLayout(macro_row)

        gui_row, self.gui_keybind = self.make_a_keybind_row(
            "GUI toggle", "Show or hide this window",
            "Insert", self.gui_key_was_chosen,
        )
        layout.addLayout(gui_row)
        layout.addSpacing(8)

        self.show_keybind_toggle = ToggleRow("Show keybind on overlay", checked=True)
        self.show_keybind_toggle.toggledState.connect(self.controller.set_show_keybind)
        layout.addWidget(self.show_keybind_toggle)

        self.auto_attach_toggle = ToggleRow("Auto attach on launch")
        self.auto_attach_toggle.toggledState.connect(self.controller.set_auto_attach)
        layout.addWidget(self.auto_attach_toggle)

        self.show_overlay_toggle = ToggleRow("Show overlay")
        self.show_overlay_toggle.toggledState.connect(self.controller.set_show_overlay)
        layout.addWidget(self.show_overlay_toggle)

        self.silent_launch_toggle = ToggleRow("Silent launch")
        self.silent_launch_toggle.toggledState.connect(self.controller.set_silent_launch)
        layout.addWidget(self.silent_launch_toggle)
        layout.addSpacing(4)

        layout.addLayout(self.build_the_hit_sound_row())
        layout.addLayout(self.build_the_sound_row())
        layout.addStretch()
        return panel

    def build_the_hit_sound_row(self):
        row = QHBoxLayout()
        label = QLabel("Hit sound")
        label.setStyleSheet("font-size:12px;color:#e8e8ea;font-weight:500;")
        row.addWidget(label)
        row.addStretch()

        self.sound_trigger_combo = QComboBox()
        self.sound_trigger_combo.setObjectName("Dropdown")
        self.sound_trigger_combo.setFixedWidth(136)
        self.sound_trigger_combo.addItem("On hit", "hit")
        self.sound_trigger_combo.addItem("On key press", "keypress")
        self.sound_trigger_combo.currentIndexChanged.connect(self.sound_trigger_was_changed)
        row.addWidget(self.sound_trigger_combo)

        self.hit_sound_toggle = ToggleSwitch(checked=True)
        self.hit_sound_toggle.toggledState.connect(self.controller.set_toggle_sound)
        row.addWidget(self.hit_sound_toggle)
        return row

    def build_the_sound_row(self):
        row = QHBoxLayout()
        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        label = QLabel("Sound file")
        label.setObjectName("KbLabel")
        self.sound_file_label = QLabel("-")
        self.sound_file_label.setObjectName("KbSub")
        text_column.addWidget(label)
        text_column.addWidget(self.sound_file_label)
        row.addLayout(text_column)
        row.addStretch()

        play_button = QPushButton("Play")
        play_button.setObjectName("GhostButton")
        play_button.clicked.connect(self.controller.preview_hit_sound)
        row.addWidget(play_button)

        choose_button = QPushButton("Choose...")
        choose_button.setObjectName("GhostButton")
        choose_button.clicked.connect(self.pick_a_sound_file)
        row.addWidget(choose_button)

        folder_button = QPushButton("Folder")
        folder_button.setObjectName("GhostButton")
        folder_button.clicked.connect(self.controller.open_sounds_folder)
        row.addWidget(folder_button)
        return row

    def build_the_success_rate_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.success_toggle = ToggleRow("Variable success rate")
        self.success_toggle.toggledState.connect(self.success_rate_was_toggled)
        layout.addWidget(self.success_toggle)
        layout.addSpacing(8)

        self.success_slider = SliderRow("Success rate", value=100)
        self.success_slider.set_enabled_state(False)
        self.success_slider.valueChanged.connect(self.controller.set_success_rate)
        layout.addWidget(self.success_slider)

        layout.addStretch()
        return panel

    def pick_a_sound_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a hit sound",
            str(Path.home()),
            "Audio files (*.mp3 *.wav *.ogg *.m4a *.flac *.aac);;All files (*.*)",
        )
        if path:
            self.controller.set_hit_sound(path)

    def sound_trigger_was_changed(self, index):
        choice = self.sound_trigger_combo.itemData(index)
        if choice:
            self.controller.set_hit_sound_trigger(choice)

    def macro_key_was_chosen(self, key):
        self.controller.set_keybind(key)

    def gui_key_was_chosen(self, key):
        self.controller.set_gui_keybind(key)

    def success_rate_was_toggled(self, checked):
        self.success_slider.set_enabled_state(checked)
        self.controller.set_success_rate_enabled(checked)

    def refresh_from_state(self, state):
        self.macro_keybind.set_key(state["keybind"])
        self.gui_keybind.set_key(state["guiKeybind"])
        self.show_keybind_toggle.set_checked(state["showKeybind"])
        self.auto_attach_toggle.set_checked(state["autoAttach"])
        self.show_overlay_toggle.set_checked(state["showOverlay"])
        self.silent_launch_toggle.set_checked(state["silentLaunch"])
        self.hit_sound_toggle.set_checked(state["toggleSound"])
        self.success_toggle.set_checked(state["successRateEnabled"])
        self.success_slider.set_enabled_state(state["successRateEnabled"])
        self.success_slider.set_value(state["successRate"])
        self.sound_file_label.setText(state.get("hitSound") or "-")

        wanted = state.get("hitSoundTrigger", "hit")
        if self.sound_trigger_combo.currentData() != wanted:
            wanted_index = self.sound_trigger_combo.findData(wanted)
            if wanted_index >= 0:
                self.sound_trigger_combo.blockSignals(True)
                self.sound_trigger_combo.setCurrentIndex(wanted_index)
                self.sound_trigger_combo.blockSignals(False)
