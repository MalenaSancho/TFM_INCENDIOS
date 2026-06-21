import pandas as pd
import numpy as np
import xarray as xr
import os
from datetime import timedelta

print("Fase D: Iniciando generación de pseudo-ausencias (Clase Y=0) mediante muestreo estratificado...")

# --- 1. CONFIGURACIÓN DE RUTAS E HIPERPARÁMETROS DE EXCLUSIÓN ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_incendios = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', 'BASE_INCENDIOS_LATLON.csv')
ruta_salida = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', 'BASE_NO_INCENDIOS_LATLON.csv')
ruta_topo = os.path.join(ruta_script, '..', 'DATOS', '4.TOPOGRAFIA', 'TOPOGRAFIA_COMPLETA.nc')

# Umbrales restrictivos basados en Stojanova et al. (2012)
DISTANCIA_MINIMA_KM = 15.0
MARGEN_DIAS = 3

# --- 2. CARGA DEL CONJUNTO DE INCENDIOS REALES (Clase Positiva) ---
df_fires = pd.read_csv(ruta_incendios)
df_fires['Fecha'] = pd.to_datetime(df_fires['Fecha'])
num_incendios = len(df_fires)
print(f"Observaciones positivas (Y=1) cargadas: {num_incendios}")

# --- 3. ESTRATIFICACIÓN TEMPORAL (Distribución Empírica) ---
# Cálculo de la densidad de probabilidad mensual para evitar sesgos estacionales
df_fires['Mes'] = df_fires['Fecha'].dt.month
probabilidad_meses = df_fires['Mes'].value_counts(normalize=True).sort_index()

# --- 4. ENMASCARAMIENTO MATRICIAL ESPACIAL ---
print("\nExtrayendo molde geográfico de la matriz topográfica (Restricción de fronteras)...")
ds_topo = xr.open_dataset(ruta_topo, engine='h5netcdf')

lat_name = 'latitude' if 'latitude' in ds_topo.coords else 'lat'
lon_name = 'longitude' if 'longitude' in ds_topo.coords else 'lon'

lats = ds_topo[lat_name].values
lons = ds_topo[lon_name].values

# Reducción dimensional del tensor de altitud
altitud = ds_topo['Altitud'].squeeze().values 

# Control de dimensionalidad residual
if altitud.ndim == 3:
    altitud = altitud[0, :, :]

# Extracción de coordenadas donde existe información topográfica válida (Interior de Albacete)
valid_y, valid_x = np.where(~np.isnan(altitud))

lats_validos = lats[valid_y]
lons_validos = lons[valid_x]

print(f"Enmascaramiento completado: {len(lats_validos)} píxeles viables identificados.")

# --- 5. FUNCIONES DE CÁLCULO VECTORIZADO ---
def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia ortodrómica (círculo máximo) entre dos puntos geográficos."""
    R = 6371.0 # Radio volumétrico medio de la Tierra en km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def generar_fecha_estratificada(año_min, año_max):
    """Genera una fecha sintética ponderada por la distribución mensual real de incendios."""
    año = np.random.randint(año_min, año_max + 1)
    mes = np.random.choice(probabilidad_meses.index, p=probabilidad_meses.values)
    dia = np.random.randint(1, 28)
    return pd.Timestamp(year=año, month=mes, day=dia)

# --- 6. ALGORITMO ITERATIVO DE GENERACIÓN DE PSEUDO-AUSENCIAS ---
print(f"\nGenerando la clase negativa (Y=0). Objetivo: {num_incendios} observaciones...")

pseudo_ausencias = []
intentos = 0

while len(pseudo_ausencias) < num_incendios:
    intentos += 1
    
    # 1. Muestreo espacial aleatorio condicionado por la máscara topográfica
    idx_aleatorio = np.random.randint(0, len(lats_validos))
    lat_cand = lats_validos[idx_aleatorio]
    lon_cand = lons_validos[idx_aleatorio]
    
    # 2. Generación temporal estratificada
    fecha_cand = generar_fecha_estratificada(2000, 2025)
    
    # 3. Aplicación de la restricción temporal (+/- 3 días)
    fecha_inicio = fecha_cand - timedelta(days=MARGEN_DIAS)
    fecha_fin = fecha_cand + timedelta(days=MARGEN_DIAS)
    incendios_cercanos = df_fires[(df_fires['Fecha'] >= fecha_inicio) & (df_fires['Fecha'] <= fecha_fin)]
    
    # 4. Evaluación de la restricción espacial (Distancia de exclusión > 15 km)
    valido = True
    if not incendios_cercanos.empty:
        distancias = calcular_distancia_haversine(
            lat_cand, lon_cand, 
            incendios_cercanos['Latitud'].values, 
            incendios_cercanos['Longitud'].values
        )
        if np.any(distancias < DISTANCIA_MINIMA_KM):
            valido = False
            
    # 5. Consolidación de la observación validada
    if valido:
        pseudo_ausencias.append({
            'idpif': f"Y0_{len(pseudo_ausencias)}",
            'superficie_arbolada': 0.0,
            'superficie_no_arbolada': 0.0,
            'Fecha': fecha_cand.date(),
            'Longitud': float(lon_cand),
            'Latitud': float(lat_cand),
            'INCENDIO': 0
        })
        
    if len(pseudo_ausencias) % 500 == 0 and valido:
        print(f" - Progreso de consolidación: {len(pseudo_ausencias)} / {num_incendios}")

# --- 7. EXPORTACIÓN DE LA CLASE NEGATIVA ---
df_ausencias = pd.DataFrame(pseudo_ausencias)
df_ausencias.to_csv(ruta_salida, index=False)

print("\n" + "="*50)
print(f"Diseño muestral completado con éxito.")
print(f"Total de pseudo-ausencias generadas y validadas: {len(df_ausencias)}")
print("="*50)