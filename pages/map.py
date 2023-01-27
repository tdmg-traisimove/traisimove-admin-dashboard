"""
Note that the callback will trigger even if prevent_initial_call=True. This is
because dcc.Location must be in app.py. Since the dcc.Location component is not
in the layout when navigating to this page, it triggers the callback. The
workaround is to check if the input value is None.
"""
from uuid import UUID

from bson import Binary
from dash import dcc, html, Input, Output, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

import emission.core.wrapper.user as ecwu

register_page(__name__, path="/map")

intro = """## Map"""


def create_fig(trips_group_by_user_id, user_id_list):
    fig = go.Figure()
    start_lon, start_lat = 0, 0
    for user_id in user_id_list:
        color = trips_group_by_user_id[user_id]['color']
        trips = trips_group_by_user_id[user_id]['trips']
        start_coordinates = [trip['start_coordinates'] for trip in trips]
        end_coordinates = [trip['end_coordinates'] for trip in trips]
        n = len(start_coordinates)

        for i in range(n):
            if i == 0:
                start_lon = start_coordinates[i][0]
                start_lat = end_coordinates[i][1]

            fig.add_trace(
                go.Scattermapbox(
                    mode="markers+lines",
                    lon=[start_coordinates[i][0], end_coordinates[i][0]],
                    lat=[start_coordinates[i][1], end_coordinates[i][1]],
                    marker={'size': 10, 'color': color},
                    legendrank=i + 1,
                )
            )

    fig.update_layout(
        showlegend=False,
        margin={'l': 0, 't': 30, 'b': 0, 'r': 0},
        mapbox={
            'style': "stamen-terrain",
            'center': {'lon': start_lon, 'lat': start_lat},
            'zoom': 11
        },
        height=700,
    )

    return fig


def get_trips_group_by_user_id(trips_data):
    trips_group_by_user_id = None
    trips_df = pd.DataFrame(trips_data['data'])
    if not trips_df.empty:
        trips_group_by_user_id = trips_df.groupby('user_id')
    return trips_group_by_user_id

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
    for user_id in trips_group_by_user_id:
        color = trips_group_by_user_id[user_id]['color']
        user_ids.add(user_id)
        options.append(create_single_option(user_id, color))
    return options, user_ids

def create_user_emails_options(trips_group_by_user_id):
    options = list()
    user_emails = set()
    for user_id in trips_group_by_user_id:
        color = trips_group_by_user_id[user_id]['color']
        user_email = ecwu.User.fromUUID(Binary.from_uuid(UUID(user_id), 3))._User__email
        user_emails.add(user_email)
        options.append(create_single_option(user_email, color))
    return options, user_emails


layout = html.Div(
    [
        dcc.Store(id="store-trips-map", data={}),
        dcc.Markdown(intro),
        dbc.Row([
            dbc.Col([
                html.Label('User UUIDs'),
                dcc.Dropdown(id='user-id-dropdown', multi=True),
            ]),
            dbc.Col([
                html.Label('User Emails'),
                dcc.Dropdown(id='user-email-dropdown', multi=True),
            ])
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
    user_ids_options, user_ids = create_user_ids_options(trips_data)
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
    user_emails_options, user_emails = create_user_emails_options(trips_data)
    if selected_user_emails is not None:
        selected_user_emails = [user_email for user_email in selected_user_emails if user_email in user_emails]
    return user_emails_options, selected_user_emails

@callback(
    Output('trip-map', 'figure'),
    Input('store-trips-map', 'data'),
    Input('user-id-dropdown', 'value'),
    Input('user-email-dropdown', 'value'),
)
def update_output(trips_data, selected_user_ids, selected_user_emails):
    user_ids = set(selected_user_ids) if selected_user_ids is not None else set()
    if selected_user_emails is not None:
        for user_email in selected_user_emails:
            user_ids.add(str(ecwu.User.fromEmail(user_email).uuid.as_uuid(3)))
    return create_fig(trips_data, user_ids)

@callback(
    Output('store-trips-map', 'data'),
    Input('store-trips', 'data'),
)
def store_trips_map_data(trips_data):
    trips_group_by_user_id = get_trips_group_by_user_id(trips_data)
    saved_data = dict()
    if trips_group_by_user_id:
        user_ids = list(trips_group_by_user_id)
        n = len(user_ids) % 360
        k = 359 // (n - 1) if n > 1 else 0
        for ind, user_id in enumerate(trips_group_by_user_id.groups.keys()):
            color = f'hsl({ind * k}, 100%, 50%)'
            trips = trips_group_by_user_id.get_group(user_id).sort_values('trip_start_time_str').to_dict("records")
            saved_data[user_id] = {'color': color, 'trips': trips}
    return saved_data
