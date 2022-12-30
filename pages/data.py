"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must
be in app.py.  Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.

"""


import dash
from dash import dcc, html, Input, Output, State, callback, register_page
import dash_table
import dash_bootstrap_components as dbc

# Etc
import pandas as pd
from datetime import date

# e-mission modules
import emission.core.get_database as edb
import emission.storage.decorations.user_queries as esdu
import bin.debug.export_participants_trips_csv as eptc
register_page(__name__, path="/data")

uuid_list = esdu.get_all_uuids()

intro = """
## Data

"""


layout = html.Div(
    [   
        dcc.Markdown(intro),
        dcc.DatePickerRange(
                    display_format='D/M/Y',
                    start_date_placeholder_text='D/M/Y',
                    end_date_placeholder_text='D/M/Y',
                    start_date=date(2017, 6, 21)
        ),
        dcc.Interval(id='interval_db', interval=60000, n_intervals=0),
        dcc.Tabs(id="tabs-datatable", value='tab-participants-datatable', children=[
            # the table is refreshed every 60000 milisecs (60 seconds)
            dcc.Tab(label='Participants', value='tab-participants-datatable'),
            dcc.Tab(label='Demographics survey', value='tab-demographics-survey-datatable'),
            dcc.Tab(label='Trips', value='tab-trips-datatable'),
        ]),
        html.Div(id='tabs-content')
    ]
)

@callback(
    Output('tabs-content', 'children'),
    [
        Input('tabs-datatable', 'value'),
        Input('interval_db', 'n_intervals')
    ]
)
def render_content(tab, n_intervals):
    if tab == 'tab-participants-datatable':
        return html.Div(populate_participants_table())
    elif tab == 'tab-trips-datatable':
        return html.Div(populate_trips_table())
    elif tab == 'tab-demographics-survey-datatable':
        return html.Div(populate_participants_table())


def populate_participants_table():
    # Convert the Collection (table) date to a pandas DataFrame
    all_uuid_data = list(edb.get_uuid_db().find({}, {"_id": 0}))
    all_uuid_df = pd.json_normalize(all_uuid_data)
    all_uuid_df.rename(
        columns={"user_email": "user_token",
                "uuid": "user_id"}, 
        inplace=True
    )
    all_uuid_df.to_csv("data/participant_table.csv", index=False)
    all_uuid_df = pd.read_csv("data/participant_table.csv")
    return populate_datatable(all_uuid_df)

def populate_demographic_survey_table():
    # Convert the Collection (table) date to a pandas DataFrame
    all_uuid_data = list(edb.get_uuid_db().find({}))
    all_uuid_df = pd.json_normalize(all_uuid_data)
    all_uuid_df.rename(columns={"user_email": "user_token"}, inplace=True)
    all_uuid_df.to_csv("demographics_table.csv")
    all_uuid_df = pd.read_csv("demographics_table.csv")
    return populate_datatable(all_uuid_df)

def populate_trips_table():
    trip_table_fp = open("trip_table.csv", "w")
    for curr_uuid in uuid_list:
        if curr_uuid != '':
            eptc.export_trip_table_as_csv(
                curr_uuid, 
                start_day_str = '2015-01-01', 
                end_day_str = '2016-12-31',
                timezone='UTC', 
                fp=trip_table_fp
            )
    trip_table_fp.close()
    df = pd.read_csv("trip_table.csv")
    df.drop(columns=df.columns[0], axis=1, inplace=True)
    df.insert(0, 'user_id_temp', df['user_id'])
    df.drop('user_id', axis=1, inplace=True)
    df.rename(columns={'user_id_temp': 'user_id'}, inplace=True)
    return populate_datatable(df)

def populate_datatable(df):
    if not isinstance(df, pd.DataFrame):
        pass
    return [
        dash_table.DataTable(
            # id='my-table',
            # columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            # filter_action="native",
            export_format="csv",
            filter_options={"case": "sensitive"},
            sort_action="native",  # give user capability to sort columns
            sort_mode="single",  # sort across 'multi' or 'single' columns
            page_current=0,  # page number that user is on
            page_size=6,  # number of rows visible per page
            style_cell={'textAlign': 'left', 
                        # 'minWidth': '100px',
                        # 'width': '100px', 
                        # 'maxWidth': '100px'
                        },
            style_table={'overflowX': 'scroll',}
        )
    ]