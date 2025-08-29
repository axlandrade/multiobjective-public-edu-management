@echo OFF
echo "Iniciando a bateria de experimentos..."

echo "Executando para P1..."
python src/main.py --data data/run1_P1_k5.csv --output_dir resultados/run1_P1_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P2_k5.csv --output_dir resultados/run1_P2_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P3_k5.csv --output_dir resultados/run1_P3_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P4_k5.csv --output_dir resultados/run1_P4_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P5_k5.csv --output_dir resultados/run1_P5_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P6_k5.csv --output_dir resultados/run1_P6_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P7_k5.csv --output_dir resultados/run1_P7_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P8_k5.csv --output_dir resultados/run1_P8_k5 --time_limit 3600

echo "Executando para P2..."
python src/main.py --data data/run1_P9_k5.csv --output_dir resultados/run1_P9_k5 --time_limit 3600

echo "Executando para P10..."
python src/main.py --data data/run1_P10_k5.csv --output_dir resultados/run1_P10_k5 --time_limit 3600

echo "Bateria de experimentos concluida!"
pause