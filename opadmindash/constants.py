default_trip_columns = {
    "user_id",
    "data.start_fmt_time",
    "data.end_fmt_time",
    "data.start_local_dt.timezone",
    "data.start_loc.coordinates",
    "data.end_loc.coordinates",
    "data.start_loc",
    "data.end_loc",
    "data.user_input.trip_user_input.data.jsonDocResponse.data.travel_mode",
}

valid_trip_columns = {
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
    "metadata",
    "metadata.key",
    "metadata.platform",
    "metadata.write_ts",
    "metadata.time_zone",
    "metadata.write_local_dt",
    "metadata.write_fmt_time",
    "user_id"
}

default_uuids_columns = {
    "user_email",
    "uuid",
    "update_ts",
}

valid_uuids_columns = {
    "user_email",
    "uuid",
    "update_ts",
}