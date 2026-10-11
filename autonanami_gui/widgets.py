from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, Property
from PySide6.QtGui import QPainter, QColor, QKeySequence
from PySide6.QtWidgets import (
    QAbstractButton, QPushButton, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QSlider,
)



class ToggleSwitch(QAbstractButton):
    toggledState = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(34, 19)
        self.setCursor(Qt.PointingHandCursor)
        self._offset = 3.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(17.0 if checked else 3.0)
        self._anim.start()
        self.toggledState.emit(checked)

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def set_checked(self, checked):
        self.blockSignals(True)
        self.setChecked(checked)
        self._offset = 17.0 if checked else 3.0
        self.update()
        self.blockSignals(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track_color = QColor("#e8e8ea") if self.isChecked() else QColor("#232326")
        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 9.5, 9.5)
        dot_color = QColor("#111111") if self.isChecked() else QColor("#8a8a8f")
        painter.setBrush(dot_color)
        painter.drawEllipse(QRectF(self._offset, 2.5, 14, 14))


class KeybindBox(QPushButton):
    keyChanged = Signal(str)

    def __init__(self, initial="1", parent=None):
        super().__init__(initial, parent)
        self.setObjectName("KeybindBox")
        self._listening = False
        self.clicked.connect(self.start_listening)

    def start_listening(self):
        if self._listening:
            return
        self._listening = True
        self.setProperty("listening", "true")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText("...")
        self.grabKeyboard()

    def stop_listening(self):
        self._listening = False
        self.releaseKeyboard()
        self.setProperty("listening", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def keyPressEvent(self, event):
        if not self._listening:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key_Escape:
            self.stop_listening()
            self.setText(self._last_key())
            return
        key_text = QKeySequence(event.key()).toString()
        if not key_text:
            key_text = event.text().upper() or "?"
        self._current_key = key_text
        self.setText(key_text)
        self.stop_listening()
        self.keyChanged.emit(key_text)

    def _last_key(self):
        return getattr(self, "_current_key", self.text())

    def set_key(self, key_text):
        self._current_key = key_text
        self.setText(key_text)


class SliderRow(QWidget):
    valueChanged = Signal(int)

    def __init__(self, label, value=100, minimum=0, maximum=100, suffix="%", parent=None):
        super().__init__(parent)
        self._suffix = suffix
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(7)

        head = QHBoxLayout()
        self.label = QLabel(label)
        self.label.setStyleSheet(f"font-size:12px;color:#c8c8cc;")
        self.value_label = QLabel(f"{value}{suffix}")
        self.value_label.setStyleSheet(
            f"color:#fff;font-weight:600;font-family:'Courier New';font-size:11.5px;"
        )
        head.addWidget(self.label)
        head.addStretch()
        head.addWidget(self.value_label)
        outer.addLayout(head)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("QuietSlider")
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self._on_value_changed)
        outer.addWidget(self.slider)

    def _on_value_changed(self, value):
        self.value_label.setText(f"{value}{self._suffix}")
        self.valueChanged.emit(value)

    def set_value(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.value_label.setText(f"{value}{self._suffix}")

    def set_enabled_state(self, enabled):
        self.slider.setEnabled(enabled)


class StatusRow(QWidget):
    def __init__(self, label, value="N/A", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 9, 0, 9)
        self.label = QLabel(label)
        self.label.setObjectName("StLabel")
        layout.addWidget(self.label)
        layout.addStretch()

        self.dot = QLabel()
        self.dot.setFixedSize(7, 7)
        self._set_dot_off()
        layout.addWidget(self.dot)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("StVal")
        layout.addWidget(self.value_label)

    def _set_dot_off(self):
        self.dot.setStyleSheet("background:#3f3f43;border-radius:3px;")

    def _set_dot_on(self):
        self.dot.setStyleSheet("background:#e8e8ea;border-radius:3px;")

    def set_state(self, active, text):
        self.value_label.setText(text)
        if active:
            self._set_dot_on()
        else:
            self._set_dot_off()

    def set_value_only(self, text):
        self.dot.hide()
        self.value_label.setText(text)


class ToggleRow(QWidget):
    toggledState = Signal(bool)

    def __init__(self, label, checked=False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 11, 0, 11)
        self.label = QLabel(label)
        self.label.setStyleSheet("font-size:12px;color:#e8e8ea;font-weight:500;")
        layout.addWidget(self.label)
        layout.addStretch()
        self.toggle = ToggleSwitch(checked=checked)
        self.toggle.toggledState.connect(self.toggledState.emit)
        layout.addWidget(self.toggle)

    def set_checked(self, checked):
        self.toggle.set_checked(checked)
