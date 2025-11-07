# Paso 1: Crear entorno virtual

1.- Abrir la carpeta con el proyecto en vs code
2.- crear entorno virtual ejecutando python -m venv .venv
3.- activar entorno:
- Windows: .venv\Scripts\activate
- Linux/macOS: source .venv/bin/activate
4.- Seleccionar interprete (usar este nuevo entorno)
5.- Instalar librerias pip install amplpy pandas 

# opciones:

**parsear todo (solo ejecutar una vez):**

- python src/main.py -a parse

**Resolver el optimo segun instancia**

Corridas para Single-Source (SS)

python src/main.py -a optimal -i Instance50x50 -m SS
python src/main.py -a optimal -i Instance1000x300 -m SS
python src/main.py -a optimal -i 2000x2000_1 -m SS
python src/main.py -a optimal -i 4000x4000_1 -m SS
python src/main.py -a optimal -i 5000x5000_1 -m SS

Corridas para Multi-Source (MS)

python src/main.py -a optimal -i Instance50x50 -m MS
python src/main.py -a optimal -i Instance1000x300 -m MS
python src/main.py -a optimal -i 2000x2000_1 -m MS
python src/main.py -a optimal -i 4000x4000_1 -m MS
python src/main.py -a optimal -i 5000x5000_1 -m MS

**Resolver con heurística**

Corridas para Single-Source (SS)
python src/main.py -a heuristic -i Instance50x50 -m SS -n 1000
python src/main.py -a heuristic -i Instance1000x300 -m SS -n 1000
python src/main.py -a heuristic -i 2000x2000_1 -m SS -n 1000
python src/main.py -a heuristic -i 4000x4000_1 -m SS -n 500
python src/main.py -a heuristic -i 5000x5000_1 -m SS -n 100

Corridas para Multi-Source (MS)
python src/main.py -a heuristic -i Instance50x50 -m MS -n 1000
python src/main.py -a heuristic -i Instance1000x300 -m MS -n 1000
python src/main.py -a heuristic -i 2000x2000_1 -m MS -n 1000
python src/main.py -a heuristic -i 4000x4000_1 -m MS -n 500
python src/main.py -a heuristic -i 5000x5000_1 -m MS -n 100