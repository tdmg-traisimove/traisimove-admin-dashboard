"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must be in app.py.
Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.
"""
from dash import dcc, html, Input, Output, callback, register_page, dash_table, State
# Etc
import logging
import pandas as pd
from dash.exceptions import PreventUpdate

from utils import constants
from utils import permissions as perm_utils
from utils import db_utils
from utils.db_utils import df_to_filtered_records, query_trajectories
from utils.datetime_utils import iso_to_date_only
import emission.core.timer as ect
import emission.storage.decorations.stats_queries as esdsq
register_page(__name__, path="/data")

intro = """## Data"""

layout = html.Div(
    [   
        dcc.Markdown(intro),
        dcc.Tabs(id="tabs-datatable", value='tab-uuids-datatable', children=[
            dcc.Tab(label='UUIDs', value='tab-uuids-datatable'),
            dcc.Tab(label='Trips', value='tab-trips-datatable'),
            dcc.Tab(label='Demographics', value='tab-demographics-datatable'),
            dcc.Tab(label='Trajectories', value='tab-trajectories-datatable'),
        ]),
        html.Div(id='tabs-content'),
    ]
)


def clean_location_data(df):
    with ect.Timer() as total_timer:

        # Stage 1: Clean start location coordinates
        if 'data.start_loc.coordinates' in df.columns:
            with ect.Timer() as stage1_timer:
                df['data.start_loc.coordinates'] = df['data.start_loc.coordinates'].apply(lambda x: f'({x[0]}, {x[1]})')
            esdsq.store_dashboard_time(
                "admin/data/clean_location_data/clean_start_loc_coordinates",
                stage1_timer
            )

        # Stage 2: Clean end location coordinates
        if 'data.end_loc.coordinates' in df.columns:
            with ect.Timer() as stage2_timer:
                df['data.end_loc.coordinates'] = df['data.end_loc.coordinates'].apply(lambda x: f'({x[0]}, {x[1]})')
            esdsq.store_dashboard_time(
                "admin/data/clean_location_data/clean_end_loc_coordinates",
                stage2_timer
            )

    esdsq.store_dashboard_time(
        "admin/db_utils/clean_location_data/total_time",
        total_timer
    )

    return df

def update_store_trajectories(start_date: str, end_date: str, tz: str, excluded_uuids):
    with ect.Timer() as total_timer:

        # Stage 1: Query trajectories
        with ect.Timer() as stage1_timer:
            df = query_trajectories(start_date, end_date, tz)
        esdsq.store_dashboard_time(
            "admin/data/update_store_trajectories/query_trajectories",
            stage1_timer
        )

        # Stage 2: Filter records based on user exclusion
        with ect.Timer() as stage2_timer:
            records = df_to_filtered_records(df, 'user_id', excluded_uuids["data"])
        esdsq.store_dashboard_time(
            "admin/data/update_store_trajectories/filter_records",
            stage2_timer
        )

        # Stage 3: Prepare the store data structure
        with ect.Timer() as stage3_timer:
            store = {
                "data": records,
                "length": len(records),
            }
        esdsq.store_dashboard_time(
            "admin/data/update_store_trajectories/prepare_store_data",
            stage3_timer
        )

    esdsq.store_dashboard_time(
        "admin/data/update_store_trajectories/total_time",
        total_timer
    )

    return store


@callback(
    Output('tabs-content', 'children'),
    Input('tabs-datatable', 'value'),
    Input('store-uuids', 'data'),
    Input('store-excluded-uuids', 'data'),
    Input('store-trips', 'data'),
    Input('store-demographics', 'data'),
    Input('store-trajectories', 'data'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
    Input('date-picker-timezone', 'value'),
)
def render_content(tab, store_uuids, store_excluded_uuids, store_trips, store_demographics, store_trajectories, start_date, end_date, timezone):
    with ect.Timer() as total_timer:
        data, columns, has_perm = None, [], False

        # Handle UUIDs tab
        if tab == 'tab-uuids-datatable':
            with ect.Timer() as stage1_timer:
                data = store_uuids["data"]
                data = db_utils.add_user_stats(data)
                columns = perm_utils.get_uuids_columns()
                has_perm = perm_utils.has_permission('data_uuids')
            esdsq.store_dashboard_time(
                "admin/data/render_content/handle_uuids_tab",
                stage1_timer
            )

        # Handle Trips tab
        elif tab == 'tab-trips-datatable':
            with ect.Timer() as stage2_timer:
                data = store_trips["data"]
                columns = perm_utils.get_allowed_trip_columns()
                columns.update(
                    col['label'] for col in perm_utils.get_allowed_named_trip_columns()
                )
                columns.update(store_trips["userinputcols"])
                has_perm = perm_utils.has_permission('data_trips')
                df = pd.DataFrame(data)
                if df.empty or not has_perm:
                    return None

                logging.debug(f"Final list of retained cols {columns=}")
                logging.debug(f"Before dropping, {df.columns=}")
                df = df.drop(columns=[col for col in df.columns if col not in columns])
                logging.debug(f"After dropping, {df.columns=}")
                df = clean_location_data(df)

                trips_table = populate_datatable(df, 'trips-table')
                # Return an HTML Div containing a button (button-clicked) and the populated datatable
                return html.Div([
                    html.Button(
                        'Display columns with raw units',
                        id='button-clicked',  # identifier for the button
                        n_clicks=0,  # initialize number of clicks to 0
                        style={'marginLeft': '5px'}
                    ),
                    trips_table,  # populated trips table component
                ])
            esdsq.store_dashboard_time(
                "admin/data/render_content/handle_trips_tab",
                stage2_timer
            )

        # Handle Demographics tab
        elif tab == 'tab-demographics-datatable':
            with ect.Timer() as stage3_timer:
                data = store_demographics["data"]
                has_perm = perm_utils.has_permission('data_demographics')
                # If only one survey is available, process it without creating a subtab
                if len(data) == 1:
                    # Here data is a dictionary
                    data = list(data.values())[0]
                    columns = list(data[0].keys())
                # For multiple surveys, create subtabs for unique surveys
                elif len(data) > 1:
                    # Returns subtab only if has_perm is True
                    if not has_perm:
                        return None
                    return html.Div([
                        dcc.Tabs(id='subtabs-demographics', value=list(data.keys())[0], children=[
                            dcc.Tab(label=key, value=key) for key in data
                        ]),
                        html.Div(id='subtabs-demographics-content')
                    ])
            esdsq.store_dashboard_time(
                "admin/data/render_content/handle_demographics_tab",
                stage3_timer
            )

        # Handle Trajectories tab
        elif tab == 'tab-trajectories-datatable':
            # Currently store_trajectories data is loaded only when the respective tab is selected
            # Here we query for trajectory data once "Trajectories" tab is selected
            with ect.Timer() as stage4_timer:
                (start_date, end_date) = iso_to_date_only(start_date, end_date)
                if store_trajectories == {}:
                    store_trajectories = update_store_trajectories(start_date, end_date, timezone, store_excluded_uuids)
                data = store_trajectories["data"]
                if data:
                    columns = list(data[0].keys())
                    columns = perm_utils.get_trajectories_columns(columns)
                    has_perm = perm_utils.has_permission('data_trajectories')
            esdsq.store_dashboard_time(
                "admin/data/render_content/handle_trajectories_tab",
                stage4_timer
            )

        # Prepare final DataFrame and return datatable
        with ect.Timer() as stage5_timer:
            df = pd.DataFrame(data)
            if df.empty or not has_perm:
                return None

            df = df.drop(columns=[col for col in df.columns if col not in columns])

            result = populate_datatable(df)
        esdsq.store_dashboard_time(
            "admin/data/render_content/prepare_final_dataframe_and_return",
            stage5_timer
        )

    esdsq.store_dashboard_time(
        "admin/data/render_content/total_time",
        total_timer
    )

    return result

# Handle subtabs for demographic table when there are multiple surveys
@callback(
    Output('subtabs-demographics-content', 'children'),
    Input('subtabs-demographics', 'value'),
    Input('store-demographics', 'data'),
)
def update_sub_tab(tab, store_demographics):
    with ect.Timer() as total_timer:

        # Stage 1: Retrieve and process data for the selected subtab
        with ect.Timer() as stage1_timer:
            data = store_demographics["data"]
            if tab in data:
                data = data[tab]
                if data:
                    columns = list(data[0].keys())
        esdsq.store_dashboard_time(
            "admin/data/update_sub_tab/retrieve_and_process_data",
            stage1_timer
        )

        # Stage 2: Convert data to DataFrame
        with ect.Timer() as stage2_timer:
            df = pd.DataFrame(data)
            if df.empty:
                esdsq.store_dashboard_time(
                    "admin/data/update_sub_tab/convert_to_dataframe",
                    stage2_timer
                )
                esdsq.store_dashboard_time(
                    "admin/data/update_sub_tab/total_time",
                    total_timer
                )
                return None
        esdsq.store_dashboard_time(
            "admin/data/update_sub_tab/convert_to_dataframe",
            stage2_timer
        )

        # Stage 3: Filter columns based on the allowed set
        with ect.Timer() as stage3_timer:
            df = df.drop(columns=[col for col in df.columns if col not in columns])
        esdsq.store_dashboard_time(
            "admin/data/update_sub_tab/filter_columns",
            stage3_timer
        )

        # Stage 4: Populate the datatable with the cleaned DataFrame
        with ect.Timer() as stage4_timer:
            result = populate_datatable(df)
        esdsq.store_dashboard_time(
            "admin/data/update_sub_tab/populate_datatable",
            stage4_timer
        )

    # Store the total time for the entire function
    esdsq.store_dashboard_time(
        "admin/data/update_sub_tab/total_time",
        total_timer
    )

    return result

@callback(
    Output('trips-table', 'hidden_columns'),  # Output hidden columns in the trips-table
    Output('button-clicked', 'children'),  # Updates button label
    Input('button-clicked', 'n_clicks'),  # Number of clicks on the button
    State('button-clicked', 'children')  # State representing the current label of button
)
# Controls visibility of columns in trips table and updates the label of button based on the number of clicks.
def update_dropdowns_trips(n_clicks, button_label):
    with ect.Timer() as total_timer:

        # Stage 1: Determine hidden columns and button label based on number of clicks
        with ect.Timer() as stage1_timer:
            if n_clicks % 2 == 0:
                hidden_col = ["data.duration_seconds", "data.distance_meters", "data.distance"]
                button_label = 'Display columns with raw units'
            else:
                hidden_col = ["data.duration", "data.distance_miles", "data.distance_km", "data.distance"]
                button_label = 'Display columns with humanized units'
        esdsq.store_dashboard_time(
            "admin/data/update_dropdowns_trips/determine_hidden_columns_and_label",
            stage1_timer
        )

    # Store the total time for the entire function
    esdsq.store_dashboard_time(
        "admin/data/update_dropdowns_trips/total_time",
        total_timer
    )

    # Return the list of hidden columns and the updated button label
    return hidden_col, button_label



def populate_datatable(df, table_id=''):
    with ect.Timer() as total_timer:

        # Stage 1: Check if df is a DataFrame and raise PreventUpdate if not
        with ect.Timer() as stage1_timer:
            if not isinstance(df, pd.DataFrame):
                raise PreventUpdate
        esdsq.store_dashboard_time(
            "admin/data/populate_datatable/check_dataframe_type",
            stage1_timer
        )

        # Stage 2: Create the DataTable from the DataFrame
        with ect.Timer() as stage2_timer:
            result = dash_table.DataTable(
                id=table_id,
                # columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict('records'),
                export_format="csv",
                filter_options={"case": "sensitive"},
                # filter_action="native",
                sort_action="native",  # give user capability to sort columns
                sort_mode="single",  # sort across 'multi' or 'single' columns
                page_current=0,  # page number that user is on
                page_size=50,  # number of rows visible per page
                style_cell={
                    'textAlign': 'left',
                    # 'minWidth': '100px',
                    # 'width': '100px',
                    # 'maxWidth': '100px',
                },
                style_table={'overflowX': 'auto'},
                css=[{"selector": ".show-hide", "rule": "display:none"}]
            )
        esdsq.store_dashboard_time(
            "admin/data/populate_datatable/create_datatable",
            stage2_timer
        )

    # Store the total time for the entire function
    esdsq.store_dashboard_time(
        "admin/data/populate_datatable/total_time",
        total_timer
    )

    return result
