# Paso 1: Crear entorno virtual

1.- Abrir la carpeta con el proyecto en vs code
2.- crear entorno virtual ejecutando 
```bash 
python -m venv .venv 
```
3.- activar entorno:
- Windows:   
```bash
Set-ExecutionPolicy RemoteSigned -Scope Process
.venv\Scripts\activate
```
- Linux/macOS: 
```bash
source .venv/bin/activate
```
4.- Seleccionar interprete (usar este nuevo entorno)
5.- Instalar librerias usando el comando 
```bash
pip install -r requirements.txt
```

# Paso 2: Ejecutar Opciones:

## Transformar instancias .txt a .dat:

```bash
python src/main.py -a parse
```

## Resolver el optimo segun instancia

### Para Single-Source (SS)
```bash
python src/main.py -a optimal -i Instance50x50 -m SS
```
```bash
python src/main.py -a optimal -i Instance1000x300 -m SS
```
```bash
python src/main.py -a optimal -i 2000x2000_1 -m SS
```
```bash
python src/main.py -a optimal -i 4000x4000_1 -m SS
```
```bash
python src/main.py -a optimal -i 5000x5000_1 -m SS
```

### Para Multi-Source (MS)
```bash
python src/main.py -a optimal -i Instance50x50 -m MS
```
```bash
python src/main.py -a optimal -i Instance1000x300 -m MS
```
```bash
python src/main.py -a optimal -i 2000x2000_1 -m MS
```
```bash
python src/main.py -a optimal -i 4000x4000_1 -m MS
```
```bash
python src/main.py -a optimal -i 5000x5000_1 -m MS
```

## Resolver con heurística

### Corridas para Single-Source (SS)

```bash
python src/main.py -a heuristic -i Instance50x50 -m SS -n 1000
```
```bash
python src/main.py -a heuristic -i Instance1000x300 -m SS -n 1000
```
```bash
python src/main.py -a heuristic -i 2000x2000_1 -m SS -n 1000
```
```bash
python src/main.py -a heuristic -i 4000x4000_1 -m SS -n 500
```
```bash
python src/main.py -a heuristic -i 5000x5000_1 -m SS -n 100
```
### Corridas para Multi-Source (MS)

```bash
python src/main.py -a heuristic -i Instance50x50 -m MS -n 1000
```
```bash
python src/main.py -a heuristic -i Instance1000x300 -m MS -n 1000
```
```bash
python src/main.py -a heuristic -i 2000x2000_1 -m MS -n 1000
```
```bash
python src/main.py -a heuristic -i 4000x4000_1 -m MS -n 500
```
```bash
python src/main.py -a heuristic -i 5000x5000_1 -m MS -n 100
```