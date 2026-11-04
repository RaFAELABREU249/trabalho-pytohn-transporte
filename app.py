from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Transporte e Mobilidade Urbana",
    page_icon="🚲",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "Tabela_13_Meio_de_transporte.xlsx"
SHEET_NAME = "BR GR UF MU"

RACES = ["Branca", "Preta ou Parda", "Indígena"]
MODES = [
    "A pé",
    "Bicicleta",
    "Motocicleta ou Mototaxi",
    "Automóvel, taxi ou assemelhados",
    "Transporte coletivo",
    "Outros",
]
REGIONS = ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-oeste"]
REGION_BY_UF = {
    "AC": "Norte",
    "AL": "Nordeste",
    "AM": "Norte",
    "AP": "Norte",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "DF": "Centro-oeste",
    "ES": "Sudeste",
    "GO": "Centro-oeste",
    "MA": "Nordeste",
    "MG": "Sudeste",
    "MS": "Centro-oeste",
    "MT": "Centro-oeste",
    "PA": "Norte",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "PR": "Sul",
    "RJ": "Sudeste",
    "RN": "Nordeste",
    "RO": "Norte",
    "RR": "Norte",
    "RS": "Sul",
    "SC": "Sul",
    "SE": "Nordeste",
    "SP": "Sudeste",
    "TO": "Norte",
}
UF_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins",
}
RACE_COLORS = {
    "Branca": "#58A6FF",
    "Preta ou Parda": "#FF4B4B",
    "Indígena": "#F5C451",
}
MODE_COLUMNS = [
    f"{race}::{mode}"
    for race in RACES
    for mode in MODES
]
MODE_GROUPS = {
    "Ativo (a pé + bicicleta)": ["A pé", "Bicicleta"],
    "Individual (automóvel/táxi + moto/mototáxi)": [
        "Automóvel, taxi ou assemelhados",
        "Motocicleta ou Mototaxi",
    ],
    "Coletivo (sem separar ônibus/metrô)": ["Transporte coletivo"],
}


@st.cache_data(show_spinner="Lendo a tabela de transporte...")
def load_transport_data(
    file_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_excel(
        file_path,
        sheet_name=SHEET_NAME,
        header=None,
        skiprows=3,
        engine="calamine",
    )
    if raw.shape[1] < 19:
        raise ValueError(
            "A aba de dados não contém as 18 colunas esperadas de transporte."
        )

    raw = raw.iloc[:, :19].copy()
    raw.columns = ["localidade", *MODE_COLUMNS]
    raw["localidade"] = raw["localidade"].astype("string").str.strip()
    raw[MODE_COLUMNS] = raw[MODE_COLUMNS].replace(".", np.nan)
    raw[MODE_COLUMNS] = raw[MODE_COLUMNS].apply(
        pd.to_numeric,
        errors="coerce",
    )

    long_data = raw.melt(
        id_vars="localidade",
        value_vars=MODE_COLUMNS,
        var_name="categoria",
        value_name="percentual",
    )
    long_data[["raca", "modal"]] = long_data["categoria"].str.split(
        r"::",
        n=1,
        expand=True,
    )
    long_data = long_data.drop(columns="categoria")

    municipalities = long_data[
        long_data["localidade"].str.contains(r"\([A-Z]{2}\)$", regex=True)
    ].copy()
    municipalities[["municipio", "uf"]] = municipalities[
        "localidade"
    ].str.extract(r"^(.*) \(([A-Z]{2})\)$")
    municipalities["regiao"] = municipalities["uf"].map(REGION_BY_UF)
    return long_data, municipalities


def style_figure(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        margin={"l": 16, "r": 16, "t": 48, "b": 16},
        legend_title_text="",
    )
    return figure


st.title("Transporte e Mobilidade Urbana")
st.caption(
    "Como mulheres ocupadas se deslocam para o trabalho — "
    "distribuição percentual por cor ou raça, Brasil, 2022."
)

if not DATA_FILE.is_file():
    st.error(
        f"Não encontrei `{DATA_FILE.name}` na pasta do aplicativo. "
        "Mantenha a planilha junto de `app.py`."
    )
    st.stop()

transport_data, municipality_data = load_transport_data(str(DATA_FILE))

with st.sidebar:
    st.header("Filtros")
    selected_region = st.selectbox(
        "Grande Região",
        ["Todas", *REGIONS],
        help=(
            "A planilha não identifica regiões metropolitanas. "
            "Este filtro usa as Grandes Regiões do Brasil."
        ),
    )
    available_ufs = [
        uf
        for uf, region in REGION_BY_UF.items()
        if selected_region == "Todas" or region == selected_region
    ]
    selected_uf = st.selectbox(
        "UF",
        ["Todas", *sorted(available_ufs)],
        format_func=lambda uf: (
            "Todas as UFs" if uf == "Todas" else f"{uf} — {UF_NAMES[uf]}"
        ),
    )
    selected_mode = st.selectbox(
        "Meio de transporte (mediana e boxplot)",
        MODES,
        index=MODES.index("Bicicleta"),
    )
    selected_races = st.multiselect(
        "Cor ou raça",
        RACES,
        default=RACES,
    )
    st.selectbox(
        "Categoria de renda",
        ["Não disponível na tabela"],
        disabled=True,
        help="A planilha não apresenta dados de renda.",
    )

if not selected_races:
    st.warning("Selecione ao menos uma categoria de cor ou raça.")
    st.stop()

if selected_uf != "Todas":
    aggregate_location = UF_NAMES[selected_uf]
elif selected_region != "Todas":
    aggregate_location = selected_region
else:
    aggregate_location = "Brasil"

filtered_municipalities = municipality_data
if selected_region != "Todas":
    filtered_municipalities = filtered_municipalities[
        filtered_municipalities["regiao"] == selected_region
    ]
if selected_uf != "Todas":
    filtered_municipalities = filtered_municipalities[
        filtered_municipalities["uf"] == selected_uf
    ]

st.info(
    "A fonte descreve mulheres ocupadas de 10 anos ou mais e a distribuição "
    "percentual do meio de transporte em que passam mais tempo no trajeto "
    "ao trabalho principal. A tabela não informa tempo de viagem, renda, "
    "região metropolitana, nem separa ônibus de metrô."
)
st.caption(
    f"Recorte agregado dos gráficos de distribuição: **{aggregate_location}**. "
    "As medianas e o boxplot usam os municípios do recorte."
)

st.subheader(f"Mediana municipal — {selected_mode}")
median_columns = st.columns(len(selected_races))
for column, race in zip(median_columns, selected_races):
    values = filtered_municipalities.loc[
        (filtered_municipalities["raca"] == race)
        & (filtered_municipalities["modal"] == selected_mode),
        "percentual",
    ].dropna()
    with column:
        if values.empty:
            st.metric(f"Cor/raça {race}", "N/D")
            st.caption("Nenhum município com valor disponível neste recorte.")
        else:
            st.metric(f"Cor/raça {race}", f"{values.median():.1f}%")
            st.caption(f"Mediana simples de {len(values):,} municípios.")

st.divider()
left_chart, right_chart = st.columns([1.15, 1])

aggregate_data = transport_data[
    transport_data["localidade"] == aggregate_location
]

with left_chart:
    st.subheader("Ativo, particular ou coletivo")
    grouped_values = []
    for race in selected_races:
        race_data = aggregate_data[aggregate_data["raca"] == race].set_index(
            "modal"
        )["percentual"]
        for group_name, modes in MODE_GROUPS.items():
            group_data = race_data.reindex(modes)
            if group_data.isna().any():
                continue
            grouped_values.append(
                {
                    "Categoria": group_name,
                    "Percentual": group_data.sum(),
                    "Cor ou raça": race,
                }
            )

    if grouped_values:
        grouped_figure = px.bar(
            pd.DataFrame(grouped_values),
            x="Categoria",
            y="Percentual",
            color="Cor ou raça",
            barmode="group",
            color_discrete_map=RACE_COLORS,
            labels={"Percentual": "Percentual (%)"},
        )
        style_figure(grouped_figure).update_layout(
            xaxis_title=None,
            yaxis_title="Percentual (%)",
        )
        st.plotly_chart(grouped_figure, width="stretch")
        st.caption(
            "Ativo = a pé + bicicleta. O grupo individual inclui as categorias "
            "de automóvel/táxi e motocicleta/mototáxi, então não equivale "
            "perfeitamente a transporte particular. A tabela não separa "
            "ônibus e metrô; “Outros” não entra nesses grupos."
        )
    else:
        st.warning("Não há valores completos para montar este gráfico.")

with right_chart:
    st.subheader(f"Distribuição dos modais — {aggregate_location}")
    race_columns = st.columns(len(selected_races))
    for column, race in zip(race_columns, selected_races):
        race_data = aggregate_data[aggregate_data["raca"] == race]
        with column:
            if race_data.empty:
                st.info(f"Sem valores disponíveis para {race}.")
                continue
            if race_data["percentual"].isna().any():
                st.info(
                    f"Distribuição incompleta para {race}; rosca não exibida."
                )
                continue
            pie_figure = px.pie(
                race_data,
                names="modal",
                values="percentual",
                hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            pie_figure.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )
            style_figure(pie_figure).update_layout(
                title={"text": race, "x": 0.5},
                showlegend=False,
                margin={"l": 4, "r": 4, "t": 42, "b": 4},
            )
            st.plotly_chart(
                pie_figure,
                width="stretch",
                key=f"donut_{race}",
            )

st.divider()
left_chart, right_chart = st.columns([1, 1])

with left_chart:
    st.subheader(f"Variação municipal — {selected_mode}")
    box_data = filtered_municipalities[
        (filtered_municipalities["modal"] == selected_mode)
        & filtered_municipalities["raca"].isin(selected_races)
    ].dropna(subset=["percentual"])
    if box_data.empty:
        st.warning("Não há valores disponíveis para o boxplot neste recorte.")
    else:
        box_figure = px.box(
            box_data,
            x="raca",
            y="percentual",
            color="raca",
            points="outliers",
            hover_data=["municipio", "uf"],
            category_orders={"raca": selected_races},
            color_discrete_map=RACE_COLORS,
            labels={
                "raca": "Cor ou raça",
                "percentual": "Percentual municipal (%)",
            },
        )
        style_figure(box_figure).update_layout(
            showlegend=False,
            xaxis_title=None,
            yaxis_title="Percentual municipal (%)",
        )
        st.plotly_chart(box_figure, width="stretch")
        st.caption(
            "O boxplot compara percentuais entre municípios e destaca "
            "valores atípicos; não representa duração do deslocamento."
        )

with right_chart:
    st.subheader("Municípios com maior uso de bicicleta")
    bike_data = filtered_municipalities[
        (filtered_municipalities["modal"] == "Bicicleta")
        & filtered_municipalities["raca"].isin(selected_races)
    ]
    bike_ranking = (
        bike_data.groupby(["municipio", "uf"], as_index=False)["percentual"]
        .mean()
        .sort_values("percentual", ascending=False)
        .head(15)
    )
    if bike_ranking.empty:
        st.warning("Não há percentuais de bicicleta disponíveis neste recorte.")
    else:
        bike_ranking["cidade"] = (
            bike_ranking["municipio"] + " (" + bike_ranking["uf"] + ")"
        )
        bike_figure = px.bar(
            bike_ranking.sort_values("percentual"),
            x="percentual",
            y="cidade",
            orientation="h",
            labels={
                "percentual": "Percentual de bicicleta (%)",
                "cidade": "Município",
            },
            color_discrete_sequence=["#FF4B4B"],
        )
        style_figure(bike_figure).update_layout(
            showlegend=False,
            xaxis_title="Percentual de bicicleta (%)",
            yaxis_title=None,
        )
        st.plotly_chart(bike_figure, width="stretch")
        st.caption(
            "Ranking pela média simples dos grupos de cor ou raça selecionados; "
            "não é ponderado pelo tamanho da população."
        )

with st.expander("Sobre os dados e as limitações"):
    st.markdown(
        """
        - **Fonte no projeto:** arquivo `Tabela_13_Meio_de_transporte.xlsx`,
          aba `BR GR UF MU`, referente a 2022.
        - **População observada:** mulheres de 10 anos ou mais ocupadas na
          semana de referência.
        - **Mediana:** mediana simples dos percentuais municipais para o modal
          selecionado; municípios sem valor publicado são ignorados.
        - **Transporte coletivo:** a tabela não discrimina ônibus e metrô.
        - **Limitações:** não há duração do trajeto, categoria de renda ou
          identificação de região metropolitana. Por isso, esses filtros e a
          análise de gargalos por tempo não podem ser calculados com esta fonte.
        """
    )

st.subheader("Leituras e imagens sobre mobilidade")
st.markdown(
    """
    - [Reportagens sobre caos no trânsito — Google Notícias](https://news.google.com/search?q=caos%20no%20tr%C3%A2nsito%20Brasil&hl=pt-BR&gl=BR&ceid=BR%3Apt-419)
    - [Reportagens sobre mobilidade sustentável — Google Notícias](https://news.google.com/search?q=mobilidade%20sustent%C3%A1vel%20Brasil&hl=pt-BR&gl=BR&ceid=BR%3Apt-419)
    - [WRI Brasil — mobilidade urbana sustentável](https://www.wribrasil.org.br/)
    - [Fotos de vias e transportes públicos — Wikimedia Commons](https://commons.wikimedia.org/w/index.php?search=transporte+p%C3%BAblico+Brasil&title=Special:MediaSearch&type=image)
    """
)
