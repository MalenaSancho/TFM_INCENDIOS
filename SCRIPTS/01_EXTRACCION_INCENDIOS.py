import pandas as pd
import xml.etree.ElementTree as ET
import os

# --- 1. CONFIGURACIÓN DE RUTAS ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
NOMBRE_ARCHIVO_XML = 'EGIF_2000_2025_ALBACETE.xml'
RUTA_ENTRADA = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', NOMBRE_ARCHIVO_XML)
RUTA_SALIDA = os.path.join(ruta_script, '..', 'DATOS', '1.INCENDIOS', '01_EGIF_2000_2025_ALBACETE.csv')

# --- 2. APLANADO DE NODOS XML ---
def aplanar_nodo_full(nodo, prefijo=""):
    datos = {}
    
    # Extracción del texto del nodo
    if nodo.text and nodo.text.strip():
        # Generación de nombres compuestos temporales para evitar sobrescritura de variables
        nombre_col = f"{prefijo}_{nodo.tag}" if prefijo else nodo.tag
        datos[nombre_col] = nodo.text.strip()
    
    # Extracción de atributos
    for k, v in nodo.attrib.items():
        nombre_attr = f"{prefijo}_{nodo.tag}_{k}" if prefijo else f"{nodo.tag}_{k}"
        datos[nombre_attr] = v

    # Recorrido recursivo de los nodos anidados (hijos)
    for hijo in nodo:
        nuevo_prefijo = f"{prefijo}_{nodo.tag}" if prefijo else nodo.tag
        datos.update(aplanar_nodo_full(hijo, nuevo_prefijo))
        
    return datos

# --- 3. PROCESO PRINCIPAL ---
print(f"Fase A.1: Iniciando extracción y aplanado del archivo: {NOMBRE_ARCHIVO_XML}")

if not os.path.exists(RUTA_ENTRADA):
    print("Error: Archivo de entrada no encontrado.")
    exit()

try:
    tree = ET.parse(RUTA_ENTRADA)
    root = tree.getroot()
    print(f"Archivo XML cargado correctamente. Registros detectados: {len(root)}")
except Exception as e:
    print(f"Error durante la lectura del archivo XML: {e}")
    exit()

# GENERACIÓN DEL DATAFRAME COMPLETO
lista_total = []
print("Extrayendo variables del árbol XML...")
for incendio in root:
    lista_total.append(aplanar_nodo_full(incendio))

df = pd.DataFrame(lista_total)
cols_iniciales = len(df.columns)
print(f"Dimensiones iniciales: {len(df)} filas x {cols_iniciales} columnas (incluyendo redundancias)")

# --- 4. LIMPIEZA DE NOMENCLATURA DE COLUMNAS ---
print("Estandarizando nomenclatura de las columnas...")
df.columns = [c.replace('pif_', '').replace('incendio_', '').replace('parte_', '') for c in df.columns]

# --- 5. DESDUPLICACIÓN BASADA EN CONTENIDO ---
print("Identificando y eliminando columnas con información redundante...")

# Algoritmo de desduplicación transponiendo la matriz
df_transpuesta = df.T 
df_dedup_T = df_transpuesta.drop_duplicates() 
df_final = df_dedup_T.T 

cols_finales = len(df_final.columns)
eliminadas = cols_iniciales - cols_finales

print(f"Columnas redundantes eliminadas: {eliminadas}")
print(f"Columnas únicas resultantes: {cols_finales}")

# --- 6. SIMPLIFICACIÓN DE NOMBRES DE COLUMNAS ---
nuevas_cols = {}
for col in df_final.columns:
    parts = col.split('_')
    if len(parts) > 1 and parts[-1] == parts[-2]:
        nuevas_cols[col] = "_".join(parts[:-1]) 
        
df_final = df_final.rename(columns=nuevas_cols)

# --- 7. EXPORTACIÓN DE RESULTADOS ---
print("Exportando el conjunto de datos estructurado...")
df_final.to_csv(RUTA_SALIDA, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "-"*50)
print("Proceso de extracción y aplanado finalizado con éxito.")
print(f"Ruta de salida: {RUTA_SALIDA}")
print(f"Dimensiones finales: {len(df_final)} filas x {len(df_final.columns)} columnas")
print("-"*50)