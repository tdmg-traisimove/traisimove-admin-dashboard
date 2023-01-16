"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must
be in app.py.  Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.

"""


import dash
from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
from datetime import date
from plotly import graph_objs as go
import plotly.express as px

# Etc
import pandas as pd
from datetime import date
import arrow

# e-mission modules
import emission.core.get_database as edb
import emission.storage.decorations.user_queries as esdu
import bin.debug.export_participants_trips_csv as eptc

register_page(__name__, path="/")

def get_uuid_df():
    uuid_data = list(edb.get_uuid_db().find({}, {"_id": 0}))
    uuid_df = pd.json_normalize(uuid_data)
    uuid_df.rename(
        columns={"user_email": "user_token",
                "uuid": "user_id"},
        inplace=True
    )
    uuid_df['user_id'] = uuid_df['user_id'].astype(str)
    uuid_df['update_ts'] = pd.to_datetime(uuid_df['update_ts'])
    return uuid_df

def compute_sign_up_trend(uuid_df):
    uuid_df['update_ts'] = pd.to_datetime(uuid_df['update_ts'])
    res_df = (
        uuid_df
            .groupby(uuid_df['update_ts'].dt.date)
            .size()
            .reset_index(name='count')
            .rename(columns={'update_ts': 'date'})
        )
    res_df['date'] = pd.to_datetime(res_df['date'])
    return res_df

def get_confirmed_trips():
    query_result = edb.get_analysis_timeseries_db().find(
        # query
        {'$and':
            [
                {'metadata.key': 'analysis/confirmed_trip'},
                {'data.user_input.trip_user_input': {'$exists': False}}
            ]
         },
         {
            "_id": 0,
            "user_id": 1,
            "trip_start_time_str": "$data.start_fmt_time",
            "trip_start_time_tz": "$data.start_local_dt.timezone",
            "travel_modes": "$data.user_input.trip_user_input.data.jsonDocResponse.data.travel_mode"
        }
    )
    query_result_df = pd.DataFrame(list(query_result))
    return query_result_df

def compute_trips_trend(trips_df, date_col):
    trips_df[date_col] = pd.to_datetime(trips_df[date_col], utc=True)
    trips_df[date_col] = pd.DatetimeIndex(trips_df[date_col]).date
    counts = (trips_df
        .groupby(date_col)
        .size()
        .reset_index(name='count')
        .rename(columns={date_col: 'date'})
    )
    return counts

def find_last_get(uuid):
    last_get_result_list = list(edb.get_timeseries_db().find({"user_id": uuid,
        "metadata.key": "stats/server_api_time",
        "data.name": "POST_/usercache/get"}).sort("data.ts", -1).limit(1))
    last_get = last_get_result_list[0] if len(last_get_result_list) > 0 else None
    return last_get

def get_number_of_active_users(uuid_list, threshold):
    now = arrow.get().timestamp
    last_get_entries = [find_last_get(npu) for npu in uuid_list]
    number_of_active_users = 0
    for uuid, lge in zip(uuid_list, last_get_entries):
        if lge is not None:
            last_call_diff = arrow.get().timestamp - lge["metadata"]["write_ts"]
            if last_call_diff <= threshold:
                number_of_active_users += 1
    return number_of_active_users

intro = """
## Home

"""

card_icon = {
    "color": "white",
    "textAlign": "center",
    "fontSize": 30,
    "margin": "auto",
}

@callback(
    Output('card-users', 'children'),
    [Input('store-uuids', 'data')]
)
def update_card_users(store_uuids):
    nrow = pd.DataFrame(store_uuids.get('data')).shape[0]
    card = generate_card("# Users", f"{nrow} users", "fa fa-users")
    return card

@callback(
    Output('card-active-users', 'children'),
    [Input('store-uuids', 'data')]
)
def update_card_active_users(store_uuids):
    uuid_df = pd.DataFrame(store_uuids.get('data'))
    ONE_DAY = 100 * 24 * 60 * 60
    number_of_active_users = get_number_of_active_users(uuid_df['user_id'], ONE_DAY)
    card = generate_card("# Active users", f"{number_of_active_users} users", "fa fa-person-walking")
    return card

@callback(
    Output('card-trips', 'children'),
    [Input('store-trips', 'data')]
)
def update_card_trips(store_trips):
    nrow = pd.DataFrame(store_trips.get('data')).shape[0]
    card = generate_card("# Confirmed trips", f"{nrow} trips", "fa fa-angles-right")
    return card

def generate_card(title_text, body_text, icon): 
    card = dbc.CardGroup([
            dbc.Card(
                dbc.CardBody(
                    [
                            html.H5(title_text, className="card-title"),
                            html.P(body_text, className="card-text",),
                        ]
                    )
                ),
                dbc.Card(
                    html.Div(className=icon, style=card_icon),
                    className="bg-primary",
                    style={"maxWidth": 75},
                ),
            ])
    return card

def generate_barplot(data, x, y, title):
    fig = px.bar(data, x=x, y=y)
    fig.update_layout(title=title)
    return fig


@callback(
    Output('fig-sign-up-trend', 'figure'),
    [Input('store-uuids', 'data')]
)
def generate_plot_sign_up_trend(store_uuids):
    df = pd.DataFrame(store_uuids.get("data"))
    trend_df = compute_sign_up_trend(df)
    fig = generate_barplot(trend_df, x = 'date', y = 'count', title = "Sign-ups trend")
    return fig

@callback(
    Output('fig-trips-trend', 'figure'),
    [Input('store-trips', 'data')]
)
def generate_plot_trips_trend(store_trips):
    df = pd.DataFrame(store_trips.get("data"))
    trend_df = compute_trips_trend(df, date_col = "trip_start_time_str")
    fig = generate_barplot(trend_df, x = 'date', y = 'count', title = "Trips trend")
    return fig



layout = html.Div(
    [
        # A data store. This can save JSON-formats or simple data like booleans or integers
        dcc.Store(id='dataIsLoadedFlag', storage_type='memory'), # We can store JSON-izable data here, nothing too big

        dcc.Markdown(intro),

        # dcc.DatePickerRange(
        #             display_format='D/M/Y',
        #             start_date_placeholder_text='D/M/Y',
        #             end_date_placeholder_text='D/M/Y',
        #             start_date=date(2017, 6, 21)
        # ),

        # Cards 
        dbc.Row([
            dbc.Col(id='card-users'),
            dbc.Col(id='card-active-users'),
            dbc.Col(id='card-trips')
        ]),

        # Plots
        dbc.Row([
            dcc.Graph(id="fig-sign-up-trend"),
            dcc.Graph(id="fig-trips-trend"),
        ])
    ]
)
