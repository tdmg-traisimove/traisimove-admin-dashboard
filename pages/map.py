"""
Note that the callback will trigger even if prevent_initial_call=True. This is
because dcc.Location must be in app.py. Since the dcc.Location component is not
in the layout when navigating to this page, it triggers the callback. The
workaround is to check if the input value is None.
"""
from uuid import UUID

from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import random

import emission.core.wrapper.user as ecwu
import emission.core.get_database as edb
import logging

from utils.permissions import has_permission

register_page(__name__, path="/map")

intro = """## Map"""


def create_lines_map(trips_group_by_user_id, user_id_list):
    start_lon, start_lat = 0, 0
    traces = []
    for user_id in user_id_list:
        color = trips_group_by_user_id[user_id]['color']
        trips = trips_group_by_user_id[user_id]['trips']

        for i, trip in enumerate(trips):
            if i == 0:
                start_lon = trip['start_coordinates'][0]
                start_lat = trip['start_coordinates'][1]
            traces.append(
                go.Scattermapbox(
                    mode="markers+lines",
                    lon=[trip['start_coordinates'][0], trip['end_coordinates'][0]],
                    lat=[trip['start_coordinates'][1], trip['end_coordinates'][1]],
                    marker={'size': 10, 'color': color},
                )
            )

    fig = go.Figure(data=traces)
    fig.update_layout(
        showlegend=False,
        margin={'l': 0, 't': 30, 'b': 0, 'r': 0},
        mapbox_style="open-street-map",
        mapbox_center_lon=start_lon,
        mapbox_center_lat=start_lat,
        mapbox_zoom=11,
        height=650,
    )

    return fig


def create_heatmap_fig(trips_group_by_user_mode, user_mode_list):
    coordinates = {'lat': [], 'lon': [], 'color':[]}
    for user_mode in user_mode_list:
        color = trips_group_by_user_mode[user_mode]['color']
        trips = trips_group_by_user_mode[user_mode]['trips']

        for trip in trips:
            coordinates['lon'].append(trip['start_coordinates'][0])
            coordinates['lon'].append(trip['end_coordinates'][0])
            coordinates['lat'].append(trip['start_coordinates'][1])
            coordinates['lat'].append(trip['end_coordinates'][1])
            coordinates['color'].extend([color,color])

    fig = go.Figure()
    if len(coordinates.get('lat', [])) > 0:
        fig.add_trace(
            go.Densitymapbox(
                lon=coordinates['lon'],
                lat=coordinates['lat'],
                name = '',
                
            )
        )

        fig.add_trace(
            go.Scattermapbox(
                lat=coordinates['lat'],
                lon=coordinates['lon'],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=9,
                    color=coordinates['color'],
                ),
                name = '',
            )
        )

        fig.update_layout(
            mapbox_style='open-street-map',
            mapbox_center_lon=coordinates['lon'][0],
            mapbox_center_lat=coordinates['lat'][0],
            mapbox_zoom=11,
            margin={"r": 0, "t": 30, "l": 0, "b": 0},
            height=650,
        )
    return fig


def create_bubble_fig(trips_group_by_user_mode, user_mode_list):
    coordinates = {'lat': [], 'lon': [], 'color': []}
    for user_mode in user_mode_list:
        color = trips_group_by_user_mode[user_mode]['color']
        trips = trips_group_by_user_mode[user_mode]['trips']

        for trip in trips:
            coordinates['lon'].append(trip['start_coordinates'][0])
            coordinates['lon'].append(trip['end_coordinates'][0])
            coordinates['lat'].append(trip['start_coordinates'][1])
            coordinates['lat'].append(trip['end_coordinates'][1])
            coordinates['color'].extend([color,color])

    fig = go.Figure()
    if len(coordinates.get('lon', [])) > 0:
        fig.add_trace(
            go.Scattermapbox(
                lat=coordinates['lat'],
                lon=coordinates['lon'],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=9,
                    color=coordinates['color'],
                ),
            )
        )
        fig.update_layout(
            autosize=True,
            mapbox_style='open-street-map',
            mapbox_center_lon=coordinates['lon'][0],
            mapbox_center_lat=coordinates['lat'][0],
            mapbox_zoom=11,
            mapbox_bearing=0,
            margin={'r': 0, 't': 30, 'l': 0, 'b': 0},
            height=650,
        )
    return fig


def get_trips_group_by_user_id(trips_data):
    trips_group_by_user_id = None
    trips_df = pd.DataFrame(trips_data['data'])
    if not trips_df.empty:
        trips_group_by_user_id = trips_df.groupby('user_id')
    return trips_group_by_user_id

def get_trips_group_by_user_mode(trips_data):
    trips_group_by_user_mode = None
    trips_df = pd.DataFrame(trips_data['data'])
    data_types = trips_df.dtypes
    trips_df['data.user_input.mode_confirm'] = trips_df['data.user_input.mode_confirm'].fillna('Unknown')
    if not trips_df.empty:
        trips_group_by_user_mode = trips_df.groupby('data.user_input.mode_confirm')
    return trips_group_by_user_mode

def create_single_option(value, color):
    return {
        'label': html.Span(
            [
                html.Div(id='dropdown-squares', style={'background-color': color}),
                html.Span(value, style={'font-size': 15, 'padding-left': 10})
            ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
        ),
        'value': value
    }

def create_user_ids_options(trips_group_by_user_id):
    options = list()
    user_ids = set()
    if has_permission('options_uuids'):
        for user_id in trips_group_by_user_id:
            color = trips_group_by_user_id[user_id]['color']
            user_ids.add(user_id)
            options.append(create_single_option(user_id, color))
    return options, user_ids

def create_user_emails_options(trips_group_by_user_id):
    options = list()
    user_emails = set()
    if has_permission('options_emails'):
        for i, user_id in enumerate(trips_group_by_user_id):
            color = trips_group_by_user_id[user_id]['color']
            logging.warn("dict is %s" % ecwu.User.fromUUID(UUID(user_id)).__dict__)
            logging.warn("all users are %s" % list(edb.get_uuid_db().find()))
            try:
                user_email = ecwu.User.fromUUID(UUID(user_id))._User__email
            except AttributeError as e:
                continue
            user_emails.add(user_email)
            options.append(create_single_option(user_email, color))
    return options, user_emails

def create_user_modes_options(trips_group_by_user_mode):
    options = list()
    user_modes = set()
    for user_mode in trips_group_by_user_mode:
        color = trips_group_by_user_mode[user_mode]['color']
        user_modes.add(user_mode)
        options.append(create_single_option(user_mode, color))
    return options, user_modes

map_type_options = []
if has_permission('map_heatmap'):
    map_type_options.append({'label': 'Density Heatmap', 'value': 'heatmap'})
if has_permission('map_bubble'):
    map_type_options.append({'label': 'Bubble Map', 'value': 'bubble'})
if has_permission('map_trip_lines'):
    map_type_options.append({'label': 'Trips Lines', 'value': 'lines'})


layout = html.Div(
    [
        dcc.Store(id="store-trips-map", data={}),
        dcc.Markdown(intro),

        dbc.Row([
            dbc.Col(
                [
                    html.Label('Map Type'),
                    dcc.Dropdown(id='map-type-dropdown', value='', options=map_type_options),
                ],
                xl=3,
                lg=4,
                sm=6,
            )
        ]),

        dbc.Row([
            dbc.Col([
                html.Label('User UUIDs'),
                dcc.Dropdown(id='user-id-dropdown', multi=True),
            ], style={'display': 'block' if has_permission('options_uuids') else 'none'}),
            dbc.Col([
                html.Label('User Emails'),
                dcc.Dropdown(id='user-email-dropdown', multi=True),
            ], style={'display': 'block' if has_permission('options_emails') else 'none'}),
            dbc.Col([
                html.Label('Modes'),
                dcc.Dropdown(id='user-mode-dropdown', multi=True),
            ], style={'display': 'block'})
        ]),

        dbc.Row(
            dcc.Graph(id="trip-map")
        ),
    ]
)

@callback(
    Output('user-id-dropdown', 'options'),
    Output('user-id-dropdown', 'value'),
    Input('store-trips-map', 'data'),
    Input('user-id-dropdown', 'value'),
)
def update_user_ids_options(trips_data, selected_user_ids):
    user_ids_options, user_ids = create_user_ids_options(trips_data[0]['users_data'])
    if selected_user_ids is not None:
        selected_user_ids = [user_id for user_id in selected_user_ids if user_id in user_ids]
    return user_ids_options, selected_user_ids


@callback(
    Output('user-email-dropdown', 'options'),
    Output('user-email-dropdown', 'value'),
    Input('store-trips-map', 'data'),
    Input('user-email-dropdown', 'value'),
)
def update_user_emails_options(trips_data, selected_user_emails):
    user_emails_options, user_emails = create_user_emails_options(trips_data[0]['users_data'])
    if selected_user_emails is not None:
        selected_user_emails = [user_email for user_email in selected_user_emails if user_email in user_emails]
    return user_emails_options, selected_user_emails

@callback(
    Output('user-mode-dropdown', 'options'),
    Output('user-mode-dropdown', 'value'),
    Input('store-trips-map', 'data'),
    Input('user-mode-dropdown', 'value'),
)
def update_user_modes_options(trips_data, selected_user_modes):
    user_modes_options, user_modes = create_user_modes_options(trips_data[1]['users_data'])
    if selected_user_modes is not None:
        selected_user_modes = [mode_confirm for mode_confirm in selected_user_modes if mode_confirm in user_modes]
    return user_modes_options, selected_user_modes

@callback(
    Output('trip-map', 'figure'),
    Input('map-type-dropdown', 'value'),
    Input('user-id-dropdown', 'value'),
    Input('user-email-dropdown', 'value'),
    Input('user-mode-dropdown', 'value'),
    State('store-trips-map', 'data'),
)
def update_output(map_type, selected_user_ids, selected_user_emails, selected_user_modes, trips_data):
    user_ids = set(selected_user_ids) if selected_user_ids is not None else set()
    user_modes=set(selected_user_modes) if selected_user_modes is not None else set()
    if selected_user_emails is not None:
        for user_email in selected_user_emails:
            user_ids.add(str(ecwu.User.fromEmail(user_email).uuid))
    arg1 = trips_data[0].get('users_data', {})
    arg2 = user_ids       
    if(selected_user_modes):
        arg1 = trips_data[1].get('users_data', {})
        arg2 = user_modes
    if map_type == 'lines':
        return create_lines_map(arg1, arg2)
    elif map_type == 'heatmap':
        return create_heatmap_fig(trips_data[1].get('users_data', {}), user_modes)
    elif map_type == 'bubble':
        return create_bubble_fig(trips_data[1].get('users_data', {}), user_modes)
    else:
        return go.Figure()


@callback(
    Output('user-id-dropdown', 'disabled'),
    Output('user-email-dropdown', 'disabled'),
    Input('map-type-dropdown', 'value'),
)
def control_user_dropdowns(map_type):
    disabled = True
    if map_type == 'lines':
        disabled = False
    return disabled, disabled


@callback(
    Output('store-trips-map', 'data'),
    Input('store-trips', 'data'),
)
def store_trips_map_data(trips_data):
    trips_group_by_user_id = get_trips_group_by_user_id(trips_data)
    users_data = dict()
    if trips_group_by_user_id:
        user_ids = list(trips_group_by_user_id)
        n = len(user_ids) % 360
        k = 359 // (n - 1) if n > 1 else 0
        for ind, user_id in enumerate(trips_group_by_user_id.groups.keys()):
            color = f'hsl({ind * k}, 100%, 50%)'
            trips = trips_group_by_user_id.get_group(user_id).sort_values('trip_start_time_str').to_dict("records")
            users_data[user_id] = {'color': color, 'trips': trips}
    groupped_data = []
    groupped_data.append({'users_data':users_data})
    users_data = dict()
    trips_group_by_user_mode = get_trips_group_by_user_mode(trips_data)
    if trips_group_by_user_mode:
        user_modes = list(trips_group_by_user_mode)
        n = len(user_modes) % 360
        k = 359 // (n - 1) if n > 1 else 0
        for ind, user_mode in enumerate(trips_group_by_user_mode.groups.keys()):
            color = f'hsl({ind * k}, 100%, 50%)'
            trips = trips_group_by_user_mode.get_group(user_mode).sort_values('trip_start_time_str').to_dict("records")
            users_data[user_mode] = {'color': color, 'trips': trips}
    groupped_data.append({'users_data':users_data})
    return groupped_data
