import logging
from datetime import datetime, timezone
from uuid import UUID

import arrow

import pandas as pd
import pymongo

import emission.core.get_database as edb
import emission.storage.timeseries.abstract_timeseries as esta
import emission.storage.timeseries.timequery as estt

from utils import constants
from utils import permissions as perm_utils


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

    # logging.debug("Before filtering, df columns are %s" % df.columns)
    if not df.empty:
        columns = [col for col in perm_utils.get_all_trip_columns() if col in df.columns]
        df = df[columns]
        # logging.debug("After getting all columns, they are %s" % df.columns)
        for col in constants.BINARY_TRIP_COLS:
            if col in df.columns:
                df[col] = df[col].apply(str)
        for named_col in perm_utils.get_all_named_trip_columns():
            if named_col['path'] in df.columns:
                df[named_col['label']] = df[named_col['path']]
                # df = df.drop(columns=[named_col['path']])
        # TODO: We should really display both the humanized value and the raw value
        # humanized value for people to see the entries in real time
        # raw value to support analyses on the downloaded data
        # I still don't fully grok which columns are displayed
        # https://github.com/e-mission/op-admin-dashboard/issues/29#issuecomment-1530105040
        # https://github.com/e-mission/op-admin-dashboard/issues/29#issuecomment-1530439811
        # so just replacing the distance and duration with the humanized values for now
        use_imperial = perm_utils.config.get("display_config",
            {"use_imperial": False}).get("use_imperial", False)
        # convert to km to humanize
        df['data.distance'] = df['data.distance'] / 1000
        # convert km further to miles because this is the US, Liberia or Myanmar
        # https://en.wikipedia.org/wiki/Mile
        if use_imperial:
            df['data.distance'] = df['data.distance'] * 0.6213712

        df['data.duration'] = df['data.duration'].apply(lambda d: arrow.utcnow().shift(seconds=d).humanize(only_distance=True))

    # logging.debug("After filtering, df columns are %s" % df.columns)
    # logging.debug("After filtering, the actual data is %s" % df.head())
    # logging.debug("After filtering, the actual data is %s" % df.head().trip_start_time_str)
    return df


def add_user_stats(user_data):
    for user in user_data:
        user_id = user['user_id']

        # TODO: Use the time-series functions when the needed functionality is added.
        total_trips = edb.get_analysis_timeseries_db().count_documents(
            {
                'user_id': UUID(user_id),
                'metadata.key': 'analysis/confirmed_trip',
            }
        )
        user['total_trips'] = total_trips

        labeled_trips = edb.get_analysis_timeseries_db().count_documents(
            {
                'user_id': UUID(user_id),
                'metadata.key': 'analysis/confirmed_trip',
                'data.user_input': {'$ne': {}},
            }
        )
        user['labeled_trips'] = labeled_trips

        if total_trips > 0:
            ts = esta.TimeSeries.get_time_series(UUID(user_id))
            start_ts = ts.get_first_value_for_field(
                key='analysis/confirmed_trip',
                field='data.start_fmt_time',
                sort_order=pymongo.ASCENDING
            )
            if start_ts != -1:
                user['first_trip'] = start_ts

            end_ts = ts.get_first_value_for_field(
                key='analysis/confirmed_trip',
                field='data.start_fmt_time',
                sort_order=pymongo.DESCENDING
            )
            if end_ts != -1:
                user['last_trip'] = end_ts

    return user_data