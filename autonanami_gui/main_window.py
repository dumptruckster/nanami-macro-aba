from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QButtonGroup, QApplication,
)

from autonanami_gui.controller import AutomationController
from autonanami_gui.style import STYLESHEET
from autonanami_gui.overlay import OverlayWidget
from autonanami_gui.pages.home_page import HomePage
from autonanami_gui.pages.settings_page import SettingsPage


SIDEBAR_ITEMS = [
    ("Connection", 0),
    ("Settings", 1),
]

TOPBAR_TABS = ["Home", "Settings"]


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(920, 560)

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(STYLESHEET)

        self.controller = AutomationController(self)
        self.overlay = OverlayWidget()
        self.controller.state_changed.connect(self.overlay.apply_state)
        self.controller.state_changed.connect(self.when_something_changes)
        self.controller.gui_toggle_requested.connect(self.toggle_window_visibility)

        self.overlay_timer = QTimer(self)
        self.overlay_timer.setInterval(500)
        self.overlay_timer.timeout.connect(self.move_the_overlay_into_place)
        self.drag_offset = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        root = QFrame()
        root.setObjectName("Root")
        outer.addWidget(root)
        self.root_frame = root

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.build_the_top_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.build_the_sidebar())

        self.pages = QStackedWidget()
        self.home_page = HomePage(self.controller)
        self.settings_page = SettingsPage(self.controller)
        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.settings_page)
        body.addWidget(self.pages, 1)

        root_layout.addLayout(body, 1)

    def build_the_top_bar(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.mousePressEvent = self.start_dragging
        bar.mouseMoveEvent = self.drag_by

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 18, 16, 14)
        layout.setSpacing(20)

        brand = QLabel("AutoNanami")
        brand.setObjectName("Brand")
        layout.addWidget(brand)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(22)
        for index, name in enumerate(TOPBAR_TABS):
            button = QPushButton(name)
            button.setObjectName("TabButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked, i=index: self.show_page(i))
            self.tab_group.addButton(button, index)
            tabs_row.addWidget(button)
        layout.addLayout(tabs_row)
        layout.addStretch()

        minimize_button = QPushButton("-")
        minimize_button.setObjectName("WinButton")
        minimize_button.setFixedSize(28, 26)
        minimize_button.clicked.connect(self.showMinimized)
        layout.addWidget(minimize_button)

        close_button = QPushButton("x")
        close_button.setObjectName("WinButton")
        close_button.setFixedSize(28, 26)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        return bar

    def build_the_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(150)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 18, 12, 18)
        layout.setSpacing(2)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (name, page_index) in enumerate(SIDEBAR_ITEMS):
            button = QPushButton(name)
            button.setObjectName("NavItem")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked, page=page_index: self.sidebar_item_clicked(page))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)

        layout.addStretch()
        return sidebar

    def sidebar_item_clicked(self, page_index):
        self.show_page(page_index, keep_sidebar_selection=True)

    def show_page(self, page_index, keep_sidebar_selection=False):
        self.pages.setCurrentIndex(page_index)
        self.tab_group.button(page_index).setChecked(True)
        if keep_sidebar_selection:
            return
        for nav_index, (_name, target_page) in enumerate(SIDEBAR_ITEMS):
            if target_page == page_index:
                self.nav_group.button(nav_index).setChecked(True)
                break

    def start_dragging(self, event):
        self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def drag_by(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)

    def when_something_changes(self, state):
        self.home_page.refresh_from_state(state)
        self.settings_page.refresh_from_state(state)

        should_show_overlay = state["attached"] and state["showOverlay"]
        if should_show_overlay and not self.overlay.isVisible():
            self.overlay.move(self.where_the_overlay_goes() or QPoint(16, 90))
            self.overlay.show()
            self.overlay_timer.start()
        elif not should_show_overlay:
            self.overlay.hide()
            self.overlay_timer.stop()

    def toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def move_the_overlay_into_place(self):
        if not self.overlay.isVisible():
            return
        spot = self.where_the_overlay_goes()
        if spot is not None:
            self.overlay.move(spot)

    def where_the_overlay_goes(self):
        try:
            return self.controller.overlay_position()
        except Exception:
            return None

    def closeEvent(self, event):
        self.controller.shutdown()
        super().closeEvent(event)