"""
Note that the callback will trigger even if prevent_initial_call=True. This is
because dcc.Location must be in app.py. Since the dcc.Location component is not
in the layout when navigating to this page, it triggers the callback. The
workaround is to check if the input value is None.
"""
import logging
import random
from uuid import UUID
from collections import defaultdict

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dash import dcc, html, Input, Output, ALL, callback, register_page, callback_context
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

import emission.core.wrapper.user as ecwu
import emcommon.diary.base_modes as emcdb
import emcommon.bluetooth.ble_matching as emcble
import emission.analysis.configs.dynamic_config as eacd

from utils.permissions import has_permission

config = eacd.get_dynamic_config()
ble_enabled = config.get('vehicle_identities')


def filter_trips(trips, selected_values, trip_key):
    """
    Return a subset of trips where the value of trip.get(trip_key) is in
    selected_values.
    If selected_values is empty, return all trips
    """
    if not selected_values:
        logging.info("No values selected => returning data unfiltered")
        return trips
    filtered_trips = []
    for trip in trips:
        value = trip.get(trip_key)
        if value and value in selected_values:
            filtered_trips.append(trip)
    return filtered_trips


################################################################################
# Begin page definitions
################################################################################
register_page(__name__, path="/map")

intro = """## Map"""


def create_lines_map(coordinates):
    traces = []
    # iterate by 2 since coordinates stores start and end pairwise
    for i in range(0, len(coordinates['lon']), 2):
        traces.append(
            go.Scattermapbox(
                mode="markers+lines",
                lon=[coordinates['lon'][i], coordinates['lon'][i+1]],
                lat=[coordinates['lat'][i], coordinates['lat'][i+1]],
                marker={'size': 9, 'color': coordinates['color'][i]},
                text=coordinates['text'],
                hoverinfo='text',
            )
        )

    fig = go.Figure(data=traces)
    (zoom, center) = get_mapbox_zoom_and_center(coordinates)
    fig.update_layout(
        showlegend=False,
        margin={'l': 0, 't': 30, 'b': 0, 'r': 0},
        mapbox_style="open-street-map",
        mapbox_center_lon=center[0],
        mapbox_center_lat=center[1],
        mapbox_zoom=zoom,
        height=650,
    )

    return fig


def get_start_and_end_hover_text(trip):
    trip_info = {
        'User': trip.get('user_id', 'Unknown user'),
        'Distance (m)': round(trip.get('data.distance_meters', 0), 2),
        'Labeled Mode': trip.get('mode_confirm', 'Unlabeled'),
        'Sensed Mode': trip.get("data.primary_sensed_mode") or "None",
    }
    if ble_enabled:
        trip_info['BLE Mode'] = trip.get("data.primary_ble_sensed_mode") or "None"

    start_info = dict(trip_info, Time=trip.get('trip_start_time_str'))
    end_info = dict(trip_info, Time=trip.get('trip_end_time_str'))
    fmt_dict = lambda d: '<br>'.join([f'<b>{k}:</b> {v}' for k, v in d.items()])
    return [fmt_dict(start_info), fmt_dict(end_info)]


def get_map_coordinates(filtered_trips, label_options):
    """
    Build arrays of lat, lon, color, and text so that the bubble map can
    display detailed hover info (including base BLE mode) for each start/end.
    """
    coordinates = {
        'lat': [],
        'lon': [],
        'color': [],
        'text': [],  # We'll store the hover text for each point here
    }

    for trip in filtered_trips:
        coordinates['lon'].extend([trip['start_coordinates'][0], trip['end_coordinates'][0]])
        coordinates['lat'].extend([trip['start_coordinates'][1], trip['end_coordinates'][1]])
        primary_mode = trip.get('mode_confirm') \
                       or (ble_enabled and trip.get('data.primary_ble_sensed_mode')) \
                       or trip.get("data.primary_sensed_mode")
        rich_mode = emcdb.get_rich_mode_for_value(primary_mode, label_options)
        color = rich_mode['color']
        coordinates['color'].extend([color, color])
        (start_hover_text, end_hover_text) = get_start_and_end_hover_text(trip)
        coordinates['text'].extend([start_hover_text, end_hover_text])
    return coordinates

def create_heatmap_fig(coordinates):
    fig = go.Figure()
    if coordinates.get('lat'):
        fig.add_trace(
            go.Densitymapbox(
                lon=coordinates['lon'],
                lat=coordinates['lat'],
                name = '',
                
            )
        )
        (zoom, center) = get_mapbox_zoom_and_center(coordinates)
        fig.update_layout(
            mapbox_style='open-street-map',
            mapbox_center_lon=center[0],
            mapbox_center_lat=center[1],
            mapbox_zoom=zoom,
            margin={"r": 0, "t": 30, "l": 0, "b": 0},
            height=650,
        )
    return fig


# derived from https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/12
# workaround until dash team implements dynamic zoom on mapbox Scattermapbox and Densitymapbox
def get_mapbox_zoom_and_center(coords):
    if (not coords.get('lon') or not coords.get('lat') or len(coords['lon']) != len(coords['lat'])):
        logging.error("Invalid input to get_mapbox_zoom_and_center, coords: " + str(coords))
        return 0, (0, 0)
    min_lonlat = (min(coords['lon']), min(coords['lat']))
    max_lonlat = (max(coords['lon']), max(coords['lat']))
    midpoint = (min_lonlat[0] + max_lonlat[0]) / 2, (min_lonlat[1] + max_lonlat[1]) / 2
    area = (max_lonlat[0] - min_lonlat[0]) * (max_lonlat[1] - min_lonlat[1])
    zoom = np.interp(x=area,
                      xp=[0, 5**-10, 4**-10, 3**-10, 2**-10, 1**-10, 1**-5],
                      fp=[20, 15,    14,     13,     12,     7,      5])
    zoom = int(min(15, zoom))
    logging.debug("zoom: " + str(zoom) + " midpoint: " + str(midpoint))
    return zoom, midpoint

def create_bubble_fig(coordinates):
    fig = go.Figure()
    if coordinates.get('lon'):
        fig.add_trace(
            go.Scattermapbox(
                lat=coordinates['lat'],
                lon=coordinates['lon'],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=9,
                    color=coordinates['color'],
                ),
                text=coordinates['text'],
                hoverinfo='text',
            )
        )
        (zoom, center) = get_mapbox_zoom_and_center(coordinates)
        fig.update_layout(
            autosize=True,
            mapbox_style='open-street-map',
            mapbox_center_lon=center[0],
            mapbox_center_lat=center[1],
            mapbox_zoom=zoom,
            mapbox_bearing=0,
            margin={'r': 0, 't': 30, 'l': 0, 'b': 0},
            height=650,
        )
    return fig


def create_single_option(value, color=None, label=None, icon=None):
    if icon:
        square = DashIconify(icon=f"mdi:{icon}", style={'margin': 'auto', 'color': color})
    elif color:
        square = html.Div(
            style={
                'background-color': color,
                'width': 10,
                'height': 10,
                'margin': 'auto'
            }
        )
    else:
        square = html.Div()

    text = html.Span(
        label or value,
        style={
            'font': '14px monospace',
            'color': color if color and icon else 'unset',
            'maxHeight': 60,
            'overflow': 'hidden'
        }
    )
    return {
        'label': html.Span([square, text], style={'display': 'flex', 'gap': 5}),
        'value': value,
    }


def create_users_dropdown_options(trips, uuids_perm, tokens_perm):
    options = []
    unique_users = set()
    for trip in trips:
        user_id = trip.get('user_id')
        if user_id:
            unique_users.add(user_id)
    options = []
    for user_id in sorted(unique_users):
        if tokens_perm:
            token = ecwu.User.fromUUID(UUID(user_id))._User__email
            label = f"{token}\n({user_id})" if uuids_perm else token
        else:
            label = user_id if uuids_perm else ''
        options.append(create_single_option(user_id, label=label))
    return options


def create_modes_dropdown_options(trips, mode_key, label_options):
    unique_modes = set()
    for trip in trips:
        sensed_mode = trip.get(mode_key)
        if sensed_mode:
            unique_modes.add(sensed_mode)
    options = []
    for mode in sorted(unique_modes):
        base_mode = emcdb.get_rich_mode_for_value(mode, label_options)
        opt = create_single_option(
            mode,
            base_mode['color'],
            label=mode,
            icon=base_mode['icon']
        )
        options.append(opt)
    return options


map_type_options = []
if has_permission('map_heatmap'):
    map_type_options.append({'label': 'Density Heatmap', 'value': 'heatmap'})
if has_permission('map_bubble'):
    map_type_options.append({'label': 'Bubble Map', 'value': 'bubble'})
if has_permission('map_trip_lines'):
    map_type_options.append({'label': 'Trips Lines', 'value': 'lines'})


layout = html.Div(
    [
        # Store for label options so it exists
        dcc.Store(id="store-label-options", data={}),
        dcc.Markdown(intro),

        dbc.Row([
            dbc.Col(
                [
                    html.Label('Map Type'),
                    dcc.Dropdown(
                        id='map-type-dropdown',
                        options=map_type_options,
                        value=map_type_options[0]['value'] if map_type_options else None,
                    ),
                ],
                xl=3, lg=4, sm=6,
            )
        ]),
        dbc.Row(id='map-filters-row'),
        dbc.Row(id="trip-map-row")
    ],
    style={'display': 'flex', 'flex-direction': 'column', 'gap': 8}
)

@callback(
    Output('map-filters-row', 'children'),
    Input('map-type-dropdown', 'value'),
    Input('store-trips', 'data'),
    Input('store-label-options', 'data'),
)
def create_filters_dropdowns(map_type, trips_data, label_options):
    filters = []
    trips = trips_data['data']

    labeled_modes_options = create_modes_dropdown_options(trips, 'mode_confirm', label_options)
    filters.append(('Labeled Modes', 'labeled_modes', labeled_modes_options))

    sensed_modes_options = create_modes_dropdown_options(trips, 'data.primary_sensed_mode', label_options)
    filters.append(('Sensed Modes', 'sensed_modes', sensed_modes_options))

    if config.get('vehicle_identities'):
        ble_modes_options = create_modes_dropdown_options(trips, 'data.primary_ble_sensed_mode', label_options)
        filters.append(('BLE Modes', 'ble_modes', ble_modes_options))

    uuids_perm, tokens_perm = has_permission('options_uuids'), has_permission('options_tokens')
    if map_type == 'lines' and (uuids_perm or tokens_perm):
        users_options = create_users_dropdown_options(trips, uuids_perm, tokens_perm)
        filters.append(('Users', 'users', users_options))

    return [
        dbc.Col(
            [
                html.Label(label),
                dcc.Dropdown(
                    id={'type': 'map-filter-dropdown', 'id': filter_id},
                    options=options,
                    multi=True,
                    disabled=len(options) == 0,
                    optionHeight=(60 if filter_id == 'users' else 35),
                )
            ],
            lg=4, sm=6,
        )
        for label, filter_id, options in filters
    ]


@callback(
    Output('trip-map-row', 'children'),
    Input('map-type-dropdown', 'value'),
    Input({'type': 'map-filter-dropdown', 'id': ALL}, 'value'),
    Input({'type': 'map-filter-dropdown', 'id': ALL}, 'id'),
    Input('store-trips', 'data'),
    Input('store-label-options', 'data'),
)
def update_output(map_type, filter_values, filter_ids, trips_data, label_options):
    logging.info("=== Entered update_output callback ===")
    logging.info(f"map_type: {map_type}")
    logging.info(f"filter_values: {filter_values}, filter_ids: {filter_ids}")

    trips = trips_data['data']

    # dict mapping filter IDs to selected values
    filter_dict = {filter_id['id']: value for filter_id, value in zip(filter_ids, filter_values)}
    selected_labeled_modes = filter_dict.get('labeled_modes', [])
    selected_ble_modes = filter_dict.get('ble_modes', [])
    selected_sensed_modes = filter_dict.get('sensed_modes', [])
    selected_uuids = filter_dict.get('users', [])

    logging.info(f"selected_labeled_modes={selected_labeled_modes} | selected_ble_modes={selected_ble_modes} | selected_sensed_modes={selected_sensed_modes} | selected_uuids={selected_uuids}")

    if selected_labeled_modes:
        trips = filter_trips(trips, selected_labeled_modes, 'mode_confirm')
    if selected_sensed_modes:
        trips = filter_trips(trips, selected_sensed_modes, 'data.primary_sensed_mode')
    if selected_ble_modes:
        trips = filter_trips(trips, selected_ble_modes, 'data.primary_ble_sensed_mode')
    if selected_uuids:
        trips = filter_trips(trips, selected_uuids, 'user_id')

    filter_message = dbc.Alert(f'Showing {len(trips)} trips', color="light")
    if not trips:
        logging.info("No trips in filtered data, returning with message")
        return filter_message
    
    coordinates = get_map_coordinates(trips, label_options)
    # Build the figure based on map_type
    if map_type == 'lines':
        logging.info("Drawing lines map")
        fig = create_lines_map(coordinates)
    elif map_type == 'heatmap':
        logging.info("Drawing heatmap")
        fig = create_heatmap_fig(coordinates)
    elif map_type == 'bubble':
        logging.info("Drawing bubble map")
        fig = create_bubble_fig(coordinates)
    else:
        logging.info("No known map_type specified; creating empty figure")
        fig = go.Figure()
    logging.info("=== update_output callback complete ===\n")

    return html.Div([
        dcc.Graph(figure=fig),
        filter_message,
    ])


@callback(
    Output({'type': 'map-filter-dropdown', 'id': 'users'}, 'disabled'),
    Input({'type': 'map-filter-dropdown', 'id': 'labeled_modes'}, 'value'),
)
def control_user_dropdowns(selected_modes):
    # If the user has chosen any labeled modes, disable the user selection
    return bool(selected_modes)
