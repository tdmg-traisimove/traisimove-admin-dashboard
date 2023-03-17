# Dockerized Dash App Template


https://towardsdatascience.com/dockerize-your-dash-app-1e155dd1cea3


Basic Dash app with data load, global variable module, and various UI examples.

### NREL Branding
This app uses the NREL Branding component, which is included as a .tgz and is installed via pip (see below).


## How to run this app

(The following instructions apply to Windows command line.)

Create and activate a new virtual environment (recommended) by running
the following:

On Windows

```
virtualenv venv
\venv\scripts\activate
```
On Mac
```
virtualenv venv
source venv/bin/activate
```

Or if using linux

```bash
python3 -m venv myvenv
source myvenv/bin/activate
```

Install the requirements:

```
pip install -r dashboard/requirements.txt
```

Run the app:

```
python app.py
```
You can run the app on your browser at http://127.0.0.1:8050



## Resources

To learn more about Dash, please visit [documentation](https://plot.ly/dash).


## Docker

`docker build -t dash-app .`

`docker run dash-app`

## Docker Compose (recommended)

`docker compose -f docker-compose-dash-app.yml build`

`docker compose -f docker-compose-dash-app.yml up`

# Dynamic Config

## User Permissions

The following document outlines the permissions that a user can have within the dashboard application. The permission
is specified as a key-value pair, where the key is the name of the permission and the value is either `true` or `false`.
If the value is `true`, the user has access to the corresponding feature or data, and if the value is `false`, the user 
does not have access. You need to place these key-value pairs within the `admin_dashboard` key in one of the configs of 
the emission.

These are all the permissions that you can specify:

### Overview Page
- `overview_users`: User can see the total number of users in the Overview page.
- `overview_active_users`: User can see the number of active users in the Overview page.
- `overview_trips`: User can see the number of trips in the Overview page.
- `overview_signup_trends`: User can view the signup trend graph in the Overview page.
- `overview_trips_trend`: User can view the trip trend graph in the Overview page.

### Data Page
- `data_uuids`: User can view the UUIDs data in the Data page.
- `data_trips`: User can view the trips data in the Data page.
- `data_trips_columns_exclude`: It used to specify a list of column names that should be excluded from the trips data
that is displayed on the Data page. It includes valid columns from the **Stage_analysis_timeseries** collection. Valid
columns are specified in the following sections.
- `data_uuids_columns_exclude`: It used to specify a list of column names that should be excluded from the uuids data
that is displayed on the Data page. It includes valid columns from the **Stage_uuids** collection. Valid columns are 
specified in the following sections.

### Token Page
- `token_generate`: User can generate new tokens in the Token page.
- `token_prefix`: The prefix that will be added to all tokens when creating new tokens.

### Map Page
- `map_heatmap`: User can view the heatmap in the Map page.
- `map_bubble`: User can view the bubble map in the Map page.
- `map_trip_lines`: User can view the trip lines map in the Map page.

### Push Notification Page
- `push_send`: User can send push notifications in the Push Notification page.

### Dropdown Options
- `options_uuids`: User can see the UUIDs of users in dropdowns and choose between them.
- `options_emails`: User can see the emails of users in dropdowns and choose between them.
<br><br><br>


## Stage_uuids

This document represents a single row in a MongoDB collection. The document contains a single object of a uuid with the
following fields that you can provide in `data_uuids_columns_exlude`:

```python
valid_uuids_columns = [
    'user_token',
    'user_id',
    'update_ts',
]
```


## Stage_analysis_timeseries

It contains information about a segmentation trip. It has the following fields that you can provide in
`data_trips_columns_exclude`.

```python
valid_trip_columns = [
    "data.source",
    "data.start_ts",
    "data.start_local_dt",
    "data.start_fmt_tm",
    "data.start_place",
    "data.start_loc",
    "data.end_ts",
    "data.end_local_dt",
    "data.end_fmt_time",
    "data.end_place",
    "data.end_loc",
    "data.duration",
    "data.distance",
    "metadata.key",
    "metadata.platform",
    "metadata.write_ts",
    "metadata.time_zone",
    "metadata.write_local_dt",
    "metadata.write_fmt_time",
    "user_id",
]
```
<br><br>