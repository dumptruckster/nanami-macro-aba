from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QFrame,
)

from autonanami_gui.widgets import StatusRow


class HomePage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._log_count = 0

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        root.addWidget(self._build_connection_panel(), 1)
        root.addWidget(self._build_log_panel(), 1)

        self.controller.log_message.connect(self.append_log)

    def _build_connection_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(4)

        title = QLabel("Connection")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        layout.addSpacing(12)

        field_label = QLabel("Target process")
        field_label.setObjectName("FieldLabel")
        layout.addWidget(field_label)

        row = QHBoxLayout()
        self.pid_combo = QComboBox()
        self.pid_combo.setObjectName("Dropdown")
        self.pid_combo.addItem("N/A")
        row.addWidget(self.pid_combo, 1)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("GhostButton")
        self.refresh_button.setFixedWidth(72)
        self.refresh_button.clicked.connect(self.refresh_pids)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)
        layout.addSpacing(14)

        self.process_row = StatusRow("Process", "Detached")
        self.macro_row = StatusRow("Macro", "Idle")
        self.module_row = StatusRow("Module", "N/A")
        self.module_row.set_value_only("N/A")
        layout.addWidget(self.process_row)
        layout.addWidget(self.macro_row)
        layout.addWidget(self.module_row)
        layout.addSpacing(20)

        self.attach_button = QPushButton("Attach to Roblox")
        self.attach_button.setObjectName("PrimaryButton")
        self.attach_button.clicked.connect(self.toggle_attach)
        layout.addWidget(self.attach_button)

        self.macro_button = QPushButton("Start macro")
        self.macro_button.setObjectName("SecondaryButton")
        self.macro_button.setEnabled(False)
        self.macro_button.clicked.connect(self.toggle_macro)
        layout.addWidget(self.macro_button)

        layout.addStretch()
        return panel

    def _build_log_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(18, 16, 18, 12)
        title = QLabel("Activity log")
        title.setObjectName("PanelTitle")
        header.addWidget(title)
        header.addStretch()
        self.log_count_label = QLabel("0 entries")
        self.log_count_label.setStyleSheet("font-size:11px;color:#68686d;")
        header.addWidget(self.log_count_label)
        layout.addLayout(header)

        self.log_display = QTextEdit()
        self.log_display.setObjectName("LogDisplay")
        self.log_display.setReadOnly(True)
        self.log_display.document().setMaximumBlockCount(500)
        layout.addWidget(self.log_display, 1)

        clear_row = QHBoxLayout()
        clear_row.setContentsMargins(18, 10, 18, 16)
        self.clear_button = QPushButton("Clear logs")
        self.clear_button.setObjectName("GhostButton")
        self.clear_button.clicked.connect(self.clear_logs)
        clear_row.addWidget(self.clear_button)
        layout.addLayout(clear_row)

        return panel

    def refresh_pids(self):
        pids = self.controller.list_pids()
        self.pid_combo.clear()
        if not pids:
            self.pid_combo.addItem("N/A")
            self.append_log("No Roblox process found — launch the game and hit Refresh.", "warning")
            return
        for entry in pids:
            self.pid_combo.addItem(f"{entry['name']} ({entry['pid']})", entry["pid"])
        self.append_log(f"Found {len(pids)} Roblox process{'es' if len(pids) > 1 else ''}.", "info")

    def toggle_attach(self):
        state = self.controller.get_state()
        if state["attached"]:
            self.controller.detach()
        else:
            self.controller.attach_to_pid(self.pid_combo.currentData())

    def toggle_macro(self):
        state = self.controller.get_state()
        if state["running"]:
            self.controller.stop_macro()
        else:
            self.controller.start_macro()

    def clear_logs(self):
        self.log_display.clear()
        self._log_count = 0
        self.log_count_label.setText("0 entries")

    def append_log(self, message, level="info"):
        colors = {
            "info": "#888888",
            "success": "#00cc44",
            "warning": "#ffaa00",
            "error": "#ff4444",
        }
        color = colors.get(level, "#888888")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(
            f'<span style="color:#555">[{timestamp}]</span> '
            f'<span style="color:{color}">{message}</span>'
        )
        self._log_count += 1
        self.log_count_label.setText(f"{self._log_count} entries")

    def refresh_from_state(self, state):
        self.process_row.set_state(state["attached"], "Attached" if state["attached"] else "Detached")
        self.macro_row.set_state(state["running"], "Running" if state["running"] else "Idle")
        self.module_row.value_label.setText(state["moduleBase"])

        self.attach_button.setText("Detach" if state["attached"] else "Attach to Roblox")
        self.attach_button.setObjectName("DangerButton" if state["attached"] else "PrimaryButton")
        self.attach_button.style().unpolish(self.attach_button)
        self.attach_button.style().polish(self.attach_button)

        self.macro_button.setEnabled(state["attached"])
        self.macro_button.setText("Stop macro" if state["running"] else "Start macro")
