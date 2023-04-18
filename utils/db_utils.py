import logging
from datetime import datetime, timezone

import pandas as pd

import emission.core.get_database as edb
import emission.storage.timeseries.abstract_timeseries as esta
import emission.storage.timeseries.timequery as estt

from utils import constants
from utils.permissions import get_all_trip_columns, get_all_named_trip_columns


def query_uuids(start_date, end_date):
    query = {'update_ts': {'$exists': True}}
    if start_date is not None:
        start_time = datetime.combine(start_date, datetime.min.time()).astimezone(timezone.utc)
        query['update_ts']['$gte'] = start_time

    if end_date is not None:
        end_time = datetime.combine(end_date, datetime.max.time()).astimezone(timezone.utc)
        query['update_ts']['$lt'] = end_time

    projection = {
        '_id': 0,
        'user_id': '$uuid',
        'user_token': '$user_email',
        'update_ts': 1
    }

    # This should actually use the profile DB instead of (or in addition to)
    # the UUID DB so that we can see the app version, os, manufacturer...
    # I will write a couple of functions to get all the users in a time range
    # (although we should define what that time range should be) and to merge
    # that with the profile data
    entries = edb.get_uuid_db().find()
    df = pd.json_normalize(list(entries))
    if not df.empty:
        df['update_ts'] = pd.to_datetime(df['update_ts'])
        df['user_id'] = df['uuid'].apply(str)
        df['user_token'] = df['user_email']
        df.drop(columns=["uuid", "_id"], inplace=True)
    return df

def query_confirmed_trips(start_date, end_date):
    start_ts, end_ts = None, datetime.max.timestamp()
    if start_date is not None:
        start_ts = datetime.combine(start_date, datetime.min.time()).timestamp()

    if end_date is not None:
        end_ts = datetime.combine(end_date, datetime.max.time()).timestamp()

    ts = esta.TimeSeries.get_aggregate_time_series()
    # Note to self, allow end_ts to also be null in the timequery
    # we can then remove the start_time, end_time logic
    entries = ts.find_entries(
        key_list=["analysis/confirmed_trip"],
        time_query=estt.TimeQuery("data.start_ts", start_ts, end_ts),
    )
    df = pd.json_normalize(list(entries))

    # logging.warn("Before filtering, df columns are %s" % df.columns)
    if not df.empty:
        columns = [col for col in get_all_trip_columns() if col in df.columns]
        df = df[columns]
        for col in constants.BINARY_TRIP_COLS:
            if col in df.columns:
                df[col] = df[col].apply(str)
        for named_col in get_all_named_trip_columns():
            if named_col['path'] in df.columns:
                df[named_col['label']] = df[named_col['path']]

    # logging.warn("After filtering, df columns are %s" % df.columns)
    return df
