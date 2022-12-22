"""
Note that the callback will trigger even if prevent_initial_call=True. This is because dcc.Location must
be in app.py.  Since the dcc.Location component is not in the layout when navigating to this page, it triggers the callback.
The workaround is to check if the input value is None.

"""


import dash
from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc

register_page(__name__, path="/data")

intro = """
## Data

Data Data Data Data Data Data Data DataData Data Data Data
Data Data Data Data
Data Data Data Data

Data Data Data DataData Data Data DataData Data Data Data
Data Data Data DataData Data Data DataData Data Data DataData Data Data Data

Data Data Data DataData Data Data DataData Data Data DataData Data Data DataData Data Data Data
"""


layout = html.Div(
    [
        dcc.Markdown(intro)
    ]
)
