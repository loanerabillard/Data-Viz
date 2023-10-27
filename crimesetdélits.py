import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import pydeck as pdk
import folium
import base64
from streamlit_folium import folium_static
from streamlit_folium import st_folium
import plotly.express as px
import seaborn as sns
import altair as alt

from import_data import(
    géo_load,
    load_data
)


def display_unique_classes(df):
    valeurs_uniques_classe = df['classe'].unique()
    st.write(valeurs_uniques_classe)


def display_france_crime_density_map(df_gouv, shapefile_path):
    st.markdown('### Densité de la criminalité sur la carte de la France')
    crime_by_department = df_gouv.groupby('Code.département').agg({'faits': 'sum'}).reset_index()
    crime_by_department['Code.département'] = crime_by_department['Code.département'].str.lstrip('0')
    gdf_france_departments = gpd.read_file(shapefile_path)
    merged = gdf_france_departments.set_index('code_insee').join(crime_by_department.set_index('Code.département'))
    metropolitan_departments = merged[~merged.index.str.startswith(('971', '972', '973', '974', '975', '976'))]
    fig, ax = plt.subplots(1, figsize=(20, 20))
    y_min = metropolitan_departments.total_bounds[1] + 1  
    y_max = metropolitan_departments.total_bounds[3] 
    ax.set_xlim(metropolitan_departments.total_bounds[0] + 1, metropolitan_departments.total_bounds[2] - 1)
    ax.set_ylim(y_min, y_max)  
    metropolitan_departments.boundary.plot(ax=ax, linewidth=1, color='black')
    metropolitan_departments.plot(column='faits', ax=ax, legend=True, cmap='OrRd', linewidth=0.8, edgecolor='0.8', legend_kwds={'label': "Densité de crime par département"})

    for x, y, label in zip(metropolitan_departments.geometry.centroid.x, metropolitan_departments.geometry.centroid.y, metropolitan_departments.index):
        ax.text(x, y, label, fontsize=12, ha='center', va='center')

    plt.axis('off')

    st.pyplot(fig)






def display_crimes_by_year_line_chart(df, selected_infractions):
    st.markdown('## Évolution du nombre total de crimes par année')

    filtered_data = df[df['classe'].isin(selected_infractions)]

    if not filtered_data.empty:
        data_by_year = filtered_data.groupby(['annee', 'classe'])['faits'].sum().unstack()
        data_by_year.index = ["20{:02d}".format(year) for year in data_by_year.index]
        st.line_chart(data_by_year, use_container_width=True)
    else:
        st.write("Aucune donnée disponible pour les infractions sélectionnées.")



def init_interactive_map():
    tiles = "CartoDB dark_matter"
    location = [46.603354, 3]
    zoom_start = 6

    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=tiles,
        scrollWheelZoom=False,
        zoom_control=False
    )
    return m 

def create_choropleth (data, géo) :
    return folium.Choropleth(
        geo_data=géo,
        name='choropleth',
        data=data,
        columns=['Code.département', 'faits'],  
        key_on='feature.properties.code',  
        fill_color='YlGn',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Crimes by Department'
    )



def render_streamlit_map(carte, cle):
    """Affiche la visualisation de la carte dans l'application Streamlit."""
    st.write("Cliquez sur une région de la carte pour la sélectionner.")
    st_carte = st_folium(carte, key=cle, use_container_width=True, zoom=5)
    if "dep" not in st.session_state:
        st.session_state["dep"] = "00"

    if st_carte["last_active_drawing"]:
        st.session_state["dep"] = st_carte["last_active_drawing"]["properties"]["code"]
        st.write(f"Département sélectionné : {st.session_state['dep']}")




def generate_pie_chart_by_year_and_department(data, selected_year, selected_department):
    filtered_data = data[(data['annee'] == selected_year) & (data['Code.département'] == selected_department)]

    class_counts = filtered_data.groupby('classe')['faits'].sum()
    class_names = class_counts.index  
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']  

    fig, ax = plt.subplots(figsize=(12, 8))
    wedges, texts, autotexts = ax.pie(class_counts, autopct='%1.1f%%', startangle=90, colors=colors)

    legend_labels = [f'{name}: {count}' for name, count in zip(class_names, class_counts)]
    ax.legend(wedges, legend_labels, title='Classes de crime', loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))

    ax.axis('equal') 
    ax.set_title(f"Répartition des faits par classe pour le département {selected_department} en {selected_year}", fontsize=24)

    st.pyplot(fig)



def generate_bar_chart(data, selected_department, selected_year):
    filtered_data = data[data['Code.département'] == selected_department]

    if not filtered_data.empty:
        filtered_data = filtered_data[filtered_data['annee'] == selected_year]

        st.bar_chart(filtered_data[['classe', 'faits']].set_index('classe'))

    else:
        st.warning("Aucune donnée correspondant au département sélectionné.")






def display_crimes_by_department_altair_chart(df, selected_infractions):
    st.markdown('## Répartition des types de crimes par année et département')

    filtered_data = df[(df['classe'].isin(selected_infractions)) ]

    if not selected_infractions:
        st.warning("Sélectionnez au moins une infractions.")
    else:
        if not filtered_data.empty:

            filtered_data['annee'] = "20" + filtered_data['annee'].astype(str).str[-2:]

            chart = alt.Chart(filtered_data).mark_bar().encode(
                x=alt.X('annee:N', title='Année'),
                y=alt.Y('sum(faits):Q', title='Total des Faits'),
                color=alt.Color('classe:N', title='Classe de crime')
            ).properties(
                width=800,
                height=400
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            )

            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Aucune donnée disponible pour les infractions et les départements sélectionnés.")





def generate_scatter_plot(data, selected_classes, selected_years):
    st.markdown("## Relation entre le nombre de faits et le taux pour mille par classe de crime\n")

    filtered_data = data[(data['classe'].isin(selected_classes)) & 
                         (data['annee'].isin(selected_years))]
    filtered_data = filtered_data.dropna(subset=['Code.département'])


    if not filtered_data.empty:
        chart = alt.Chart(filtered_data).mark_circle(size=60).encode(
            x=alt.X('faits', title='Nombre de Faits'),
            y=alt.Y('tauxpourmille', title='Taux pour Mille'),
            color=alt.Color('classe:N', title='Classe de Crime'),
            tooltip=["classe", "annee"],
        ).properties(
            width=700,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Aucune donnée disponible pour les sélections effectuées.")





def calculate_department_dangerousness(data, department_code):
    department_data = data[data['Code.département'] == department_code]

    if not department_data.empty:
        dangerousness_data = department_data.groupby('classe')['faits'].sum().reset_index()
        dangerousness_data = dangerousness_data.rename(columns={'faits': 'Nombre de Faits'})

        dangerousness_data = dangerousness_data.sort_values(by='Nombre de Faits', ascending=False)

        return dangerousness_data
    else:
        return pd.DataFrame()


def create_dangerousness_bar_chart(data, department_code):
    if not data.empty:
        chart = alt.Chart(data).mark_bar().encode(
            x=alt.X('classe:N', title='Classe de Crime', sort='-y'),
            y=alt.Y('Nombre de Faits:Q', title='Nombre de Faits'),
            color=alt.Color('classe:N', title='Classe de Crime'),
        ).properties(
            width=700,
            height=400
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        )

        return chart
    else:
        st.warning("Aucune donnée disponible pour ce département.")








def main():

    df = load_data()

    st.sidebar.title("Délinquance en France")

    selected_option = st.sidebar.radio("Sélectionnez une section :", ("Accueil", "Représentation Temporelle", "Représentation Territorial"))

    
    # Lien vers votre profil LinkedIn avec une icône
    linkedin_url = "www.linkedin.com/in/loane-rabillard-02517a1b7"
    linkedin_icon = '<i class="fab fa-linkedin"></i>'
    st.sidebar.markdown(f'<a href="{linkedin_url}" target="_blank" rel="noopener noreferrer">{linkedin_icon} LinkedIn</a>', unsafe_allow_html=True)

    # Lien vers votre profil GitHub avec une icône
    github_url = "https://github.com/loanerabillard/Data-Visualization.git"
    github_icon = '<i class="fab fa-github"></i>'
    st.sidebar.markdown(f'<a href="{github_url}" target="_blank" rel="noopener noreferrer">{github_icon} GitHub</a>', unsafe_allow_html=True)

    # Ajout d'un espace pour créer un effet de pied de page
    st.sidebar.text(" ")
    st.sidebar.text(" ")

    if selected_option == "Représentation Temporelle":

        st.title("Représentation Temporelle de la délinquance en France\n")

        selected_infractions = st.multiselect('Sélectionnez une ou plusieurs infractions :', df['classe'].unique())

        if selected_infractions:
            display_crimes_by_year_line_chart(df, selected_infractions)
            display_crimes_by_department_altair_chart(df, selected_infractions)
        
        df['annee'] = pd.to_datetime(df['annee'], format='%y').dt.strftime('20%y')

        selected_years = st.multiselect('Sélectionnez une année :', df['annee'].unique())

        if selected_years:
            generate_scatter_plot(df, selected_infractions, selected_years)
        else:
            st.warning("Sélectionnez au moins une classe de crime, un département et une année pour afficher le graphique.")    


    elif selected_option == "Représentation Territorial":
        st.title("Carte Intéractive de la France")

        geo_data = géo_load()

        st.markdown("### Cette carte affiche les crimes par rapport aux departments.")
        m = init_interactive_map()
        create_choropleth(df, geo_data).add_to(m)
        render_streamlit_map(m, "map")
        st.write(st.session_state['dep'])

        st.title("Répartition des Faits par Classe")

        df['annee'] = pd.to_datetime(df['annee'], format='%y').dt.strftime('20%y')

        selected_year = st.selectbox("Sélectionnez une année", df['annee'].unique())

        selected_department = st.session_state['dep']

        if selected_year and selected_department:
            generate_pie_chart_by_year_and_department(df, selected_year, selected_department)

        generate_bar_chart(df, st.session_state['dep'], selected_year)
        

        if selected_department:
            st.subheader(f"Dangereusité du département {st.session_state['dep']}")
            
            dangerousness_data = calculate_department_dangerousness(df, st.session_state['dep'])
            
            chart = create_dangerousness_bar_chart(dangerousness_data, st.session_state['dep'])

            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Sélectionnez un département pour afficher la dangereusité par classe.")


    else:  # Default to "Accueil" as the main page
        st.title("Bases statistiques départementale de la délinquance enregistrée par la police et la gendarmerie nationales\n")
        st.markdown("### Tableau de données (DataFrame)")
        st.write("\n",df.head())
        st.markdown("### Liste des infractions")
        display_unique_classes(df)

        shapefile_path = "departements-20180101.shp"
        display_france_crime_density_map(df, shapefile_path)

   

    

if __name__ == '__main__':
    main()




