import cdsapi
import os

# --- 1. CONFIGURACIÓN DEL ENTORNO Y RUTAS ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
CARPETA_SALIDA = os.path.join(ruta_script, '..', 'DATOS', '2.CLIMA')

# Creación dinámica del directorio de destino si no existe
if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

# --- 2. AUTENTICACIÓN EN LA API DE COPERNICUS (C3S) ---
# Nota: Es recomendable utilizar el archivo de configuración .cdsapirc. 
# En su defecto, se definen las credenciales a continuación.
URL = 'https://cds.climate.copernicus.eu/api'
KEY = 'PON TU API KEY AQUÍ'  

# Inicialización del cliente de la API
c = cdsapi.Client(url=URL, key=KEY)
     
# --- 3. DEFINICIÓN DE PARÁMETROS ESPACIOTEMPORALES ---
# Bounding Box (Caja Envolvente) para la provincia de Albacete: [Norte, Oeste, Sur, Este]
AREA_ALBACETE = [39.5, -3.0, 38.0, -0.5]

# Horizonte temporal del estudio: 2010 a 2025
YEARS = [str(year) for year in range(2010, 2026)]

# Formato estandarizado de meses (01 al 12)
MONTHS = [f"{month:02d}" for month in range(1, 13)]

# --- 4. BUCLE DE EXTRACCIÓN Y DESCARGA (ITERACIÓN MENSUAL) ---
print(f"Fase B.1: Iniciando petición automatizada de datos climáticos...")
print(f"Directorio de destino: {CARPETA_SALIDA}")
print("El proceso iterativo puede demorar según la congestión del servidor de Copernicus.")

for year in YEARS:
    for month in MONTHS:
        filename = os.path.join(CARPETA_SALIDA, f'clima_albacete_{year}_{month}.nc')
        
        # Control de reanudación: omite peticiones si el archivo ya fue descargado previamente
        if os.path.exists(filename):
            print(f" - Saltando periodo {year}-{month}: Archivo local ya existente.")
            continue

        print(f" - Solicitando datos para el periodo: {year}-{month}...")
        
        try:
            c.retrieve(
                'reanalysis-era5-land',
                {
                    'variable': [
                        '2m_temperature',           # Temperatura del aire a 2 metros
                        '2m_dewpoint_temperature',  # Temperatura del punto de rocío a 2 metros
                        'total_precipitation',      # Precipitación total acumulada
                        '10m_u_component_of_wind',  # Componente zonal del viento a 10 metros
                        '10m_v_component_of_wind',  # Componente meridional del viento a 10 metros
                    ],
                    'year': year,
                    'month': month,
                    'day': [
                        '01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
                        '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',
                        '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',
                        '31',
                    ],
                    'time': [
                        '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
                        '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                        '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                        '18:00', '19:00', '20:00', '21:00', '22:00', '23:00',
                    ],
                    'area': AREA_ALBACETE,
                    'format': 'netcdf',
                },
                filename)
        except Exception as e:
            print(f" Error de conexión o petición en el periodo {year}-{month}: {e}")

print("Proceso de adquisición de variables meteorológicas completado.")