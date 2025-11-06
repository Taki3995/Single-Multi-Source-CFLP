"""
El objetivo de este archivo es leer los .txt y crear nuevos archivos .dat con la misma información, para que AMPL los entienda. 
Los archivos .txt se desglosan de la siguiente manera:

Linea 1: tenemos num_locations num_clients. En .dat esta como loc := 2000 y cli := 2000, y en .txt está como 2000 2000

Luego vienen lineas de separación, las cuales contienen un *

Bloque 1: num_locations (datos localizacion), cada una con capacidad costo_fijo (en .txt se ve como 1.1e+03 95.8)

Bloque 2: num_clients (datos clientes - demanda), listados uno tras otro

Bloque 3: num_clientes * num_locations (datos de costos - tc) valores de costo de transporte listados uno tras otro 
(el costo de cli_1 -> loc_1, cli_1 -> loc_2, ..., cli_n -> loc_n)
"""

import os
import sys

def parse_and_convert(txt_file_path, dat_file_path):
    """
    Lee un archivo de instancia .txt y lo convierte 
    a un archivo .dat compatible con AMPL.
    """
    print(f"Iniciando conversión: {txt_file_path} -> {dat_file_path}")
    
    try:
        with open(txt_file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de entrada: {txt_file_path}")
        return

    # --- 1. Leer Cabecera (loc, cli) ---
    current_line_index = 0
    try:
        parts = lines[current_line_index].strip().split()
        n_locations = int(parts[0])
        n_clients = int(parts[1])
        current_line_index += 1
    except Exception as e:
        print(f"Error leyendo cabecera (loc, cli) de {txt_file_path}: {e}")
        return

    # --- 2. Omitir separador (*) ---
    # Avanza hasta que encuentra la línea que contiene el *
    while '*' not in lines[current_line_index]:
        current_line_index += 1
    current_line_index += 1 # Se mueve a la línea siguiente al *

    # --- Listas para guardar los datos ---
    out_lines = []
    fc_data = []      # Costo Fijo (FC)
    icap_data = []    # Capacidad (ICap)
    dem_data = []     # Demanda (dem)
    
    # Añadir cabeceras del .dat
    out_lines.append(f"param cli := {n_clients};\n")
    out_lines.append(f"param loc := {n_locations};\n\n")

    # --- 3. Bloque 1: Leer Datos de Localizaciones (ICap y FC) ---
    print(f"Leyendo {n_locations} localizaciones...")
    try:
        fc_str = ["param FC :="]
        icap_str = ["param ICap :="]
        
        for j in range(n_locations):
            line = lines[current_line_index + j]
            parts = line.strip().split()
            
            capacity = float(parts[0])
            fixed_cost = float(parts[1])
            
            # Formato: [indice] [valor]
            icap_str.append(f"\n\t{j + 1}\t{capacity}")
            fc_str.append(f"\n\t{j + 1}\t{fixed_cost}")
        
        out_lines.append("".join(fc_str) + ";\n\n")
        out_lines.append("".join(icap_str) + ";\n\n")
        
        current_line_index += n_locations
    except Exception as e:
        print(f"Error leyendo el bloque de localizaciones: {e}")
        return

    # --- Función auxiliar para leer bloques continuos de números ---
    def read_continuous_block(start_index, total_count):
        """Lee un bloque de 'total_count' números que pueden estar en varias líneas."""
        data_list = []
        current_count = 0
        idx = start_index
        
        while current_count < total_count:
            if idx >= len(lines):
                raise Exception("Error: Fin de archivo inesperado leyendo bloque.")
            
            line_parts = lines[idx].strip().split()
            for part in line_parts:
                data_list.append(float(part))
                current_count += 1
            idx += 1
            
        return data_list, idx # Retorna la lista de datos y el nuevo índice de línea

    # --- 4. Bloque 2: Leer Demandas (dem) ---
    print(f"Leyendo {n_clients} demandas...")
    try:
        all_demands, current_line_index = read_continuous_block(current_line_index, n_clients)
        
        dem_str = ["param dem :="]
        for i, demand in enumerate(all_demands):
            dem_str.append(f"\n\t{i + 1}\t{demand}")
            
        out_lines.append("".join(dem_str) + ";\n\n")
    except Exception as e:
        print(f"Error leyendo el bloque de demandas: {e}")
        return

    # --- 5. Bloque 3: Leer Costos de Transporte (TC) ---
    print(f"Leyendo {n_clients}x{n_locations} costos de transporte...")
    try:
        total_costs = n_clients * n_locations
        all_costs, current_line_index = read_continuous_block(current_line_index, total_costs)
        
        # Escribir la cabecera de la matriz TC
        tc_header = ["param TC :\n\t"]
        tc_header.extend([f"{j+1}\t" for j in range(n_locations)])
        tc_header.append(":=")
        out_lines.append("".join(tc_header) + "\n")
        
        # Escribir las filas de la matriz
        cost_idx = 0
        for i in range(n_clients):
            row_str = [f"\t{i + 1}\t"] # Índice de la fila (cliente)
            for j in range(n_locations):
                row_str.append(f"{all_costs[cost_idx]}\t")
                cost_idx += 1
            out_lines.append("".join(row_str) + "\n")
        
        out_lines.append(";\n")
    except Exception as e:
        print(f"Error leyendo el bloque de costos de transporte: {e}")
        return

    # --- 6. Escribir el archivo .dat ---
    try:
        # Asegurarse de que el directorio de salida exista
        os.makedirs(os.path.dirname(dat_file_path), exist_ok=True)
        
        with open(dat_file_path, 'w') as f:
            f.writelines(out_lines)
            
        print(f"Archivo guardado en {dat_file_path} con éxito!")
        
    except Exception as e:
        print(f"Error escribiendo el archivo .dat: {e}")


# --- Bloque para probar este script individualmente ---
if __name__ == "__main__":
    # Probar el parser sin ejecutar main.py
    # Uso: python src/data_parser.py 2000x2000_1
    
    if len(sys.argv) > 1:
        instance_name = sys.argv[1] # Ej: "2000x2000_1"
    else:
        # Poner una instancia por defecto para pruebas rápidas
        print("Advertencia: No se especificó instancia. Usando '2000x2000_1' por defecto.")
        instance_name = "2000x2000_1" 

    # Construir las rutas basándonos en la estructura de carpetas
    # __file__ es 'CFLP_PROYECTO/src/data_parser.py'
    # os.path.dirname(__file__) es 'CFLP_PROYECTO/src'
    # os.path.abspath(os.path.join(..., '..')) es 'CFLP_PROYECTO'
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    txt_path = os.path.join(base_dir, 'data', 'instances_txt', f"{instance_name}.txt")
    dat_path = os.path.join(base_dir, 'data', 'instances_dat', f"{instance_name}.dat")
    
    parse_and_convert(txt_path, dat_path)