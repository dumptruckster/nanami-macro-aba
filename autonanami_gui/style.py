STYLESHEET = """
QWidget {
    font-family: 'Segoe UI';
    color: #f2f2f3;
    background: transparent;
}

#Root {
    background: #111113;
    border-radius: 10px;
    border: 1px solid #232326;
}

#TopBar {
    border-bottom: 1px solid #232326;
}

#Brand {
    font-size: 15px;
    font-weight: 700;
    color: #f2f2f3;
}

QPushButton#WinButton {
    background: transparent;
    border: none;
    color: #68686d;
    border-radius: 5px;
    font-size: 13px;
}
QPushButton#WinButton:hover {
    background: #1c1c1f;
    color: #f2f2f3;
}

QPushButton#TabButton {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #68686d;
    font-size: 13px;
    font-weight: 600;
    padding: 0 0 12px 0;
}
QPushButton#TabButton:checked {
    color: #f2f2f3;
    border-bottom: 2px solid #f2f2f3;
}

#Sidebar {
    border-right: 1px solid #232326;
}

QPushButton#NavItem {
    text-align: left;
    background: transparent;
    border: none;
    border-radius: 5px;
    color: #9a9a9f;
    font-size: 13px;
    padding: 9px 10px;
}
QPushButton#NavItem:checked {
    background: #1c1c1f;
    color: #f2f2f3;
    font-weight: 600;
}
QPushButton#NavItem:hover:!checked {
    color: #f2f2f3;
}

#Panel {
    background: #141416;
    border: 1px solid #232326;
    border-radius: 8px;
}

QLabel#PanelTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f2f2f3;
}

QLabel#FieldLabel {
    font-size: 11px;
    color: #9a9a9f;
}

QComboBox#Dropdown {
    background: #0d0d0f;
    border: 1px solid #232326;
    border-radius: 5px;
    padding: 8px 12px;
    font-size: 12.5px;
    color: #f2f2f3;
}
QComboBox#Dropdown::drop-down {
    border: none;
    width: 24px;
}
QComboBox#Dropdown QAbstractItemView {
    background: #0d0d0f;
    border: 1px solid #232326;
    color: #f2f2f3;
    selection-background-color: #1c1c1f;
}

QLabel#StLabel {
    font-size: 11px;
    color: #68686d;
}
QLabel#StVal {
    font-size: 12px;
    font-weight: 600;
    color: #d8d8da;
    font-family: 'Courier New';
}

QPushButton#PrimaryButton {
    background: #f2f2f3;
    border: none;
    border-radius: 6px;
    color: #111111;
    font-size: 12px;
    font-weight: 700;
    padding: 11px;
}
QPushButton#PrimaryButton:disabled {
    background: #1c1c1f;
    color: #68686d;
}
QPushButton#PrimaryButton:hover:!disabled {
    background: #e2e2e3;
}

QPushButton#DangerButton {
    background: #e2504f;
    border: none;
    border-radius: 6px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 11px;
}

QPushButton#SecondaryButton {
    background: transparent;
    border: 1px solid #232326;
    border-radius: 6px;
    color: #e8e8ea;
    font-size: 12px;
    font-weight: 600;
    padding: 11px;
}
QPushButton#SecondaryButton:disabled {
    color: #68686d;
}
QPushButton#SecondaryButton:hover:!disabled {
    background: #1c1c1f;
}

QPushButton#GhostButton {
    background: transparent;
    border: 1px solid #232326;
    border-radius: 6px;
    color: #9a9a9f;
    font-size: 11.5px;
    font-weight: 600;
    padding: 10px;
}
QPushButton#GhostButton:hover {
    background: #1c1c1f;
}

QSlider#QuietSlider::groove:horizontal {
    height: 6px;
    background: #0d0d0f;
    border: 1px solid #232326;
    border-radius: 3px;
}
QSlider#QuietSlider::sub-page:horizontal {
    height: 6px;
    background: #f2f2f3;
    border-radius: 3px;
}
QSlider#QuietSlider::handle:horizontal {
    background: #f2f2f3;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #111113;
}
QSlider#QuietSlider:hover::handle:horizontal {
    background: #e2e2e3;
    border: 2px solid #111113;
}
QSlider#QuietSlider:disabled::groove:horizontal {
    border: 1px solid #1c1c1f;
}
QSlider#QuietSlider:disabled::sub-page:horizontal {
    background: #1c1c1f;
}
QSlider#QuietSlider:disabled::handle:horizontal {
    background: #68686d;
    border: 2px solid #111113;
}

QPushButton#KeybindBox {
    background: #0d0d0f;
    border: 1px solid #232326;
    border-radius: 5px;
    color: #ffffff;
    font-family: 'Courier New';
    font-size: 12px;
    font-weight: 700;
    min-width: 44px;
    min-height: 30px;
    padding: 0 10px;
}
QPushButton#KeybindBox[listening="true"] {
    border: 1px solid #f2f2f3;
}

QLabel#KbLabel {
    font-size: 12px;
    color: #e8e8ea;
    font-weight: 600;
}
QLabel#KbSub {
    font-size: 10.5px;
    color: #68686d;
}

QTextEdit#LogDisplay {
    background: #0a0a0b;
    border: none;
    font-family: 'Courier New';
    font-size: 11px;
}
"""
