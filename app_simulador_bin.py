# app_simulador_bin.py

import streamlit as st
import pandas as pd
import sqlite3
import os
import io

# --- Atualiza o banco SQLite diretamente ---
PASTA_CSV = "arquivos"
ARQUIVOS_CSV = {
    "info_tipo_bin": "info_tipo_bin.csv",
    "info_posicao_bin": "info_posicao_bin.csv"
}

conn = sqlite3.connect("logistica.db")

for tabela, nome_arquivo in ARQUIVOS_CSV.items():
    caminho = os.path.join(PASTA_CSV, nome_arquivo)
    if os.path.exists(caminho):
        try:
            df = pd.read_csv(caminho, sep=";", engine="python", encoding="latin1")
            df.columns = [c.strip().replace(" ", "_") for c in df.columns]

            if tabela == "info_tipo_bin" and "Volume_(L)" in df.columns:
                df["Volume_(L)"] = df["Volume_(L)"].astype(str).str.replace(",", ".", regex=False)
                df["Volume_(L)"] = pd.to_numeric(df["Volume_(L)"], errors="coerce").fillna(0)

            df.to_sql(tabela, conn, if_exists="replace", index=False)
            print(f"🔄 Atualizado: {tabela}")
        except Exception as e:
            print(f"❌ Erro ao processar {nome_arquivo}: {e}")
    else:
        print(f"⚠️ Arquivo não encontrado: {nome_arquivo}")

conn.close()
print("✅ Banco logistica.db atualizado com sucesso.")

# --- Configuração inicial ---
st.set_page_config(page_title="Simulador de Bins de Picking", page_icon="📦", layout="wide")
st.title("📦 Simulador de Quantidade de Bins por Posição de Picking")

# --- Upload do arquivo do cliente ---
arquivo = st.file_uploader("📂 Selecionar arquivo de simulação (.xlsx)", type=["xlsx"])

if arquivo:
    try:
        df_base = pd.read_excel(arquivo, sheet_name="base_item_pacotes")
        df_posicoes_prod = pd.read_excel(arquivo, sheet_name="info_posicao_produtos")

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
        df_base["Peso"] = pd.to_numeric(df_base["Peso"], errors="coerce").fillna(0)
        df_base["Volume"] = pd.to_numeric(df_base["Volume"], errors="coerce").fillna(0)
        df_base["Qtd.solicitada total"] = pd.to_numeric(df_base["Qtd.solicitada total"], errors="coerce").fillna(1)
        df_base.loc[df_base["UM peso"] == "G", "Peso"] /= 1000
        df_base.loc[df_base["UM volume"] == "ML", "Volume"] /= 1000
        df_base["Volume unitário (L)"] = df_base["Volume"] / df_base["Qtd.solicitada total"]

        # --- Lê tabelas do banco ---
        conn = sqlite3.connect("logistica.db")
        df_tipo_bin = pd.read_sql("SELECT * FROM info_tipo_bin", conn)
        df_posicao_bin = pd.read_sql("SELECT * FROM info_posicao_bin", conn)
        conn.close()

        # --- Renomeia e normaliza colunas ---
        df_posicoes_prod = df_posicoes_prod.rename(columns={
            "Posição no depósito": "Posicao",
            "Tipo de depósito": "Tipo_de_depósito"
        })
        df_posicao_bin = df_posicao_bin.rename(columns={
            "Posição_no_depósito": "Posicao",
            "Tipo_de_depósito": "Tipo_de_depósito",
            "Qtd._Caixas_BIN_ABASTECIMENTO": "Quantidade_Bin"
        })
        df_tipo_bin = df_tipo_bin.rename(columns={
            "Tipo": "Tipo",
            "Volume_(L)": "Volume_max_L"
        })

        df_tipo_bin["Tipo"] = df_tipo_bin["Tipo"].astype(str).str.strip()
        df_posicao_bin["Tipo"] = df_posicao_bin["Tipo"].astype(str).str.strip()
        df_posicao_bin["Tipo_de_depósito"] = df_posicao_bin["Tipo_de_depósito"].astype(str).str.zfill(4).str.strip()
        df_posicoes_prod["Tipo_de_depósito"] = df_posicoes_prod["Tipo_de_depósito"].astype(str).str.zfill(4).str.strip()
        df_tipo_bin["Volume_max_L"] = pd.to_numeric(df_tipo_bin["Volume_max_L"], errors="coerce").fillna(0)

        # --- Joins ---
        df_posicoes_prod = df_posicoes_prod.merge(df_posicao_bin, on=["Posicao", "Tipo_de_depósito"], how="left")
        df_posicoes_prod = df_posicoes_prod.merge(df_tipo_bin, on="Tipo", how="left")

        # --- Cálculo das bins ---
        resultado = []
        for _, row in df_base.iterrows():
            produto = row["Produto"]
            estrutura = row["Tipo_de_depósito"]
            loja = row["Recebedor mercadoria"]
            volume_unitario = row["Volume unitário (L)"]
            qtd = row["Qtd.solicitada total"]

            # Seleciona apenas as posições do mesmo produto e estrutura
            posicoes = df_posicoes_prod[
                (df_posicoes_prod["Produto"] == produto) &
                (df_posicoes_prod["Tipo_de_depósito"] == estrutura)
            ]

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

            volume_total = volume_unitario * qtd
            for _, pos in posicoes.iterrows():
                posicao = pos.get("Posicao", "N/A")
                tipo_bin = pos.get("Tipo", "N/A")
                volume_max = pos.get("Volume_max_L", 1)

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

                bins_necessarias = int(-(-volume_total // volume_max))
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

        # --- Relatório Resumo por Produto e Estrutura ---

        
        df_estrutura = df_posicao_bin[["Posicao", "Tipo_de_depósito", "Estrutura"]].drop_duplicates()
        
        # Ajusta tipos
        df_posicao_bin["Tipo_de_depósito"] = df_posicao_bin["Tipo_de_depósito"].astype(str).str.zfill(4).str.strip()

        # Junta a descrição da estrutura
        df_resumo = df_resultado.merge(df_posicao_bin, how="left", left_on=["Posicao", "Estrutura"], right_on=["Posicao", "Tipo_de_depósito"])

        # Junta a descrição do produto
        df_resumo = df_resumo.merge(df_posicoes_prod[["Produto", "Descrição breve do produto"]].drop_duplicates(), on="Produto", how="left")

        # Seleciona e renomeia colunas finais
        df_resumo = df_resumo[[
            "Estrutura_x",            # Estrutura (Tipo_de_depósito da simulação)
            "Estrutura_y",            # Descrição da estrutura (do banco)
            "Posicao",
            "Produto",
            "Descrição breve do produto",
            "Tipo_Bin",
            "Bins_Necessarias",
            "Bins_Disponiveis",
            "Diferença"
        ]]

        df_resumo.columns = [
            "Estrutura",
            "Descrição - estrutura",
            "Posição",
            "Produto",
            "Descrição – produto",
            "Tipo_Bin",
            "Bins_Necessarias",
            "Bins_Disponiveis",
            "Diferença"
        ]

        # Exibe e permite download
        st.subheader("📊 Resumo por Produto e Estrutura")
        st.dataframe(df_resumo)

        buffer_resumo = io.BytesIO()
        with pd.ExcelWriter(buffer_resumo, engine="xlsxwriter") as writer:
            df_resumo.to_excel(writer, sheet_name="Resumo Produto Estrutura", index=False)

        st.download_button(
            label="📥 Baixar Resumo Produto/Estrutura",
            data=buffer_resumo.getvalue(),
            file_name="Resumo_Produto_Estrutura.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    except Exception as e:
        st.error(f"Erro no processamento: {e}")

# --- Rodapé ---
st.markdown("---")
st.markdown("Desenvolvido por Ânderson Oliveira | Simulador Bin v1.0")
