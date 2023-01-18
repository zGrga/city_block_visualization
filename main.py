import streamlit as st
import pandas as pd
import folium
import numpy as np
from itertools import permutations
import os
import json
from shapely.geometry.polygon import Polygon
from shapely.geometry import shape, Point

from streamlit_folium import st_folium, folium_static
st.set_page_config(layout="wide")

st.title('Select the best city block')
st.write('The main purpose of this visualization' +
    ' is to create selector which can help you in selecting the best city block for you.' + 
    ' The main idea is to create a score for every city block. The score is basically a grade for each of the segments.')


@st.cache
def prepare_data():
    data = pd.read_csv('data.csv')
    ind = pd.unique(data.loc[:, 'class']).tolist()
    colors = ['red', 'green', 'blue', 'yellow', 'purple']
    return data, ind, colors

def prepare_city_blocks():
    to_load = {
            'type': 'FeatureCollection',
            'features': []
        }
    for i in os.listdir('./blocks'):
        with open(os.path.join('./blocks', i), 'r') as file:
            tmp = {
                'type': 'Feature',
                'id': i.split('.')[0],
                'properties': {
                    'name': f' {i.split(".")[0]}'
                },
                'geometry': json.load(file)
            }
            to_load['features'].append(tmp)

    return to_load

@st.cache
def prepare_poligons():
    poligons = dict()
    for i in os.listdir('./blocks'):
        with open(os.path.join('./blocks', i), 'r') as file:
            poligons[i.split('.')[0]] = shape(json.load(file))

    return poligons



if 'city_blocks' not in st.session_state:
    st.session_state.city_blocks = prepare_city_blocks()

if 'changed' not in st.session_state:
    st.session_state.changed = False

if 'poligons' not in st.session_state:
    st.session_state.poligons = prepare_poligons()


st.session_state.data, st.session_state.ind, st.session_state.colors =  prepare_data()


to_add_group = []

with st.form('forma'):
    st.header('Options')
    st.write('Here you can select a grade on each subject to determine which objects are the most important to you.')
    st.write('The score will be calculated by multiplying the number of objects in given city block by the selected grade.')
    
    l = len(pd.unique(st.session_state.data.loc[:, 'class']))
    sl = st.columns(l)
    sliders = dict()
    for index, i in enumerate(pd.unique(st.session_state.data.loc[:, 'class'])):
        with sl[index]:
            sliders[i] = st.slider(f'{i}', 0, 5)

    button = st.form_submit_button('Submit')
    if button:
        poligons = st.session_state.poligons

        total_score = {
            'name': [],
            'value': []
        }
        for i in poligons:
            total_score['name'].append(i)
            total_score['value'].append(0)

            for j in sliders:
                tmp = st.session_state.data.loc[st.session_state.data['class'] == j, :]
                total_score['value'][-1] += tmp.apply(lambda row: poligons[i].contains(Point(row['X'], row['Y'])), axis=1).sum() * sliders[j]

        scores = pd.DataFrame.from_dict(total_score)

        st.session_state.m2 = folium.Map(location=[45.8167, 15.9833], zoom_start=10, tiles='cartodbpositron')
        c = folium.Choropleth(geo_data=st.session_state.city_blocks,
                        data=scores,
                        columns=['name', 'value'],
                        key_on='feature.id',
                        legend_name='General score',
                        highlight=True).add_to(st.session_state.m2)


        for s in c.geojson.data['features']:
            s['properties']['value'] = int(scores.loc[scores['name'] == s['id'], 'value'].values[0])
        
        folium.GeoJsonTooltip(['name', 'value']).add_to(c.geojson)
        st.session_state.changed = True
        st.session_state.scores = scores


col1, col2 = st.columns(2)
with col1:
        # Mapa 1
    st.header('Map')

    st.write('On this map you can select the layers that are important to you and see their positions.')

    with st.spinner('Creating a map'):
        m = folium.Map(location=[45.8167, 15.9833], zoom_start=10, tiles='cartodbpositron')

        c = folium.Choropleth(geo_data=st.session_state.city_blocks,
                                key_on='feature.id',
                                legend_name='General score',
                                highlight=True,
                                fill_opacity=0.05,
                                fill_color='red').add_to(m)
        folium.GeoJsonTooltip(['name'], localize=True).add_to(c.geojson)

        for i in pd.unique(st.session_state.data.loc[:, 'class']):
            to_add_group.append(folium.FeatureGroup(i, show=False))
            tmp = st.session_state.data.loc[st.session_state.data['class'] == i, :]

            
            tmp.apply(lambda row: folium.CircleMarker([row['Y'], row['X']],
                                                popup=row['naziv'],
                                                radius=5,
                                                fill=True,
                                                fill_opacity = 0.6,
                                                color = st.session_state.colors[st.session_state.ind.index(row['class'])],
                                                tooltip=row['naziv'],
                                                fill_color=st.session_state.colors[st.session_state.ind.index(row['class'])]).add_to(to_add_group[-1]), axis=1)

        for i in to_add_group:
            i.add_to(m)
        
        folium.LayerControl().add_to(m)

        st_data = folium_static(m, width=650)

with col2:
    st.header('City blocks')

    st.write('On this map the scores of each city block will be visualized.')

    if not st.session_state.changed:
        st.session_state.m2 = folium.Map(location=[45.8167, 15.9833], zoom_start=10, tiles='cartodbpositron')
        c = folium.Choropleth(geo_data=st.session_state.city_blocks,
                                key_on='feature.id',
                                legend_name='General score',
                                highlight=True).add_to(st.session_state.m2)
        
        folium.GeoJsonTooltip(['name']).add_to(c.geojson)
    else:
        st.session_state.changed = False

    st_data_2 = folium_static(st.session_state.m2, width=650)


if 'scores' in st.session_state:
    st.title('Distribution of score')
    st.bar_chart(st.session_state.scores, x='name', y='value')