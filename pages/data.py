"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must
be in app.py.  Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.

"""
from dash import dcc, html, Input, Output, callback, register_page
import dash_table
import dash_bootstrap_components as dbc

# Etc
import pandas as pd
from dash.exceptions import PreventUpdate

from opadmindash.generate_random_tokens import generateRandomTokensForProgram

register_page(__name__, path="/data")

intro = """
## Data

"""

layout = html.Div(
    [   
        dcc.Markdown(intro),
        dbc.Row([
            dbc.Col(
                [
                    html.Label('Program'),
                    dcc.Input(value='program', id='token-program', type='text', required=True, style={
                        'font-size': '14px', 'width': '100%', 'display': 'block', 'margin-bottom': '10px',
                        'margin-right': '5px', 'height': '30px', 'verticalAlign': 'top', 'background-color': '#b4dbf0',
                        'overflow': 'hidden',
                    }),

                    html.Label('Token Length'),
                    dcc.Input(value=5, id='token-length', type='number', min=3, max=100, required=True, style={
                        'font-size': '14px', 'width': '100%', 'display': 'block', 'margin-bottom': '10px',
                        'margin-right': '5px', 'height': '30px', 'verticalAlign': 'top', 'background-color': '#b4dbf0',
                        'overflow': 'hidden',
                    }),

                    html.Label('Number of Tokens'),
                    dcc.Input(value=1, id='token-count', type='number', min=0, required=True, style={
                        'font-size': '14px', 'width': '100%', 'display': 'block', 'margin-bottom': '10px',
                        'margin-right': '5px', 'height': '30px', 'verticalAlign': 'top', 'background-color': '#b4dbf0',
                        'overflow': 'hidden',
                    }),
                ],
                xl=3,
                lg=4,
                sm=6,
            ),
            dbc.Col(
                [
                    html.Label('Output Format'),
                    dcc.Dropdown(options=['url safe', 'hex', 'base64'], value='url safe', id='token-format'),

                    html.Br(),
                    html.Button(children='Generate Tokens', id='token-generate', n_clicks=0, style={
                        'font-size': '14px', 'width': '140px', 'display': 'block', 'margin-bottom': '10px',
                        'margin-right': '5px', 'height':'40px', 'verticalAlign': 'top', 'background-color': 'green',
                        'color': 'white',
                    }),
                ],
                xl=3,
                lg=4,
                sm=6,
            ),
        ]),
        dcc.Tabs(id="tabs-datatable", value='tab-uuids-datatable', children=[
            # dcc.Tab(label='Demographics survey', value='tab-demographics-survey-datatable'),
            dcc.Tab(label='Tokens', value='tab-tokens-datatable'),
            dcc.Tab(label='UUIDs', value='tab-uuids-datatable'),
            dcc.Tab(label='Trips', value='tab-trips-datatable'),
        ]),
        html.Div(id='tabs-content')
    ]
)

@callback(
    Output('token-generate', 'n_clicks'),
    Input('token-program', 'value'),
    Input('token-length', 'value'),
    Input('token-count', 'value'),
    Input('token-format', 'value'),
    Input('token-generate', 'n_clicks'),
)
def generate_tokens(program, token_length, token_count, out_format, n_clicks):
    if n_clicks is not None and n_clicks > 0:
        tokens = generateRandomTokensForProgram(program, token_length, token_count, out_format)
        for token in tokens:
            print(token)


@callback(
    Output('tabs-content', 'children'),
    [
        Input('tabs-datatable', 'value'),
        Input('interval-component', 'n_intervals'),
        Input('store-uuids', 'data'),
        Input('store-trips', 'data')
    ]
)
def render_content(tab, n_intervals, store_uuids, store_trips):
    if tab == 'tab-uuids-datatable':
        df = pd.DataFrame(store_uuids["data"])
        if df.empty:
            raise PreventUpdate
        return populate_datatable(df)
    elif tab == 'tab-trips-datatable':
        df = pd.DataFrame(store_trips["data"])
        if df.empty:
            raise PreventUpdate
        df = df.drop(columns=["start_coordinates", "end_coordinates"])
        return populate_datatable(df)
    elif tab == 'tab-tokens-datatable':
        pass

def populate_datatable(df):
    if not isinstance(df, pd.DataFrame):
        pass
    return dash_table.DataTable(
            # id='my-table',
            # columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            export_format="csv",
            filter_options={"case": "sensitive"},
            # filter_action="native",
            sort_action="native",  # give user capability to sort columns
            sort_mode="single",  # sort across 'multi' or 'single' columns
            page_current=0,  # page number that user is on
            page_size=50,  # number of rows visible per page
            style_cell={'textAlign': 'left', 
                        # 'minWidth': '100px',
                        # 'width': '100px', 
                        # 'maxWidth': '100px'
                        },
            style_table={'overflowX': 'auto',}
        )