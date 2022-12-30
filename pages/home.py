"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must
be in app.py.  Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.

"""


import dash
from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
from datetime import date

register_page(__name__, path="/")

intro = """
## Home

"""

card_icon = {
    "color": "white",
    "textAlign": "center",
    "fontSize": 30,
    "margin": "auto",
}

def generate_card(title_text, body_text, icon): 
    card = dbc.Col([
        dbc.CardGroup([
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
            ],
            className="mt-4 shadow")
    ], md=3)
    return card

card_users=generate_card("Users (new today)", "100 users (+5)", "fa fa-users")
card_active_users=generate_card("Active users", "70 users", "fa fa-person-walking")
card_trips =generate_card("Number of trips", "728 trips", "fa fa-angles-right")

layout = html.Div(
    [
        dcc.Markdown(intro),
        dcc.DatePickerRange(
                    display_format='D/M/Y',
                    start_date_placeholder_text='D/M/Y',
                    end_date_placeholder_text='D/M/Y',
                    start_date=date(2017, 6, 21)
        ),
        dbc.Row([
            card_users,
            card_active_users,
            card_trips
        ])
    ]
)

