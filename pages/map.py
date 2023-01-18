"""
Note that the callback will trigger even if prevent_initial_call=True. This is
because dcc.Location must be in app.py. Since the dcc.Location component is not
in the layout when navigating to this page, it triggers the callback. The
workaround is to check if the input value is None.
"""
import pandas as pd
from dash import dcc, html, Input, Output, callback, register_page
import dash_bootstrap_components as dbc
from datetime import datetime, date
import emission.core.get_database as edb

import plotly.graph_objects as go

register_page(__name__, path="/map")

intro = """## Map"""


def get_confirmed_trips(start_date, end_date):

    query = {
        '$and': [
            {'metadata.key': 'analysis/confirmed_trip'},
            {'data.start_ts': {'$exists': True}}
        ]
    }
    if start_date is not None:
        start_time = datetime.combine(start_date, datetime.min.time())
        query['$and'][1]['data.start_ts']['$gte'] = start_time.timestamp()

    if end_date is not None:
        end_time = datetime.combine(end_date, datetime.max.time())
        query['$and'][1]['data.statr_ts']['$lt'] = end_time.timestamp()

    query_result = edb.get_analysis_timeseries_db().find(
        query,
        {
            "_id": 0,
            "user_id": 1,
            "trip_start_time_str": "$data.start_fmt_time",
            "trip_end_time_str": "$data.end_fmt_time",
            "timezone": "$data.start_local_dt.timezone",
            "start_coordinates": "$data.start_loc.coordinates",
            "end_coordinates": "$data.end_loc.coordinates",
        }
    )
    confirmed_trips_df = pd.json_normalize(list(query_result))
    return confirmed_trips_df


def get_output_data(start_date, end_date):
    confirmed_trips_df = get_confirmed_trips(start_date, end_date)
    group = confirmed_trips_df.groupby('user_id')
    fig = go.Figure()

    options = list()
    for user_id in group.groups:
        options.append(str(user_id))

    fig.add_trace(
        go.Scattermapbox(
            mode="markers+lines",
            lon=[-50, -60, 40],
            lat=[30, 10, -20],
            marker={'size': 10}
        )
    )

    fig.update_layout(
        margin={'l': 0, 't': 0, 'b': 0, 'r': 0},
        mapbox={
            'style': "stamen-terrain",
            'center': {'lon': -20, 'lat': -20},
            'zoom': 2
        }
    )

    return options, fig




layout = html.Div(
    [
        dcc.Markdown(intro),
        dbc.Row([
            dbc.Col(
                dcc.DatePickerRange(
                    id='map-date-picker',
                    display_format='D/M/Y',
                    start_date_placeholder_text='D/M/Y',
                    end_date_placeholder_text='D/M/Y',
                    min_date_allowed=date(2010, 1, 1),
                    max_date_allowed=date.today(),
                    initial_visible_month=date.today(),
                )
            ),
            dbc.Col(
                dcc.Dropdown(id='user-dropdown'),
            )
        ]),

        dbc.Row(
            dcc.Graph(id="trip-map")
        ),
    ]
)


@callback(
    Output('user-dropdown', 'options'),
    Output('trip-map', 'figure'),
    Input('map-date-picker', 'start_date'),
    Input('map-date-picker', 'end_date'),
)
def update_output(start_date, end_date):
    start_date_obj = date.fromisoformat(start_date) if start_date else None
    end_date_obj = date.fromisoformat(end_date) if end_date else None
    return get_output_data(start_date_obj, end_date_obj)
