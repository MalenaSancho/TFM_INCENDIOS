import xarray as xr
import numpy as np
import os

print("Fase B.2: Procesamiento del Modelo Digital de Elevaciones y derivación de variables topográficas...")

# --- 1. CONFIGURACIÓN DEL ENTORNO Y RUTAS ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_carpeta = os.path.join(ruta_script, '..', 'DATOS', '4.TOPOGRAFIA')
archivo_original = os.path.join(ruta_carpeta, 'SRTMGL1_NC.003_30m_aid0001.nc')
archivo_salida = os.path.join(ruta_carpeta, 'TOPOGRAFIA_COMPLETA.nc')

try:
    if not os.path.exists(archivo_original):
        print(f"Error: Archivo base de topografía no encontrado en {archivo_original}")
        exit()

    print(f"Cargando el cubo de datos (Data Cube) de altitud original...")
    ds = xr.open_dataset(archivo_original, engine='h5netcdf')
    
    # Identificación automática de la variable principal de elevación (excluyendo metadatos espaciales)
    var_name = [v for v in ds.data_vars if ds[v].ndim >= 2 and 'crs' not in v.lower()][0]
    elevacion = ds[var_name].squeeze()
    
    print("Derivando variables topográficas mediante el cálculo de gradientes espaciales...")
    # Cálculo de derivadas parciales mediante numpy.gradient (diferencias en el eje Y y eje X)
    dy, dx = np.gradient(elevacion.values)
    
    # 1. Inclinación del terreno (Pendiente / Slope): Magnitud del gradiente espacial
    slope = np.sqrt(dx**2 + dy**2)
    
    # 2. Orientación de ladera (Aspect): Cálculo del azimut en grados sexagesimales (0º a 360º)
    aspect = np.degrees(np.arctan2(dy, -dx))
    aspect = np.where(aspect < 0, aspect + 360, aspect)

    print("Estructurando y exportando el cubo de datos topográfico consolidado...")
    # Generación de un nuevo Dataset multivariante integrando altitud, pendiente y orientación
    ds_nuevo = ds.copy()
    ds_nuevo = ds_nuevo.rename({var_name: 'Altitud'}) # Estandarización de nomenclatura
    ds_nuevo['Pendiente'] = (elevacion.dims, slope)
    ds_nuevo['Orientacion'] = (elevacion.dims, aspect)
    
    ds_nuevo.to_netcdf(archivo_salida, engine='h5netcdf')
    ds.close()
    
    print("-" * 50)
    print("Proceso de derivación topográfica finalizado con éxito.")
    print(f"Archivo NetCDF consolidado exportado en:\n{archivo_salida}")
    print("-" * 50)

except Exception as e:
    print(f"\nError durante el procesamiento topográfico: {e}")