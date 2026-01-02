from abc import ABC, abstractmethod
import win32print
from datetime import datetime
import json
import os
import unicodedata



# retira acentos
def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKD", text)\
        .encode("ascii", "ignore")\
        .decode("ascii")


def load_config():
    if not os.path.exists("config.json"):
        return {}

    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def default_coupon_data(operador, itens, total, pagamentos):
    return {
        "empresa": "PDV EXPRESSO",
        "operador": operador,
        "itens": itens,
        "total": total,
        "pagamentos": pagamentos,
        "troco": max(sum(p["valor"] for p in pagamentos) - total, 0),
        "rodape": "Obrigado pela preferência!"
    }

def paper_profile(paper_mm: int):
    """
    Retorna configurações conforme largura do papel
    """
    if paper_mm == 58:
        return {
            "cols": 32,
            "line": "-" * 32
        }
    else:  # 80mm
        return {
            "cols": 48,
            "line": "-" * 48
        }


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def qty_format(qty: float, por_peso: bool) -> str:
    if por_peso:
        return f"{qty:.3f}".replace(".", ",") + " kg"
    return f"{int(qty)} un"



class PrinterBase(ABC):

    @abstractmethod
    def print_coupon(self, data: dict):
        pass





class CupomPrinter:
    def __init__(self, printer_name, paper_mm=58):
        self.printer_name = printer_name
        self.cols = 32 if paper_mm == 58 else 48
        self.line = "-" * self.cols

    def _money(self, v):
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _raw_print(self, text: str):
        hPrinter = win32print.OpenPrinter(self.printer_name)
        try:
            win32print.StartDocPrinter(
                hPrinter, 1, ("Cupom PDV", None, "RAW")
            )
            win32print.StartPagePrinter(hPrinter)

            # Reset basico
            win32print.WritePrinter(hPrinter, b"\x1b@")

            safe_text = normalize_text(text)

            win32print.WritePrinter(
                hPrinter,
                safe_text.encode("ascii")
            )

            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)

    def imprimir(self, operador, table, total, pagamentos, db):
        txt = []

        # Cabeçalho
        txt.append("MERCADINHO BOM PRECO\n")
        txt.append("CUPOM NAO FISCAL\n")
        txt.append(self.line + "\n")

        txt.append(datetime.now().strftime("Data: %d/%m/%Y  Hora: %H:%M\n"))
        txt.append(f"Operador: {operador}\n")
        txt.append(self.line + "\n")

        # Itens
        for row in range(table.rowCount()):
            codigo = table.item(row, 1).text()
            desc = table.item(row, 2).text()
            qtd = float(table.item(row, 3).text().replace(",", "."))
            unit = float(table.item(row, 4).text())
            total_item = float(table.item(row, 5).text())

            produto = db.buscar_por_codigo(codigo)
            por_peso = produto["por_peso"]

            txt.append(desc[:self.cols] + "\n")

            if por_peso:
                txt.append(f"{qtd:.3f} kg x {self._money(unit)}/kg\n")
            else:
                txt.append(f"{int(qtd)} un x {self._money(unit)}\n")

            txt.append(
                f"TOTAL:{self._money(total_item).rjust(self.cols - 6)}\n\n"
            )

        txt.append(self.line + "\n")
        txt.append(
            f"TOTAL:{self._money(total).rjust(self.cols - 6)}\n"
        )
        txt.append(self.line + "\n")

        pago = sum(p["valor"] for p in pagamentos)
        for pag in pagamentos:
            txt.append(
                f"{pag['forma']}:{self._money(pag['valor']).rjust(self.cols - len(pag['forma']) - 1)}\n"
            )

        troco = pago - total
        if troco > 0:
            txt.append(
                f"TROCO:{self._money(troco).rjust(self.cols - 6)}\n"
            )

        txt.append(self.line + "\n")
        txt.append("OBRIGADO PELA PREFERENCIA\nVOLTE SEMPRE\n\n")
        txt.append("\x1dV\x00")  # corte de papel ESC/POS

        self._raw_print("".join(txt))



# teste da impressora
# from printer import CupomPrinter
#
# p = CupomPrinter("impressora knup", 58)
# p._raw_print("cartão débito \n\n\x1dV\x00")














