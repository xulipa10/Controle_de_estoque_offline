import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from main_window import MenuPrincipal

if __name__ == "__main__":


    app = QApplication(sys.argv)

    # ÍCONE GLOBAL DA APLICAÇÃO
    app.setWindowIcon(QIcon("app.ico"))
    window = MenuPrincipal()
    window.show()
    sys.exit(app.exec())
