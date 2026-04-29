# ==============================================================================
# FILE: run.py
# PURPOSE: Be the obvious file you can run to execute the whole project.
# ==============================================================================
#
# WHEN YOU RUN THIS FILE, THE PROJECT WILL:
#   1. Read the real CSV files from data/
#   2. Build the recommendation graph
#   3. Attach ideology scores to each channel/node
#   4. Simulate recommendation-following paths
#   5. Compute summary metrics
#   6. Save figures and a CSV summary into results/
#
# ==============================================================================


# Import the "main" function from the real pipeline file.
from src.run_pipeline import main


if __name__ == "__main__":
    main()