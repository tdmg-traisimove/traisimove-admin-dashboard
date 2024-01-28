"""
This app creates an animated sidebar using the dbc.Nav component and some local CSS. Each menu item has an icon, when
the sidebar is collapsed the labels disappear and only the icons remain. Visit www.fontawesome.com to find alternative
icons to suit your needs!

dcc.Location is used to track the current location, a callback uses the current location to render the appropriate page
content. The active prop of each NavLink is set automatically according to the current pathname. To use this feature you
must install dash-bootstrap-components >= 0.11.0.

For more details on building multi-page Dash applications, check out the Dash documentation: https://dash.plot.ly/urls
"""
import os
import arrow

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html, Dash
import dash_auth
import logging
# Set the logging right at the top to make sure that debug
# logs are displayed in dev mode
# until https://github.com/plotly/dash/issues/532 is fixed
if os.getenv('DASH_DEBUG_MODE', 'True').lower() == 'true':
    logging.basicConfig(level=logging.DEBUG)

from utils.db_utils import query_uuids, query_confirmed_trips, query_demographics
from utils.permissions import has_permission
import flask_talisman as flt



OPENPATH_LOGO = "https://www.nrel.gov/transportation/assets/images/openpath-logo.jpg"
auth_type = os.getenv('AUTH_TYPE')


if auth_type == 'cognito':
    from utils.cognito_utils import authenticate_user, get_cognito_login_page
elif auth_type == 'basic':
    from config import VALID_USERNAME_PASSWORD_PAIRS

app = Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    use_pages=True,
)
server = app.server  # expose server variable for Procfile

if auth_type == 'basic':
    auth = dash_auth.BasicAuth(
        app,
        VALID_USERNAME_PASSWORD_PAIRS
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
                    href=dash.get_relative_path("/"),
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-sharp fa-solid fa-database me-2"),
                        html.Span("Data"),
                    ],
                    href=dash.get_relative_path("/data"),
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-right-to-bracket me-2"),
                        html.Span("Tokens"),
                    ],
                    href=dash.get_relative_path("/tokens"),
                    active="exact",
                    style={'display': 'block' if has_permission('token_generate') else 'none'},
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-globe me-2"),
                        html.Span("Map"),
                    ],
                    href=dash.get_relative_path("/map"),
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-envelope-open-text me-2"),
                        html.Span("Push notification"),
                    ],
                    href=dash.get_relative_path("/push_notification"),
                    active="exact",
                    style={'display': 'block' if has_permission('push_send') else 'none'},
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-gear me-2"),
                        html.Span("Settings"),
                    ],
                    href=dash.get_relative_path("/settings"),
                    active="exact",
                )
            ],
            vertical=True,
            pills=True,
        ),
    ],
    className="sidebar",
)

# according to docs, DatePickerRange will accept YYYY-MM-DD format
today_date = arrow.now().format('YYYY-MM-DD')
last_week_date = arrow.now().shift(days=-7).format('YYYY-MM-DD')
tomorrow_date = arrow.now().shift(days=1).format('YYYY-MM-DD')

content = html.Div([
    # Global Date Picker
    html.Div([
        dcc.DatePickerRange(
            id='date-picker',
            display_format='D MMM Y',
            start_date=last_week_date,
            end_date=today_date,
            min_date_allowed='2010-1-1',
            max_date_allowed=tomorrow_date,
            initial_visible_month=today_date,
        ),
        html.Div([
            html.Span('Query trips using: ', style={'margin-right': '10px'}),
            dcc.Dropdown(
                id='date-picker-timezone',
                options=[
                    {'label': 'UTC Time', 'value': 'utc'},
                    {'label': 'My Local Timezone', 'value': 'local'},
                    # {'label': 'Local Timezone of Trips', 'value': 'trips'},
                ],
                value='utc',
                clearable=False,
                searchable=False,
                style={'width': '220px'},
            ),
        ],
            style={'margin': '10px 10px 0 0',
                   'display': 'flex',
                   'justify-content': 'right',
                   'align-items': 'center'},
        ),
        dcc.Checklist(
            id='global-filters',
            options=[
                {'label': 'Exclude "test" users', 'value': 'exclude-test-users'},
            ],
            value=['exclude-test-users'],
        ),
    ],
        style={'margin': '10px 10px 0 0',
               'display': 'flex',
               'flex-direction': 'column',
               'align-items': 'end'}
    ),

    # Pages Content
    dcc.Loading(
        type='default',
        fullscreen=True,
        children=html.Div(dash.page_container, style={
            "margin-left": "5rem",
            "margin-right": "2rem",
            "padding": "2rem 1rem",
        })
    ),
])


home_page = [
    sidebar,
    content,
]

@app.callback(
    Output("store-demographics", "data"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
    Input('date-picker-timezone', 'value'),
    Input('store-excluded-uuids', 'data'),
)
def update_store_demographics(start_date, end_date, timezone, excluded_uuids):
    dataframes = query_demographics()
    records = {}
    for key, df in dataframes.items():
        if df.empty:
            records[key] = []
        else:
            non_excluded_df = df[~df['user_id'].isin(excluded_uuids["data"])] # filter excluded UUIDs
            records[key] = non_excluded_df.to_dict("records")
    store = {
        "data": records,
        "length": len(records),
    }
    return store

app.layout = html.Div(
    [
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='store-trips', data={}),
        dcc.Store(id='store-uuids', data={}),
        dcc.Store(id='store-excluded-uuids', data={}), # if 'test' users are excluded, a list of their uuids
        dcc.Store(id='store-demographics', data= {}),
        dcc.Store(id ='store-trajectories', data = {}),   
        html.Div(id='page-content', children=home_page),
    ]
)


# Load data stores
@app.callback(
    Output("store-uuids", "data"),
    Output("store-excluded-uuids", "data"),
    Input('date-picker', 'start_date'),  # these are ISO strings
    Input('date-picker', 'end_date'),  # these are ISO strings
    Input('date-picker-timezone', 'value'),
    Input('global-filters', 'value'),
)
def update_store_uuids(start_date, end_date, timezone, filters):
    # trim the time part, leaving only date as YYYY-MM-DD
    start_date = start_date[:10] if start_date else None
    end_date = end_date[:10] if end_date else None
    dff = query_uuids(start_date, end_date, timezone)
    if dff.empty: return {"data": [], "length": 0}, {"data": [], "length": 0}

    # if 'exclude-testusers' filter is active,
    # exclude any rows with user_token containing 'test', and
    # output a list of those excluded UUIDs so other callbacks can exclude them too
    if 'exclude-test-users' in filters:
      excluded_uuids_list = dff[dff['user_token'].str.contains('test')]['user_id'].tolist()
      non_excluded_dff = dff[~dff['user_id'].isin(excluded_uuids_list)]
      records = non_excluded_dff.to_dict("records")
    else:
      excluded_uuids_list = []
      records = dff.to_dict("records")

    store_uuids = {
        "data": records,
        "length": len(records),
    }
    store_excluded_uuids = {
        "data": excluded_uuids_list,
        "length": len(excluded_uuids_list),
    }
    return store_uuids, store_excluded_uuids


@app.callback(
    Output("store-trips", "data"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
    Input('date-picker-timezone', 'value'),
    Input('store-excluded-uuids', 'data'),
)
def update_store_trips(start_date, end_date, timezone, excluded_uuids):
    # trim the time part, leaving only date as YYYY-MM-DD
    start_date = start_date[:10] if start_date else None
    end_date = end_date[:10] if end_date else None
    df = query_confirmed_trips(start_date, end_date, timezone)
    if df.empty: return {"data": [], "length": 0}

    non_excluded_df = df[~df['user_id'].isin(excluded_uuids["data"])] # filter excluded UUIDs
    records = non_excluded_df.to_dict("records")
    # logging.debug("returning records %s" % records[0:2])
    store = {
        "data": records,
        "length": len(records),
    }
    return store


# Define the callback to display the page content based on the URL path
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'search'),
)
def display_page(search):
    if auth_type == 'cognito':
        try:
            is_authenticated = authenticate_user(search)
        except Exception as e:
            print(e)
            return get_cognito_login_page('Unsuccessful authentication, try again.', 'red')

        if is_authenticated:
            return home_page
        return get_cognito_login_page()

    return home_page

extra_csp_url = [
    "https://raw.githubusercontent.com",
    "https://*.tile.openstreetmap.org",
    "https://cdn.jsdelivr.net",
    "https://use.fontawesome.com",
    "https://www.nrel.gov",
    "data:",
    "blob:"
]
csp = {
       'default-src': ["'self'", "'unsafe-inline'"] + extra_csp_url
      }

flt.Talisman(server, content_security_policy=csp, strict_transport_security=False)

if __name__ == "__main__":
    envPort = int(os.getenv('DASH_SERVER_PORT', '8050'))
    envDebug = os.getenv('DASH_DEBUG_MODE', 'True').lower() == 'true'
    app.logger.setLevel(logging.DEBUG)
    logging.debug("before override, current server config = %s" % server.config)
    server.config.update(
        TESTING=envDebug,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True
    )
    logging.debug("after override, current server config = %s" % server.config)
    app.run_server(debug=envDebug, host='0.0.0.0', port=envPort)
