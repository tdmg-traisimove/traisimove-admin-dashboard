import json
import requests

from opadmindash.constants import valid_trip_columns, valid_uuids_columns


raw_url = "https://raw.githubusercontent.com/"
config_url = raw_url + "AlirezaRa94/nrel-openpath-deploy-configs/main/configs/admin-dashboard-permissions.nrel-op.json"
response = requests.get(config_url)
permissions = json.loads(response.text).get("admin_dashboard", {})


def has_permission(perm):
    return True if permissions.get(perm) is True else False


def get_trips_columns():
    columns = list()
    for column in permissions.get("data_trips_columns", []):
        if column in valid_trip_columns:
            columns.append(column)
    return columns if columns else valid_trip_columns


def get_uuids_columns():
    columns = list()
    for column in permissions.get("data_uuids_columns", []):
        if column in valid_uuids_columns:
            columns.append(column)
    return columns if columns else valid_uuids_columns
