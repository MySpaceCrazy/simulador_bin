📦 Simulador de Quantidade de Bins
Este aplicativo em Streamlit simula a quantidade de bins (caixas plásticas de armazenagem) necessárias para armazenar produtos em posições específicas de um depósito logístico, baseado em informações de volume, peso e estrutura de armazenagem.

🧩 Objetivo
Determinar:

Quantos bins são necessários para cada produto e posição.

Se a posição possui bins suficientes.

Gerar relatórios detalhados e resumos para análise e tomada de decisão.

🗂️ Estrutura dos Dados
O simulador utiliza:

1. Arquivo Excel (.xlsx) do usuário:
Sheet base_item_pacotes: contém os produtos solicitados, volumes, pesos, recebedor, etc.

Sheet info_posicao_produtos: relaciona produtos às posições e estruturas do depósito.

2. Banco SQLite (logistica.db):
Tabela info_tipo_bin: define o volume máximo de cada tipo de bin.

Tabela info_posicao_bin: mapeia posições, tipos de bin disponíveis e quantidade de bins por posição.

🔄 Atualização automática do banco
Na inicialização, o app lê arquivos .csv em ./arquivos:

Atualiza o banco logistica.db com as tabelas info_tipo_bin e info_posicao_bin.

⚙️ Etapas da Simulação
1. Upload do Arquivo
Usuário faz upload do .xlsx com as duas abas exigidas.

2. Validação das colunas
Confere a existência das colunas obrigatórias nas abas:

base_item_pacotes: Produto, Qtd, Peso, Volume, etc.

info_posicao_produtos: Produto, Posição, Tipo_de_depósito, etc.

3. Tratamento de Dados
Converte unidades (de G para KG, de ML para L).

Cria colunas auxiliares como Volume unitário (L) e Tipo_de_depósito.

Normaliza campos de texto.

4. Leitura do Banco
Lê as tabelas info_tipo_bin e info_posicao_bin para obter capacidade dos bins e distribuição.

5. Join entre tabelas
Relaciona os produtos da base com as posições disponíveis e os tipos de bins.

📊 Lógica do Cálculo
Para cada linha da base:

Busca as posições disponíveis para o produto e estrutura.

Calcula o volume_total = volume_unitário × quantidade.

Calcula o número de bins_necessárias = ceil(volume_total / volume_bin).

Compara com os bins_disponíveis na posição.

Registra a diferença e volumetria máxima possível.

📁 Relatórios Gerados
✅ Detalhado por Loja, Estrutura e Produto
Inclui:

Produto, Loja, Estrutura

Quantidade de bins necessárias e disponíveis

Volume total e volumetria máxima

📌 Resumo por Produto e Estrutura (agrupado)
Agrupado por:

Estrutura, Produto, Posição, Tipo de bin

Soma das bins necessárias e volumes

Bins disponíveis por posição

Diferencial entre necessário vs disponível

🚨 Resumo de Posições
Separado por:

Posições - OK: possuem bins suficientes

Posições - Não Atendem: bins insuficientes

Apresenta totais por estrutura.

❌ Resumo de Erros
Erros típicos:

Produto sem posição mapeada

Bin sem volume registrado

⏱️ Indicadores de Execução
Ao final da simulação, exibe:

Tempo total da simulação

Total de linhas da base

Linhas simuladas com sucesso

Linhas com erro

🧑‍💻 Sobre o Autor
Ânderson Oliveira
Engenheiro de Dados | Soluções Logísticas | Automações



📌 Observações
O app foi otimizado para performance com bases de até 200 mil linhas.

Linhas com erro são preservadas no relatório e não interrompem a simulação.

Os arquivos .csv de bin/tipo devem estar na pasta ./arquivos.

