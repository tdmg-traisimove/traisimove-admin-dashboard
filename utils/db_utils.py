from datetime import datetime, timezone
import sys

import pandas as pd
import logging

import emission.core.get_database as edb
import emission.storage.timeseries.abstract_timeseries as esta
import emission.storage.timeseries.timequery as estt

from utils.permissions import get_trips_columns, get_additional_trip_columns


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

    projection = {
        '_id': 0,
        'user_id': 1,
        'trip_start_time_str': '$data.start_fmt_time',
        'trip_end_time_str': '$data.end_fmt_time',
        'timezone': '$data.start_local_dt.timezone',
        'start_coordinates': '$data.start_loc.coordinates',
        'end_coordinates': '$data.end_loc.coordinates',
    }

    for column in get_trips_columns():
        projection[column] = 1

    for column in get_additional_trip_columns():
        projection[column['label']] = column['path']

    ts = esta.TimeSeries.get_aggregate_time_series()
    # Note to self, allow end_ts to also be null in the timequery
    # we can then remove the start_time, end_time logic
    entries = ts.find_entries(
        key_list=["analysis/confirmed_trip"],
        time_query=estt.TimeQuery("data.start_ts", start_ts, end_ts),
    )
    df = pd.json_normalize(list(entries))
    # Alireza TODO: Make this be configurable, to support only the projection needed
    # logging.warn("Before filtering, df columns are %s" % df.columns)
    df = df[["user_id", "data.start_fmt_time", "data.end_fmt_time", "data.distance", "data.duration", "data.start_loc.coordinates", "data.end_loc.coordinates"]]
    # logging.warn("After filtering, df columns are %s" % df.columns)
    if not df.empty:
        df['user_id'] = df['user_id'].apply(str)
        df['trip_start_time_str'] = df['data.start_fmt_time']
        df['trip_end_time_str'] = df['data.end_fmt_time']
        df['start_coordinates'] = df['data.start_loc.coordinates']
        df['end_coordinates'] = df['data.end_loc.coordinates']
        if 'data.start_place' in df.columns:
            df['data.start_place'] = df['data.start_place'].apply(str)
        if 'data.end_place' in df.columns:
            df['data.end_place'] = df['data.end_place'].apply(str)
    return df
