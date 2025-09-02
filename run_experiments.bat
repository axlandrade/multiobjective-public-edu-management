@echo OFF
echo "Starting Experiments..."

echo "Running for P1..."
python src\main.py --data data\run1_P1_k5.csv --output_dir results\run1_P1_k5 --time_limit 3600

echo "Running for P2..."
python src\main.py --data data\run1_P2_k5.csv --output_dir results\run1_P2_k5 --time_limit 3600

echo "Running for P3..."
python src\main.py --data data\run1_P3_k5.csv --output_dir results\run1_P3_k5 --time_limit 3600

echo "Running for P4..."
python src\main.py --data data\run1_P4_k5.csv --output_dir results\run1_P4_k5 --time_limit 3600

echo "Running for P5..."
python src\main.py --data data\run1_P5_k5.csv --output_dir results\run1_P5_k5 --time_limit 3600

echo "Running for P6..."
python src\main.py --data data\run1_P6_k5.csv --output_dir results\run1_P6_k5 --time_limit 3600

echo "Running for P7..."
python src\main.py --data data\run1_P7_k5.csv --output_dir results\run1_P7_k5 --time_limit 3600

echo "Running for P8..."
python src\main.py --data data\run1_P8_k5.csv --output_dir results\run1_P8_k5 --time_limit 3600

echo "Running for P9..."
python src\main.py --data data\run1_P9_k5.csv --output_dir results\run1_P9_k5 --time_limit 3600

echo "Running for P10..."
python src\main.py --data data\run1_P10_k5.csv --output_dir results\run1_P10_k5 --time_limit 3600

echo "Experiments done!"
pause