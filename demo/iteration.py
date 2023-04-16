"""
FOR DEMONSTRATION PURPOSES ONLY.

Used for the demonstration video. Fakes an iteration step, "predicting" correct and incorrect annotations
which can later be approved or discarded by the tool.
"""
import os
import pandas as pd
import numpy as np

from const import *

subsample = pd.read_csv(PATH_SUBSAMPLE, sep="|", low_memory=False)
initial = pd.read_csv(PATH_INITIAL, sep="|", low_memory=False)

# Initial and approved contain images already labeled
labeled = initial
next_idx = 0
for approved in sorted([os.path.join(PATH_MODEL, f) for f in os.listdir(PATH_MODEL) if "approved" in f], key=lambda x: int(x.split("_")[1])):
    labeled = pd.concat([labeled, pd.read_csv(approved, sep="|")])
    next_idx += 1

# Sample from the remaining images
np.random.seed(SEED)
remaining = subsample.loc[~subsample["image_name"].isin(labeled["image_name"].unique())]
next_sample = remaining.loc[remaining["image_name"].isin(np.random.choice(a=remaining["image_name"].unique(), size=N_PER_ITERATION, replace=False))]
next_sample.reset_index(inplace=True, drop=True)

# Fake predictions by altering two of four images
index_altered = next_sample.loc[next_sample["image_name"].isin(next_sample["image_name"].unique()[2:])].index

# Add some noise
# noise = np.random.normal(loc=0.0, scale=100.0, size=(len(index_altered), 4))
# next_sample.loc[index_altered, ["bbox_xmin", "bbox_ymin", "bbox_width", "bbox_height"]] += noise

# Randomly drop annotations
drop_indices = np.random.choice(index_altered, 10, replace=False)
next_sample = next_sample.drop(drop_indices).reset_index(drop=True)

# Save next sample (fake iteration)
next_sample.to_csv(os.path.join(PATH_MODEL, f"predictions_{next_idx}.csv"), sep="|", index=False)
