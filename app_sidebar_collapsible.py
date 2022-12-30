"""
This app creates an animated sidebar using the dbc.Nav component and some local
CSS. Each menu item has an icon, when the sidebar is collapsed the labels
disappear and only the icons remain. Visit www.fontawesome.com to find
alternative icons to suit your needs!

dcc.Location is used to track the current location, a callback uses the current
location to render the appropriate page content. The active prop of each
NavLink is set automatically according to the current pathname. To use this
feature you must install dash-bootstrap-components >= 0.11.0.

For more details on building multi-page Dash applications, check out the Dash
documentation: https://dash.plot.ly/urls
"""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html
import os

# Data/file handling imports
import pathlib

# Global data modules to share data across callbacks
# (Not sure how this stands up in multi-user/hosted situations)
import globals as gl
import globalsUpdater as gu

OPENPATH_LOGO = "https://www.nrel.gov/transportation/assets/images/openpath-logo.jpg"

#------------------------------------------------#
# Set the data path
#------------------------------------------------#

# For data that lives within the application.
# Set the path to the data directory
DATA_PATH = pathlib.Path(__file__).parent.joinpath("./data/").resolve()

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    use_pages=True
)

sidebar = html.Div(
    [
        html.Div(
            [
                # width: 3rem ensures the logo is the exact width of the
                # collapsed sidebar (accounting for padding)
                html.Img(src=OPENPATH_LOGO, style={"width": "3rem"}),
                html.H2("OpenPATH"),
            ],
            className="sidebar-header",
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.I(className="fas fa-home me-2"), 
                        html.Span("Overview")
                    ],
                    href="/",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-sharp fa-solid fa-database me-2"),
                        html.Span("Data"),
                    ],
                    href="/data",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-globe me-2"),
                        html.Span("Map"),
                    ],
                    href="/map",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-envelope-open-text me-2"),
                        html.Span("Push notification"),
                    ],
                    href="/push_notification",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-gear me-2"),
                        html.Span("Settings"),
                    ],
                    href="/settings",
                    active="exact",
                )
            ],
            vertical=True,
            pills=True,
        ),
    ],
    className="sidebar",
)

CONTENT_STYLE = {
    "margin-left": "5rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}
content = html.Div(dash.page_container, style=CONTENT_STYLE)

app.layout = html.Div(
    [
        dcc.Location(id="url"), 
        sidebar, 
        content
    ]
)

if __name__ == "__main__":
    envPort = int(os.getenv('SERVER_PORT', '8050'))
    envDebug = os.getenv('DASH_DEBUG_MODE', 'True').lower() == 'true'
    app.run_server(debug=envDebug, host='0.0.0.0', port=envPort)
