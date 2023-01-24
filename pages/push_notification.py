"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must
be in app.py.  Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.

"""
from dash import dcc, html, Input, Output, callback, register_page
import pandas as pd

register_page(__name__, path="/push_notification")

intro = """
## Push notification
"""


layout = html.Div([
    dcc.Markdown(intro),
    html.Div([
        html.Div(children=[
            html.Label('Sending to:'),
            dcc.RadioItems(
                className='radio-items',
                id='push-receiver-options',
                options=[
                    {'label': 'All users', 'value': 'all'},
                    {'label': 'User Emails', 'value': 'email'},
                    {'label': 'User UUIDs', 'value': 'uuid'},
                ],
                value='all',
                style={
                    'padding': '5px',
                    'margin': 'auto'
                }
            ),

            html.Label('User Emails', style={'padding-top': '5px'}),
            dcc.Dropdown(multi=True, disabled=True, id='push-user-emails'),

            html.Label('UUIDs', style={'padding-top': '5px'}),
            dcc.Dropdown(multi=True, disabled=True, id='push-user-uuids'),

            html.Br(),
            html.Label('Survey Specs'),
            dcc.Dropdown(options=["Notify", "Survey", "Popup", "Website"], value='Notify'),

            html.Br(),
            html.Label('Log Messages'),
            dcc.Textarea(value='We can follow sending push here', id='push-log', disabled=True, style={
                'font-size': '14px', 'width': '100%', 'display': 'block', 'margin-bottom': '10px',
                'margin-right': '5px', 'height':'200px', 'verticalAlign': 'top', 'background-color': '#d4c49b',
                'overflow': 'hidden',
            })
        ], style={'padding': 10, 'flex': 1}),

        html.Div(children=[
            html.Label('Title'),
            html.Br(),
            dcc.Textarea(value='', id='push-title', style={
                'font-size': '14px', 'width': '100%', 'display': 'block', 'margin-bottom': '10px',
                'margin-right': '5px', 'height': '30px', 'verticalAlign': 'top', 'background-color': '#b4dbf0',
                'overflow': 'hidden',
            }),

            html.Label('Message'),
            html.Br(),
            dcc.Textarea(value='', id='push-message', style={
                'font-size': '14px', 'width': '100%', 'display': 'block', 'margin-bottom': '10px',
                'margin-right': '5px', 'height':'100px', 'verticalAlign': 'top', 'background-color': '#b4dbf0',
                'overflow': 'hidden',
            }),
            html.Br(),

            html.Button(children='Send', id='push-send-button', n_clicks=0, style={
                'font-size': '14px', 'width': '140px', 'display': 'block', 'margin-bottom': '10px',
                'margin-right': '5px', 'height':'40px', 'verticalAlign': 'top', 'background-color': 'green',
                'color': 'white',
            }),
            html.Button(children='Clear Message', id='push-clear-message-button', n_clicks=0, style={
                'font-size': '14px', 'width': '140px', 'display': 'block', 'margin-bottom': '10px',
                'margin-right': '5px', 'height':'40px', 'verticalAlign': 'top', 'background-color': 'red',
                'color': 'white',
            }),
        ], style={'padding': 10, 'flex': 1})
    ], style={'display': 'flex', 'flex-direction': 'row'})
])

@callback(
    Output('push-user-emails', 'disabled'),
    Output('push-user-uuids', 'disabled'),
    Input('push-receiver-options', 'value'),
)
def handle_receivers(value):
    emails_disabled = True
    uuids_disabled = True
    if value == 'email':
        emails_disabled = False
    elif value == 'uuid':
        uuids_disabled = False
    return emails_disabled, uuids_disabled


@callback(
    Output('push-user-emails', 'options'),
    Output('push-user-uuids', 'options'),
    Input('store-uuids', 'data'),
)
def populate_data(uuids_data):
    uuids_df = pd.DataFrame(uuids_data.get('data'))
    emails = uuids_df['user_token'].tolist()
    uuids = uuids_df['user_id'].tolist()
    return emails, uuids


@callback(
    Output('push-message', 'value'),
    Output('push-clear-message-button', 'n_clicks'),
    Input('push-clear-message-button', 'n_clicks'),
)
def clear_push_message(n_clicks):
    return '', 0


@callback(
    Output('push-log', 'value'),
    Output('push-send-button', 'n_clicks'),
    Input('push-log', 'value'),
    Input('push-send-button', 'n_clicks'),
    Input('push-receiver-options', 'value'),
    Input('push-user-emails', 'value'),
    Input('push-user-uuids', 'value'),
)
def send_push_notification(log, send_n_clicks, receiver, emails, uuids):
    if send_n_clicks > 0:
        if receiver == 'all':
            return "About to send push to all users", 0
        elif receiver == 'email':
            return f"About to send push to email list = {emails}", 0
        elif receiver == 'uuid':
            return f"About to send push to uuid list = {uuids}", 0
        else:
            return 'send clicked', 0
    return log, 0
