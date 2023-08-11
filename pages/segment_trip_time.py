from dash import dcc, html, Input, Output, State, callback, register_page, dash_table
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import pandas as pd

import emission.core.wrapper.modeprediction as ecwm
import logging

from utils.permissions import has_permission, permissions
from utils import db_utils

register_page(__name__, path="/segment_trip_time")

intro = """
## Segment average trip time
This page displays some statistics on average trip duration between two selected points.
"""

first_step = """
### First, select a detection radius.
This is the range in meters around start and end point where GPS data can be detected, closest data is prioritized.

This should somewhat match the distance a vehicle can cross at the maximum allowed speed in 30 seconds (sample rate).

A bigger number means more trips will be considered, however it might find trips on the wrong road if roads are close enough.
"""

second_step = """
### Then, select start and end points
These can be anywhere on the map, but are usually on road intersections.

A circle will be shown with the detection radius set on the previous step. For accurate results, the circle should not cover more than one parallel road.
"""

not_enough_data_message = f"""
Not enough segments could be found between endpoints. This means that the number of recorded trips going from start to end point is too low. 
* There could be data, but on an insufficient number of users, breaking anonymity (minimum number of users is currently set to {permissions.get('segment_trip_time_min_users', 0)})
* You could try to increase the detection radius, or chose different start and end points.
"""

layout = html.Div(
    [
        dcc.Store(id='link-trip-time-start', data=(0, 0)),
        dcc.Store(id='link-trip-time-end', data=(0, 0)),
        # dcc.Store(id='store-mode-by-section-id', data={}),
        dcc.Markdown(intro),
        dcc.Markdown(first_step),
        dcc.Slider(
            0,
            2500,
            id='detection-radius',
            value=200,
            tooltip={"placement": "bottom", "always_visible": True},
        ),
        dcc.Markdown(second_step),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4('Start point selection'),
                        dl.Map(
                            [dl.TileLayer(), dl.LayerGroup(id='stt-trip-layer-start')],
                            id='stt-trip-map-start',
                            style={'height': '500px'},
                            center=[32.7, -96.8],
                            zoom=5,
                        ),
                    ]
                ),
                dbc.Col(
                    [
                        html.H4('End point selection'),
                        dl.Map(
                            [dl.TileLayer(), dl.LayerGroup(id='stt-trip-layer-end')],
                            id='stt-trip-map-end',
                            style={'height': '500px'},
                            center=[32.7, -96.8],
                            zoom=5,
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            html.Div(id='message'),
        ),
    ]
)


def map_click(click_lat_lng, radius, circle_color):
    # WARN: There seem to be a bug on click_lat_lng leaflet event, values can be out of bound (e.g: -357 for lat in eu), some kind of modulus might be required
    # Couldn't reproduce it though
    layer_children = [
        dl.Circle(center=click_lat_lng, radius=radius, color=circle_color)
    ]
    endpoint_coords = click_lat_lng
    zoom = 13
    map_center = click_lat_lng
    return layer_children, endpoint_coords, zoom, map_center


@callback(
    Output('stt-trip-map-end', 'zoom', allow_duplicate=True),
    Output('stt-trip-map-end', 'center', allow_duplicate=True),
    Input('link-trip-time-start', 'data'),
    State('stt-trip-map-end', 'zoom'),
    State('stt-trip-map-end', 'center'),
    State('link-trip-time-end', 'data'),
    prevent_initial_call=True,
)
# This is optional, it's used on first selection to help user locate his endpoint
def center_end_map_helper(link_trip_time_start, end_zoom, end_center, link_trip_time_end):
    if link_trip_time_end[0] == 0:
        end_zoom = 13
        end_center = link_trip_time_start
    return end_zoom, end_center


@callback(
    Output('stt-trip-layer-start', 'children'),
    Output('link-trip-time-start', 'data'),
    Output('stt-trip-map-start', 'zoom'),
    Output('stt-trip-map-start', 'center'),
    Input('stt-trip-map-start', 'click_lat_lng'),
    State('detection-radius', 'value'),
    prevent_initial_call=True,
)
def map_start_click(click_lat_lng, radius):
    return map_click(click_lat_lng, radius, "green")


@callback(
    Output('stt-trip-layer-end', 'children'),
    Output('link-trip-time-end', 'data'),
    Output('stt-trip-map-end', 'zoom'),
    Output('stt-trip-map-end', 'center'),
    Input('stt-trip-map-end', 'click_lat_lng'),
    State('detection-radius', 'value'),
    prevent_initial_call=True,
)
def map_end_click(click_lat_lng, radius):
    return map_click(click_lat_lng, radius, "red")


def format_duration_df(df, time_column_name='Time sample'):
    df['Median time (minutes)'] = df.duration / 60  # convert seconds in minutes
    df = df.reset_index().rename(
        columns={
            'start_fmt_time': time_column_name,
            'duration': 'Median time (seconds)',
            'section': 'Count',
            'mode': 'Mode',
        }
    )
    if time_column_name in df:
        if 'Mode' in df:
            df = df[
                [
                    'Mode',
                    time_column_name,
                    'Median time (seconds)',
                    'Median time (minutes)',
                    'Count',
                ]
            ]  # reorder cols
        else:
            df = df[
                [
                    time_column_name,
                    'Median time (seconds)',
                    'Median time (minutes)',
                    'Count',
                ]
            ]  # reorder cols
    else:
        df = df[
            ['Mode', 'Median time (seconds)', 'Median time (minutes)', 'Count']
        ]  # reorder cols
    df = df.to_dict('records')  # Format for display
    return df


@callback(
    Output('message', 'children'),
    Input('link-trip-time-start', 'data'),
    Input('link-trip-time-end', 'data'),
    State('detection-radius', 'value'),
    prevent_initial_call=True,
)
def generate_content_on_endpoints_change(link_trip_time_start, link_trip_time_end, radius):
    if link_trip_time_end[0] == 0 or link_trip_time_start[0] == 0:
        return ''
    # logging.debug("link_trip_time_start: " + str(link_trip_time_start))
    # logging.debug("link_trip_time_end: " + str(link_trip_time_end))

    # Warning: This is a database call, looks here if there is a performance hog.
    # From initial tests, this seems to be performing well, without the need to do geoqueries in memory
    df = db_utils.query_segments_crossing_endpoints(
        link_trip_time_start[0],
        link_trip_time_start[1],
        link_trip_time_end[0],
        link_trip_time_end[1],
        radius,
    )
    total_nb_trips = df.shape[0]
    if total_nb_trips > 0:
        modes = [e.name for e in ecwm.PredictedModeTypes]
        # Warning: Another db call here.
        # In theory, we could load all inferred_section modes in memory at start time, instead of fetching it everytime
        # However, when testing it, the operation is quite heavy on the db and on ram.
        # I opted for querying only sections we're interested in, every time. Page load is still decent, especially when the number of section is low.
        mode_by_section_id = db_utils.query_inferred_sections_modes(
            df['section'].to_list()
        )
        df['mode'] = df['section'].apply(
            lambda section_id: modes[mode_by_section_id[str(section_id)]]
        )
        median_trip_time = df['duration'].median()
        times = pd.to_datetime(df['start_fmt_time'], errors='coerce', utc=True)
        duration_per_hour = format_duration_df(
            df.groupby(times.dt.hour).agg({'duration': 'median', 'section': 'count'}),
            time_column_name='Hour',
        )
        duration_per_mode = format_duration_df(
            df.groupby('mode').agg({'duration': 'median', 'section': 'count'})
        )
        duration_per_mode_per_hour = format_duration_df(
            df.groupby(['mode', times.dt.hour]).agg(
                {'duration': 'median', 'section': 'count'}
            ),
            time_column_name='Hour',
        )
        duration_per_mode_per_month = format_duration_df(
            df.groupby(['mode', times.dt.month]).agg(
                {'duration': 'median', 'section': 'count'}
            ),
            time_column_name='Month',
        )
        return dbc.Row(
            [
                dbc.Col(
                    [
                        html.Br(),
                        html.H3('Results'),
                        html.Div(
                            f'Computed median segment duration is {median_trip_time} seconds, {total_nb_trips} trips considered'
                        ),
                        html.Br(),
                        html.H4('Median segment duration by mode of transport'),
                        dash_table.DataTable(
                            id='duration_per_mode',
                            data=duration_per_mode,
                            sort_action='native',
                            sort_mode='multi',
                            export_format='csv',
                        ),
                        html.Br(),
                        html.H4(
                            'Median segment duration by mode and hour of the day (UTC)'
                        ),
                        dash_table.DataTable(
                            id='duration_per_hour',
                            data=duration_per_hour,
                            sort_action='native',
                            sort_mode='multi',
                            export_format='csv',
                        ),
                        html.Br(),
                        html.H4(
                            'Median segment duration by mode and hour of the day (UTC)'
                        ),
                        dash_table.DataTable(
                            id='duration_per_mode_per_hour',
                            data=duration_per_mode_per_hour,
                            sort_action='native',
                            sort_mode='multi',
                            export_format='csv',
                        ),
                        html.Br(),
                        html.H4('Median segment duration by mode and month'),
                        dash_table.DataTable(
                            id='duration_per_mode_per_month',
                            data=duration_per_mode_per_month,
                            sort_action='native',
                            sort_mode='multi',
                            export_format='csv',
                        ),
                    ],
                    xs=6,
                ),
                dbc.Col(
                    [
                        html.Br(),
                        html.H3('Trips Data'),
                        dash_table.DataTable(
                            id='trips_data',
                            data=df[
                                ['start_fmt_time', 'end_fmt_time', 'mode', 'duration']
                            ].to_dict('records'),
                            page_size=15,
                            sort_action='native',
                            sort_mode='multi',
                            export_format='csv',
                        ),
                    ],
                    xs=6,
                    style={
                        'display': 'block'
                        if has_permission('segment_trip_time_full_trips')
                        else 'none'
                    },
                ),
            ]
        )
    return [html.H3('Results'), dcc.Markdown(not_enough_data_message)]


# This is left as an example on loading all inferred_section modes in memory at start time, instead of fetching it everytime
# This lead to poor memory performances on a larger db
# @callback(
#     Output('store-mode-by-section-id', 'data'),
#     Input('store-trips', 'data') # Only using this an initial trigger
# )
# def load_mode_by_section_id(s):
#     return db_utils.query_inferred_sections_modes()
