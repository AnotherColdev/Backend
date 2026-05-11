import pandas as pd
from app.services.transformer_service import process_dataset

# 1. Carga aquí tu archivo de prueba (.csv)
# Asegúrate que tenga las columnas mínimas (zone_code, zone_name) y variables numéricas.
path_del_archivo = "mi_archivo_de_prueba.csv"

print(f"[*] Cargando archivo: {path_del_archivo}")
try:
    # Agregamos sep=';' en caso de que sea un CSV delimitado por punto y coma (muy común en español)
    try:
        df_externo = pd.read_csv(path_del_archivo, sep=';')
        if 'zone_code' not in df_externo.columns:
            # Si a pesar del ';' no existe, probamos con la coma normal
            df_externo = pd.read_csv(path_del_archivo, sep=',')
    except:
        df_externo = pd.read_csv(path_del_archivo, sep=',')
        
    print(f"[*] Filas Iniciales: {len(df_externo)}")

    # 2. Re-usar la lógica real de negocio del microservicio
    df_procesado, reglas_aplicadas = process_dataset(df_externo)

    # 3. Guardar o evaluar el resultado
    df_procesado.to_csv("resultado_limpio.csv", index=False)
    
    print("\n[+] Transformación Finalizada Exitosamente!")
    print(f"[+] Filas Finales luego de quitar duplicados: {len(df_procesado)}")
    print("\n[!] Reglas que fueron aplicadas:")
    for rule in reglas_aplicadas:
        print(f"  - {rule}")
        
    print("\nEl archivo transformado se ha guardado como 'resultado_limpio.csv'.")

except FileNotFoundError:
    print("Error: No se encontró el archivo. Asegúrate que 'mi_archivo_de_prueba.csv' exista en tu carpeta.")