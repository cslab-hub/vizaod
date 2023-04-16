import pandas as pd
import json
import argparse
import os

from io import StringIO
from csv import writer

from tqdm import tqdm


HEADER_COLUMNS = [
    "image_name",
    "image_id",
    "image_width",
    "image_height",
    "annotation_id",
    "category",
    "category_id",
    "iscrowd",
    "bbox_xmin",
    "bbox_ymin",
    "bbox_xmax",
    "bbox_ymax",
    "bbox_width",
    "bbox_height",
    "bbox_area",
    "segmentation",
    "segmentation_area"
]


def convert_coco_json_to_csv(input_json_file, tqdm_progress_bar=False):
    """_summary_

    Args:
        input_json_file (_type_): _description_
        tqdm_progress_bar (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    file = open(input_json_file, "r")

    # Load the JSON annotations
    json_dict = json.load(file)
    json_dict["images"] = sorted(json_dict["images"], key=lambda d: d["id"])
    json_dict["annotations"] = sorted(json_dict["annotations"], key=lambda d: d["image_id"])
    id_to_category = {x["id"]: x["name"] for x in json_dict["categories"]}

    # Prepare bytes object
    output = StringIO()
    csv_writer = writer(output, delimiter="|")

    # Write the header
    csv_writer.writerow(HEADER_COLUMNS)

    # Iterate over the JSON dictionary and convert the contents into CSV rows
    ann_idx_s = 0
    ann_idx_e = 0
    row_idx = 0
    no_images = len(json_dict["images"])

    # Iterate over all images
    if tqdm_progress_bar:
        iterator = tqdm(json_dict["images"])
    else:
        iterator = json_dict["images"]
    for img_dict in iterator:

        # Find indexes for start and endpoint of the annotations for the current image
        tmp = img_dict["id"]
        while tmp == img_dict["id"]:
            ann_idx_e += 1
            try:
                tmp = json_dict["annotations"][ann_idx_e]["image_id"]
            except IndexError:
                break

        # Iterate over all annotations for the current image
        for ann_dict in json_dict["annotations"][ann_idx_s:ann_idx_e]:
            row = [
                img_dict["file_name"],                          # image_name
                img_dict["id"],                                 # image_id
                img_dict["width"],                              # image_width
                img_dict["height"],                             # image_height
                ann_dict["id"],                                 # annotation_id
                id_to_category[ann_dict["category_id"]],        # category
                ann_dict["category_id"],                        # category_id
                ann_dict["iscrowd"],                            # iscrowd
                ann_dict["bbox"][0],                            # bbox_xmin
                ann_dict["bbox"][1],                            # bbox_ymin
                ann_dict["bbox"][0] + ann_dict["bbox"][2],      # bbox_xmax
                ann_dict["bbox"][1] + ann_dict["bbox"][3],      # bbox_ymax
                ann_dict["bbox"][2],                            # bbox_width
                ann_dict["bbox"][3],                            # bbox_height
                ann_dict["bbox"][2] * ann_dict["bbox"][3],      # bbox_area
                ann_dict["segmentation"],                       # segmentation
                ann_dict["area"]                                # segmentation_area
            ]
            csv_writer.writerow(row)
            row_idx += 1

        # Update annotation indices
        ann_idx_s = ann_idx_e

    # Read results into dataframe and return it
    output.seek(0)
    df = pd.read_csv(output, sep="|")

    return df


# For usage as a standalone script
if __name__ == "__main__":
    
    # Parse and check the input arguments
    parser = argparse.ArgumentParser(description="JSON to CSV annotation file converter for the JSON COCO annotation format.")
    parser.add_argument("-i", "--input-json-file", dest="input_json_file", type=str, help="Input JSON file.", required=True)
    parser.add_argument("-o", "--output-csv-file", dest="output_csv_file", type=str, help="Output CSV file. Defaults to the " + \
                            "name of the input JSON file (with .csv extension instead of .json)", required=False)
    args = parser.parse_args()
    input_json_file = args.input_json_file
    output_csv_file = args.output_csv_file

    if not os.path.exists(input_json_file):
        print(f"Input JSON file '{input_json_file}' does not exist!")
        exit()

    if not output_csv_file:
        output_csv_file = f"{input_json_file[:-5]}.csv"

    print(f"Converting annotations from '{input_json_file}' to '{output_csv_file}' ...")

    if os.path.exists(output_csv_file):
        print(f"WARNING: This will overwrite the contents of '{output_csv_file}'!")
        input("Press ENTER to contine, CTRL+C to cancel ...")

    df = convert_coco_json_to_csv(input_json_file, True)

    df.to_csv(output_csv_file, sep="|", index=False)

