"""
FOR DEMONSTRATION PURPOSES ONLY.

Preparation of the files needed for the demonstration video.
"""
import os
import shutil
import pandas as pd
import numpy as np

import argparse

from const import *


# Parse arguments
parser = argparse.ArgumentParser(description="Preparation for the demonstration video.")
parser.add_argument("-pi", "--path-images", dest="path_images", type=str, help="Path to the images to subsample from.", required=True)
parser.add_argument("-pa", "--path-annotations", dest="path_annotations", type=str, help="Path to the annotations to subsample from.", required=True)
args = parser.parse_args()

# Check if given paths exist
if not os.path.exists(args.path_images):
    print(f"Path to images '{args.path_images}' does not exist!")
    exit()
if not os.path.exists(args.path_annotations):
    print(f"Path to annotations '{args.path_annotations}' does not exist!")
    exit()

# If the demonstration directory already exist, delete it and create new
if os.path.exists(PATH_SUBSAMPLE):
    os.remove(PATH_SUBSAMPLE)
if os.path.exists(PATH_SSOD):
    shutil.rmtree(PATH_SSOD)
os.mkdir(PATH_SSOD)
os.mkdir(PATH_IMAGES)
os.mkdir(PATH_MODEL)

# Randomly subsample from the given dataset
print(f"Subsampling {N_SAMPLES} images and their corresponding annotations ...")
np.random.seed(SEED)
original = pd.read_csv(args.path_annotations, sep="|", low_memory=False)
subsample = original.loc[original["image_name"].isin(np.random.choice(a=original["image_name"].unique(), size=N_SAMPLES, replace=False))]
subsample.to_csv(PATH_SUBSAMPLE, sep="|", index=False)

# Copy the randomly subsampled images
print(f"Copying the images ...")
for image_name in subsample["image_name"].unique():
    cmd = "cp " + os.path.join(args.path_images, image_name) + " " + os.path.join(PATH_IMAGES, image_name)
    os.system(cmd)

# Create an initial subsample (used for the first training step)
print(f"Sampling the initial annotations ...")
initial = subsample.loc[subsample["image_name"].isin(np.random.choice(a=subsample["image_name"].unique(), size=N_INITIAL, replace=False))]
initial.to_csv(PATH_INITIAL, sep="|", index=False)
