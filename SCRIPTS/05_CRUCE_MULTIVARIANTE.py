import pandas as pd
import xarray as xr
import numpy as np
import os
import warnings
import zipfile
import tempfile

# Supresión de advertencias de ejecución de NumPy para operaciones con valores nulos
warnings.filterwarnings("ignore", category=RuntimeWarning)

print("Fase C: Iniciando integración espaciotemporal multivariante...")

# --- 1. CONFIGURACIÓN DE RUTAS Y CARGA DE DATOS BASE ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_base = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', 'BASE_INCENDIOS_LATLON.csv')

df = pd.read_csv(ruta_base)
df['Fecha'] = pd.to_datetime(df['Fecha'])

ruta_topo  = os.path.join(ruta_script, '..', 'DATOS', '4.TOPOGRAFIA', 'TOPOGRAFIA_COMPLETA.nc')
ruta_ndvi  = os.path.join(ruta_script, '..', 'DATOS', '3.SATELITE', 'NDVI', 'MOD13Q1.061_250m_aid0001.nc')
ruta_usos  = os.path.join(ruta_script, '..', 'DATOS', '3.SATELITE', 'LANDCOVER', 'MCD12Q1.061_500m_aid0001.nc')

print("Cargando matrices multidimensionales de topografía y vegetación...")
try:
    ds_topo = xr.open_dataset(ruta_topo, engine='h5netcdf')
    
    # Armonización de calendarios (Conversión de formato juliano a estándar gregoriano)
    ds_ndvi = xr.open_dataset(ruta_ndvi, engine='h5netcdf', decode_times=True, use_cftime=True)
    if isinstance(ds_ndvi.indexes['time'], xr.coding.cftimeindex.CFTimeIndex):
        ds_ndvi['time'] = ds_ndvi.indexes['time'].to_datetimeindex()

    ds_usos = xr.open_dataset(ruta_usos, engine='h5netcdf', decode_times=True, use_cftime=True)
    if isinstance(ds_usos.indexes['time'], xr.coding.cftimeindex.CFTimeIndex):
        ds_usos['time'] = ds_usos.indexes['time'].to_datetimeindex()

    print("Archivos base cargados y dimensiones temporales armonizadas.")
except Exception as e:
    print(f"Error al cargar los archivos NetCDF base: {e}")
    exit()

# Identificación automática de las variables de interés
var_ndvi = [v for v in ds_ndvi.data_vars if 'NDVI' in v][0] 
var_usos = [v for v in ds_usos.data_vars if 'LC_Type' in v or 'LC' in v][0]

# --- 2. FUNCIÓN DE EXTRACCIÓN ESPACIOTEMPORAL ---
def extraer_datos_satelite(row):
    lat = row['Latitud']
    lon = row['Longitud']
    fecha = row['Fecha']
    resultados = {}
    
    # --- A. TOPOGRAFÍA ---
    try:
        lat_name = 'latitude' if 'latitude' in ds_topo.coords else 'lat'
        lon_name = 'longitude' if 'longitude' in ds_topo.coords else 'lon'
        pixel_topo = ds_topo.sel({lat_name: lat, lon_name: lon}, method='nearest')
        
        resultados['Altitud'] = float(np.nanmean(pixel_topo['Altitud'].values))
        resultados['Pendiente'] = float(np.nanmean(pixel_topo['Pendiente'].values))
        resultados['Orientacion'] = float(np.nanmean(pixel_topo['Orientacion'].values))
    except:
        resultados['Altitud'] = np.nan
        resultados['Pendiente'] = np.nan
        resultados['Orientacion'] = np.nan

    # --- B. VEGETACIÓN ---
    try:
        lat_name = 'latitude' if 'latitude' in ds_ndvi.coords else 'lat'
        lon_name = 'longitude' if 'longitude' in ds_ndvi.coords else 'lon'
        pixel_ndvi = ds_ndvi.sel(time=fecha, method='nearest').sel({lat_name: lat, lon_name: lon}, method='nearest')
        resultados['NDVI'] = float(np.nanmean(pixel_ndvi[var_ndvi].values)) / 10000.0
    except:
        resultados['NDVI'] = np.nan
        
    try:
        lat_name = 'latitude' if 'latitude' in ds_usos.coords else 'lat'
        lon_name = 'longitude' if 'longitude' in ds_usos.coords else 'lon'
        pixel_usos = ds_usos.sel(time=fecha, method='nearest').sel({lat_name: lat, lon_name: lon}, method='nearest')
        resultados['LandCover'] = int(np.nanmean(pixel_usos[var_usos].values))
    except:
        resultados['LandCover'] = np.nan

    # --- C. CLIMATOLOGÍA (EXTRACCIÓN DINÁMICA Y GESTIÓN DE COMPRESIÓN) ---
    try:
        nombre_archivo = f"clima_albacete_{fecha.year}_{fecha.month:02d}.nc"
        ruta_clima_mes = os.path.join(ruta_script, '..', 'DATOS', '2.CLIMA', nombre_archivo)
        
        archivo_a_leer = ruta_clima_mes
        archivo_temporal = None
        
        # 1. Detección de compresión (Magic Bytes de formato ZIP)
        with open(ruta_clima_mes, 'rb') as f:
            es_zip = f.read(2) == b'PK'
            
        # 2. Descompresión en memoria temporal si procede
        if es_zip:
            with zipfile.ZipFile(ruta_clima_mes, 'r') as z:
                nombre_interno = z.namelist()[0]
                archivo_a_leer = z.extract(nombre_interno, path=tempfile.gettempdir())
                archivo_temporal = archivo_a_leer
                
        # 3. Lectura y extracción del píxel meteorológico
        with xr.open_dataset(archivo_a_leer, engine='netcdf4') as ds_clima:
            # Estandarización dinámica de la nomenclatura de coordenadas espaciales y temporales
            lat_name = 'latitude' if 'latitude' in ds_clima.coords else 'lat'
            lon_name = 'longitude' if 'longitude' in ds_clima.coords else 'lon'
            time_name = 'valid_time' if 'valid_time' in ds_clima.coords else 'time'
            
            # Búsqueda del vecino más cercano (Nearest Neighbor)
            pixel_clima = ds_clima.sel({time_name: fecha}, method='nearest').sel({lat_name: lat, lon_name: lon}, method='nearest')
            
            var_temp = 't2m' if 't2m' in ds_clima.data_vars else '2m_temperature'
            var_lluvia = 'tp' if 'tp' in ds_clima.data_vars else 'total_precipitation'
            var_viento = 'u10' if 'u10' in ds_clima.data_vars else '10m_u_component_of_wind'
            
            resultados['Temp_C'] = float(np.nanmean(pixel_clima[var_temp].values)) - 273.15 
            resultados['Lluvia_mm'] = float(np.nanmean(pixel_clima[var_lluvia].values)) * 1000 
            resultados['Viento_U'] = float(np.nanmean(pixel_clima[var_viento].values))
            
        # 4. Eliminación de archivos temporales extraídos
        if archivo_temporal and os.path.exists(archivo_temporal):
            try:
                os.remove(archivo_temporal)
            except:
                pass
                
    except Exception as e:
        resultados['Temp_C'] = np.nan
        resultados['Lluvia_mm'] = np.nan
        resultados['Viento_U'] = np.nan

    return pd.Series(resultados)

# --- 3. EJECUCIÓN DEL FLUJO ---
print("Ejecutando cruce de variables multivariante. Este proceso requiere alta capacidad de cómputo...")
df_nuevas = df.apply(extraer_datos_satelite, axis=1)
df_final = pd.concat([df, df_nuevas], axis=1)

# --- 4. EXPORTACIÓN ---
ruta_salida = os.path.join(ruta_script, '..', 'DATOS', 'DATASET_INCENDIOS_CRUZADO.csv')
df_final.to_csv(ruta_salida, index=False)

print("-" * 50)
print("Integración espaciotemporal completada.")
print(f"Matriz consolidada exportada en:\n{ruta_salida}")
print("-" * 50)
print("\nVista previa de las variables meteorológicas anexadas:")
print(df_final[['Fecha', 'Temp_C', 'Lluvia_mm', 'Viento_U']].head())