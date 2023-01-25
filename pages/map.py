"""
Note that the callback will trigger even if prevent_initial_call=True. This is
because dcc.Location must be in app.py. Since the dcc.Location component is not
in the layout when navigating to this page, it triggers the callback. The
workaround is to check if the input value is None.
"""
from dash import dcc, html, Input, Output, callback, register_page, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate

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


def create_user_ids_options(trips_group_by_user_id):
    options = list()
    for user_id in trips_group_by_user_id:
        color = trips_group_by_user_id[user_id]['color']
        options.append({
            'label': html.Span(
                [
                    html.Div(id='dropdown-squares', style={'background-color': color}),
                    html.Span(user_id, style={'font-size': 15, 'padding-left': 10})
                ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
            ),
            'value': user_id
        })
    return options


layout = html.Div(
    [
        dcc.Store(id="store-trips-map", data={}),
        dcc.Markdown(intro),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(id='user-dropdown', multi=True),
            )
        ]),

        dbc.Row(
            dcc.Graph(id="trip-map")
        ),
    ]
)

@callback(
    Output('user-dropdown', 'options'),
    Output('user-dropdown', 'value'),
    Input('store-trips-map', 'data'),
    Input('user-dropdown', 'value'),
)
def update_user_ids_options(trips_data, selected_user_ids):
    user_ids_options = create_user_ids_options(trips_data)
    if selected_user_ids is not None:
        selected_user_ids = [user_id for user_id in selected_user_ids if user_id in trips_data]
    return user_ids_options, selected_user_ids

@callback(
    Output('trip-map', 'figure'),
    Input('store-trips-map', 'data'),
    Input('user-dropdown', 'value'),
)
def update_output(trips_data, user_id_list):
    user_id_list = user_id_list if user_id_list is not None else []
    return create_fig(trips_data, user_id_list)

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
