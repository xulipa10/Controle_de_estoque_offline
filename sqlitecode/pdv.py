
from printer import load_config
from fechamento import CaixaDB, FechamentoDialog, SangriaDialog
import sqlite3
from datetime import datetime
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QGridLayout, QMessageBox,
    QInputDialog, QStackedLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QFont


DB_PATH = "Data.db"


# ===================== GERENCIADOR DE PRODUTOS (SQLITE) =====================
class ProdutoDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    codigo TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    quantidade REAL NOT NULL,
                    custo REAL NOT NULL,
                    venda REAL NOT NULL,
                    por_peso INTEGER DEFAULT 0
                )
            """)

    def buscar_por_codigo(self, codigo):
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT codigo, nome, quantidade, custo, venda, por_peso FROM produtos WHERE codigo = ?",
                (codigo,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "codigo": row[0],
                    "nome": row[1],
                    "quantidade": row[2],
                    "custo": row[3],
                    "venda": row[4],
                    "por_peso": bool(row[5])
                }
        return None


# ===================== GERENCIADOR DE VENDAS (SQLITE) =====================
class VendaDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS vendas
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             data
                             TEXT,
                             hora
                             TEXT,
                             total
                             REAL
                         )
                         """)
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS itens_venda
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             venda_id
                             INTEGER,
                             codigo
                             TEXT,
                             descricao
                             TEXT,
                             quantidade
                             INTEGER,
                             unitario
                             REAL,
                             total
                             REAL
                         )
                         """)
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS pagamentos_venda
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             venda_id
                             INTEGER,
                             forma
                             TEXT,
                             valor
                             REAL
                         )
                         """)

    def salvar_venda(self, total, itens, pagamentos):
        now = datetime.now()

        with self._connect() as conn:
            cur = conn.cursor()

            # salva venda
            cur.execute("""
                        INSERT INTO vendas (data, hora, total)
                        VALUES (?, ?, ?)
                        """, (
                            now.strftime("%d/%m/%Y"),
                            now.strftime("%H:%M:%S"),
                            total
                        ))

            venda_id = cur.lastrowid

            # salva itens
            for item in itens:
                cur.execute("""
                            INSERT INTO itens_venda (venda_id, codigo, descricao,
                                                     quantidade, unitario, total)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                venda_id,
                                item["codigo"],
                                item["descricao"],
                                item["qtd"],
                                item["unit"],
                                item["total"]
                            ))

            # salva pagamentos
            for pagamento in pagamentos:
                cur.execute("""
                            INSERT INTO pagamentos_venda (venda_id, forma, valor)
                            VALUES (?, ?, ?)
                            """, (
                                venda_id,
                                pagamento["forma"],
                                pagamento["valor"]
                            ))

            conn.commit()


class ConsultaPreco(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db

        self.setWindowTitle("Consulta de Preço")
        self.setMinimumSize(500, 300)

        layout = QVBoxLayout(self)

        self.label_titulo = QLabel("CONSULTA DE PREÇO")
        self.label_titulo.setAlignment(Qt.AlignCenter)
        self.label_titulo.setFont(QFont("Arial", 20, QFont.Bold))

        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Digite ou bip o código de barras")
        self.input_codigo.setFont(QFont("Arial", 16))
        self.input_codigo.returnPressed.connect(self.buscar_produto)

        self.label_nome = QLabel("")
        self.label_nome.setAlignment(Qt.AlignCenter)
        self.label_nome.setFont(QFont("Arial", 18))

        self.label_preco = QLabel("R$ 0,00")
        self.label_preco.setAlignment(Qt.AlignCenter)
        self.label_preco.setFont(QFont("Arial", 40, QFont.Bold))

        layout.addWidget(self.label_titulo)
        layout.addWidget(self.input_codigo)
        layout.addWidget(self.label_nome)
        layout.addWidget(self.label_preco)

    def buscar_produto(self):
        codigo = self.input_codigo.text().strip()

        produto = self.db.buscar_por_codigo(codigo)

        if not produto:
            self.label_nome.setText("PRODUTO NÃO ENCONTRADO")
            self.label_preco.setText("")
            self.input_codigo.clear()
            return

        nome = produto["nome"]
        preco = produto["venda"]

        self.label_nome.setText(nome)
        self.label_preco.setText(f"R$ {preco:.2f}")

        self.input_codigo.clear()


# ===================== PDV =====================
class PDV(QMainWindow):
    def __init__(self, nome_operador):
        super().__init__()

        self.tela_consulta = None

        self.config = load_config()

        self.setAttribute(Qt.WA_DeleteOnClose)  # Destruir tela ao fechar

        self.venda_aberta = False
        self.venda_id_atual = None  # futuro: venda suspensa

        self.operador = nome_operador
        self.caixa_db = CaixaDB()
        self.caixa_id = self.caixa_db.abrir_caixa(self.operador)

        self.MODOS_PAGAMENTO = [
            "Dinheiro",
            "Cartão Débito",
            "Cartão Crédito",
            "PIX"
        ]

        self.pagamentos = []  # lista de {"forma": str, "valor": float}
        self.pagamento_selecionado = None
        self.valor_recebido = 0.0
        self.troco = 0.0
        self.total_value = 0  # valor total da venda
        self.pagamento_iniciado = False

        self.venda_db = VendaDB(DB_PATH)
        self.db = ProdutoDB(DB_PATH)

        self.setWindowTitle("PDV Expresso")
        self.resize(1366, 768)
        self.is_fullscreen = False

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(4)

        # ================= Barra Superior =================
        self.top_bar = QLabel()
        self.top_bar.setFixedHeight(40)
        self.top_bar.setStyleSheet("""
            background-color: #e0e0e0;
            font-weight: bold;
            padding-left: 10px;
        """)
        main_layout.addWidget(self.top_bar)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

        # ================= Área Central =================

        center_layout = QHBoxLayout()

        center_layout.addSpacing(150)

        self.stack = QStackedLayout()

        # -------- Tela CAIXA LIVRE --------
        self.caixa_livre_label = QLabel("CAIXA LIVRE")
        self.caixa_livre_label.setAlignment(Qt.AlignCenter)
        self.caixa_livre_label.setStyleSheet("""
            font-size: 80px;
            font-weight: bold;
            color: #00000;
        """)

        caixa_livre_widget = QWidget()
        layout_caixa = QVBoxLayout(caixa_livre_widget)
        layout_caixa.addStretch()
        layout_caixa.addWidget(self.caixa_livre_label)
        layout_caixa.addStretch()

        self.stack.addWidget(caixa_livre_widget)  # índice 0





        # Tabela de Itens
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Item", "Código", "Descrição", "Qtd", "Unit.", "Total"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setStyleSheet("font-size: 14px;")
        # Depois de criar a tabela
        self.table.setColumnWidth(2, 350)  # pixels de largura para a coluna "Descrição"
        self.table.setColumnWidth(5, 110)

        self.stack.addWidget(self.table)

        center_layout.addLayout(self.stack, 5)
        self.stack.setCurrentIndex(0)

        # Logo (imagem)
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap("logo2.png")  # caminho da imagem
        self.logo.setPixmap(
            pixmap.scaled(
                300, 300,  # tamanho máximo
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        center_layout.addWidget(self.logo, 2)

        main_layout.addLayout(center_layout)

        # ================= Caixa de Código de Barras e Multiplicador =================
        barcode_layout = QHBoxLayout()
        barcode_layout.setContentsMargins(0, 0, 20, 0)  # margem direita
        barcode_layout.addStretch()  # empurra os widgets para a direita

        # Caixa de código de barras
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Digite ou passe o código de barras")
        self.barcode_input.setFixedHeight(40)
        self.barcode_input.setFixedWidth(200)
        self.barcode_input.setStyleSheet("font-size: 20px; padding-left: 10px;")
        self.barcode_input.returnPressed.connect(self.handle_barcode)
        barcode_layout.addWidget(self.barcode_input)

        # Conecta o evento de alteração de texto
        self.barcode_input.textChanged.connect(self.check_multiplier_inline)

        # Caixa de multiplicador
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("Qtd")
        self.qty_input.setFixedHeight(40)
        self.qty_input.setFixedWidth(60)
        self.qty_input.setText("1")  # valor padrão 1
        self.qty_input.setAlignment(Qt.AlignCenter)
        self.qty_input.setStyleSheet("font-size: 20px;")
        barcode_layout.addWidget(self.qty_input)

        main_layout.addLayout(barcode_layout)

        # ================= Total da Venda =================
        self.total_value = 0.0
        self.total_label = QLabel("TOTAL: R$ 0,00")
        self.total_label.setFixedHeight(80)  # maior que antes
        self.total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_label.setStyleSheet("""
            font-size: 50px;
            font-weight: bold;
            color: #1e88e5;
            padding-right: 20px;
            background-color: #e0e0e0;
            border-radius: 8px;
        """)
        main_layout.addWidget(self.total_label)

        # ================= Barra de Funções =================
        func_layout = QGridLayout()
        func_layout.setSpacing(4)
        self.functions = [
            "F1 Abrir Venda", "F2 Ajuda", "F3 Produto",
            "F4 Cancelar Produto", "F5 Cancelar Venda", "F6 Pagamento",
            "F7 Consultar Preço", "F8", "F9 Sangria",
            "F10 Fechar Caixa", "F11 Tela Cheia", "F12 Finalizar"
        ]
        for col, text in enumerate(self.functions):
            btn = QPushButton(text)
            btn.setMinimumHeight(45)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet("""
                background-color: #cfe2ff;
                font-weight: bold;
            """)
            # conecta botão ao handle_function
            btn.clicked.connect(lambda checked, i=col+1: self.handle_function(i))
            func_layout.addWidget(btn, 0, col)
        main_layout.addLayout(func_layout)

        # ================= Atalhos F1-F12 =================
        for i in range(1, 13):
            shortcut = QShortcut(QKeySequence(f"F{i}"), self)
            shortcut.activated.connect(self.make_function_handler(i))



    def abrir_venda(self):
        if self.venda_aberta:
            QMessageBox.warning(self, "Venda", "Já existe uma venda em andamento")
            return

        self.reset_venda()
        self.venda_aberta = True
        self.stack.setCurrentIndex(1)  # MOSTRA TABELA
        self.show_message("Venda aberta")

    def make_function_handler(self, func_number):
        return lambda: self.handle_function(func_number)

    def update_display_total(self):

        if not self.pagamento_iniciado:
            self.update_total()
            return

        pago = sum(p["valor"] for p in self.pagamentos)
        restante = self.total_value - pago

        if restante > 0:
            valor = f"{restante:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.total_label.setText(f"FALTA: R$ {valor}")
            self.total_label.setStyleSheet("""
                font-size: 50px;
                font-weight: bold;
                color: #d32f2f;
                padding-right: 20px;
                background-color: #e0e0e0;
                border-radius: 8px;
            """)
        else:
            troco = abs(restante)
            valor = f"{troco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.total_label.setText(f"TROCO: R$ {valor}")
            self.total_label.setStyleSheet("""
                font-size: 50px;
                font-weight: bold;
                color: #2e7d32;
                padding-right: 20px;
                background-color: #e0e0e0;
                border-radius: 8px;
            """)

    # ================= Verifica multiplicador inline =================
    def check_multiplier_inline(self, text):
        text = text.strip()
        if text.endswith('*'):
            try:
                qty = int(text[:-1])
                if qty > 0:
                    self.qty_input.setText(str(qty))
            except ValueError:
                self.qty_input.setText("1")
            self.barcode_input.clear()

    def handle_barcode(self):
        texto = self.barcode_input.text().strip()

        if not texto:
            return

        if not self.venda_aberta:
            QMessageBox.warning(
                self,
                "Venda não iniciada",
                "Abra uma venda antes de adicionar itens"
            )
            self.barcode_input.clear()
            return

        # mantém sua regra de venda bloqueada
        if self.venda_bloqueada():
            QMessageBox.warning(
                self,
                "Pagamento em andamento",
                "Finalize ou cancele o pagamento para continuar"
            )
            self.barcode_input.clear()
            return

        qtd = 1.0
        codigo = texto

        #  NOVO PADRÃO: PESO/CODIGO
        if "/" in texto:
            try:
                peso_str, codigo = texto.split("/", 1)
                qtd = float(peso_str.replace(",", "."))
                if qtd <= 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Formato inválido",
                    "Use o formato: 0.500/CODIGO"
                )
                self.barcode_input.clear()
                return
        else:
            # leitura do multiplicador normal
            try:
                qtd = float(self.qty_input.text().replace(",", "."))
                if qtd <= 0:
                    qtd = 1
            except ValueError:
                qtd = 1

        produto = self.db.buscar_por_codigo(codigo)

        if not produto:
            QMessageBox.warning(self, "Produto não encontrado", f"Código: {codigo}")
            self.barcode_input.clear()
            return

        # REGRA DE NEGÓCIO CRÍTICA
        if not produto["por_peso"] and not qtd.is_integer():
            QMessageBox.warning(
                self,
                "Produto unitário",
                "Este produto não pode ser vendido fracionado"
            )
            self.qty_input.setText("1")
            self.barcode_input.clear()
            return

        self.add_item(
            produto["codigo"],
            produto["nome"],
            qtd,
            produto["venda"]
        )

        # reset
        self.barcode_input.clear()
        self.qty_input.setText("1")

    def cancelar_venda(self):
        if not self.venda_aberta:
            QMessageBox.information(
                self,
                "Cancelar venda",
                "Não há venda aberta para cancelar"
            )
            return

        if self.table.rowCount() > 0:
            resp = QMessageBox.question(
                self,
                "Cancelar venda",
                "Deseja realmente cancelar a venda em andamento?\n"
                "Todos os itens e pagamentos serão perdidos.",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                return

        self.reset_venda()
        self.venda_aberta = False
        self.stack.setCurrentIndex(0)  # MOSTRA CAIXA LIVRE
        self.show_message("Venda cancelada")

    # ================= Lógica de Adição/Cancelamento =================
    def add_item(self, code, desc, qty, price):

        row = self.table.rowCount()
        total = qty * price

        if not self.venda_aberta:
            QMessageBox.warning(
                self,
                "Venda não iniciada",
                "Abra uma venda antes de adicionar itens"
            )
            self.barcode_input.clear()
            return

        if self.venda_bloqueada():
            QMessageBox.warning(
                self,
                "Pagamento em andamento",
                "Não é possível adicionar itens após iniciar o pagamento"
            )
            return

        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # Número do item
        self.table.setItem(row, 1, QTableWidgetItem(code))
        self.table.setItem(row, 2, QTableWidgetItem(desc))

        qtd_txt = f"{qty:.3f}" if isinstance(qty, float) else str(qty)

        self.table.setItem(row, 3, QTableWidgetItem(qtd_txt))
        self.table.setItem(row, 4, QTableWidgetItem(f"{price:.2f}"))
        self.table.setItem(row, 5, QTableWidgetItem(f"{total:.2f}"))

        for i in range(0,6):
            if i != 2:
                self.table.item(row,i).setTextAlignment(Qt.AlignCenter)

        self.total_value += total
        self.update_display_total()

    def cancel_item_by_number(self, item_number):
        if self.venda_bloqueada():
            QMessageBox.warning(
                self,
                "Pagamento em andamento",
                "Não é possível cancelar itens após iniciar o pagamento"
            )
            return
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == str(item_number):
                value = float(self.table.item(row, 5).text())
                self.total_value -= value
                self.table.removeRow(row)
                self.update_display_total()
                self.renumber_items()
                self.show_message(f"Item {item_number} cancelado")
                return
        self.show_message(f"Item {item_number} não encontrado")

    def renumber_items(self):
        for row in range(self.table.rowCount()):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

    def venda_bloqueada(self):
        if self.pagamento_selecionado != "Dinheiro":
            return False
        return self.valor_recebido >= self.total_value

    def update_total(self):

        self.total_label.setStyleSheet("""
                font-size: 50px;
                font-weight: bold;
                color: #1e88e5;
                padding-right: 20px;
                background-color: #e0e0e0;
                border-radius: 8px;
            """)

        text = f"{self.total_value:,.2f}"
        text = text.replace(",", "X").replace(".", ",").replace("X", ".")
        self.total_label.setText(f"TOTAL: R$ {text}")

    def update_clock(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.top_bar.setText(f"OPERADOR: {self.operador} | {now}")

    def show_message(self, message):
        self.top_bar.setText(f"{message} | {datetime.now().strftime('%H:%M:%S')}")

    def reset_venda(self):
        self.table.setRowCount(0)
        self.total_value = 0
        self.valor_recebido = 0
        self.pagamento_selecionado = None

        self.total_label.setStyleSheet("""
            font-size: 50px;
            font-weight: bold;
            color: #1e88e5;
            padding-right: 20px;
            background-color: #e0e0e0;
            border-radius: 8px;
        """)
        self.update_total()
        self.pagamento_iniciado = False
        self.pagamentos.clear()

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen

    def consultar_preco(self):
        if self.tela_consulta is None:
            self.tela_consulta = ConsultaPreco(self.db)

        self.tela_consulta.show()
        self.tela_consulta.raise_()
        self.tela_consulta.activateWindow()

    # ================= Funções F1-F12 =================
    def handle_function(self, func):

        if func == 1:
            self.abrir_venda()

        elif func == 2:
            self.show_message("Ajuda acionada")

        elif self.venda_bloqueada() and func not in (6, 12, 4):
            self.show_message("Pagamento em andamento")
            return

        elif func == 3:
            self.add_item("123", "Produto Exemplo", 1, 10.00)

        elif func == 4:
            if self.table.rowCount() == 0:
                self.show_message("Nenhum item para cancelar")
                return
            item_number, ok = QInputDialog.getInt(
                self, "Cancelar Item", "Digite o número do item a cancelar:", 1, 1, self.table.rowCount()
            )
            if ok:
                self.cancel_item_by_number(item_number)

        elif func == 5:
            self.cancelar_venda()

        elif func == 6:

            if not self.venda_aberta:
                QMessageBox.warning(
                    self,
                    "Venda não iniciada",
                    "Abra uma venda antes de adicionar itens"
                )
                self.barcode_input.clear()
                return

            if self.table.rowCount() == 0:
                self.show_message("Nenhuma venda em andamento")
                return

            pagamento, ok = QInputDialog.getItem(
                self,
                "Forma de Pagamento",
                "Selecione o pagamento:",
                self.MODOS_PAGAMENTO,
                0,
                False
            )

            if not ok:
                return

            restante = self.total_value - sum(p["valor"] for p in self.pagamentos)

            if restante <= 0:
                QMessageBox.information(self, "Pagamento", "Venda já paga")
                return

            if pagamento == "Dinheiro":
                max_valor = 999999.99  # permite troco
            else:
                max_valor = restante  # cartão / pix

            valor, ok = QInputDialog.getDouble(
                self,
                "Pagamento",
                f"Total: R$ {self.total_value:,.2f}\n"
                f"Já pago: R$ {self.total_value - restante:,.2f}\n"
                f"Restante: R$ {restante:,.2f}\n"
                "Informe o valor:",
                restante,
                0,
                max_valor,
                2
            )

            if not ok or valor <= 0:
                return

            self.pagamentos.append({
                "forma": pagamento,
                "valor": valor
            })

            self.show_message(f"Pagamento {pagamento}: R$ {valor:,.2f}")
            self.pagamento_iniciado = True
            self.update_display_total()

        elif func == 7:
            self.consultar_preco()

        elif func == 9:

            if self.venda_aberta:
                QMessageBox.warning(

                    self,

                    "Sangria",

                    "Finalize ou cancele a venda antes da sangria"

                )

                return

            from printer import CupomPrinter, load_config

            config = load_config()

            printer = CupomPrinter(

                printer_name=config.get("printer_name"),

                paper_mm=int(config.get("paper_mm", 58))

            )

            dlg = SangriaDialog(

                caixa_id=self.caixa_id,

                operador=self.operador,

                printer=printer

            )

            dlg.exec()

        elif func == 10:

            if self.venda_aberta:
                QMessageBox.warning(

                    self,

                    "Fechar Caixa",

                    "Finalize ou cancele a venda antes de Fechar o caixa"

                )

                return

            from printer import CupomPrinter, load_config
            config = load_config()

            printer = CupomPrinter(
                printer_name=config.get("printer_name"),
                paper_mm=int(config.get("paper_mm", 58))
            )

            dlg = FechamentoDialog(
                caixa_id=self.caixa_id,
                operador=self.operador,
                printer=printer
            )

            if dlg.exec():
                self.close()  # fecha PDV

        elif func == 11:
            self.toggle_fullscreen()

        elif func == 12:

            if self.table.rowCount() == 0:
                self.show_message("Nenhuma venda para finalizar")
                return

            total_pago = sum(p["valor"] for p in self.pagamentos)
            if total_pago < self.total_value:
                QMessageBox.warning(self, "Pagamento", "Pagamento insuficiente")
                return

            itens = []
            for row in range(self.table.rowCount()):
                itens.append({
                    "codigo": self.table.item(row, 1).text(),
                    "descricao": self.table.item(row, 2).text(),
                    "qtd": float(self.table.item(row, 3).text()),
                    "unit": float(self.table.item(row, 4).text()),
                    "total": float(self.table.item(row, 5).text())
                })

            self.venda_db.salvar_venda(
                total=self.total_value,
                itens=itens,
                pagamentos=self.pagamentos
            )

            # baixa de produtos
            with self.db._connect() as conn:
                cur = conn.cursor()
                for item in itens:
                    cur.execute(
                        """
                        UPDATE produtos
                        SET quantidade = quantidade - ?
                        WHERE codigo = ?
                        """,
                        (item["qtd"], item["codigo"])
                    )
                conn.commit()


                # AREA PARA REGISTRAR PAGAMENTO
                total_venda = self.total_value
                total_formas = 0

                for p in self.pagamentos:
                    forma = p["forma"]
                    valor_pago = p["valor"]

                    total_formas += valor_pago

                    # dinheiro pode ter troco
                    if forma == "Dinheiro":
                        valor_efetivo = min(valor_pago, total_venda)
                    else:
                        valor_efetivo = valor_pago

                    self.caixa_db.registrar_pagamento(
                        self.caixa_id,
                        forma,
                        valor_efetivo
                    )

                    total_venda -= valor_efetivo

                    if total_venda <= 0:
                        break

                # Area para tentar imprimir cupom


            resp = QMessageBox.question(
                self,
                "Impressão de Cupom",
                "Deseja imprimir o cupom?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if resp == QMessageBox.Yes:
                try:
                    printer_name = self.config.get("printer_name")
                    paper_mm = int(self.config.get("paper_mm", 58))

                    if not printer_name:
                        raise Exception("Impressora não configurada")

                    from printer import CupomPrinter

                    printer = CupomPrinter(
                        printer_name=printer_name,
                        paper_mm=paper_mm
                    )

                    printer.imprimir(
                        operador=self.operador,
                        table=self.table,
                        total=self.total_value,
                        pagamentos=self.pagamentos,
                        db=self.db
                    )

                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Impressão",
                        f"Cupom não impresso:\n{str(e)}"
                    )

            self.venda_aberta = False
            self.venda_id_atual = None
            self.reset_venda()
            self.stack.setCurrentIndex(0)  # MOSTRA CAIXA LIVRE
            self.show_message("Venda finalizada com sucesso")

        else:
            self.show_message(f"Função F{func}")

