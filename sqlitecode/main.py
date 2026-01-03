import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from main_window import MenuPrincipal

if __name__ == "__main__":
    # ÍCONE GLOBAL DA APLICAÇÃO

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("app.ico"))
    window = MenuPrincipal()
    window.show()
    sys.exit(app.exec())
