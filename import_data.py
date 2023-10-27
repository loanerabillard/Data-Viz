import streamlit as st
import pandas as pd
import geopandas as gpd


@st.cache
def load_data():
    df = pd.read_csv('donnee-dep-data.gouv-2022-geographie2023-produit-le2023-07-17.csv', delimiter=';')
    return df

@st.cache
def géo_load():
    departements = gpd.read_file("departements.geojson")
    return departements