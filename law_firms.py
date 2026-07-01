"""
Script legacy — usa filtrar_leads.py en su lugar.

Ver README.md para instrucciones de uso.
"""
import pandas as pd


arquivo = "dataset_findlaw-scraper_2026-06-25_12-11-04-503.csv"


df = pd.read_csv("findlaw.csv")


# estados disponíveis
print(df["address/region"].value_counts())


# filtrar estados
df_estados = df[
    df["address/region"].isin(["CA","IL"])
].copy()


# encontrar colunas de áreas
colunas_pratica = [
    c for c in df.columns 
    if "practiceAreas" in c
]


# juntar áreas
df_estados["areas"] = (
    df_estados[colunas_pratica]
    .fillna("")
    .astype(str)
    .apply(" ".join, axis=1)
)


# filtro
firmas_filtradas = df_estados[
    df_estados["areas"]
    .str.contains(
        "Personal Injury",
        case=False,
        na=False
    )
]


print(firmas_filtradas[
    [
        "name",
        "address/city",
        "address/region",
        "phone",
        "areas"
    ]
])


print(
    "Número de firmas:",
    len(firmas_filtradas)
)


firmas_filtradas.to_csv(
    "firmas_filtradas.csv",
    index=False
)