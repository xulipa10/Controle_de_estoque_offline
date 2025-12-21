import sys
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QFormLayout,
    QDialog, QMessageBox, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import Qt

DB_PATH = "Data.db"


# ===================== GERENCIADOR DE PRODUTOS (SQLite) =====================
class ProdutoDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS produtos
                         (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             codigo TEXT UNIQUE NOT NULL,
                             nome TEXT NOT NULL,
                             quantidade REAL NOT NULL,
                             custo REAL NOT NULL,
                             venda REAL NOT NULL,
                             por_peso INTEGER DEFAULT 0
                         )
                         """)

    def carregar(self):
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT codigo, nome, quantidade, custo, venda, por_peso FROM produtos"

            )
            return [
                {
                    "codigo": row[0],
                    "nome": row[1],
                    "quantidade": row[2],
                    "custo": row[3],
                    "venda": row[4],
                    "por_peso": row[5]
                }
                for row in cur.fetchall()
            ]

    def buscar_por_codigo(self, codigo):
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT codigo, nome, quantidade, custo, venda, por_peso FROM produtos WHERE codigo = ?",
                (codigo,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "codigo": row[0],
                "nome": row[1],
                "quantidade": row[2],
                "custo": row[3],
                "venda": row[4],
                "por_peso": row[5]
            }

    def buscar_por_nome(self, nome):
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT codigo, nome, quantidade, custo, venda, por_peso
                FROM produtos
                WHERE nome LIKE ?
                """,
                (f"%{nome}%",)
            )
            return [
                {
                    "codigo": row[0],
                    "nome": row[1],
                    "quantidade": row[2],
                    "custo": row[3],
                    "venda": row[4],
                    "por_peso": row[5]
                }
                for row in cur.fetchall()
            ]

    def adicionar_ou_atualizar(self, produto, entrada=False):
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT quantidade FROM produtos WHERE codigo = ?",
                (produto["codigo"],)
            )
            row = cur.fetchone()

            if row:
                if entrada:
                    nova_qtd = row[0] + produto["quantidade"]
                    conn.execute(
                        "UPDATE produtos SET quantidade = ? WHERE codigo = ?",
                        (nova_qtd, produto["codigo"])
                    )
                else:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET nome = ?, quantidade = ?, custo = ?, venda = ?, por_peso = ?
                        WHERE codigo = ?
                        """,
                        (
                            produto["nome"],
                            produto["quantidade"],
                            produto["custo"],
                            produto["venda"],
                            produto["codigo"],
                            produto["por_peso"]
                        )
                    )
            else:
                conn.execute(
                    """
                    INSERT INTO produtos (codigo, nome, quantidade, custo, venda, por_peso)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        produto["codigo"],
                        produto["nome"],
                        produto["quantidade"],
                        produto["custo"],
                        produto["venda"],
                        produto["por_peso"]
                    )
                )


# ===================== TELA DE CADASTRO =====================
class CadastroProduto(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Cadastro / Alteração de Produto")
        self.setFixedSize(400, 300)

        layout = QFormLayout(self)

        self.por_peso = QCheckBox("Produto vendido por peso (kg)")
        layout.addRow(self.por_peso)

        self.codigo = QLineEdit()
        self.nome = QLineEdit()
        self.quantidade = QLineEdit()
        self.custo = QLineEdit()
        self.venda = QLineEdit()

        layout.addRow("Código:", self.codigo)
        layout.addRow("Nome:", self.nome)
        layout.addRow("Quantidade:", self.quantidade)
        layout.addRow("Valor de Custo:", self.custo)
        layout.addRow("Valor de Venda:", self.venda)

        btn_salvar = QPushButton("Salvar / Atualizar")
        btn_salvar.clicked.connect(self.salvar)
        layout.addRow(btn_salvar)

    def salvar(self):
        try:
            produto = {
                "codigo": self.codigo.text(),
                "nome": self.nome.text(),
                "quantidade": float(self.quantidade.text().replace(",", ".")),
                "custo": float(self.custo.text()),
                "venda": float(self.venda.text()),
                "por_peso": 1 if self.por_peso.isChecked() else 0
            }
        except ValueError:
            QMessageBox.warning(self, "Erro", "Preencha corretamente os campos numéricos")
            return

        self.db.adicionar_ou_atualizar(produto)
        QMessageBox.information(self, "OK", "Produto salvo com sucesso")
        self.close()


# ===================== TELA DE ENTRADA =====================
class EntradaProduto(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Entrada de Produto")
        self.setMinimumSize(500, 300)


        layout = QFormLayout(self)
        self.lbl_produto = QLabel("Produto: ---")
        self.lbl_produto.setStyleSheet("font-weight:bold;")
        layout.addRow("Produto:", self.lbl_produto)

        self.codigo = QLineEdit()
        self.quantidade = QLineEdit()

        layout.addRow("Código:", self.codigo)
        layout.addRow("Quantidade Entrada:", self.quantidade)

        btn = QPushButton("Dar Entrada")
        btn.clicked.connect(self.entrada)
        layout.addRow(btn)

        self.codigo.textChanged.connect(self.buscar_produto)
        self.produto_atual = None

    def buscar_produto(self):
        codigo = self.codigo.text().strip()

        if not codigo:
            self.lbl_produto.setText("Produto: ---")
            self.produto_atual = None
            return

        produto = self.db.buscar_por_codigo(codigo)

        if produto:
            self.produto_atual = produto
            self.lbl_produto.setText(
                f'{produto["nome"]} | Estoque atual: {produto["quantidade"]}'
            )
        else:
            self.lbl_produto.setText("Produto não encontrado")
            self.produto_atual = None

    def entrada(self):
        if not self.produto_atual:
            QMessageBox.warning(self, "Erro", "Produto inválido ou não encontrado")
            return

        try:
            if self.produto_atual["por_peso"]:
                qtd = float(self.quantidade.text().replace(",", "."))
            else:
                qtd = float(self.quantidade.text())

            if qtd <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erro", "Quantidade inválida")
            return

        self.db.adicionar_ou_atualizar(
            {"codigo": self.produto_atual["codigo"], "quantidade": qtd},
            entrada=True
        )

        QMessageBox.information(self, "OK", "Entrada realizada com sucesso")
        self.close()


# ===================== TELA DE BUSCA =====================
class BuscaProduto(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Busca de Produto")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)

        hbox = QHBoxLayout()
        self.input_busca = QLineEdit()
        hbox.addWidget(self.input_busca)
        btn_buscar = QPushButton("Buscar")
        btn_buscar.clicked.connect(self.buscar)
        hbox.addWidget(btn_buscar)
        layout.addLayout(hbox)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Código", "Nome", "Qtd", "Custo", "Venda", "Tipo"]
        )

        layout.addWidget(self.table)

    def buscar(self):
        termo = self.input_busca.text()
        resultados = []

        if termo.isdigit():
            p = self.db.buscar_por_codigo(termo)
            if p:
                resultados.append(p)

        resultados += self.db.buscar_por_nome(termo)

        self.table.setRowCount(0)
        for p in resultados:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p["codigo"]))
            self.table.setItem(row, 1, QTableWidgetItem(p["nome"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(p["quantidade"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["custo"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(p["venda"])))

            peso = "KG" if p["por_peso"] else "UN"
            self.table.setItem(row, 5, QTableWidgetItem(peso))


# ===================== JANELA PRINCIPAL =====================
class EstoqueApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de Estoque")
        self.setFixedSize(600, 400)

        self.db = ProdutoDB(DB_PATH)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        lbl = QLabel("Controle de Estoque")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:22px; font-weight:bold;")
        layout.addWidget(lbl)

        grid = QHBoxLayout()
        layout.addLayout(grid)

        btn_cad = QPushButton("Cadastro / Alteração")
        btn_cad.setFixedHeight(50)
        btn_cad.setStyleSheet("background-color:#4CAF50; color:white; font-weight:bold;")
        btn_cad.clicked.connect(lambda: CadastroProduto(self.db).exec())

        btn_ent = QPushButton("Entrada de Produtos")
        btn_ent.setFixedHeight(50)
        btn_ent.setStyleSheet("background-color:#2196F3; color:white; font-weight:bold;")
        btn_ent.clicked.connect(lambda: EntradaProduto(self.db).exec())

        btn_bus = QPushButton("Buscar Produto")
        btn_bus.setFixedHeight(50)
        btn_bus.setStyleSheet("background-color:#FF9800; color:white; font-weight:bold;")
        btn_bus.clicked.connect(lambda: BuscaProduto(self.db).exec())

        btn_sair = QPushButton("Sair")
        btn_sair.setFixedHeight(50)
        btn_sair.setStyleSheet("background-color:#f44336; color:white; font-weight:bold;")
        btn_sair.clicked.connect(self.close)

        col1 = QVBoxLayout()
        col1.addWidget(btn_cad)
        col1.addWidget(btn_ent)

        col2 = QVBoxLayout()
        col2.addWidget(btn_bus)
        col2.addWidget(btn_sair)

        grid.addLayout(col1)
        grid.addLayout(col2)


# ===================== MAIN =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EstoqueApp()
    window.show()
    sys.exit(app.exec())
