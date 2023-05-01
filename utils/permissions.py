import json
import os

import requests

from utils import constants

STUDY_NAME = os.getenv('STUDY_NAME')
PATH = os.getenv('CONFIG_PATH')
CONFIG_URL = PATH + STUDY_NAME + ".nrel-op.json"
response = requests.get(CONFIG_URL)
permissions = json.loads(response.text).get("admin_dashboard", {})


def has_permission(perm):
    return True if permissions.get(perm) is True else False


def get_allowed_named_trip_columns():
    return permissions.get('additional_trip_columns', [])


def get_required_columns():
    required_cols = {'user_id'}
    required_cols.update(col['path'] for col in constants.REQUIRED_NAMED_COLS)
    return required_cols


def get_all_named_trip_columns():
    named_columns = [item for item in constants.REQUIRED_NAMED_COLS]
    named_columns.extend(
        get_allowed_named_trip_columns()
    )
    return named_columns

def get_all_trip_columns():
    columns = set()
    columns.update(get_allowed_trip_columns())
    columns.update(
        col['path'] for col in get_allowed_named_trip_columns()
    )
    columns.update(get_required_columns())
    return columns


def get_allowed_trip_columns():
    columns = set(constants.VALID_TRIP_COLS)
    for column in permissions.get("data_trips_columns_exclude", []):
        columns.discard(column)
    return columns


def get_uuids_columns():
    columns = set(constants.valid_uuids_columns)
    for column in permissions.get("data_uuids_columns_exclude", []):
        columns.discard(column)
    return columns


def get_token_prefix():
    return permissions['token_prefix'] + '_' if permissions.get('token_prefix') else ''
