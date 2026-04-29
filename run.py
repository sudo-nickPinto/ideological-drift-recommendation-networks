# ==============================================================================
# FILE: run.py
# PURPOSE: Be the ONE obvious file you can run to execute the whole project.
# ==============================================================================
#
# HIGH-LEVEL EXPLANATION:
#   If you are new to Python, this is the file you should care about.
#
#   You do NOT need to understand every module in src/ before using the
#   project. This file exists so you can do one simple thing:
#
#       open run.py
#       press the VS Code Play button
#
#   That runs the full workflow for you.
#
# WHAT THIS FILE DOES:
#   This file does not do the heavy analysis itself.
#   Instead, it calls the real pipeline code in src/run_pipeline.py.
#
#   In plain English:
#   - run.py = the front door
#   - src/run_pipeline.py = the full checklist behind the door
#
# WHEN YOU RUN THIS FILE, THE PROJECT WILL:
#   1. Read the real CSV files from data/
#   2. Build the recommendation graph
#   3. Attach ideology scores to each channel/node
#   4. Simulate recommendation-following paths
#   5. Compute summary metrics
#   6. Save figures and a CSV summary into results/
#
# WHY THIS FILE IS SMALL:
#   Beginner-friendly code often benefits from having one obvious starting
#   point. Keeping this file short makes it easy to answer the question:
#
#       "What do I click to run everything?"
#
#   The answer is: click Play on this file.
#
# ==============================================================================


# Import the "main" function from the real pipeline file.
#
# A function is a named chunk of code that does a job.
# Here, the job of main() is: run the whole project.
from src.run_pipeline import main


if __name__ == "__main__":
    # This special Python line means:
    # "If this file is the one the user started, begin running here."
    #
    # That is what makes the Play button work on run.py.
    main()