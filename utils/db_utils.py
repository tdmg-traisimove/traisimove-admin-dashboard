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
    start_ts, end_ts = None, datetime.max.replace(tzinfo=timezone.utc).timestamp()
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
        user_uuid = UUID(user['user_id'])

        # TODO: Use the time-series functions when the needed functionality is added.
        total_trips = edb.get_analysis_timeseries_db().count_documents(
            {
                'user_id': user_uuid,
                'metadata.key': 'analysis/confirmed_trip',
            }
        )
        user['total_trips'] = total_trips

        labeled_trips = edb.get_analysis_timeseries_db().count_documents(
            {
                'user_id': user_uuid,
                'metadata.key': 'analysis/confirmed_trip',
                'data.user_input': {'$ne': {}},
            }
        )
        user['labeled_trips'] = labeled_trips

        profile_data = edb.get_profile_db().find_one({'user_id': user_uuid})
        user['platform'] = profile_data.get('curr_platform')
        user['manufacturer'] = profile_data.get('manufacturer')
        user['app_version'] = profile_data.get('client_app_version')
        user['os_version'] = profile_data.get('client_os_version')
        user['phone_lang'] = profile_data.get('phone_lang')




        if total_trips > 0:
            time_format = 'YYYY-MM-DD HH:mm:ss'
            ts = esta.TimeSeries.get_time_series(user_uuid)
            start_ts = ts.get_first_value_for_field(
                key='analysis/confirmed_trip',
                field='data.end_ts',
                sort_order=pymongo.ASCENDING
            )
            if start_ts != -1:
                user['first_trip'] = arrow.get(start_ts).format(time_format)

            end_ts = ts.get_first_value_for_field(
                key='analysis/confirmed_trip',
                field='data.end_ts',
                sort_order=pymongo.DESCENDING
            )
            if end_ts != -1:
                user['last_trip'] = arrow.get(end_ts).format(time_format)

            last_call = ts.get_first_value_for_field(
                key='stats/server_api_time',
                field='data.ts',
                sort_order=pymongo.DESCENDING
            )
            if last_call != -1:
                user['last_call'] = arrow.get(last_call).format(time_format)

    return user_data

def query_segments_crossing_endpoints(start_lat, start_long, end_lat, end_long, range_around_endpoints=400):
    # data.loc only appears in analysis/recreated_location
    query_start = {
        'data.loc': {
            '$near': {
                '$geometry': {
                    'type': 'Point',
                    'coordinates': [start_long, start_lat]
                }, 
                '$maxDistance': range_around_endpoints
            }
        }
    }
    query_end = {
        'data.loc': {
            '$near': {
                '$geometry': {
                    'type': 'Point',
                    'coordinates': [end_long, end_lat]
                }, 
                '$maxDistance': range_around_endpoints
            }
        }
    }
    res_end = edb.get_analysis_timeseries_db().find(query_end)
    end_by_section = {}
    for elt in res_end:
        elt_data = elt.get('data')
        if elt_data:
            section_id = elt_data.get('section')
            # This makes sure that only the first encounter of the section is added
            # The near query gives closest points first, so the first one is the one we want
            if section_id not in end_by_section:
                end_by_section[section_id] = elt
    
    res_start = edb.get_analysis_timeseries_db().find(query_start)
    start_by_section = {}
    for elt in res_start:
        elt_data = elt.get('data')
        if elt_data:
            section_id = elt_data.get('section')
            if section_id not in start_by_section:
                start_by_section[section_id] = elt
    
    vals = []
    user_id_seen_dict = {}
    number_user_seen = 0
    # Now we can read every section crossing start point
    for section_id in start_by_section:
        matching_start = start_by_section[section_id]
        matching_start_data = matching_start.get('data')
        if matching_start_data is None:
            # Something is wrong with the fetched data, shouldn't happen
            continue
        if 'idx' not in matching_start_data:
            # Sometimes, idx is missing in data, not sure why
            continue
        matching_end = end_by_section.get(section_id)
        if matching_end is None:
            # This section_id didn't cross the end point
            continue
        matching_end_data = matching_end.get('data', {})
        # idx allows us to check that the start section is crossed first, we do not care about trips going the other way
        if 'idx' in matching_end_data and matching_start_data.get('idx') < matching_end_data.get('idx'):
            user_id = str(start_by_section[section_id].get('user_id'))
            if user_id_seen_dict.get(user_id) is None:
                number_user_seen += 1
                user_id_seen_dict[user_id] = True
            vals.append({
                'start': start_by_section[section_id], 
                'end': end_by_section[section_id], 
                'duration': matching_end_data.get('ts') - matching_start_data.get('ts'),
                'section': section_id, 
                'mode': matching_start_data.get('mode'), # Note: this is the mode given by the phone, not the computed one, we'll read it later from inferred_sections
                'start_fmt_time': matching_start_data.get('fmt_time'),
                'end_fmt_time': matching_end_data.get('fmt_time')
            })
    if perm_utils.permissions.get("segment_trip_time_min_users", 0) <= number_user_seen:
        return pd.DataFrame.from_dict(vals)
    return pd.DataFrame.from_dict([])

# The following query can be called multiple times, let's open db only once
analysis_timeseries_db = edb.get_analysis_timeseries_db()

# When sections isn't set, this fetches all inferred_section
# Otherwise, it filters on given section ids using '$in'
# Note: for performance reasons, it is not recommended to use '$in' a list bigger than ~100 values
# In our use case, this could happen on popular trips, but the delay is deemed acceptable
def query_inferred_sections_modes(sections=[]):
    query = {'metadata.key': 'analysis/inferred_section'}
    if len(sections) > 0:
        query['data.cleaned_section'] = {'$in': sections} 
    res = analysis_timeseries_db.find(query, {'data.cleaned_section': 1, 'data.sensed_mode': 1})
    mode_by_section_id = {}
    for elt in res:
        elt_data = elt.get('data')
        if elt_data:
            mode_by_section_id[str(elt_data.get('cleaned_section'))] = elt_data.get('sensed_mode') or 0
    return mode_by_section_id
