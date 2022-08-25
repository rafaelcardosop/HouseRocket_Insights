import pandas as pd
import streamlit as st
import numpy as np
import geopandas
import folium
from streamlit_folium import folium_static
from folium.plugins   import MarkerCluster
import plotly.express as px
from datetime import datetime
import os

#Para ampliar a visualização no streamlit
st.set_page_config (layout='wide')

#Para carregar os dados no cache, onde irá consumir dali, da memoria RAM
@st.cache (allow_output_mutation=True)

#Função para ler os dados
def get_data (path):
    data = pd.read_csv (path)
    data['date'] = pd.to_datetime(data['date']).dt.strftime ('%Y-%m-%d')

    return data

@st.cache( allow_output_mutation=True )
def get_geofile( url ):
    geofile = geopandas.read_file( url )

    return geofile

def set_feature (data):
    data['price_m2'] = data['price'] / data ['sqft_lot']

    return data

def overview_data(data):
    # data overview - filters
    f_attributes = st.sidebar.multiselect('Enter columns', data.columns)
    f_zipcode = st.sidebar.multiselect('Enter zipcode', data['zipcode'].unique())

    # conversions
    data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y-%m-%d')
    st.title('Data Overview')

    # data overview - filters conditionals
    if (f_zipcode != []) & (f_attributes != []):
        data_1 = data.loc[data['zipcode'].isin(f_zipcode), :]
        data = data.loc[data['zipcode'].isin(f_zipcode), f_attributes]
    elif (f_zipcode == []) & (f_attributes != []):
        data_1 = data.copy()
        data = data.loc[:, f_attributes]
    elif (f_zipcode != []) & (f_attributes == []):
        data_1 = data.loc[data['zipcode'].isin(f_zipcode), :]
        data = data.loc[data['zipcode'].isin(f_zipcode), :]
    else:
        data_1 = data.copy()
        data = data.copy()

    #Mostrando a tabela
    st.write (data)

    #Colocando as tabelas lado a lado
    c1, c2 = st.columns ((1, 1 ))
    # Average metrics = criando as variaveis com as metricas.

    df1 = data_1 [['id', 'zipcode']].groupby ('zipcode').count (). reset_index()
    df2 = data_1 [['price','zipcode']]. groupby ('zipcode').mean ().reset_index()
    df3 = data_1 [['sqft_living', 'zipcode']].groupby ('zipcode').mean().reset_index()
    df4 = data_1 [['price_m2', 'zipcode']].groupby ('zipcode').mean().reset_index()

    #merge = unindo as variaveis para mostrar em um dataset só
    m1 = pd.merge (df1, df2, on = 'zipcode', how='inner')
    m2 = pd.merge (m1,df3, on ='zipcode', how='inner')
    df = pd.merge (m2,df4, on ='zipcode', how='inner')

    # mudando o nome das colunas
    df.columns = ['ZIPCODE','TOTAL_HOUSES','PRICE','SQFT_LIVING','PRICE/M2']

    c1.header ('Average Values')
    # Mostrando a tabela e mudando o tamanho.
    c1.dataframe (df, height=800)

    #Statistic descriptive

    #Selecionando apenas o que é 'int64' e 'float64'
    num_attributes = data.select_dtypes (include=['int64','float64'])

    media = pd.DataFrame (num_attributes.apply (np.mean ) )
    mediana = pd.DataFrame (num_attributes.apply (np.median ) )
    std = pd.DataFrame (num_attributes.apply (np.std ) )

    max_ = pd.DataFrame (num_attributes.apply (np.max))
    min_ = pd.DataFrame (num_attributes.apply (np.min))

    df1 = pd.concat ([max_, min_, media, mediana, std], axis=1).reset_index()

    df1.columns = ['attributes', 'max', 'min', 'mean', 'median', 'std']

    c2.header ('Descriptive Analysis')
    c2.dataframe (df1,height=800)

    return None

def portfolio_density (data, geofile):  
    st.title( 'Region Overview' )

    c1, c2 = st.columns( ( 1, 1 ) )
    c1.header( 'Portfolio Density' )


    df = data.copy()

    # Base Map - Folium
    density_map = folium.Map( location=[data['lat'].mean(), 
                              data['long'].mean() ],
                              default_zoom_start=15 ) 

    marker_cluster = MarkerCluster().add_to( density_map )
    for name, row in df.iterrows():
        folium.Marker( [row['lat'], row['long'] ], 
            popup='Sold R${0} on: {1}. Features: {2} sqft, {3} bedrooms, {4} bathrooms, year built: {5}'.format(
                                         row['price'],
                                         row['date'],
                                         row['sqft_living'],
                                         row['bedrooms'],
                                         row['bathrooms'],
                                         row['yr_built'] ) ).add_to( marker_cluster )

    #Para plotar o mapa
    with c1:
        folium_static( density_map )


    # Region Price Map
    c2.header( 'Price Density' )

    df = data[['price', 'zipcode']].groupby( 'zipcode' ).mean().reset_index()
    df.columns = ['ZIP', 'PRICE']

    #df = df.sample( 10 )

    #Serve para pegar apenas as informações do geofile existentes dentro do meu dataset
    geofile = geofile[geofile['ZIP'].isin( df['ZIP'].tolist() )]

    region_price_map = folium.Map( location=[data['lat'].mean(), 
                                   data['long'].mean() ],
                                   default_zoom_start=15 ) 


    region_price_map.choropleth( data = df,
                                 geo_data = geofile,
                                 columns=['ZIP', 'PRICE'],
                                 key_on='feature.properties.ZIP',
                                 fill_color='YlOrRd',
                                 fill_opacity = 0.7,
                                 line_opacity = 0.2,
                                 legend_name='AVG PRICE' )

    with c2:
        folium_static( region_price_map )

        return None

def commercial_distribution (data):
    st.sidebar.title ('Commercial Options')

    #Adicionando titulo na sessão.
    st.title ('Commercial Attributes')

    #---------Average Price per Year - Variação media de preço anual

    data['date'] = pd.to_datetime(data['date']).dt.strftime ('%Y-%m-%d')

    #Filters
    min_year_built = int (data ['yr_built'].min() )
    max_year_built = int (data ['yr_built'].max() )

    #Subtitulo do filtro
    st.sidebar.subheader ('Select Max Year Built')

    f_year_built = st.sidebar.slider ('Year Built', min_year_built,
                                                    max_year_built, 
                                                    min_year_built) # <-- Default 

    #Nome do grafico
    st.header ('Average Price per Year Built') # Preço médio por ano construido

    # Data selection
    df = data.loc[data['yr_built'] < f_year_built]
    df = df [['yr_built','price']].groupby ('yr_built').mean().reset_index()


    #Plot
    fig = px.line (df, x='yr_built', y= 'price')
    st.plotly_chart(fig, use_container_width=True)

    #---------Average Price per Day - Variação media de preço por dia

    st.header ('Average Price per Day')
    st.sidebar.subheader ('Selec Max Date')

    #Filters
    min_date = datetime.strptime (data ['date'].min(), '%Y-%m-%d')
    max_date = datetime.strptime (data ['date'].max(), '%Y-%m-%d')

    f_date = st.sidebar.slider ('Date', min_date,
                                        max_date,
                                        min_date) # <-- Default 

    #Data Filtering

    #Convertendo os dados 'date' para data, pois estavam como STR.
    data['date'] = pd.to_datetime (data['date'])

    df = data.loc[data ['date'] < f_date]
    df = df [['date','price']].groupby ('date').mean().reset_index()


    #Plot
    fig = px.line (df, x='date', y= 'price')
    st.plotly_chart(fig, use_container_width=True)


    # ------------- Histograma
    st.header ('Price Distribution')
    st.sidebar.subheader ('Select Max Price')

    #Filter
    min_price = int ( data['price'].min())
    max_price = int ( data['price'].max())
    avg_price = int ( data['price'].mean())

    f_price = st.sidebar.slider ('Price', min_price, max_price, avg_price)

    df = data.loc [data ['price'] < f_price ]

    #data plot
    fig = px.histogram(df, x='price', nbins = 50 )
    st.plotly_chart (fig, use_container_width= True)

    return None

def atrributes_distribution (data):
    st.sidebar.title ('Attributes Options')
    st.title ('House Attributes')

    #Filters
    f_bedrooms = st.sidebar.selectbox ( 'Max Number of Bedrooms', data[ 'bedrooms'].sort_values().unique())

    f_bathrooms = st.sidebar.selectbox ('Max Number of Bathrooms', data['bathrooms'].sort_values().unique())

    f_floors = st.sidebar.selectbox ('Max Number of Floors', data['floors'].sort_values().unique())

    f_waterview = st.sidebar.checkbox ('Only Houses With Water View')

    c1 , c2 = st.columns (2)

    # House per Bedrooms
    c1.header ('Houses per bedrooms')
    df = data [ data['bedrooms'] < f_bedrooms]
    fig = px.histogram (df, x = 'bedrooms', nbins=19)
    c1.plotly_chart (fig, use_container_width=True)

    # House per Bathrooms
    c2.header ('Houses per bathrooms')
    df = data [ data['bathrooms'] < f_bathrooms]
    fig = px.histogram (df, x = 'bathrooms', nbins=19)
    c2.plotly_chart (fig, use_container_width=True)


    c1 , c2 = st.columns (2)
    # House per Floors
    c1.header ('Houses per floor')
    df = data [ data['floors'] < f_floors]
    fig = px.histogram (df, x = 'floors', nbins=19)
    c1.plotly_chart (fig, use_container_width=True)

    # House per Water view
    if f_waterview:
        df = data[data['waterfront']== 1]

    else:
        df = data.copy()

    fig = px.histogram (df, x = 'waterfront', nbins=10)
    c2.plotly_chart (fig, use_container_width=True)

    return None


if __name__ == '__main__':
    #ETL
    #Extraction
    path = 'kc_house_data.csv'
    data = get_data (path)

    if os.path.isfile('./Zip_Codes.geojson'):
        geo_data = get_geofile ('./Zip_Codes.geojson')

    else:
        st.title('GEO Data File is missing.')

    #Transformation
    data = set_feature (data)
    
    overview_data (data)

    portfolio_density (data, geo_data)

    commercial_distribution (data)

    atrributes_distribution (data)
