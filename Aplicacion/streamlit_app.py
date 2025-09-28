import os
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
import streamlit as st
from rasterstats import zonal_stats
from rasterio.windows import Window

st.set_page_config(page_title='Tmin Perú — Dashboard', layout='wide')
st.title('🇵🇪 Tmin Perú — Dashboard de Zonal Stats')
st.caption('App generada desde el notebook v4 (descarga datos + cache_resource)')

DATA = Path(__file__).resolve().parents[1] / 'data'
OUTPUTS = Path(__file__).resolve().parents[1] / 'outputs'
OUTPUTS.mkdir(exist_ok=True, parents=True)
os.environ['SHAPE_RESTORE_SHX'] = 'YES'

def strip_accents_upper(s):
    try:
        from unidecode import unidecode
        return unidecode(str(s)).upper() if s is not None else s
    except Exception:
        import unicodedata
        if s is None: return s
        s = unicodedata.normalize('NFKD', str(s))
        s = ''.join(c for c in s if not unicodedata.combining(c))
        return s.upper()

def normalize_keys_upper(gdf):
    return {c.upper().strip(): c for c in gdf.columns}

def build_or_find_ubigeo(gdf):
    cmap = normalize_keys_upper(gdf)
    for cu in ['UBIGEO','UBIGEO_DIST','UBIGEO_D','UBI_DIST','CODUBIGEO','COD_UBIGEO','ID_UBIGEO','CODIGO_UBIGEO','UBIGEO6','UBIGEO_6','CODDIST','ID_DIST','COD_DIST','COD_DISTRITO']:
        if cu in cmap:
            col = cmap[cu]
            vals = pd.to_numeric(gdf[col], errors='coerce').fillna(-1).astype(int).astype(str)
            return vals.str.zfill(6)
    dd = next((cmap[x] for x in ['CCDD','CODDPTO','COD_DEPA','DEPARTAMENTO_ID','ID_DPTO','DPTO'] if x in cmap), None)
    pp = next((cmap[x] for x in ['CCPP','CODPROV','COD_PROV','PROVINCIA_ID','ID_PROV','PROV'] if x in cmap), None)
    di = next((cmap[x] for x in ['CCDI','CODDIST','COD_DIST','DISTRITO_ID','ID_DIST','DIST'] if x in cmap), None)
    if dd and pp and di:
        z = (gdf[dd].astype(str).str.extract(r'(\d+)', expand=False).fillna('').str.zfill(2) +
             gdf[pp].astype(str).str.extract(r'(\d+)', expand=False).fillna('').str.zfill(2) +
             gdf[di].astype(str).str.extract(r'(\d+)', expand=False).fillna('').str.zfill(2))
        return z
    for c in gdf.columns:
        s = gdf[c].astype(str).str.strip()
        if s.str.fullmatch(r'\d{6}').mean() > 0.8:
            return s
    raise ValueError('No se pudo detectar/crear UBIGEO de 6 dígitos.')

def guess_scale_factor(arr):
    if arr.size == 0 or np.all(~np.isfinite(arr)):
        return 1.0
    vmax = float(np.nanmax(np.abs(arr)))
    return 0.1 if 80 < vmax < 1000 else 1.0

@st.cache_resource(show_spinner=False)
def open_raster(path):
    src = rasterio.open(path)
    tags = src.tags() or {}
    sf = None
    for k in ['SCALE','scale_factor','Scale','SCALE_FACTOR']:
        if k in tags:
            try:
                sf = float(tags[k]); break
            except Exception:
                pass
    if sf is None:
        w = Window(0,0, min(200, src.width), min(200, src.height))
        sample = src.read(1, window=w, masked=True)
        sf = guess_scale_factor(np.asarray(sample))
    return src, sf

@st.cache_resource(show_spinner=False)
def load_vector(path):
    gdf = gpd.read_file(path)
    gdf = gdf.set_crs('EPSG:4326', allow_override=True) if gdf.crs is None else gdf.to_crs('EPSG:4326')
    gdf['UBIGEO_OK'] = build_or_find_ubigeo(gdf)
    cmap = normalize_keys_upper(gdf)
    name_col = next((cmap[x] for x in ['NOMBDIST','NOMB_DIST','NOMBRE','DIST_NAME','DISTRITO','NOM_DIST','NAME'] if x in cmap), None)
    gdf['NOMBRE_OK'] = (gdf[name_col] if name_col else gdf['UBIGEO_OK']).astype(str)
    gdf['NOMBRE_OK'] = gdf['NOMBRE_OK'].astype(str).str.strip().apply(strip_accents_upper)
    gdf['UBIGEO_OK'] = gdf['UBIGEO_OK'].astype(str).str.strip()
    return gdf

# Sidebar — inputs
st.sidebar.header('Datos')
vector_name = st.sidebar.text_input('Shapefile (.shp)', 'DISTRITOS.shp')
raster_name = st.sidebar.text_input('Raster GeoTIFF', 'tmin_raster.tif')
start_year = st.sidebar.number_input('Año Banda 1', 1900, 2100, 2020)

vector_path = DATA / vector_name
raster_path = DATA / raster_name

if not vector_path.exists() or not raster_path.exists():
    st.error('No encuentro datos en ./data. Ejecuta la celda 0 del notebook para descargarlos.'); st.stop()

gdf = load_vector(vector_path)
src, sf = open_raster(raster_path)
st.sidebar.success(f'Vector OK ({len(gdf)}) · Raster OK ({src.count} banda/s) · scale={sf}')

band = st.sidebar.slider('Banda', 1, src.count, 1)
year = int(start_year + (band-1))

@st.cache_data(show_spinner=True)
def compute_zonal(band, year):
    zs = zonal_stats(
        vectors=gdf, raster=str(raster_path), band=band,
        stats=['count','mean','min','max','std','percentile_10','percentile_90','percentile_5'],
        all_touched=False, nodata=None, geojson_out=False
    )
    df = pd.DataFrame(zs)
    if sf and sf != 1.0:
        for c in ['mean','min','max','std','percentile_10','percentile_90','percentile_5']:
            if c in df.columns: df[c] = df[c]*sf
    df['UBIGEO_OK'] = gdf['UBIGEO_OK'].values
    df['NOMBRE_OK'] = gdf['NOMBRE_OK'].values
    df['year'] = year
    return df

df = compute_zonal(band, year)
st.subheader(f'Resultados — Año {year} (Banda {band})')

# KPIs
c1,c2,c3,c4 = st.columns(4)
c1.metric('Distritos', f'{df.shape[0]:,}')
c2.metric('Tmin media (°C)', f"{df['mean'].mean():.2f}")
c3.metric('Tmin p10 (°C)', f"{df['percentile_10'].mean():.2f}")
c4.metric('Tmin p90 (°C)', f"{df['percentile_90'].mean():.2f}")

st.info('Las estadísticas zonales promedian los valores del ráster dentro de cada polígono (distrito). Métricas p10/p90 describen caudas frías/cálidas.')

# Gráficos
st.markdown('### Distribución (Histograma)')
fig, ax = plt.subplots(figsize=(6.3,3.6))
ax.hist(df['mean'].dropna(), bins=30, color='#3182bd', edgecolor='white', alpha=0.9)
ax.set_xlabel('Tmin media (°C)'); ax.set_ylabel('Frecuencia'); ax.grid(alpha=0.25)
st.pyplot(fig, clear_figure=True)

st.markdown('### Caja y bigotes (Boxplot ≈ año/banda seleccionada)')
fig2, ax2 = plt.subplots(figsize=(6.3,3.6))
ax2.boxplot([df['mean'].dropna().values], patch_artist=True,
            boxprops=dict(facecolor='#9ecae1', color='#08519c'),
            medianprops=dict(color='#08306b', linewidth=2),
            whiskerprops=dict(color='#08519c'), capprops=dict(color='#08519c'))
ax2.set_xticklabels([str(year)])
ax2.set_ylabel('Tmin media (°C)'); ax2.grid(alpha=0.25)
st.pyplot(fig2, clear_figure=True)

st.markdown('### Dispersión coloreada (media vs std; color = p10)')
fig3, ax3 = plt.subplots(figsize=(6.3,3.6))
sc = ax3.scatter(df['mean'], df['std'], c=df['percentile_10'], cmap='viridis', s=20, alpha=0.85, edgecolors='none')
cb = plt.colorbar(sc, ax=ax3); cb.set_label('Tmin p10 (°C)')
ax3.set_xlabel('Tmin media (°C)'); ax3.set_ylabel('Desv. estándar (°C)'); ax3.grid(alpha=0.25)
st.pyplot(fig3, clear_figure=True)

st.markdown('### Mapa coroplético — Tmin media (°C)')
gplot = gdf[['UBIGEO_OK','NOMBRE_OK','geometry']].merge(df[['UBIGEO_OK','mean']], on='UBIGEO_OK', how='left')
fig4, ax4 = plt.subplots(figsize=(7.5,7.5))
gplot.plot(column='mean', cmap='coolwarm', legend=True, ax=ax4, edgecolor='black', linewidth=0.2)
ax4.set_axis_off(); ax4.set_title(f'Tmin media por distrito — {year}')
st.pyplot(fig4, clear_figure=True)

# Tablas con explicación
st.markdown('### Tablas y descarga')
st.caption('Top-15 más fríos / más cálidos para priorización territorial')
cold15 = df.nsmallest(15, 'mean')[['UBIGEO_OK','NOMBRE_OK','mean','percentile_10','percentile_90']]
hot15  = df.nlargest(15, 'mean')[['UBIGEO_OK','NOMBRE_OK','mean','percentile_10','percentile_90']]
colA, colB = st.columns(2)
with colA:
    st.dataframe(cold15.style.format({'mean':'{:.2f}','percentile_10':'{:.2f}','percentile_90':'{:.2f}'}), use_container_width=True)
    st.download_button('Descargar CSV (Fríos)', cold15.to_csv(index=False), file_name=f'top15_cold_{year}.csv', mime='text/csv')
with colB:
    st.dataframe(hot15.style.format({'mean':'{:.2f}','percentile_10':'{:.2f}','percentile_90':'{:.2f}'}), use_container_width=True)
    st.download_button('Descargar CSV (Cálidos)', hot15.to_csv(index=False), file_name=f'top15_hot_{year}.csv', mime='text/csv')

master = gplot.drop(columns='geometry').rename(columns={'mean':'tmin_mean_c'})
st.download_button('Descargar tabla completa (CSV)', master.to_csv(index=False), file_name=f'tmin_distritos_{year}.csv', mime='text/csv')

st.markdown('---')
st.subheader('Conclusión y guía de políticas públicas')
st.markdown("""Distritos con **Tmin media** y **p10** más bajos concentran mayor riesgo sanitario (IRA/ARI),
pérdidas agropecuarias y ausentismo escolar, sobre todo en zonas altoandinas. En Amazonía aparecen
**oleadas de frío** puntuales.""")
st.markdown('**Medidas**: viviendas térmicas (ISUR), kits antiheladas, calendarios agrícolas y refugios para ganado; protocolos MINSA/MINEDU ante alertas.')
st.caption('KPIs: −X% IRA; −X% mortalidad de alpacas/ovinos; +X% asistencia escolar; −X días de interrupción.')
