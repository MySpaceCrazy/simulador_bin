import sqlite3
import pandas as pd

conn = sqlite3.connect("logistica.db")

df_tipo = pd.read_sql("SELECT * FROM info_tipo_bin", conn)
df_posicao = pd.read_sql("SELECT * FROM info_posicao_bin", conn)

conn.close()

# Exibe para verificar
print(df_tipo.head())
print(df_posicao.head())
