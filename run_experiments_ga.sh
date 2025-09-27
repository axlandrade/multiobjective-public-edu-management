#!/bin/bash
echo "======================================================"
echo "Starting the GENETIC ALGORITHM experiment batch run..."
echo "======================================================"

# --- Configuration ---
PROB_SETS=("P1" "P2" "P3" "P4" "P5" "P6" "P7" "P8" "P9" "P10")
K_VALUE=5
INSTANCE_PREFIX="run1"

# --- Execution Loop ---
for P_SET in "${PROB_SETS[@]}"
do
    INSTANCE_NAME="${INSTANCE_PREFIX}_${P_SET}_k${K_VALUE}"
    INSTANCE_FILE="data/${INSTANCE_NAME}.csv"
    
    echo ""
    echo ">>> Processing Instance with GA: $INSTANCE_NAME <<<"
    
    if [ ! -f "$INSTANCE_FILE" ]; then
        echo "Warning: Data file not found, skipping: $INSTANCE_FILE"
        continue
    fi

    # Execute the main GA script
    python src/run_genetic_algorithm.py --data "$INSTANCE_FILE"
    
    echo ">>> Finished GA execution for: $INSTANCE_NAME <<<"
done

echo ""
echo "======================================================"
echo "All GA experiment batches completed!"
echo "======================================================"