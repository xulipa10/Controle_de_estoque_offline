import sys
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QMessageBox, QTableWidget,
    QTableWidgetItem
)
from PySide6.QtCore import Qt

DB_PATH = "data.db"

# ===================== BANCO DE DADOS =====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        

    # CRUD OPERADOR
    def criar_operador(self, nome, senha):
        try:
            self.conn.execute(
                "INSERT INTO operadores (nome, senha) VALUES (?, ?)",
                (nome, senha)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def excluir_operador(self, operador_id):
        self.conn.execute(
            "DELETE FROM operadores WHERE id = ?",
            (operador_id,)
        )
        self.conn.commit()

    def listar_operadores(self):
        cur = self.conn.execute(
            "SELECT id, nome FROM operadores ORDER BY nome"
        )
        return cur.fetchall()

    def validar_login(self, nome, senha):
        cur = self.conn.execute(
            "SELECT id, nome FROM operadores WHERE nome = ? AND senha = ?",
            (nome, senha)
        )
        return cur.fetchone()


db = Database()

class OperadorManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Operadores")
        self.resize(400, 300)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # formulário
        form = QHBoxLayout()
        self.nome = QLineEdit()
        self.nome.setPlaceholderText("Nome")
        self.senha = QLineEdit()
        self.senha.setPlaceholderText("Senha")

        btn_add = QPushButton("Cadastrar")
        btn_add.clicked.connect(self.cadastrar)

        form.addWidget(self.nome)
        form.addWidget(self.senha)
        form.addWidget(btn_add)

        layout.addLayout(form)

        # tabela
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["ID", "Nome"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.table)

        btn_del = QPushButton("Excluir Selecionado")
        btn_del.clicked.connect(self.excluir)

        layout.addWidget(btn_del)

        self.carregar()

    def carregar(self):
        self.table.setRowCount(0)
        for row_data in db.listar_operadores():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(row_data[0])))
            self.table.setItem(row, 1, QTableWidgetItem(row_data[1]))

    def cadastrar(self):
        if not self.nome.text() or not self.senha.text():
            QMessageBox.warning(self, "Erro", "Preencha todos os campos")
            return

        if not db.criar_operador(self.nome.text(), self.senha.text()):
            QMessageBox.warning(self, "Erro", "Operador já existe")
            return

        self.nome.clear()
        self.senha.clear()
        self.carregar()

    def excluir(self):
        row = self.table.currentRow()
        if row < 0:
            return

        operador_id = int(self.table.item(row, 0).text())
        db.excluir_operador(operador_id)
        self.carregar()

