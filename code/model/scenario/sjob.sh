#!/bin/bash
#SBATCH --job-name hiv-esw
#SBATCH --nodes=1
#SBATCH --cpus-per-task=40
#SBATCH --time=0:15:00
#SBATCH --array=0

module load python/3.8
# pip install --upgrade scipy pathos PyPDF2
export MPLCONFIGDIR=$SCRATCH
export PYTHONPATH=.:$PYTHONPATH
# python3.8 model/scenario/imis.py scinet case=base b=$SLURM_ARRAY_TASK_ID
# python3.8 model/scenario/art.py scinet b=$SLURM_ARRAY_TASK_ID
# python3.8 model/scenario/foi.py scinet case=TODO b=$SLURM_ARRAY_TASK_ID

# using this script on scinet:
# sbatch scinet.sh
