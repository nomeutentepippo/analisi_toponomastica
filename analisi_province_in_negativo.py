#!/usr/bin/env python
# coding: utf-8

# In[7]:


import osmnx as ox
import numpy as np
import pandas as pd
from rapidfuzz import process
import time
import geocoder
from geopy.exc import GeocoderTimedOut

import networkx as nx
import osmnx as ox
from pyrosm import OSM

import pickle

import geopandas as gpd
import folium 

import warnings
warnings.filterwarnings('ignore')


# In[8]:


def calculate_mean_coordinate(row):
    #m = MultiLineString()
    x, y = row['geometry'].centroid.x, row['geometry'].centroid.y
    return (y, x)

def carica_dati_comuni(geojson_file):
    #comuni https://github.com/openpolis/geojson-italy
    #geojson_file = r"data\limits_IT_municipalities.geojson"
    comuni = gpd.read_file(geojson_file)
    comuni = comuni[['name', 'prov_name', 'reg_name', 'geometry']]
    #calcolo area comuni
    for_area = comuni.copy()
    for_area = for_area.to_crs({'init': 'epsg:32633'})
    comuni['area'] = (for_area['geometry'].area/ 10**6).round(4)
    return comuni

def carica_dati_province(geojson_file):
    #province
    #geojson_file = r"data\limits_IT_provinces.geojson"
    province = gpd.read_file(geojson_file)
    province = province[['prov_name', 'reg_name', 'geometry']]
    #calcolo area comuni
    for_area = province.copy()
    for_area = for_area.to_crs({'init': 'epsg:32633'})
    province['area'] = (for_area['geometry'].area/ 10**6).round(4)
    return province

def get_aggregazione_comuni_con_filtro(searchfor):
    networks = ['network_NE', 'network_NO', 'network_C', 'network_NE', 'network_I', 'network_S']
    #searchfor = ['Pietro Nenni', 'Giorgio Amendola', 'Ugo La Malfa', "Alcide De Gasperi", 'Ugo la Malfa', "Alcide de Gasperi",
    #            "Meuccio Ruini", "Alessandro Casati"]

    total_comuni_grouped = pd.DataFrame(columns=["comune", 'prov_name', 'reg_name', "n_filtrate", "n_streets"])
    for network in networks:
        streets = pd.read_pickle("./"+network+".pkl") 
        streets = streets[['name','geometry', 'length']]
        streets['mean_coordinate'] = streets.apply(calculate_mean_coordinate, axis=1)
        streets['filter'] = streets['name'].str.contains('|'.join(searchfor), case=False)
        #faccio diventare mean_coordinate un geometry
        gdf_streets = gpd.GeoDataFrame(streets,  geometry=gpd.points_from_xy(streets.mean_coordinate.str[1], streets.mean_coordinate.str[0]))
        #metto in join con i comuni sulla base dell'appartenza geografica 
        sjoined_streets = gpd.sjoin(gdf_streets, comuni, predicate="within")
        #levo i duplicati delle strade dovute alle biforcazioni
        sjoined_streets = sjoined_streets.sort_values(['length'], ascending=False)
        sjoined_streets = sjoined_streets.drop_duplicates(subset=['name_left', 'name_right', 'prov_name','reg_name'], keep='first')
        #sjoined_streets
        comuni_grouped = sjoined_streets.groupby(['name_right', 'prov_name', 'reg_name'])['filter'].agg(['sum','count']).reset_index()
        comuni_grouped.columns = ["comune", 'prov_name', 'reg_name', "n_filtrate", "n_streets"]
        #comuni_grouped
        total_comuni_grouped = pd.concat([total_comuni_grouped, comuni_grouped]).reset_index(drop=True)
    return total_comuni_grouped

def calcola_metriche_comuni_in_gdp(total_comuni_grouped, comuni):
    vie_per_comune = comuni.merge(total_comuni_grouped, left_on=['name', 'prov_name', 'reg_name'], right_on=['comune', 'prov_name', 'reg_name'], how="left")
    #vie_per_comune['listings_count'] = vie_per_comune['listings_count'].fillna(0)
    # vie_per_comune
    gpd_geo_comuni = vie_per_comune[["name", "prov_name", "reg_name", "geometry", "area", "n_filtrate", "n_streets"]]
    gpd_geo_comuni["n_streets-over-area"] = (gpd_geo_comuni["n_streets"] / gpd_geo_comuni["area"]).astype(float).round(4)
    gpd_geo_comuni["n_filtrate-over-area"] = (gpd_geo_comuni["n_filtrate"] / gpd_geo_comuni["area"]).astype(float).round(4)
    gpd_geo_comuni["n_filtrate-over-n_streets"] = (gpd_geo_comuni["n_filtrate"]*100 / gpd_geo_comuni["n_streets"]).astype(float).round(4)
    
    gpd_geo_comuni.columns = ['Comune', 'Provincia', 'Regione', 'geometry', 'Superficie', 
                            'Vie di interesse', 'Vie totali', 'Vie per km^2', 
                            'Vie per di interesse km^2', 'Percentuale vie di interesse']
    return gpd_geo_comuni, vie_per_comune

def calcola_metriche_province_in_gdp(vie_per_comune, province):
    vie_per_provincia = vie_per_comune.groupby(['prov_name', 'reg_name'])['n_filtrate', 'n_streets'].apply(lambda x : x.sum()).reset_index()
    #vie_per_provincia
    gpd_geo_province = pd.merge(vie_per_provincia, province,  how='right', left_on=['prov_name','reg_name'], right_on = ['prov_name','reg_name'])
    gpd_geo_province = gpd_geo_province[["prov_name", "reg_name", "geometry", "area", "n_filtrate", "n_streets"]]
    gpd_geo_province["n_streets-over-area"] = (gpd_geo_province["n_streets"] / gpd_geo_province["area"]).astype(float).round(4)
    gpd_geo_province["n_filtrate-over-area"] = (gpd_geo_province["n_filtrate"] / gpd_geo_province["area"]).astype(float).round(4)
    gpd_geo_province["n_filtrate-over-n_streets"] = (gpd_geo_province["n_filtrate"]*100 / gpd_geo_province["n_streets"]).astype(float).round(4)
    gpd_geo_province.columns = ['Provincia', 'Regione', 'geometry', 'Superficie', 
                            'Vie di interesse', 'Vie totali', 'Vie per km^2', 
                            'Vie per di interesse km^2', 'Percentuale vie di interesse']
    gpd_geo_province = gpd.GeoDataFrame(gpd_geo_province)
    return gpd_geo_province, vie_per_provincia

def calcola_metriche_assenza_province_in_gdp(total_comuni_grouped, province):
    comuni_count_zeros = total_comuni_grouped.groupby(['prov_name', 'reg_name'])['n_filtrate'].apply(lambda x : (x == 0).sum()).reset_index().rename(columns={"n_filtrate": "count_zeros"})
    comuni_count_non_zeros = total_comuni_grouped.groupby(['prov_name', 'reg_name'])['n_filtrate'].apply(lambda x : (x != 0).sum()).reset_index().rename(columns={"n_filtrate": "count_non_zeros"})
    comuni_senza_vie_per_provincia = pd.merge(comuni_count_zeros, comuni_count_non_zeros, on=["prov_name", "reg_name"])
    gpd_geo_province = pd.merge(comuni_senza_vie_per_provincia, province,  how='right', left_on=['prov_name','reg_name'], right_on = ['prov_name','reg_name'])
    gpd_geo_province['count_comuni'] = gpd_geo_province['count_non_zeros'] + gpd_geo_province['count_zeros']
    gpd_geo_province['percentuale_comuni_con_vie_dedicate'] = (gpd_geo_province['count_non_zeros'] * 100 / gpd_geo_province['count_comuni']).astype(float).round(1)
    gpd_geo_province.drop(columns=['count_zeros'], inplace=True)
    gpd_geo_province = gpd_geo_province[['prov_name', 'reg_name', 'geometry', 'count_non_zeros', 'count_comuni', 'percentuale_comuni_con_vie_dedicate']]

    gpd_geo_province.columns = ['Provincia', 'Regione', 'geometry',  
                                'Comuni con vie dedicate', 'Numero comuni della provincia', 
                                'Percentuale comuni con via dedicata']
    gpd_geo_province = gpd.GeoDataFrame(gpd_geo_province)
    return gpd_geo_province, comuni_senza_vie_per_provincia

def ottieni_grafico(gpd_geo_province, descrizione, metrica, cmap="RdPu"):
    #colori gradazione intensità https://matplotlib.org/stable/tutorials/colors/colormaps.html
    m = gpd_geo_province.explore(metrica, cmap=cmap,
                                 vmin = 0, vmax = 100, 
                                 tiles="CartoDB positron",
                                 width = 900, height = 800,
                                 zoom_start=6,
                                )

    # https://stackoverflow.com/questions/74267926/folium-map-title-disappearing-when-activating-fullscreen-mode
    from branca.element import Template, MacroElement
    template = """
    {% macro html(this, kwargs) %}

    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Densità Toponomastica</title>
      <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">
    </head>

    <body>
    <div id='maplegend' class='maplegend' 
        style='position: absolute; z-index:9999; border:3px solid grey; background-color:rgba(255, 255, 255, 0.7);
        border-radius:6px; padding: 8px; font-size:18px; bottom: 3%; left: 1%; width: 25%'>

    <div class='title-box'>
    <div class='main-title'>Densità toponomastica provinciale</div>
    <div class='subtitle'>"""+descrizione+"""</div>

    <style type='text/css'>
      .title-box .main-title {
        text-align: left;
        margin-bottom: 8px;
        font-weight: bold;
        font-size: 100%;
        }
      .title-box .subtitle {
        text-align: left;
        margin-bottom: 8px;
        font-weight: normal;
        font-size: 75%;
        }
    </style>
    </body>

    {% endmacro %}"""

    macro = MacroElement()
    macro._template = Template(template)
    m.get_root().add_child(macro)
    return m



# In[9]:


'''
from html2image import Html2Image
hti = Html2Image()
hti.screenshot(
    html_file='province_resistenza.html', save_as='province_resistenza.png',
    size=(1920, 1080)
)
'''


# In[10]:


geojson_comuni = r"data\limits_IT_municipalities.geojson"
geojson_province = r"data\limits_IT_provinces.geojson"

comuni = carica_dati_comuni(geojson_comuni)
province = carica_dati_province(geojson_province)


# In[11]:


#https://rudighedini.wordpress.com/2013/09/16/toponomastica-uno-studio-sui-100-nomi-piu-usati-per-denominare-le-strade-italiane/
vie_da_cercare = [
                  ["Giuseppe Garibaldi", "Garibaldi"], 
                  ["Giuseppe Mazzini", "Mazzini"], 
                  "Guglielmo Marconi", "Roma", 
                  ['camillo benso conte di cavour','cavour','camillo benso di cavour', 'camillo cavour', 'camillo benso cavour'], 
                  ['giacomo matteotti', 'matteotti'], 
                  ['giuseppe verdi', 'verdi'],
                  ['dante alighieri', 'dante'], 
                  "Giovanni Falcone", 
                  "Aldo Moro", "Antonio Gramsci", "Alcide De Gasperi", "Cristoforo Colombo", "Alessandro Volta", "Enrico Fermi",
                  "Galileo Galilei", 'Armando Diaz', 'Enrico Berlinguer',
                  ["Quattro Novembre", "IV Novembre", "4 Novembre"], 
                  ["Venticinque Aprile", "XXV Aprile", "25 Aprile"], 
                  ["Venti Settembre", "XX Settembre", "20 Settembre"],
                  "Piave", "Cesare Battisti", "Vittorio Veneto", ["Monte Grappa", "Montegrappa"], 
                  ["John Fitzgerald Kennedy", "Kennedy"],
                  ['san francesco', "san francesco d'assisi"]
                 ]
for via in vie_da_cercare:
    print(via)
    if isinstance(via, list):
        descrizione = via[0]
        searchfor = via
    else:
        descrizione = via
        searchfor = [via]
    total_comuni_grouped = get_aggregazione_comuni_con_filtro(searchfor)
    gpd_geo_province, comuni_senza_vie_per_provincia = calcola_metriche_assenza_province_in_gdp(total_comuni_grouped, province)
    metrica = 'Percentuale comuni con via dedicata'
    m = ottieni_grafico(gpd_geo_province, descrizione, metrica, cmap='PuBu')
    m.save('./output/negativo_province_'+descrizione.replace(" ", "")+'.html')


# In[ ]:




