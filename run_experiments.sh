#!/bin/bash
echo "======================================================"
echo "Starting the MULTI-OBJECTIVE experiment batch run..."
echo "======================================================"

# --- Configuration ---
# Define the probability sets (P1 to P10) to test
PROB_SETS=("P1" "P2" "P3" "P4" "P5" "P6" "P7" "P8" "P9" "P10")

# Define the LAMBDA values to explore for each instance
LAMBDA_VALUES=(0.0 0.25 0.5 0.75 1.0)

# Other parameters
K_VALUE=5
TIME_LIMIT=3600
INSTANCE_PREFIX="run1"

# --- Execution Loop ---
# Outer loop: Iterate through each probability set
for P_SET in "${PROB_SETS[@]}"
do
    INSTANCE_NAME="${INSTANCE_PREFIX}_${P_SET}_k${K_VALUE}"
    INSTANCE_FILE="data/${INSTANCE_NAME}.csv"
    
    echo ""
    echo ">>> Processing Instance: $INSTANCE_NAME <<<"
    
    # Check if the data file exists
    if [ ! -f "$INSTANCE_FILE" ]; then
        echo "Warning: Data file not found, skipping: $INSTANCE_FILE"
        continue
    fi

    # Inner loop: Iterate through each lambda value
    for LAMBDA in "${LAMBDA_VALUES[@]}"
    do
        echo "----------------------------------------"
        echo "Executing with LAMBDA = $LAMBDA"
        
        OUTPUT_DIR="results/${INSTANCE_NAME}_lambda_${LAMBDA}"
        
        # Execute the main Python script
        python src/main.py \
          --data "$INSTANCE_FILE" \
          --output_dir "$OUTPUT_DIR" \
          --lambda_weight "$LAMBDA" \
          --time_limit $TIME_LIMIT
        
        echo "Finished execution for LAMBDA = $LAMBDA"
    done
    echo ">>> Finished all lambda tests for Instance: $INSTANCE_NAME <<<"
done

echo ""
echo "======================================================"
echo "All experiment batches completed!"
echo "======================================================"