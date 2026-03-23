import sqlite3
import pandas as pd
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QTableWidget,
    QTableWidgetItem
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


DB_VENDAS = "Data.db"
DB_SISTEMA = "sistema.db"


class RelatorioFinanceiro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Relatório Financeiro")
        self.resize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Labels financeiros
        self.lbl_faturamento = QLabel("Faturamento: R$ 0.00")
        self.lbl_custo = QLabel("Custo: R$ 0.00")
        self.lbl_lucro = QLabel("Lucro Bruto: R$ 0.00")

        layout.addWidget(self.lbl_faturamento)
        layout.addWidget(self.lbl_custo)
        layout.addWidget(self.lbl_lucro)

        # Tabela operador
        self.tabela_operador = QTableWidget()
        self.tabela_operador.setColumnCount(2)
        self.tabela_operador.setHorizontalHeaderLabels(["Operador", "Total Vendido"])

        layout.addWidget(self.tabela_operador)

        # Gráfico
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        btn_atualizar = QPushButton("Atualizar Relatório")
        btn_atualizar.clicked.connect(self.atualizar_relatorio)
        layout.addWidget(btn_atualizar)

        self.atualizar_relatorio()

    # =========================
    # CARREGAR DADOS
    # =========================
    def carregar_dados(self):
        conn = sqlite3.connect(DB_VENDAS)

        vendas = pd.read_sql("SELECT * FROM vendas", conn)
        itens = pd.read_sql("SELECT * FROM itens_venda", conn)
        produtos = pd.read_sql("SELECT codigo, custo FROM produtos", conn)

        conn.close()

        conn2 = sqlite3.connect(DB_SISTEMA)
        operadores = pd.read_sql("SELECT * FROM caixa_operador", conn2)
        conn2.close()

        return vendas, itens, produtos, operadores

    # =========================
    # ATUALIZAR RELATÓRIO
    # =========================
    def atualizar_relatorio(self):
        vendas, itens, produtos, operadores = self.carregar_dados()

        vendas["data"] = pd.to_datetime(vendas["data"], format="%d/%m/%Y")

        mes = datetime.now().month
        ano = datetime.now().year

        vendas_mes = vendas[
            (vendas["data"].dt.month == mes) &
            (vendas["data"].dt.year == ano)
        ]

        faturamento = vendas_mes["total"].sum()

        itens = itens.merge(produtos, on="codigo")
        itens["custo_total"] = itens["quantidade"] * itens["custo"]
        custo = itens["custo_total"].sum()

        lucro = faturamento - custo

        # Atualizar labels
        self.lbl_faturamento.setText(f"Faturamento: R$ {faturamento:.2f}")
        self.lbl_custo.setText(f"Custo: R$ {custo:.2f}")
        self.lbl_lucro.setText(f"Lucro Bruto: R$ {lucro:.2f}")

        # =========================
        # RELATÓRIO POR OPERADOR
        # =========================
        operadores["total"] = (
            operadores["total_dinheiro"] +
            operadores["total_credito"] +
            operadores["total_debito"] +
            operadores["total_pix"]
        )

        self.tabela_operador.setRowCount(0)

        for i, row in operadores.iterrows():
            linha = self.tabela_operador.rowCount()
            self.tabela_operador.insertRow(linha)
            self.tabela_operador.setItem(linha, 0, QTableWidgetItem(str(row["operador"])))
            self.tabela_operador.setItem(linha, 1, QTableWidgetItem(f'{row["total"]:.2f}'))

        # =========================
        # GRÁFICO VENDAS POR DIA
        # =========================
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        vendas_mes["dia"] = vendas_mes["data"].dt.day
        vendas_dia = vendas_mes.groupby("dia")["total"].sum()

        ax.bar(vendas_dia.index, vendas_dia.values)
        ax.set_title("Vendas por Dia")
        ax.set_xlabel("Dia")
        ax.set_ylabel("Total")

        self.canvas.draw()