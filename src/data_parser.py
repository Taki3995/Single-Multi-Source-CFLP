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

    # --- Leer Cabecera (loc, cli) ---
    current_line_index = 0
    try:
        parts = lines[current_line_index].strip().split()
        n_locations = int(parts[0])
        n_clients = int(parts[1])
        current_line_index += 1
    except Exception as e:
        print(f"Error leyendo cabecera (loc, cli) de {txt_file_path}: {e}")
        return

    # --- Omitir primer separador (*) ---
    while '*' not in lines[current_line_index]:
        current_line_index += 1
    current_line_index += 1 # Se mueve a la línea siguiente al *

    # Listas para guardar los datos
    out_lines = []
    
    # Añadir cabeceras del .dat
    out_lines.append(f"param cli := {n_clients};\n")
    out_lines.append(f"param loc := {n_locations};\n\n")

    # --- Bloque 1: Leer Datos de Localizaciones (ICap y FC) ---
    print(f"Leyendo {n_locations} localizaciones...")
    try:
        fc_str = ["param FC :="]
        icap_str = ["param ICap :="]
        
        for j in range(n_locations):
            line = lines[current_line_index + j]
            parts = line.strip().split()
            
            capacity = float(parts[0])
            fixed_cost = float(parts[1])
            
            icap_str.append(f"\n\t{j + 1}\t{capacity}")
            fc_str.append(f"\n\t{j + 1}\t{fixed_cost}")
        
        out_lines.append("".join(fc_str) + ";\n\n")
        out_lines.append("".join(icap_str) + ";\n\n")
        
        current_line_index += n_locations
    except Exception as e:
        print(f"Error leyendo el bloque de localizaciones: {e}")
        return

    # Función auxiliar para leer bloques continuos de números
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
                # Ignorar cualquier cosa que no sea un número
                if part == '*':
                    continue
                try:
                    data_list.append(float(part))
                    current_count += 1
                except ValueError:
                    # Si algo más falla, lo ignoramos y seguimos
                    pass 
                
                if current_count == total_count:
                    break
            idx += 1
            
        return data_list, idx # Retorna la lista de datos y el nuevo índice de línea

    # Saltar separador entre Bloque 1 y 2
    try:
        while '*' not in lines[current_line_index]:
            current_line_index += 1
        current_line_index += 1 # Moverse a la línea después del *
    except IndexError:
        print("Error: Se esperaba un separador '*' después del bloque de localizaciones.")
        return

    # --- Bloque 2: Leer Demandas (dem) ---
    print(f"Leyendo {n_clients} demandas...")
    try:
        all_demands, current_line_index_after_dem = read_continuous_block(current_line_index, n_clients)
        
        dem_str = ["param dem :="]
        for i, demand in enumerate(all_demands):
            dem_str.append(f"\n\t{i + 1}\t{demand}")
            
        out_lines.append("".join(dem_str) + ";\n\n")
        
        # Saltar separador entre Bloque 2 y 3
        current_line_index = current_line_index_after_dem
        while '*' not in lines[current_line_index]:
            current_line_index += 1
        current_line_index += 1 # Moverse a la línea *después* del *

    except Exception as e:
        print(f"Error leyendo el bloque de demandas: {e}")
        return

    # --- Bloque 3: Leer Costos de Transporte (TC) ---
    print(f"Leyendo {n_clients}x{n_locations} costos de transporte...")
    try:
        total_costs = n_clients * n_locations
        # El índice 'current_line_index' ya está apuntando al inicio del Bloque 3
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

    # --- Escribir el archivo .dat ---
    try:
        os.makedirs(os.path.dirname(dat_file_path), exist_ok=True)
        
        with open(dat_file_path, 'w') as f:
            f.writelines(out_lines)
            
        print(f"Archivo guardado en {dat_file_path} con éxito!")
        
    except Exception as e:
        print(f"Error escribiendo el archivo .dat: {e}")


# --- Bloque para probar este script individualmente ---
if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        instance_name = sys.argv[1] # Ej: "2000x2000_1"
    else:
        print("Advertencia: No se especificó instancia. Usando '2000x2000_1' por defecto.")
        instance_name = "2000x2000_1" 

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    txt_path = os.path.join(base_dir, 'data', 'instances_txt', f"{instance_name}.txt")
    dat_path = os.path.join(base_dir, 'data', 'instances_dat', f"{instance_name}.dat")
    
    parse_and_convert(txt_path, dat_path)