from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame


class OverlayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._running = False
        self._keybind = None
        self._show_keybind = True

        container = QFrame(self)
        container.setObjectName("OverlayCard")
        container.setStyleSheet(
            "#OverlayCard {"
            "background: #161616;"
            "border: 1px solid #2a2a2a;"
            "border-radius: 6px;"
            "}"
        )
        self.container = container

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 14, 8)
        layout.setSpacing(10)

        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        layout.addWidget(self.dot)

        self.label = QLabel("Macro off")
        self.label.setStyleSheet(
            "color:#ffffff;font-size:13px;font-weight:700;letter-spacing:0.5px;"
        )
        layout.addWidget(self.label)

        self.divider = QFrame()
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet("background: rgba(255,255,255,0.15);")
        layout.addWidget(self.divider)

        self.keybind_label = QLabel("-")
        self.keybind_label.setStyleSheet(
            "color:#00d4ff;background:rgba(0,212,255,0.12);"
            "border-radius:6px;padding:3px 8px;font-family:'Courier New';"
            "font-size:11px;font-weight:700;"
        )
        layout.addWidget(self.keybind_label)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        self._render()

    def set_macro_running(self, running):
        self._running = bool(running)
        self._render()

    def set_keybind(self, key):
        self._keybind = key
        self._render()

    def set_show_keybind(self, show):
        self._show_keybind = bool(show)
        self._render()

    def apply_state(self, state):
        self.set_macro_running(state.get("running", False))
        self.set_keybind(state.get("keybind"))
        self.set_show_keybind(state.get("showKeybind", True))

    def _render(self):
        color = "#00cc44" if self._running else "#ff4444"
        self.dot.setStyleSheet(f"background:{color};border-radius:5px;")
        self.label.setText("Macro on" if self._running else "Macro off")

        show = self._show_keybind and self._keybind
        self.divider.setVisible(bool(show))
        self.keybind_label.setVisible(bool(show))
        if self._keybind:
            self.keybind_label.setText(self._keybind)

        self.adjustSize()