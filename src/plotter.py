import pandas as pd
import matplotlib.pyplot as plt
import os
import glob

# Rutas
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOLUTIONS_DIR = os.path.join(BASE_DIR, 'solutions')

def plot_all_convergences():
    # Buscar todos los archivos history_*.csv
    csv_files = glob.glob(os.path.join(SOLUTIONS_DIR, "history_*.csv"))
    
    if not csv_files:
        print("No se encontraron archivos de historial (.csv) en solutions/")
        return

    print(f"Generando gráficos para {len(csv_files)} archivos...")

    for file in csv_files:
        try:
            # Leer datos
            df = pd.read_csv(file)
            
            # Extraer nombre limpio (ej: history_Instance50x50_MS.csv -> Instance50x50 - MS)
            filename = os.path.basename(file)
            clean_name = filename.replace("history_", "").replace(".csv", "")
            
            # Crear gráfico
            plt.figure(figsize=(10, 6))
            plt.plot(df['Iteration'], df['Cost'], marker='o', linestyle='-', color='b', markersize=4)
            
            plt.title(f'Convergencia Heurística: {clean_name}')
            plt.xlabel('Iteraciones')
            plt.ylabel('Costo Total')
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)
            
            # Guardar imagen
            output_img = file.replace(".csv", ".png")
            plt.savefig(output_img)
            plt.close()
            print(f"Gráfico guardado: {output_img}")
            
        except Exception as e:
            print(f"Error graficando {file}: {e}")

if __name__ == "__main__":
    plot_all_convergences()