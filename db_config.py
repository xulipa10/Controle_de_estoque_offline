import os
import sqlite3

DB_PATH  = os.path.join(os.getcwd(), "data.db")



def criar_tabelas():
    with sqlite3.connect(DB_PATH) as conn:
        print("tabelas criadas")

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

        conn.execute("""
                        CREATE TABLE IF NOT EXISTS vendas(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            data TEXT,
                            hora TEXT,
                            total REAL
                         )
                         """)
        

        conn.execute("""
                         CREATE TABLE IF NOT EXISTS itens_venda
                         (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             venda_id INTEGER,
                             codigo TEXT,
                             descricao TEXT,
                             quantidade INTEGER,
                             unitario REAL,
                             total REAL
                         )
                         """)
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS pagamentos_venda(
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             venda_id INTEGER,
                             forma TEXT,
                             valor REAL
                         )
                         """)
        
         # operadores
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            )
        """)

        # vendas por operador (futuro PDV)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendas_operador (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operador_id INTEGER,
                total REAL,
                data TEXT,
                forma_pagamento TEXT,
                fechado INTEGER DEFAULT 0
            )
        """)

        # Tabela de operadores
        conn.execute(""" 
            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            )
        """)

        conn.execute("""
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
        
        conn.execute("""
                          CREATE TABLE IF NOT EXISTS sangria
                          (
                              id INTEGER PRIMARY KEY AUTOINCREMENT,
                              caixa_id INTEGER NOT NULL,
                              valor REAL NOT NULL,
                              data TEXT NOT NULL,
                              motivo TEXT
                          )
                          """)
        
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
        


        conn.commit()
        
criar_tabelas()