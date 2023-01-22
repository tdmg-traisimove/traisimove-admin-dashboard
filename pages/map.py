"""
Note that the callback will trigger even if prevent_initial_call=True. This is
because dcc.Location must be in app.py. Since the dcc.Location component is not
in the layout when navigating to this page, it triggers the callback. The
workaround is to check if the input value is None.
"""
from datetime import datetime, date, timezone
from dash import dcc, html, Input, Output, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

register_page(__name__, path="/map")

intro = """## Map"""


def create_fig_for_user(group, user_id):
    fig = go.Figure()
    start_lon, start_lat = 0, 0

    if group is not None:
        if user_id is None:
            user_id = list(group.groups.keys())[0]
        if user_id is not None:
            trips = group.get_group(user_id)
            trips.sort_values('trip_start_time_str')
            start_coordinates = trips['start_coordinates'].values.tolist()
            end_coordinates = trips['end_coordinates'].values.tolist()
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
                        marker={'size': 10},
                        legendrank=i + 1,
                    )
                )

    fig.update_layout(
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        margin={'l': 0, 't': 30, 'b': 0, 'r': 0},
        mapbox={
            'style': "stamen-terrain",
            'center': {'lon': start_lon, 'lat': start_lat},
            'zoom': 11
        },
        height=700,
    )

    return fig, user_id


def get_trips_df_in_date_range(trips_df, start_date, end_date):
    trips_df['trip_start_time'] = pd.to_datetime(trips_df['trip_start_time_str'], utc=True)
    if start_date is not None:
        start_time = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        trips_df = trips_df[trips_df['trip_start_time'] >= start_time]
    if end_date is not None:
        end_time = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        trips_df = trips_df[trips_df['trip_start_time'] < end_time]
    return trips_df

def get_output_data(trips_df, user_id):
    group = None
    options = []
    if not trips_df.empty:
        group = trips_df.groupby('user_id')
        options = [user_id for user_id in group.groups.keys()]
    fig, user_id = create_fig_for_user(group, user_id)
    return options, user_id, fig


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
    Output('user-dropdown', 'value'),
    Output('trip-map', 'figure'),
    Input('store-trips', 'data'),
    Input('map-date-picker', 'start_date'),
    Input('map-date-picker', 'end_date'),
    Input('user-dropdown', 'value'),
)
def update_output(data, start_date, end_date, value):
    start_date_obj = date.fromisoformat(start_date) if start_date else None
    end_date_obj = date.fromisoformat(end_date) if end_date else None
    trips_df = pd.DataFrame(data['data'])
    trips_df = get_trips_df_in_date_range(trips_df, start_date_obj, end_date_obj)
    return get_output_data(trips_df, value)
