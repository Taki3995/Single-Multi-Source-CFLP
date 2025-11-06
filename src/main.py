import os
import argparse
from data_parser import parse_and_convert

# Definir rutas base
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TXT_DIR = os.path.join(DATA_DIR, 'instances_txt')
DAT_DIR = os.path.join(DATA_DIR, 'instances_dat')


def main(instance_name, iterations, mode):
    
    print(f"--- Iniciando Proceso para {instance_name} ---")
    
    # --- 1. Preparar Archivos de Datos ---
    txt_file = os.path.join(TXT_DIR, f"{instance_name}.txt")
    dat_file = os.path.join(DAT_DIR, f"{instance_name}.dat")
    
    # Solo convertir si el .dat no existe
    if not os.path.exists(dat_file):
        print(f"Archivo .dat no encontrado. Generando desde {txt_file}...")
        parse_and_convert(txt_file, dat_file)
    else:
        print(f"Archivo .dat ya existe en {dat_file}.")

    # luego agregar mas pasos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolver CFLP con Heurística Híbrida.")
    
    parser.add_argument("-i", "--instance", type=str, required=True, 
                        help="Nombre de la instancia (ej: 2000x2000_1)")
    parser.add_argument("-n", "--iterations", type=int, default=100, 
                        help="Número de iteraciones para la heurística")
    parser.add_argument("-m", "--mode", type=str, default="SS", 
                        choices=["SS", "MS"], help="Modo: Single-Source (SS) o Multi-Source (MS)")

    args = parser.parse_args()
    
    main(args.instance, args.iterations, args.mode)