# fechamento.py
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit,
    QPushButton, QMessageBox
)

DB_PATH = "sistema.db"


# ===================== BANCO DO CAIXA =====================
class CaixaDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def listar_sangrias(self, caixa_id):
        cur = self.conn.cursor()
        cur.execute("""
                    SELECT data, valor, motivo
                    FROM sangria
                    WHERE caixa_id = ?
                    ORDER BY id
                    """, (caixa_id,))
        return cur.fetchall()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS caixa_operador (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operador TEXT NOT NULL,
                data_abertura TEXT NOT NULL,
                data_fechamento TEXT,
                total_dinheiro REAL DEFAULT 0,
                total_credito REAL DEFAULT 0,
                total_debito REAL DEFAULT 0,
                total_pix REAL DEFAULT 0,
                informado_dinheiro REAL,
                informado_credito REAL,
                informado_debito REAL,
                informado_pix REAL,
                fechado INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()
        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS sangria
                          (
                              id INTEGER PRIMARY KEY AUTOINCREMENT,
                              caixa_id INTEGER NOT NULL,
                              valor REAL NOT NULL,
                              data TEXT NOT NULL,
                              motivo TEXT
                          )
                          """)
        self.conn.commit()

    def total_sangrias(self, caixa_id):
        cur = self.conn.cursor()
        cur.execute("""
                    SELECT COALESCE(SUM(valor), 0)
                    FROM sangria
                    WHERE caixa_id = ?
                    """, (caixa_id,))
        return cur.fetchone()[0]

    def registrar_sangria(self, caixa_id, valor, motivo=""):
        if valor <= 0:
            return

        self.conn.execute("""
                          INSERT INTO sangria (caixa_id, valor, data, motivo)
                          VALUES (?, ?, ?, ?)
                          """, (
                              caixa_id,
                              valor,
                              datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                              motivo
                          ))

        # sangria reduz o dinheiro do caixa
        self.conn.execute("""
                          UPDATE caixa_operador
                          SET total_dinheiro = total_dinheiro - ?
                          WHERE id = ?
                          """, (valor, caixa_id))

        self.conn.commit()

    # ---------- abertura ----------
    def abrir_caixa(self, operador):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id FROM caixa_operador
            WHERE operador = ? AND fechado = 0
        """, (operador,))
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute("""
            INSERT INTO caixa_operador (operador, data_abertura)
            VALUES (?, ?)
        """, (operador, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        self.conn.commit()
        return cur.lastrowid

    # ---------- registrar pagamentos ----------
    def registrar_pagamento(self, caixa_id, forma, valor):
        mapa = {
            "Dinheiro": "total_dinheiro",
            "Cartão Crédito": "total_credito",
            "Cartão Débito": "total_debito",
            "PIX": "total_pix"
        }
        campo = mapa.get(forma)
        if not campo:
            return

        self.conn.execute(f"""
            UPDATE caixa_operador
            SET {campo} = {campo} + ?
            WHERE id = ?
        """, (valor, caixa_id))
        self.conn.commit()

    # ---------- totais ----------
    def obter_totais(self, caixa_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT total_dinheiro, total_credito,
                   total_debito, total_pix
            FROM caixa_operador
            WHERE id = ?
        """, (caixa_id,))
        row = cur.fetchone()
        return {
            "dinheiro": row[0],
            "credito": row[1],
            "debito": row[2],
            "pix": row[3]
        }

    # ---------- finalizar ----------
    def finalizar_caixa(self, caixa_id, informado):
        self.conn.execute("""
            UPDATE caixa_operador
            SET informado_dinheiro = ?,
                informado_credito = ?,
                informado_debito = ?,
                informado_pix = ?,
                fechado = 1,
                data_fechamento = ?
            WHERE id = ?
        """, (
            informado["dinheiro"],
            informado["credito"],
            informado["debito"],
            informado["pix"],
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            caixa_id
        ))
        self.conn.commit()


# ===================== TELA DE FECHAMENTO =====================
class FechamentoDialog(QDialog):
    def __init__(self, caixa_id, operador, printer):
        super().__init__()
        self.caixa_id = caixa_id
        self.operador = operador
        self.printer = printer
        self.db = CaixaDB()

        self.setWindowTitle("Fechamento de Caixa")
        self.setFixedSize(400, 300)

        layout = QFormLayout(self)

        self.ed_dinheiro = QLineEdit("0")
        self.ed_credito = QLineEdit("0")
        self.ed_debito = QLineEdit("0")
        self.ed_pix = QLineEdit("0")

        layout.addRow("Dinheiro em Caixa:", self.ed_dinheiro)
        layout.addRow("Cartão Crédito:", self.ed_credito)
        layout.addRow("Cartão Débito:", self.ed_debito)
        layout.addRow("PIX:", self.ed_pix)

        btn = QPushButton("FECHAR CAIXA")
        btn.setFixedHeight(50)
        btn.setStyleSheet("background-color:#d32f2f; color:white; font-weight:bold;")
        btn.clicked.connect(self.fechar)

        layout.addRow(btn)

    def fechar(self):
        try:
            informado = {
                "dinheiro": float(self.ed_dinheiro.text().replace(",", ".")),
                "credito": float(self.ed_credito.text().replace(",", ".")),
                "debito": float(self.ed_debito.text().replace(",", ".")),
                "pix": float(self.ed_pix.text().replace(",", "."))
            }
        except ValueError:
            QMessageBox.warning(self, "Erro", "Valores inválidos")
            return

        vendido = self.db.obter_totais(self.caixa_id)
        sangrias = self.db.listar_sangrias(self.caixa_id)

        self.db.finalizar_caixa(self.caixa_id, informado)

        self.printer.imprimir_fechamento(
            operador=self.operador,
            vendido=vendido,
            informado=informado,
            sangrias=sangrias
        )

        self.accept()


class SangriaDialog(QDialog):
    def __init__(self, caixa_id, operador, printer):
        super().__init__()
        self.caixa_id = caixa_id
        self.operador = operador
        self.printer = printer
        self.db = CaixaDB()

        self.setWindowTitle("Sangria de Caixa")
        self.setFixedSize(350, 220)

        layout = QFormLayout(self)

        self.valor = QLineEdit()
        self.motivo = QLineEdit()

        layout.addRow("Valor da Sangria:", self.valor)
        layout.addRow("Motivo (opcional):", self.motivo)

        btn = QPushButton("CONFIRMAR SANGRIA")
        btn.setFixedHeight(45)
        btn.setStyleSheet("background-color:#ff9800; font-weight:bold;")
        btn.clicked.connect(self.confirmar)

        layout.addRow(btn)

    def confirmar(self):
        try:
            valor = float(self.valor.text().replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erro", "Valor inválido")
            return

        motivo = self.motivo.text().strip()

        self.db.registrar_sangria(
            caixa_id=self.caixa_id,
            valor=valor,
            motivo=motivo
        )

        # impressão automática do comprovante
        self.printer.imprimir_sangria(
            operador=self.operador,
            valor=valor,
            motivo=motivo
        )

        QMessageBox.information(self, "OK", "Sangria registrada e impressa")
        self.accept()


