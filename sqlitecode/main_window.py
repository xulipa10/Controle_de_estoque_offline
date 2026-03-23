from relatorio_financeiro import RelatorioFinanceiro

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout
)

from pdv import PDV
from controle_de_estoque import EstoqueApp
from operador_manager import OperadorManager  # Importando o Gerenciador de Operadores
from login import TelaLogin  # Importando a tela de login

class MenuPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema Comercial")
        self.resize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(20)

        btn_pdv = QPushButton("🧾 PDV")
        btn_pdv.setMinimumHeight(80)

        btn_estoque = QPushButton("📦 Estoque")
        btn_estoque.setMinimumHeight(80)

        btn_relatorio = QPushButton("📊 Relatório Financeiro")
        btn_relatorio.setMinimumHeight(80)

        btn_operadores = QPushButton("👨‍💼 Gerenciar Operadores")
        btn_operadores.setMinimumHeight(80)  # Botão para gerenciar operadores

        layout.addStretch()
        layout.addWidget(btn_pdv)
        layout.addWidget(btn_estoque)
        layout.addWidget(btn_relatorio)
        layout.addWidget(btn_operadores)  # Adicionando o botão para o gerenciador
        layout.addStretch()

        # Conectando os botões com as funções correspondentes
        btn_pdv.clicked.connect(self.abrir_login)
        btn_estoque.clicked.connect(self.abrir_estoque)
        btn_relatorio.clicked.connect(self.abrir_relatorio)
        btn_operadores.clicked.connect(self.abrir_operadores)  # Conectando o botão para abrir o gerenciador

        self.pdv_window = None
        self.estoque_window = None
        self.relatorio_window = None
        self.operadores_window = None

    def abrir_login(self):
        # Abrir a tela de login
        self.login_window = TelaLogin()
        if self.login_window.exec():  # Se o login for bem-sucedido
            operador_nome = self.login_window.nome_usuario  # Pegando o nome do operador logado
            self.abrir_pdv(operador_nome)  # Passando o nome do operador para o PDV

    def abrir_pdv(self, nome_operador):
        if self.pdv_window is None:
            self.pdv_window = PDV(nome_operador)  # Passando o nome do operador para o PDV
            self.pdv_window.destroyed.connect(
                lambda: setattr(self, "pdv_window", None)
            )

        self.pdv_window.show()

    def abrir_estoque(self):
        if self.estoque_window is None:
            self.estoque_window = EstoqueApp()
        self.estoque_window.show()
        self.estoque_window.raise_()
        self.estoque_window.activateWindow()

    def abrir_relatorio(self):
        if self.relatorio_window is None:
            self.relatorio_window = RelatorioFinanceiro()
        self.relatorio_window.show()
        self.relatorio_window.raise_()
        self.relatorio_window.activateWindow()

    # Método para abrir o Gerenciador de Operadores
    def abrir_operadores(self):
        if self.operadores_window is None:
            self.operadores_window = OperadorManager()  # Criando a instância da janela de gerenciador de operadores
        self.operadores_window.show()
        self.operadores_window.raise_()
        self.operadores_window.activateWindow()
