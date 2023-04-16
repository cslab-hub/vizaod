"""

    SSODViz - Visual Annotation Verification for Semi-Supervised Object Detection
    
    This tool is intended to ease the process of manually reviewing
    predicted annotations for semi-supervised object detection, mainly
    focusing on object detection in document layout analysis.

"""
__author__      = "David Massanés, University Osnabrück"
__copyright__   = "Copyright 2023, University Osnabrück"
__credits__     = ["David Massanés", "Arnab Ghosh Chowdhury", "Martin Atzmüller"]

from dash import Dash, html, dcc, Output, Input, State, callback_context, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from dash.dash_table import DataTable
from dash.dash_table.Format import Format, Scheme

import plotly.graph_objs as go
import plotly.express as px

import cv2
from matplotlib.colors import to_rgba

import pandas as pd

import os
import traceback

import convert_to_csv


# Change these values to set the default paths shown in the "Configurations" card
PATH_IMAGES         = "demo/ssod/images"
PATH_ANNOTATIONS    = "demo/ssod/model/predictions_0.csv"
PATH_APPROVED       = "demo/ssod/model/predictions_0_approved.csv"
PATH_DISCARDED      = "demo/ssod/model/predictions_0_discarded.csv"


# Constants & important variables
COLORS      = px.colors.qualitative.Dark24
APP_TITLE   = "SSODViz - Visual Annotation Verification for Semi-Supervised Object Detection"

TABLE_COLS  = ["category", "bbox_xmin", "bbox_ymin", "bbox_width", "bbox_height"]
FIXED_FORMAT = Format(precision=3, scheme=Scheme.fixed)
TABLE_COLS_SPECS = [
    dict(id="category", name="category"),
    dict(id="bbox_xmin", name="bbox_xmin", type="numeric", format=FIXED_FORMAT),
    dict(id="bbox_ymin", name="bbox_ymin", type="numeric", format=FIXED_FORMAT),
    dict(id="bbox_width", name="bbox_width", type="numeric", format=FIXED_FORMAT),
    dict(id="bbox_height", name="bbox_height", type="numeric", format=FIXED_FORMAT)
]

AUTOSAVE = True

INITIALIZED = False

CRT_IMG_IDX     = 0
CRT_IMG_NAME    = ""

CATEGORIES = []
ANNOTATION_COLORS = []

# Dataframes
ANNOTATIONS = pd.DataFrame()
APPROVED    = pd.DataFrame()
DISCARDED   = pd.DataFrame()


# ===============================================================================================================================================
#   HELPER FUNCTIONS
# ===============================================================================================================================================
def blank_figure():
    figure = go.Figure(go.Scatter(x=[], y = []))
    figure.update_layout(template=None)
    figure.update_xaxes(showgrid=False, showticklabels=False, zeroline=False)
    figure.update_yaxes(showgrid=False, showticklabels=False, zeroline=False)
    return figure

def image_figure(image_name):
    global PATH_IMAGES, ANNOTATIONS, ANNOTATION_COLORS

    if not image_name:
        return blank_figure()

    image_path = os.path.join(PATH_IMAGES, image_name)

    if not os.path.exists(image_path):
        print(f"Image '{image_path}' does not exist!")
        return blank_figure()

    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    fig = px.imshow(img)

    anns = [(row["bbox_xmin"], row["bbox_ymin"], row["bbox_width"], row["bbox_height"], row["category"]) \
                for _, row in ANNOTATIONS.loc[ANNOTATIONS["image_name"] == image_name].iterrows()]

    for ann in anns:
        color = ANNOTATION_COLORS[ann[4]]
        fig.add_shape(
            type="rect",
            x0=ann[0],
            y0=ann[1],
            x1=ann[2] + ann[0],
            y1=ann[3] + ann[1],
            line=dict(color=color, width=3)
        )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
    )
    
    return fig

def check_status(image_name):
    global APPROVED, DISCARDED
    if image_name in APPROVED["image_name"].values or "approved" in PATH_ANNOTATIONS:
        return ["Approved", "success"]
    elif image_name in DISCARDED["image_name"].values or "discarded" in PATH_ANNOTATIONS:
        return ["Discarded", "danger"]
    return ["Not analysed", "secondary"]

def next_image(step):
    global ANNOTATIONS, CRT_IMG_IDX, CRT_IMG_NAME
    img_names = ANNOTATIONS["image_name"].drop_duplicates()
    CRT_IMG_IDX = (CRT_IMG_IDX + step) % len(img_names)
    CRT_IMG_NAME = img_names.values[CRT_IMG_IDX]

def save_progress_approved():
    global APPROVED, PATH_APPROVED
    if PATH_APPROVED != "":
        APPROVED.to_csv(PATH_APPROVED, sep="|", index=False)

def save_progress_discarded():
    global DISCARDED, PATH_DISCARDED
    if PATH_DISCARDED != "":
        DISCARDED.to_csv(PATH_DISCARDED, sep="|", index=False)

def save_progress():
    save_progress_approved()
    save_progress_discarded()

def format_traceback():
    return html.Pre(traceback.format_exc())


# ===============================================================================================================================================
#   MAIN
# ===============================================================================================================================================
if __name__ == "__main__":

    # Create the Dash app
    external_stylesheets = [dbc.themes.PULSE, "assets/styles.css"]
    app = Dash(APP_TITLE, external_stylesheets=external_stylesheets)
    app.title = APP_TITLE

    # ===============================================================================================================================================
    #   APP LAYOUT
    # ===============================================================================================================================================
    navbar = dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    html.A(
                        html.Img(
                            src=app.get_asset_url("uos.png"),
                            alt="Link to the GitHub repository containing the source code ...",
                            height="40px"
                        ),
                        href="https://github.com/cslab-hub/ssodviz"
                    )
                ),
                dbc.Col(
                    dbc.NavbarBrand(APP_TITLE)
                ),
                dbc.Col(
                    dbc.Button("Convert Annotations", id="button_open_modal_conversion", outline=True, color="light", className="me-1", style={"width": "200px"})
                )
            ], align="center")
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-5",
    )

    image_card = dbc.Card([
        dbc.CardHeader(
            html.H3("Image Name: \"" + CRT_IMG_NAME + "\"", id="image_name")
        ),
        dbc.CardBody(
            dcc.Graph(
                id="image_graph",
                figure=blank_figure(),
                style={"height": "716px"}
            ),
            style={"padding": "0px"}
        ),
        dbc.CardFooter(
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Previous image", id="button_previous", className="me-1", outline=True, color="primary", style={"width": "100%"}),
                    ], md=4),
                    dbc.Col([
                        dbc.Badge("Not analysed", id="badge_analysed", color="secondary", pill=True, class_name="me-1", style={"width": "100%", "height": "100%", "font-size": "18px"})
                    ], md=4),
                    dbc.Col([
                        dbc.Button("Next image", id="button_next", className="me-1", outline=True, color="primary", style={"width": "100%"})
                    ], md=4)
                ], style={"height": "100%"}, justify="center", align="center")
            ])
        )
    ])
    
    config_card = dbc.Card([
        dbc.CardHeader(html.H3("Configuration")),
        dbc.CardBody([
            dbc.Container([
                dbc.Row([
                    dbc.Col("PATH_IMAGES", md=3),
                    dbc.Col(dcc.Input(id="input_path_images", value=PATH_IMAGES, style={"width": "100%"}), md=9)
                ]),
                dbc.Row([
                    dbc.Col("PATH_ANNOTATIONS", md=3),
                    dbc.Col(dcc.Input(id="input_path_annotations", value=PATH_ANNOTATIONS, style={"width": "100%"}), md=9)
                ]),
                dbc.Row([
                    dbc.Col("PATH_APPROVED", md=3),
                    dbc.Col(dcc.Input(id="input_path_approved", value=PATH_APPROVED, style={"width": "100%"}), md=9)
                ]),
                dbc.Row([
                    dbc.Col("PATH_DISCARDED", md=3),
                    dbc.Col(dcc.Input(id="input_path_discarded", value=PATH_DISCARDED, style={"width": "100%"}), md=9)
                ])
            ])
        ]),
        dbc.CardFooter(
            # dbc.ButtonGroup([
            dbc.Button("Start", id="button_start", className="me-1", outline=True, color="primary", style={"width": "100%"})
                # dbc.Button("Save progess", id="button_save", className="me-1", outline=True, color="primary", style={"width": "100%"}),
                # dbc.Button("Autosave progess: Disabled", id="button_autosave", className="me-1", outline=True, color="primary", style={"width": "100%"})
            # ], style={"width": "100%"})
        )
    ], style={"margin-bottom": "10px"})


    annotation_card = dbc.Card([
        dbc.CardHeader(html.H3("Annotation Information")),
        dbc.CardBody(
            DataTable(
                id="annotations_table",
                columns=TABLE_COLS_SPECS,
                editable=False
            )
        ),
        dbc.CardFooter(
            dbc.ButtonGroup([
                dbc.Button("Approve annotations", id="button_approve", className="me-1", outline=True, color="success"),
                dbc.Button("Discard annotations", id="button_discard", className="me-1", outline=True, color="danger")
            ], style={"width": "100%"})
        )
    ])

    app.layout = html.Div([
        navbar,
        dbc.Container([
            dbc.Row([
                dbc.Alert(
                    "Alert Main",
                    id="alert_main",
                    is_open=False,
                    duration=5000,
                    color="danger"
                ),
            ]),
            dbc.Row([
                dbc.Col(image_card, md=6),
                dbc.Col([
                    config_card,
                    annotation_card
                ], md=6, style={"padding-left": "5px"})
            ])
        ], fluid=True, style={"margin-top": "-48px", "padding": "10px"}),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Annotation Conversion")),
            dbc.ModalBody([
                dbc.Container([
                    dbc.Row([
                        dbc.Alert(
                            "Alert Modal",
                            id="alert_modal",
                            is_open=False,
                            duration=3000,
                            color="danger"
                        )
                    ]),
                    dbc.Row(
                        "Here you can convert a JSON file containing the annotations for your dataset into a CSV file with the format we are using for this application. Note that only the conversion from the COCO JSON format is currently supported.",
                        style={"margin-bottom": "20px", "margin-top": "0px"}
                    ),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col("Path to JSON file", md=3),
                        dbc.Col(dcc.Input(id="input_path_json", value="demo/conversion/annotations.json", style={"width": "100%"}), md=9)
                    ]),
                    dbc.Row([
                        dbc.Col("Path to CSV file", md=3),
                        dbc.Col(dcc.Input(id="input_path_csv", value="demo/conversion/annotations.csv", style={"width": "100%"}), md=9)
                    ], style={"margin-bottom": "10px"}),
                    dbc.Row([
                        dbc.Button(dbc.Spinner("Generate CSV", id="spinner_conversion"), id="button_conversion", className="me-1", outline=True, color="primary", style={"width": "100%"}),
                    ]),
                    dcc.ConfirmDialog(
                        id="confirm_conversion",
                        message="Do you really want to convert the annotations? This will overwrite the CSV file if it already exists!"
                    )
                ], fluid=True, style={"padding": "10px"})
            ])
        ], id="modal_conversion", is_open=False, size="lg"),
        dcc.ConfirmDialog(
            id="confirm_start",
            message="Do you really want to start?"
        ),
        dcc.ConfirmDialog(
            id="confirm_save",
            message="Do you really want to save your current progress? This will overwrite the csv files 'PATH_APPROVED' and 'PATH_DISCARDED' if they already exist!"
        )
    ], id="main_div")

    # ===============================================================================================================================================
    #   CALLBACKS
    # ===============================================================================================================================================
    @app.callback(
        [
            Output("image_graph", "figure", allow_duplicate=True),
            Output("annotations_table", "data", allow_duplicate=True),
            Output("image_name", "children", allow_duplicate=True),
            Output("badge_analysed", "children", allow_duplicate=True),
            Output("badge_analysed", "color", allow_duplicate=True),
            Output("alert_main", "children", allow_duplicate=True),
            Output("alert_main", "is_open", allow_duplicate=True)
        ],
        [
            Input("button_previous", "n_clicks"),
            Input("button_next", "n_clicks"),
            Input("button_approve", "n_clicks"),
            Input("button_discard", "n_clicks")
        ],
        prevent_initial_call=True
    )
    def update_figure_and_annotations(
        n_clicks_previous,
        n_clicks_next,
        n_clicks_approve,
        n_clicks_discard
    ):
        global PATH_IMAGES, PATH_ANNOTATIONS, PATH_APPROVED, PATH_DISCARDED, \
                ANNOTATIONS, APPROVED, DISCARDED, \
                CRT_IMG_IDX, CRT_IMG_NAME, \
                CATEGORIES, ANNOTATION_COLORS, TABLE_COLS, \
                AUTOSAVE, INITIALIZED

        if not INITIALIZED:
            return [no_update, no_update, no_update, no_update, no_update, "WARNING: You haven't started yet!", True]

        if len(ANNOTATIONS) == 0:
            return [no_update, no_update, no_update, no_update, no_update, f"WARNING: There are no annotations contained in the '{PATH_ANNOTATIONS}' file!", True]

        cbcontext = [p["prop_id"] for p in callback_context.triggered][0]

        # Do not update if we do not trigger any inputs
        if cbcontext == ".":
            raise PreventUpdate

        # Show previous image
        if cbcontext == "button_previous.n_clicks":
            next_image(-1)

        # Show next image
        elif cbcontext == "button_next.n_clicks":
            next_image(1)

        # Move the annotations to the approved CSV
        elif cbcontext == "button_approve.n_clicks":
            if PATH_APPROVED == "":
                return [no_update, no_update, no_update, no_update, no_update, f"WARNING: You can't approve any annotations when the path 'PATH_APPROVED' is not given!", True]
            APPROVED = pd.concat([APPROVED, ANNOTATIONS.loc[ANNOTATIONS["image_name"] == CRT_IMG_NAME]])
            DISCARDED = DISCARDED.loc[DISCARDED["image_name"] != CRT_IMG_NAME]
            if AUTOSAVE:
                save_progress()
            next_image(1)

        # Move the annotations to the discarded CSV
        elif cbcontext == "button_discard.n_clicks":
            if PATH_DISCARDED == "":
                return [no_update, no_update, no_update, no_update, no_update, f"WARNING: You can't discard any annotations when the path 'PATH_DISCARDED' is not given!", True]
            DISCARDED = pd.concat([DISCARDED, ANNOTATIONS.loc[ANNOTATIONS["image_name"] == CRT_IMG_NAME]])
            APPROVED = APPROVED.loc[APPROVED["image_name"] != CRT_IMG_NAME]
            if AUTOSAVE:
                save_progress()
            next_image(1)

        return [
            image_figure(CRT_IMG_NAME), 
            ANNOTATIONS.loc[ANNOTATIONS["image_name"] == CRT_IMG_NAME][TABLE_COLS].to_dict("records"),
            "Image Name: \"" + CRT_IMG_NAME + "\"",
            *check_status(CRT_IMG_NAME),
            no_update, no_update
        ]

    # ======================================================================================
    #   Callbacks related to the input paths in the configuration card
    # ======================================================================================
    @app.callback(
        [
            Output("input_path_approved", "value"),
            Output("input_path_discarded", "value")
        ],
            Input("input_path_annotations", "value")
    )
    def cb_update_path_inputs(
        value
    ):
        cbcontext = [p["prop_id"] for p in callback_context.triggered][0]

        # Do not update if we do not trigger any inputs
        if cbcontext == ".":
            raise PreventUpdate

        if "initial" in value or "approved" in value or "discarded" in value:
            return ["", ""]

        return [
            value[:-4] + "_approved.csv",
            value[:-4] + "_discarded.csv"
        ]

    # ======================================================================================
    #   Callbacks related to the conversion modal
    # ======================================================================================
    @app.callback(
        Output("modal_conversion", "is_open"),
        Input("button_open_modal_conversion", "n_clicks"),
        State("modal_conversion", "is_open")
    )
    def cb_open_modal(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    @app.callback(
        Output("confirm_conversion", "displayed"),
        Input("button_conversion", "n_clicks"),
        prevent_initial_call=True
    )
    def cb_display_confirm_conversion(n_clicks):
        return True

    @app.callback(
        Output("spinner_conversion", "children"),
        Input("confirm_conversion", "submit_n_clicks"),
        [
            State("input_path_json", "value"),
            State("input_path_csv", "value")
        ],
        prevent_initial_call=True
    )
    def conversion(n_clicks, input_path_json, input_path_csv):
        df = convert_to_csv.convert_coco_json_to_csv(input_path_json)
        df.to_csv(input_path_csv, sep="|", index=False)
        return no_update

    # ======================================================================================
    #   Callbacks for start
    # ======================================================================================
    @app.callback(
        [
            Output("image_graph", "figure", allow_duplicate=True),
            Output("annotations_table", "data", allow_duplicate=True),
            Output("annotations_table", "style_data_conditional"),
            Output("image_name", "children", allow_duplicate=True),
            Output("badge_analysed", "children", allow_duplicate=True),
            Output("badge_analysed", "color", allow_duplicate=True),
            Output("alert_main", "children", allow_duplicate=True),
            Output("alert_main", "is_open", allow_duplicate=True)
        ],
            Input("confirm_start", "submit_n_clicks"),
        [
            State("input_path_images", "value"),
            State("input_path_annotations", "value"),
            State("input_path_approved", "value"),
            State("input_path_discarded", "value")
        ],
        prevent_initial_call=True
    )
    def cb_start_verifying(
        submit_n_clicks,
        input_path_images,
        input_path_annotations,
        input_path_approved,
        input_path_discarded
    ):
        global PATH_IMAGES, PATH_ANNOTATIONS, PATH_APPROVED, PATH_DISCARDED, \
                ANNOTATIONS, APPROVED, DISCARDED, \
                CRT_IMG_IDX, CRT_IMG_NAME, \
                CATEGORIES, ANNOTATION_COLORS, TABLE_COLS, INITIALIZED

        path_err = False
        path_err_msg = []

        # Check if the given paths do exist
        if not os.path.exists(input_path_images):
            path_err = True
            path_err_msg.append(f"PATH_IMAGES '{input_path_images}' does not exist!")

        if not os.path.exists(input_path_annotations):
            if path_err_msg:
                path_err_msg.append(html.Hr())
            path_err_msg.append(f"PATH_ANNOTATIONS '{input_path_annotations}' does not exist!")
            path_err = True

        if path_err:
            return [no_update, no_update, no_update, no_update, no_update, no_update, path_err_msg, True]

        # Save given variables
        PATH_IMAGES = input_path_images
        PATH_ANNOTATIONS = input_path_annotations
        PATH_APPROVED = input_path_approved
        PATH_DISCARDED = input_path_discarded

        # Load annotations
        try:
            ANNOTATIONS = pd.read_csv(PATH_ANNOTATIONS, sep="|")
        except Exception as e:
            return [no_update, no_update, no_update, no_update, no_update, no_update, format_traceback(), True]
        APPROVED = pd.DataFrame(columns=ANNOTATIONS.columns)
        DISCARDED = pd.DataFrame(columns=ANNOTATIONS.columns)

        # If existent, load approved / discarded annotations; otherwise use new dataframes
        if os.path.exists(PATH_APPROVED):
            try:
                APPROVED = pd.read_csv(PATH_APPROVED, sep="|")
            except pd.errors.EmptyDataError:
                pass
            except Exception as e:
                return [no_update, no_update, no_update, no_update, no_update, no_update, format_traceback(), True]
        else:
            save_progress_approved()
        if os.path.exists(PATH_DISCARDED):
            try:
                DISCARDED = pd.read_csv(PATH_DISCARDED, sep="|")
            except pd.errors.EmptyDataError:
                pass
            except Exception as e:
                return [no_update, no_update, no_update, no_update, no_update, no_update, format_traceback(), True]
        else:
            save_progress_discarded()

        # Select first image
        CRT_IMG_IDX = 0
        CRT_IMG_NAME = ANNOTATIONS.loc[CRT_IMG_IDX, "image_name"]

        # Get all categories and assign colors to them
        CATEGORIES = list(ANNOTATIONS["category"].drop_duplicates())
        ANNOTATION_COLORS = {category: COLORS[idx] for idx, category in enumerate(CATEGORIES)}

        # Set up the colors for the annotations table
        table_colors = {}
        for category, color in ANNOTATION_COLORS.items():
            color = tuple([x * 255 for x in to_rgba(color, alpha=0.5 / 255)])
            table_colors[category] = f"rgba{color}"

        style_data_conditional = []
        for category in CATEGORIES:
            style_data_conditional.append({
                "if": {"filter_query": f"{{category}} = {category}"},
                "backgroundColor": table_colors[category]
            })
        
        INITIALIZED = True
        
        return [
            image_figure(CRT_IMG_NAME),
            ANNOTATIONS.loc[ANNOTATIONS["image_name"] == CRT_IMG_NAME][TABLE_COLS].to_dict("records"),
            style_data_conditional,
            "Image Name: \"" + CRT_IMG_NAME + "\"",
            *check_status(CRT_IMG_NAME),
            no_update, no_update
        ]

    @app.callback(
        Output("confirm_start", "displayed"),
        Input("button_start", "n_clicks"),
        prevent_initial_call=True
    )
    def cb_display_confirm_start(n_clicks):
        return True

    # ======================================================================================
    #   Callbacks related to the save functionality
    # ======================================================================================
    # @app.callback(
    #     Output("confirm_save", "displayed"),
    #     Input("button_save", "n_clicks"),
    #     prevent_initial_call=True
    # )
    # def cb_display_confirm_save(n_clicks):
    #     return True

    # @app.callback(
    #     [
    #         Output("main_div", "children", allow_duplicate=True),
    #         Output("alert_main", "children", allow_duplicate=True),
    #         Output("alert_main", "is_open", allow_duplicate=True)
    #     ],
    #         Input("confirm_save", "submit_n_clicks"),
    #     prevent_initial_call=True
    # )
    # def cb_save_progess(submit_n_clicks):
    #     global INITIALIZED
    #     if not INITIALIZED:
    #         return [no_update, "WARNING: You can't save your progess before having started!", True]
    #     save_progress()
    #     raise PreventUpdate

    # @app.callback(
    #     Output("button_autosave", "children"),
    #     Input("button_autosave", "n_clicks"),
    #     prevent_initial_call=True
    # )
    # def cb_toggle_autosave(n_clicks):
    #     global AUTOSAVE
    #     AUTOSAVE = not AUTOSAVE
    #     if AUTOSAVE:
    #         return "Autosave progress: Enabled"
    #     return "Autosave progress: Disabled"


    # Run the app
    app.run_server(debug=False)

