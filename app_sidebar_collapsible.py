"""
This app creates an animated sidebar using the dbc.Nav component and some local
CSS. Each menu item has an icon, when the sidebar is collapsed the labels
disappear and only the icons remain. Visit www.fontawesome.com to find
alternative icons to suit your needs!

dcc.Location is used to track the current location, a callback uses the current
location to render the appropriate page content. The active prop of each
NavLink is set automatically according to the current pathname. To use this
feature you must install dash-bootstrap-components >= 0.11.0.

For more details on building multi-page Dash applications, check out the Dash
documentation: https://dash.plot.ly/urls
"""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html
import os
from datetime import datetime, date, timezone

# Etc
import pandas as pd

# e-mission modules
import emission.core.get_database as edb

# Data/file handling imports
import pathlib

from opadmindash.permissions import get_trips_columns

OPENPATH_LOGO = "https://www.nrel.gov/transportation/assets/images/openpath-logo.jpg"

#------------------------------------------------#
# Set the data path
#------------------------------------------------#

# For data that lives within the application.
# Set the path to the data directory
DATA_PATH = pathlib.Path(__file__).parent.joinpath("./data/").resolve()

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    use_pages=True
)


sidebar = html.Div(
    [
        html.Div(
            [
                # width: 3rem ensures the logo is the exact width of the
                # collapsed sidebar (accounting for padding)
                html.Img(src=OPENPATH_LOGO, style={"width": "3rem"}),
                html.H2("OpenPATH"),
            ],
            className="sidebar-header",
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.I(className="fas fa-home me-2"), 
                        html.Span("Overview")
                    ],
                    href="/",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-sharp fa-solid fa-database me-2"),
                        html.Span("Data"),
                    ],
                    href="/data",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-right-to-bracket me-2"),
                        html.Span("Tokens"),
                    ],
                    href="/tokens",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-globe me-2"),
                        html.Span("Map"),
                    ],
                    href="/map",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-envelope-open-text me-2"),
                        html.Span("Push notification"),
                    ],
                    href="/push_notification",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-gear me-2"),
                        html.Span("Settings"),
                    ],
                    href="/settings",
                    active="exact",
                )
            ],
            vertical=True,
            pills=True,
        ),
    ],
    className="sidebar",
)


content = html.Div([
    html.Div(
        dcc.DatePickerRange(
            id='date-picker',
            display_format='D/M/Y',
            start_date_placeholder_text='D/M/Y',
            end_date_placeholder_text='D/M/Y',
            min_date_allowed=date(2010, 1, 1),
            max_date_allowed=date.today(),
            initial_visible_month=date.today(),
        ), style={'margin': '10px 10px 0 0', 'display': 'flex', 'justify-content': 'right'}
    ),
    html.Div(dash.page_container, style={
        "margin-left": "5rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    }),
])


app.layout = html.Div(
    [
        dcc.Location(id="url"), 
        sidebar, 
        content,
        dcc.Store(id="store-trips", data={}),
        dcc.Store(id="store-uuids", data={}),
        dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0),
    ]
)


def query_uuids(start_date, end_date):
    query = {'update_ts': {'$exists': True}}
    if start_date is not None:
        start_time = datetime.combine(start_date, datetime.min.time()).astimezone(timezone.utc)
        query['update_ts']['$gte'] = start_time

    if end_date is not None:
        end_time = datetime.combine(end_date, datetime.max.time()).astimezone(timezone.utc)
        query['update_ts']['$lt'] = end_time

    projection = {
        '_id': 0,
        'user_id': '$uuid',
        'user_token': '$user_email',
        'update_ts': 1
    }

    query_result = edb.get_uuid_db().find(query, projection)
    df = pd.json_normalize(list(query_result))
    if not df.empty:
        df['update_ts'] = pd.to_datetime(df['update_ts'])
        df['user_id'] = df['user_id'].apply(str)
    return df

def query_confirmed_trips(start_date, end_date):
    query = {
        '$and': [
            {'metadata.key': 'analysis/confirmed_trip'},
            {'data.start_ts': {'$exists': True}},
            {'data.user_input.trip_user_input': {'$exists': False}},
        ]
    }
    if start_date is not None:
        start_time = datetime.combine(start_date, datetime.min.time())
        query['$and'][1]['data.start_ts']['$gte'] = start_time.timestamp()

    if end_date is not None:
        end_time = datetime.combine(end_date, datetime.max.time())
        query['$and'][1]['data.start_ts']['$lt'] = end_time.timestamp()

    projection = {
        '_id': 0,
        'user_id': 1,
        'trip_start_time_str': '$data.start_fmt_time',
        'trip_end_time_str': '$data.end_fmt_time',
        'timezone': '$data.start_local_dt.timezone',
        'start_coordinates': '$data.start_loc.coordinates',
        'end_coordinates': '$data.end_loc.coordinates',
        'travel_modes': '$data.user_input.trip_user_input.data.jsonDocResponse.data.travel_mode',
    }

    for column in get_trips_columns():
        projection[column] = 1

    query_result = edb.get_analysis_timeseries_db().find(query, projection)
    df = pd.json_normalize(list(query_result))
    if not df.empty:
        df['user_id'] = df['user_id'].apply(str)
        if 'data.start_place' in df.columns:
            df['data.start_place'] = df['data.start_place'].apply(str)
        if 'data.end_place' in df.columns:
            df['data.end_place'] = df['data.end_place'].apply(str)
    return df


# Load data stores
@app.callback(
    Output("store-uuids", "data"),
    Input('interval-component', 'n_intervals'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
)
def update_store_uuids(n_intervals, start_date, end_date):
    start_date_obj = date.fromisoformat(start_date) if start_date else None
    end_date_obj = date.fromisoformat(end_date) if end_date else None
    dff = query_uuids(start_date_obj, end_date_obj)
    store = {
        "data": dff.to_dict("records"),
        "columns": [{"name": i, "id": i} for i in dff.columns],
    }
    return store


@app.callback(
    Output("store-trips", "data"),
    Input('interval-component', 'n_intervals'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
)
def update_store_trips(n_intervals, start_date, end_date):
    start_date_obj = date.fromisoformat(start_date) if start_date else None
    end_date_obj = date.fromisoformat(end_date) if end_date else None
    df = query_confirmed_trips(start_date_obj, end_date_obj)
    store = {
        "data": df.to_dict("records"),
        "columns": [{"name": i, "id": i} for i in df.columns],
    }
    return store


if __name__ == "__main__":
    envPort = int(os.getenv('DASH_SERVER_PORT', '8050'))
    envDebug = os.getenv('DASH_DEBUG_MODE', 'True').lower() == 'true'
    app.run_server(debug=envDebug, host='0.0.0.0', port=envPort)
