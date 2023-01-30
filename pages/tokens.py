import pandas as pd

import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, callback, State, register_page, dash_table
from dash.exceptions import PreventUpdate

from emission.storage.decorations.token_queries import insert_many_tokens
from opadmindash.generate_qr_codes import saveAsQRCode
from opadmindash.generate_random_tokens import generateRandomTokensForProgram
import emission.core.get_database as edb


register_page(__name__, path="/tokens")

intro = """## Tokens"""
QRCODE_PATH = '/home/alireza/WorkSpace/Fourstep/Dashboard/qrcodes'

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
                    html.Label('Out Format'),
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
        html.Div(id='token-table'),
    ]
)

@callback(
    Output('token-generate', 'n_clicks'),
    Output('token-table', 'children'),
    Input('token-generate', 'n_clicks'),
    State('token-program', 'value'),
    State('token-length', 'value'),
    State('token-count', 'value'),
    State('token-format', 'value'),
)
def generate_tokens(n_clicks, program, token_length, token_count, out_format):
    if n_clicks is not None and n_clicks > 0:
        tokens = generateRandomTokensForProgram(program, token_length, token_count, out_format)
        insert_many_tokens(tokens)
        for token in tokens:
            saveAsQRCode(QRCODE_PATH, token)
    tokens_table = populate_datatable()
    return 0, tokens_table

def populate_datatable():
    df = query_tokens()
    if df.empty:
        raise PreventUpdate
    df['id'] = df.index + 1
    df['qr_code'] = "<img src='" + QRCODE_PATH + "/" + df['token'] + ".png' />"
    df = df.reindex(columns=['id', 'token', 'qr_code'])
    return dash_table.DataTable(
        id='tokens-table',
        css=[dict(selector="p", rule="margin: 0px;")],
        columns=[
            {"id": "id", "name": "id"},
            {"id": "token", "name": "token"},
            {"id": "qr_code", "name": "qr_code", "presentation": "markdown"},
        ],
        data=df.to_dict('records'),
        export_format="csv",
        filter_options={"case": "sensitive"},
        sort_action="native",  # give user capability to sort columns
        sort_mode="single",  # sort across 'multi' or 'single' columns
        page_current=0,  # page number that user is on
        page_size=50,  # number of rows visible per page
        style_cell={
            'textAlign': 'left',
        },
        markdown_options={"html": True},
        style_table={'overflowX': 'auto'}
    )

def query_tokens():
    query_result = edb.get_token_db().find({}, {"_id": 0})
    df = pd.json_normalize(list(query_result))
    return df