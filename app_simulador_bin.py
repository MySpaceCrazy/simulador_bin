# app_simulador_bin.py

import streamlit as st
import pandas as pd
import sqlite3
import subprocess
import io

# --- Atualiza o banco SQLite automaticamente ---
try:
    subprocess.run(["python", "atualiza_sqlite.py"], check=True)
except Exception as e:
    st.error(f"Erro ao atualizar banco de dados: {e}")

# --- Configuração inicial ---
st.set_page_config(page_title="Simulador de Bins de Picking", page_icon="📦", layout="wide")
st.title("📦 Simulador de Quantidade de Bins por Posição de Picking")

# --- Upload do arquivo do cliente ---
arquivo = st.file_uploader("📂 Selecionar arquivo de simulação (.xlsx)", type=["xlsx"])

if arquivo:
    try:
        # --- Leitura das guias ---
        df_base = pd.read_excel(arquivo, sheet_name="base_item_pacotes")
        df_posicoes_prod = pd.read_excel(arquivo, sheet_name="info_posicao_produtos")

        # --- Validações iniciais ---
        colunas_obrigatorias_base = ["Produto", "Qtd.solicitada total", "Recebedor mercadoria", "Peso", "UM peso", "Volume", "UM volume", "Área de atividade"]
        colunas_obrigatorias_pos = ["Posição no depósito", "Tipo de depósito", "Área armazmto", "Produto"]

        for col in colunas_obrigatorias_base:
            if col not in df_base.columns:
                st.error(f"Coluna obrigatória ausente na base_item_pacotes: {col}")
                st.stop()

        for col in colunas_obrigatorias_pos:
            if col not in df_posicoes_prod.columns:
                st.error(f"Coluna obrigatória ausente na info_posicao_produtos: {col}")
                st.stop()

        # --- Ajustes e normalizações ---
        df_base["Recebedor mercadoria"] = df_base["Recebedor mercadoria"].astype(str).str.zfill(5)
        df_base["Tipo_de_depósito"] = df_base["Área de atividade"].astype(str).str[:2].str.zfill(4)

        # Normaliza peso e volume
        df_base["Peso"] = pd.to_numeric(df_base["Peso"], errors="coerce").fillna(0)
        df_base["Volume"] = pd.to_numeric(df_base["Volume"], errors="coerce").fillna(0)
        df_base["Qtd.solicitada total"] = pd.to_numeric(df_base["Qtd.solicitada total"], errors="coerce").fillna(1)

        df_base.loc[df_base["UM peso"] == "G", "Peso"] /= 1000
        df_base.loc[df_base["UM volume"] == "ML", "Volume"] /= 1000

        # --- Calcula volume e peso unitário ---
        df_base["Volume unitário (L)"] = df_base["Volume"] / df_base["Qtd.solicitada total"]
        df_base["Peso unitário (KG)"] = df_base["Peso"] / df_base["Qtd.solicitada total"]

        # --- Lê tabelas do banco SQLite ---
        conn = sqlite3.connect("logistica.db")
        df_tipo_bin = pd.read_sql("SELECT * FROM info_tipo_bin", conn)
        df_posicao_bin = pd.read_sql("SELECT * FROM info_posicao_bin", conn)
        conn.close()

        # --- Junta dados da posição do produto com o bin da posição ---
        df_posicoes_prod = df_posicoes_prod.rename(columns={"Posição no depósito": "Posicao", "Tipo de depósito": "Tipo_de_depósito"})
        df_posicao_bin = df_posicao_bin.rename(columns={"Posicao": "Posicao", "Tipo_de_deposito": "Tipo_de_depósito"})

        df_posicoes_prod = df_posicoes_prod.merge(df_posicao_bin, on=["Posicao", "Tipo_de_depósito"], how="left")
        df_posicoes_prod = df_posicoes_prod.merge(df_tipo_bin, on="Tipo_Bin", how="left")

        # --- Calcula demanda de bins ---
        resultado = []
        for _, row in df_base.iterrows():
            produto = row["Produto"]
            estrutura = row["Tipo_de_depósito"]
            loja = row["Recebedor mercadoria"]
            volume_unitario = row["Volume unitário (L)"]
            qtd = row["Qtd.solicitada total"]

            posicoes = df_posicoes_prod[df_posicoes_prod["Produto"] == produto]
            if posicoes.empty:
                resultado.append({
                    "Produto": produto,
                    "Recebedor": loja,
                    "Estrutura": estrutura,
                    "Posicao": "N/A",
                    "Tipo_Bin": "N/A",
                    "Bins_Necessarias": "Erro: Produto sem posição",
                    "Bins_Disponiveis": "-",
                    "Diferença": "-"
                })
                continue

            for _, pos in posicoes.iterrows():
                posicao = pos["Posicao"]
                tipo_bin = pos["Tipo_Bin"]
                volume_max = pos.get("Volume_max_L", 1)  # Evita divisão por zero

                if pd.isna(volume_max) or volume_max <= 0:
                    resultado.append({
                        "Produto": produto,
                        "Recebedor": loja,
                        "Estrutura": estrutura,
                        "Posicao": posicao,
                        "Tipo_Bin": tipo_bin,
                        "Bins_Necessarias": "Erro: Bin sem volume",
                        "Bins_Disponiveis": pos.get("Quantidade_Bin", 0),
                        "Diferença": "-"
                    })
                    continue

                # Cálculo simples da necessidade de bins
                volume_total = volume_unitario * qtd
                bins_necessarias = int(-(-volume_total // volume_max))  # Arredonda para cima
                bins_disponiveis = int(pos.get("Quantidade_Bin", 0))
                diferenca = bins_disponiveis - bins_necessarias

                resultado.append({
                    "Produto": produto,
                    "Recebedor": loja,
                    "Estrutura": estrutura,
                    "Posicao": posicao,
                    "Tipo_Bin": tipo_bin,
                    "Bins_Necessarias": bins_necessarias,
                    "Bins_Disponiveis": bins_disponiveis,
                    "Diferença": diferenca
                })

        df_resultado = pd.DataFrame(resultado)

        # --- Exibe resultado ---
        st.subheader("📊 Resultado da Simulação")
        st.dataframe(df_resultado)

        # --- Download Excel ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_resultado.to_excel(writer, sheet_name="Resumo Bins", index=False)

        st.download_button(
            label="📥 Baixar Relatório Excel",
            data=buffer.getvalue(),
            file_name="Simulacao_Bins.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erro no processamento: {e}")

# --- Rodapé do app ---
st.markdown("---")
st.markdown("Desenvolvido por Ânderson Oliveira | Simulador Bin v1.0")
