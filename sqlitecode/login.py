import sys
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
import sqlite3

# Banco de dados
DB_PATH = "sistema.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()

        # Tabela de operadores
        cur.execute(""" 
            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def validar_login(self, nome, senha):
        """Valida o login do operador no banco de dados"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, nome FROM operadores WHERE nome = ? AND senha = ?",
            (nome, senha)
        )
        return cur.fetchone()  # Retorna o operador ou None caso não exista

# Classe de Login
class TelaLogin(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tela de Login")
        self.resize(300, 200)

        # Layout principal
        layout = QVBoxLayout(self)

        # Formulário de login (nome e senha)
        form_layout = QFormLayout()

        self.nome_input = QLineEdit(self)
        self.nome_input.setPlaceholderText("Nome de usuário")
        self.senha_input = QLineEdit(self)
        self.senha_input.setPlaceholderText("Senha")
        self.senha_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Usuário:", self.nome_input)
        form_layout.addRow("Senha:", self.senha_input)

        # Botão de login
        self.btn_login = QPushButton("Entrar", self)
        self.btn_login.clicked.connect(self.validar_login)

        layout.addLayout(form_layout)
        layout.addWidget(self.btn_login)

        # Instanciando o banco de dados
        self.db = Database()

    def validar_login(self):
        nome_usuario = self.nome_input.text().strip()  # Remover espaços em branco extras
        senha = self.senha_input.text().strip()  # Remover espaços em branco extras

        # Validando login no banco de dados
        operador = self.db.validar_login(nome_usuario, senha)

        if operador:
            # Login bem-sucedido
            self.accept()  # Avisa que o login foi bem-sucedido e fecha a tela de login
            self.nome_usuario = operador[1]  # Armazenando o nome do operador
            print(f"Operador logado: {self.nome_usuario}")  # Exemplo de uso do nome do operador (pode ser passado para o PDV)
        else:
            self.show_error_message()

    def show_error_message(self):
        """Exibe a mensagem de erro quando o login falha"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Usuário ou senha incorretos!")
        msg.setWindowTitle("Erro de Login")
        msg.exec_()


