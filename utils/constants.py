REQUIRED_NAMED_COLS = [
    {'label': 'user_id', 'path': 'user_id'},
    {'label': 'trip_start_time_str', 'path': 'data.start_fmt_time'},
    {'label': 'trip_end_time_str', 'path': 'data.end_fmt_time'},
    {'label': 'start_coordinates', 'path': 'data.start_loc.coordinates'},
    {'label': 'end_coordinates', 'path': 'data.end_loc.coordinates'},
]

VALID_TRIP_COLS = [
    "data.source",
    "data.start_ts",
    "data.start_local_dt",
    "data.start_fmt_time",
    "data.start_place",
    "data.end_ts",
    "data.end_local_dt",
    "data.end_fmt_time",
    "data.end_place",
    "data.duration",
    "data.distance",
    "data.start_loc.coordinates",
    "data.end_loc.coordinates",
    "metadata.key",
    "metadata.platform",
    "metadata.write_ts",
    "metadata.time_zone",
    "metadata.write_local_dt",
    "metadata.write_fmt_time",
    "user_id"
]

BINARY_TRIP_COLS = [
    'user_id',
    'data.start_place',
    'data.end_place',
]

valid_uuids_columns = [
    'user_token',
    'user_id',
    'update_ts',
]
