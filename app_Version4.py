import io
import csv
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Kite For Life - Completo", layout="wide")

CRITERIOS = [
    "LIDERANÇA", "ASSIDUIDADE", "FLEXIBILIDADE", "TEORIA",
    "COMANDO", "CONTROLE", "BADYDRAG ESQ/DIR", "WATER START",
    "PRANCHA ESQ/DIR", "CONTRA VENTO"
]

def ler_excel_ou_csv(uploaded):
    """Lê um ficheiro .xls/.xlsx/.xlsm ou .csv enviado via uploader."""
    if uploaded is None:
        return None
    name = uploaded.name.lower()
    try:
        if name.endswith((".xls", ".xlsx", ".xlsm")):
            df = pd.read_excel(uploaded, sheet_name=0, skiprows=11)
        else:
            # csv
            uploaded.seek(0)
            df = pd.read_csv(uploaded, skiprows=11)
        # Remover colunas 'Unnamed'
        df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
        return df
    except Exception as e:
        st.warning(f"Erro ao ler o ficheiro: {e}")
        return None

def df_demo():
    demo = [
        {"Aluno": "Beatriz Vitoria", **{c: v for c, v in zip(CRITERIOS, [3, 4, 3, 2, 3, 2, 3, 2, 3, 2])}},
        {"Aluno": "Ana Cecilia",     **{c: v for c, v in zip(CRITERIOS, [2, 3, 2, 1, 2, 2, 2, 1, 2, 1])}},
        {"Aluno": "Francisco Neto",  **{c: v for c, v in zip(CRITERIOS, [4, 4, 4, 3, 4, 3, 4, 3, 4, 3])}},
    ]
    df = pd.DataFrame(demo)
    df["Média Geral"] = df[CRITERIOS].mean(axis=1).round(2)
    return df

def garantir_colunas(df):
    """Garante que o dataframe tem colunas para os critérios; se não, adiciona com zeros."""
    for c in CRITERIOS:
        if c not in df.columns:
            df[c] = 0.0
    return df

def criar_radar_plot(notas, titulo, comparacao=None):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=notas, theta=CRITERIOS, fill="toself", name=titulo))
    if comparacao is not None:
        fig.add_trace(go.Scatterpolar(r=comparacao, theta=CRITERIOS, name="Comparação",
                                      line=dict(dash="dash", color="gray")))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True)
    return fig

# --- Sidebar e Upload ---
st.sidebar.header("🌊 Kite For Life - Completo")
st.sidebar.write("Carrega um ficheiro Excel/CSV ou usa os dados demo inclusos.")
uploaded_file = st.sidebar.file_uploader("Escolhe .xls/.xlsx/.xlsm/.csv (opcional)", type=["xls", "xlsx", "xlsm", "csv"])

# Carrega dados
df_notas = ler_excel_ou_csv(uploaded_file)
if df_notas is None:
    # tenta carregar um ficheiro local com nome padrão (apenas para desenvolvimento local)
    DEFAULT_FILENAME = "kite f lifeavaliacao_de_desempenho_-_2025.xlsm - Aval.csv"
    try:
        df_notas = pd.read_csv(DEFAULT_FILENAME, skiprows=11)
        df_notas = df_notas.loc[:, ~df_notas.columns.str.contains("^Unnamed", na=False)]
    except Exception:
        df_notas = df_demo()

# Garantir colunas necessárias
df_notas = garantir_colunas(df_notas)
if "Aluno" not in df_notas.columns:
    # Se não existe coluna "Aluno", cria uma coluna de alunos fictícios (evita que a app quebre)
    df_notas["Aluno"] = [f"Aluno {i+1}" for i in range(len(df_notas))]

# Calcular média geral se não existir
if "Média Geral" not in df_notas.columns:
    df_notas["Média Geral"] = df_notas[CRITERIOS].mean(axis=1).round(2)

# Menu principal
menu = st.sidebar.selectbox("Navegação", ["Painel Geral", "Ficha do Aluno", "Lançar Novas Notas", "Exportar Avaliações"])

# Inicializar estado para avaliações submetidas nesta sessão
if "avaliacoes" not in st.session_state:
    st.session_state["avaliacoes"] = []

# --- Painel Geral ---
if menu == "Painel Geral":
    st.title("📊 Indicadores da Escola - Completo")
    col1, col2, col3 = st.columns(3)
    media_escola = df_notas["Média Geral"].mean() if "Média Geral" in df_notas.columns else 0.0
    col1.metric("Média da Escola", f"{media_escola:.2f}")
    col2.metric("Total de Alunos", len(df_notas))
    col3.metric("Status", "Operacional")

    st.subheader("Desempenho Médio por Habilidade")
    medias = df_notas[CRITERIOS].mean().reset_index()
    medias.columns = ["Critério", "Média"]
    fig_bar = px.bar(medias, x="Critério", y="Média", color="Média",
                     color_continuous_scale="Blues", range_y=[0, 5])
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Lista de Alunos")
    st.dataframe(df_notas[["Aluno", "Média Geral"]].sort_values("Média Geral", ascending=False).reset_index(drop=True))

# --- Ficha do Aluno ---
elif menu == "Ficha do Aluno":
    st.title("👤 Ficha do Aluno")
    aluno_sel = st.selectbox("Selecione o Aluno:", df_notas["Aluno"].unique())
    dados_aluno = df_notas[df_notas["Aluno"] == aluno_sel].iloc[0]
    notas_aluno = [float(dados_aluno.get(c, 0)) for c in CRITERIOS]

    st.subheader(f"{aluno_sel} — Média: {dados_aluno.get('Média Geral', 0):.2f}")
    fig_radar = criar_radar_plot(notas_aluno, aluno_sel, comparacao=list(df_notas[CRITERIOS].mean()))
    st.plotly_chart(fig_radar, use_container_width=True)

    with st.expander("Notas por Critério"):
        tabela = pd.DataFrame({"Critério": CRITERIOS, "Nota": notas_aluno})
        st.table(tabela)

# --- Lançar Novas Notas ---
elif menu == "Lançar Novas Notas":
    st.title("📝 Lançar Novas Notas")
    with st.form("form_avaliacao"):
        nome = st.text_input("Nome do Aluno", value="")
        if not nome:
            # se o utilizador não colocar nome, dá a opção de escolher existente
            nome = st.selectbox("Ou escolha um aluno existente", df_notas["Aluno"].unique())

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

            # Oferecer download imediato da avaliação submetida como CSV
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(entrada.keys()))
            writer.writeheader()
            writer.writerow(entrada)
            buf.seek(0)
            st.download_button("Descarregar esta avaliação (CSV)", data=buf.getvalue(), file_name=f"avaliacao_{nome.replace(' ', '_')}.csv", mime="text/csv")

# --- Exportar Avaliações ---
elif menu == "Exportar Avaliações":
    st.title("📥 Exportar Avaliações (sessão)")
    st.write("As avaliações submetidas nesta sessão aparecem abaixo. Para persistência automática integramos serviços externos (Google Sheets, S3, DB) — posso ajudar a adicionar.")

    if not st.session_state.avaliacoes:
        st.info("Ainda não existem avaliações submetidas nesta sessão.")
    else:
        df_av = pd.DataFrame(st.session_state.avaliacoes)
        # Mostrar tabela (se existir colunas com critérios, ordena-as)
        cols_ordenadas = ["Aluno"] + [c for c in CRITERIOS if c in df_av.columns] + [c for c in df_av.columns if c not in (["Aluno"] + CRITERIOS)]
        cols_ordenadas = [c for c in cols_ordenadas if c in df_av.columns]
        st.dataframe(df_av[cols_ordenadas])

        # Botão para descarregar todas as avaliações como CSV
        csv_bytes = df_av.to_csv(index=False).encode("utf-8")
        st.download_button("Descarregar todas as avaliações (CSV)", data=csv_bytes, file_name="avaliacoes_sessao.csv", mime="text/csv")

st.sidebar.markdown("---")
st.sidebar.write("Dicas:")
st.sidebar.write("- Para deploy no Streamlit Cloud, põe app.py e requirements.txt na raiz do repo e escolhe app.py no Deploy.")
st.sidebar.write("- Se precisas de persistência, diz-me qual serviço preferes (Google Sheets, Firebase, S3, etc.).")