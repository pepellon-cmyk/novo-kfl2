"""
Kite For Life - app_Version4.py
Versão corrigida e mais tolerante para leitura de ficheiros e deploy no Streamlit Cloud.

Funcionalidades:
- Carregamento de ficheiro .xls/.xlsx/.xlsm/.csv via file_uploader (ou usa dados demo)
- Normalização básica de nomes de colunas para mapear com os critérios
- Painel Geral, Ficha do Aluno, Lançar Novas Notas e Exportar avaliações da sessão
- Gera gráficos com Plotly (bar + radar)
- Download de avaliações submetidas na sessão
"""

import io
import csv
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Kite For Life - Version 4", layout="wide")

# Lista de critérios esperados (utiliza maiúsculas sem espaços finais)
CRITERIOS = [
    "LIDERANÇA", "ASSIDUIDADE", "FLEXIBILIDADE", "TEORIA",
    "COMANDO", "CONTROLE", "BADYDRAG ESQ/DIR", "WATER START",
    "PRANCHA ESQ/DIR", "CONTRA VENTO"
]


def normalize_colname(name: str) -> str:
    """Remove espaços extras, converte para maiúsculas e normaliza acentos simples."""
    if not isinstance(name, str):
        return ""
    return " ".join(name.strip().upper().split())


def try_read_table(uploaded):
    """
    Lê uploaded file (BytesIO/File) e tenta detectar excel/csv.
    Para excel, usa engine openpyxl quando aplicável.
    Retorna DataFrame ou None em caso de erro.
    """
    if uploaded is None:
        return None

    fname = uploaded.name.lower()
    try:
        if fname.endswith((".xls", ".xlsx", ".xlsm")):
            # pd.read_excel detecta engine; explicitamos openpyxl para xlsx/xlsm
            df = pd.read_excel(uploaded, sheet_name=0, skiprows=11, engine="openpyxl")
        else:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, skiprows=11)
        # Remove colunas 'Unnamed' que frequentemente aparecem depois de skiprows
        df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
        return df
    except Exception as e:
        st.warning(f"Falha ao ler ficheiro '{uploaded.name}': {e}")
        return None


def demo_dataframe():
    """Dados fictícios para demo/local fallback"""
    demo = [
        {"Aluno": "Beatriz Vitoria", **{c: v for c, v in zip(CRITERIOS, [3, 4, 3, 2, 3, 2, 3, 2, 3, 2])}},
        {"Aluno": "Ana Cecilia",     **{c: v for c, v in zip(CRITERIOS, [2, 3, 2, 1, 2, 2, 2, 1, 2, 1])}},
        {"Aluno": "Francisco Neto",  **{c: v for c, v in zip(CRITERIOS, [4, 4, 4, 3, 4, 3, 4, 3, 4, 3])}},
    ]
    df = pd.DataFrame(demo)
    df["Média Geral"] = df[CRITERIOS].mean(axis=1).round(2)
    return df


def map_columns_to_criterios(df: pd.DataFrame):
    """
    Tenta alinhar as colunas do dataframe com os CRITERIOS.
    Retorna um DataFrame com colunas renomeadas para os nomes dos critérios (quando possível)
    e mantém outras colunas como estão (por exemplo 'Aluno', 'Média Geral').
    """
    col_map = {}
    normalized_cols = {c: normalize_colname(c) for c in df.columns}
    inv_index = {normalize_colname(c): c for c in df.columns}

    # 1) Busca correspondência exata
    for crit in CRITERIOS:
        # tenta encontrar coluna cujo normalized == crit
        for orig, norm in normalized_cols.items():
            if norm == crit:
                col_map[inv_index[norm]] = crit
                break

    # 2) Busca correspondência por inclusão (col contains crit words) - tentativa heurística
    for crit in CRITERIOS:
        if crit in col_map.values():
            continue
        crit_words = crit.split()
        for orig, norm in normalized_cols.items():
            if inv_index[norm] in col_map:
                continue
            # se a coluna contiver a primeira palavra do critério ou vice-versa
            if any(w in norm for w in crit_words) or any(w in norm for w in [crit.replace("/", " ").split()[0]]):
                # evitar mapear colunas que claramente são 'ALUNO' ou 'MÉDIA'
                if "ALUNO" in norm or "MEDIA" in norm or "MÉDIA" in norm:
                    continue
                col_map[inv_index[norm]] = crit
                break

    # Renomear conforme o mapeamento
    df_renamed = df.rename(columns=col_map)
    return df_renamed


def ensure_criterios_columns(df: pd.DataFrame):
    """Garante que todas as colunas de CRITERIOS existem no DF (preenche com zeros quando ausentes)."""
    for c in CRITERIOS:
        if c not in df.columns:
            df[c] = 0.0
    return df


def radar_figure(notas, comparacao=None, title=None):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=notas, theta=CRITERIOS, fill="toself", name=title or "Aluno"))
    if comparacao is not None:
        fig.add_trace(go.Scatterpolar(r=comparacao, theta=CRITERIOS, name="Média Escola",
                                      line=dict(dash="dash", color="gray")))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True)
    return fig


# --- Interface / fluxo principal ---
st.sidebar.header("🌊 Kite For Life - Version 4")
st.sidebar.write("Carrega um ficheiro Excel/CSV ou usa os dados demo incluídos.")

uploaded_file = st.sidebar.file_uploader("Upload .xls/.xlsx/.xlsm/.csv (opcional)", type=["xls", "xlsx", "xlsm", "csv"])

# 1) Ler dados do uploader (se existir)
df = try_read_table(uploaded_file)

# 2) Se não carregou, tenta carregar um ficheiro local padrão (apenas em dev) ou usa demo
if df is None:
    # tentar arquivo local padrão (só em desenvolvimento local)
    DEFAULT_LOCAL = "kite f lifeavaliacao_de_desempenho_-_2025.xlsm - Aval.csv"
    try:
        local_df = pd.read_csv(DEFAULT_LOCAL, skiprows=11)
        local_df = local_df.loc[:, ~local_df.columns.str.contains("^Unnamed", na=False)]
        df = local_df
    except Exception:
        df = demo_dataframe()

# Normalizar nomes e tentar mapear critérios
#  - remover espaços estranhos e normalizar maiúsculas
df.columns = [normalize_colname(c) for c in df.columns]
df = map_columns_to_criterios(df)
df = ensure_criterios_columns(df)

# Se não houver coluna Aluno, cria identificadores simples
if "ALUNO" not in df.columns and "Aluno" not in df.columns:
    df.insert(0, "Aluno", [f"Aluno {i+1}" for i in range(len(df))])

# Padroniza nome da coluna "Aluno" para 'Aluno' se veio em maiúsculas
if "ALUNO" in df.columns and "Aluno" not in df.columns:
    df = df.rename(columns={"ALUNO": "Aluno"})

# Calcular Média Geral se ausente
if "Média Geral" not in df.columns and "MÉDIA GERAL" not in df.columns:
    # usa colunas CRITERIOS (caso existam) para calcular
    try:
        df["Média Geral"] = df[CRITERIOS].mean(axis=1).round(2)
    except Exception:
        df["Média Geral"] = 0.0
else:
    # se col vem em maiúsculas acentuadas
    if "MÉDIA GERAL" in df.columns and "Média Geral" not in df.columns:
        df = df.rename(columns={"MÉDIA GERAL": "Média Geral"})

# Assegura que 'Aluno' exista e esteja como string
df["Aluno"] = df["Aluno"].astype(str)

# Menu
menu = st.sidebar.selectbox("Navegação", ["Painel Geral", "Ficha do Aluno", "Lançar Novas Notas", "Exportar Avaliações"])

# Estado para avaliações da sessão
if "avaliacoes" not in st.session_state:
    st.session_state["avaliacoes"] = []

# --- Painel Geral ---
if menu == "Painel Geral":
    st.title("📊 Painel Geral - Kite For Life")
    col1, col2, col3 = st.columns(3)
    media_escola = float(df["Média Geral"].mean()) if "Média Geral" in df.columns else 0.0
    col1.metric("Média da Escola", f"{media_escola:.2f}")
    col2.metric("Total de Alunos", len(df))
    col3.metric("Status", "Operacional")

    st.subheader("Média por Critério")
    medias = df[CRITERIOS].mean().reset_index()
    medias.columns = ["Critério", "Média"]
    fig_bar = px.bar(medias, x="Critério", y="Média", color="Média",
                     color_continuous_scale="Blues", range_y=[0, 5])
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Lista de Alunos")
    st.dataframe(df[["Aluno", "Média Geral"]].sort_values("Média Geral", ascending=False).reset_index(drop=True))

# --- Ficha do Aluno ---
elif menu == "Ficha do Aluno":
    st.title("👤 Ficha do Aluno")
    aluno_sel = st.selectbox("Selecione o Aluno:", df["Aluno"].unique())
    dados_aluno = df[df["Aluno"] == aluno_sel].iloc[0]
    notas_aluno = [float(dados_aluno.get(c, 0)) for c in CRITERIOS]

    st.subheader(f"{aluno_sel} — Média: {dados_aluno.get('Média Geral', 0):.2f}")
    fig_radar = radar_figure(notas_aluno, comparacao=list(df[CRITERIOS].mean()), title=aluno_sel)
    st.plotly_chart(fig_radar, use_container_width=True)

    with st.expander("Notas por Critério"):
        tabela = pd.DataFrame({"Critério": CRITERIOS, "Nota": notas_aluno})
        st.table(tabela)

# --- Lançar Novas Notas ---
elif menu == "Lançar Novas Notas":
    st.title("📝 Lançar Novas Notas")
    with st.form("form_avaliacao"):
        nome = st.text_input("Nome do Aluno")
        if not nome:
            nome = st.selectbox("Ou escolha um aluno existente", df["Aluno"].unique())

        st.write("Atribua notas de 1 (Ruim) a 5 (Excelente):")
        c1, c2 = st.columns(2)
        notas_novas = {}
        for i, crit in enumerate(CRITERIOS):
            with (c1 if i % 2 == 0 else c2):
                notas_novas[crit] = st.select_slider(crit, options=[1, 2, 3, 4, 5], value=3)
        coment = st.text_area("Observações (opcional)")
        submit = st.form_submit_button("Guardar Avaliação")

        if submit:
            entrada = {"Aluno": nome, **notas_novas, "Observações": coment}
            st.session_state.avaliacoes.append(entrada)
            st.success(f"Avaliação de {nome} registada (na sessão).")

            # Download imediato como CSV
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(entrada.keys()))
            writer.writeheader()
            writer.writerow(entrada)
            buf.seek(0)
            st.download_button("Descarregar avaliação (CSV)", data=buf.getvalue(),
                               file_name=f"avaliacao_{nome.replace(' ', '_')}.csv", mime="text/csv")

# --- Exportar Avaliações ---
elif menu == "Exportar Avaliações":
    st.title("📥 Exportar Avaliações (sessão)")
    if not st.session_state.avaliacoes:
        st.info("Ainda não existem avaliações submetidas nesta sessão.")
    else:
        df_av = pd.DataFrame(st.session_state.avaliacoes)
        # Organiza colunas: Aluno -> CRITERIOS -> restantes
        cols_ordenadas = ["Aluno"] + [c for c in CRITERIOS if c in df_av.columns] + [c for c in df_av.columns if c not in (["Aluno"] + CRITERIOS)]
        cols_ordenadas = [c for c in cols_ordenadas if c in df_av.columns]
        st.dataframe(df_av[cols_ordenadas])

        csv_bytes = df_av.to_csv(index=False).encode("utf-8")
        st.download_button("Descarregar todas as avaliações (CSV)", data=csv_bytes, file_name="avaliacoes_sessao.csv", mime="text/csv")

# Footer / dicas
st.sidebar.markdown("---")
st.sidebar.write("Dicas:")
st.sidebar.write("- Coloca este ficheiro (app_Version4.py) e requirements.txt na raiz do repo antes de fazer deploy.")
st.sidebar.write("- Se usares Excel (.xlsx / .xlsm), garante openpyxl no requirements.")