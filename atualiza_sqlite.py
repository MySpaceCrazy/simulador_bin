import pandas as pd
import sqlite3
import os

# Pasta com os arquivos CSV
PASTA_CSV = "arquivos"
ARQUIVOS_CSV = {
    "info_tipo_bin": "info_tipo_bin.csv",
    "info_posicao_bin": "info_posicao_bin.csv"
}

# Conecta ao banco SQLite
conn = sqlite3.connect("logistica.db")

for tabela, nome_arquivo in ARQUIVOS_CSV.items():
    caminho = os.path.join(PASTA_CSV, nome_arquivo)
    if os.path.exists(caminho):
        print(f"🔄 Atualizando: {tabela}")
        df = pd.read_csv(caminho, sep=";|,", engine="python")
        df.columns = [c.strip().replace(" ", "_") for c in df.columns]  # Normaliza colunas
        df.to_sql(tabela, conn, if_exists="replace", index=False)
    else:
        print(f"⚠️ Arquivo não encontrado: {nome_arquivo}")

conn.close()
print("✅ Banco logistica.db atualizado com sucesso.")
