import sys

from PySide6.QtWidgets import QApplication

from autonanami_gui.main_window import MainWindow


def center_window(window):
    screen = window.screen() or QApplication.primaryScreen()
    frame = window.frameGeometry()
    frame.moveCenter(screen.availableGeometry().center())
    window.move(frame.topLeft())


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = window.controller
    app.aboutToQuit.connect(controller.shutdown)

    if controller.carried_old_settings_over:
        controller.log_message.emit("Carried your old settings over.", "info")
    controller.log_message.emit("AutoNanami is ready when you are.", "success")
    window.home_page.refresh_pids()

    if controller.get_state()["silentLaunch"]:
        controller.log_message.emit("Starting quietly — press your GUI key to open the window.", "info")
    else:
        window.show()
        center_window(window)

    code = app.exec()
    controller.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
