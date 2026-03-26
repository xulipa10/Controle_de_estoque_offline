import sqlite3
from datetime import datetime
from PySide6.QtWidgets import QDialog, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

DB_PATH = "sistema.db"


class DashboardDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)

    def dados_mes_atual(self):
        cur = self.conn.cursor()

        hoje = datetime.now()
        inicio_mes = hoje.replace(day=1)

        cur.execute("""
            SELECT operador, data_abertura,
                   total_dinheiro, total_credito,
                   total_debito, total_pix
            FROM caixa_operador
        """)

        dinheiro = credito = debito = pix = 0
        por_dia = {}
        por_operador = {}

        for op, data_str, d, c, db, p in cur.fetchall():
            data = datetime.strptime(data_str.split(" ")[0], "%d/%m/%Y")

            if data >= inicio_mes:
                d = d or 0
                c = c or 0
                db = db or 0
                p = p or 0

                dinheiro += d
                credito += c
                debito += db
                pix += p

                total = d + c + db + p

                # vendas por dia
                dia = data.strftime("%d/%m")
                if dia not in por_dia:
                    por_dia[dia] = 0
                por_dia[dia] += total

                # vendas por operador
                if op not in por_operador:
                    por_operador[op] = 0
                por_operador[op] += total

        return dinheiro, credito, debito, pix, por_dia, por_operador

    def faturamento_por_mes(self):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT data_abertura,
                   total_dinheiro, total_credito,
                   total_debito, total_pix
            FROM caixa_operador
        """)

        meses = {
            "01": 0, "02": 0, "03": 0, "04": 0,
            "05": 0, "06": 0, "07": 0, "08": 0,
            "09": 0, "10": 0, "11": 0, "12": 0
        }

        for data_str, d, c, db, p in cur.fetchall():
            data = datetime.strptime(data_str.split(" ")[0], "%d/%m/%Y")
            mes = data.strftime("%m")

            total = (d or 0) + (c or 0) + (db or 0) + (p or 0)
            meses[mes] += total

        return meses


class DashboardWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard Financeiro")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.db = DashboardDB()
        self.plotar()

    def plotar(self):
        dinheiro, credito, debito, pix, por_dia, por_operador = self.db.dados_mes_atual()
        faturamento_mes = self.db.faturamento_por_mes()

        self.figure.clear()

        # Grafico 1 - Formas de pagamento
        ax1 = self.figure.add_subplot(221)
        ax1.pie(
            [dinheiro, credito, debito, pix],
            labels=["Dinheiro", "Crédito", "Débito", "PIX"],
            autopct='%1.1f%%'
        )
        ax1.set_title("Vendas por Pagamento")

        # Grafico 2 - Vendas por dia
        ax2 = self.figure.add_subplot(222)
        ax2.bar(list(por_dia.keys()), list(por_dia.values()))
        ax2.set_title("Vendas por Dia")
        ax2.tick_params(axis='x', rotation=45)

        # Grafico 3 - Vendas por operador
        ax3 = self.figure.add_subplot(223)
        ax3.bar(list(por_operador.keys()), list(por_operador.values()))
        ax3.set_title("Vendas por Operador")

        # Grafico 4 - Faturamento por mês
        ax4 = self.figure.add_subplot(224)
        ax4.bar(list(faturamento_mes.keys()), list(faturamento_mes.values()))
        ax4.set_title("Faturamento por Mês")

        # Grafico 4 - Faturamento por mês
        ax4 = self.figure.add_subplot(224)
        ax4.bar(list(faturamento_mes.keys()), list(faturamento_mes.values()))
        ax4.set_title("Faturamento por Mês")

        # AJUSTE DE ESPAÇAMENTO
        self.figure.subplots_adjust(
            left=0.06,
            right=0.97,
            top=0.93,
            bottom=0.08,
            hspace=0.35,
            wspace=0.25
        )

        self.canvas.draw()

        self.canvas.draw()