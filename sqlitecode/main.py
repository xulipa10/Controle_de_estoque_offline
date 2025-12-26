import sys
from PySide6.QtWidgets import QApplication
from main_window import MenuPrincipal

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MenuPrincipal()
    window.show()
    sys.exit(app.exec())
