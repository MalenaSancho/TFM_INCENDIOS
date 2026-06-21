import pandas as pd
from pyproj import Transformer
import numpy as np
import os

print("Fase A.2: Preparación y limpieza de la base de datos de incendios...")

# --- 1. CARGA DEL DATASET ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_csv = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', '01_EGIF_2000_2025_ALBACETE.csv')

df = pd.read_csv(ruta_csv, sep=';', low_memory=False)

# --- 2. SELECCIÓN DE VARIABLES ÚTILES ---
columnas_utiles = [
    'Pif_idpif', 
    'Pif_tiempos_deteccion', 
    'Pif_localizacion_huso', 
    'Pif_localizacion_x', 
    'Pif_localizacion_y',
    'Pif_perdidas_superficiearboladatotal', 
    'Pif_perdidas_superficienoarboladatotal'
]
df_limpio = df[columnas_utiles].copy()

# --- 3. ESTANDARIZACIÓN TEMPORAL Y PURGA DE NULOS ---
print(" -> Estandarizando formato temporal y purgando valores nulos...")
# Eliminación de registros carentes de coordenadas espaciales o referencias temporales
df_limpio = df_limpio.dropna(subset=['Pif_tiempos_deteccion', 'Pif_localizacion_x', 'Pif_localizacion_y'])

# Transformación de la cadena temporal a formato fecha estándar
df_limpio['Fecha'] = pd.to_datetime(df_limpio['Pif_tiempos_deteccion']).dt.date

# --- 4. ESTANDARIZACIÓN GEOMÉTRICA ---
print(" -> Transformando coordenadas del sistema UTM (EPSG:25830) a grados geográficos (EPSG:4326)...")
transformer = Transformer.from_crs("epsg:25830", "epsg:4326", always_xy=True)

def convertir_coordenadas(row):
    try:
        x = float(row['Pif_localizacion_x'])
        y = float(row['Pif_localizacion_y'])
        lon, lat = transformer.transform(x, y)
        return pd.Series({'Longitud': lon, 'Latitud': lat})
    except:
        return pd.Series({'Longitud': np.nan, 'Latitud': np.nan})

# Aplicación de la transformación espacial vectorizada
coordenadas = df_limpio.apply(convertir_coordenadas, axis=1)
df_incendios = pd.concat([df_limpio, coordenadas], axis=1)

# Eliminación de errores de conversión y depuración de variables espaciales de origen
df_incendios = df_incendios.dropna(subset=['Latitud', 'Longitud'])
df_incendios = df_incendios.drop(columns=[
    'Pif_localizacion_x', 
    'Pif_localizacion_y', 
    'Pif_localizacion_huso', 
    'Pif_tiempos_deteccion'
])

# Estandarización de la nomenclatura de variables
df_incendios = df_incendios.rename(columns={
    'Pif_idpif': 'idpif',
    'Pif_perdidas_superficiearboladatotal': 'superficie_arbolada',
    'Pif_perdidas_superficienoarboladatotal': 'superficie_no_arbolada'
})

# --- 5. DEFINICIÓN DE LA VARIABLE OBJETIVO ---
# Asignación de la etiqueta de clase positiva (Y=1) a los eventos reales
df_incendios['INCENDIO'] = 1

print(f" Proceso de limpieza finalizado. Registros espaciales válidos: {len(df_incendios)}")

# --- 6. EXPORTACIÓN DEL RESULTADO ---
ruta_salida = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', 'BASE_INCENDIOS_LATLON.csv')
df_incendios.to_csv(ruta_salida, index=False)
print(f" Archivo exportado correctamente en: {ruta_salida}")