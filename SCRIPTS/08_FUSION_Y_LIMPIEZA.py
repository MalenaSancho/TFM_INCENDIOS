import pandas as pd
import os

print("Fase E.3: Iniciando consolidación y limpieza del Dataset Maestro...")

# --- 1. CONFIGURACIÓN DE RUTAS Y CARGA DE DATOS ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_y1 = os.path.join(ruta_script, '..', 'DATOS', 'DATASET_INCENDIOS_CRUZADO.csv')
ruta_y0 = os.path.join(ruta_script, '..', 'DATOS', 'DATASET_NO_INCENDIOS_CRUZADO.csv')
ruta_salida = os.path.join(ruta_script, '..', 'DATOS', 'DATASET_MASTER.csv')

# Carga independiente de ambas clases
df_1 = pd.read_csv(ruta_y1)
df_0 = pd.read_csv(ruta_y0)

print(f" - Observaciones reales (Clase Y=1): {len(df_1)}")
print(f" - Pseudo-ausencias (Clase Y=0): {len(df_0)}")

# --- 2. ACOPLAMIENTO TABULAR VERTICAL ---
df_master = pd.concat([df_1, df_0], ignore_index=True)
print(f"\nTotal de registros combinados antes de la depuración: {len(df_master)} filas")

# --- 3. DEPURACIÓN DE VALORES NULOS (PÍXELES FRONTERIZOS) ---
# Eliminación de registros marginales procedentes del enmascaramiento matricial
# que carecen de gradiente topográfico en los bordes de la provincia.
df_master_clean = df_master.dropna()
filas_borradas = len(df_master) - len(df_master_clean)
print(f"Registros eliminados por ausencia de datos viables: {filas_borradas}")

# --- 4. MEZCLA ALEATORIA MULTIFACTORIAL (SHUFFLE) ---
# Desordenación secuencial de las filas con semilla fija para prevenir 
# sesgos de aprendizaje y fugas de información durante la validación cruzada.
df_master_clean = df_master_clean.sample(frac=1, random_state=42).reset_index(drop=True)

# --- 5. VERIFICACIÓN DEL BALANCE DE CLASES ---
print("\nDistribución final de la variable objetivo (Balance de clases):")
print(df_master_clean['INCENDIO'].value_counts())

# --- 6. EXPORTACIÓN DEL DATASET MAESTRO ---
df_master_clean.to_csv(ruta_salida, index=False)

print("\n" + "-"*50)
print("Consolidación del Dataset Maestro finalizada con éxito.")
print(f"Matriz de entrenamiento exportada en:\n{ruta_salida}")
print("-" * 50)