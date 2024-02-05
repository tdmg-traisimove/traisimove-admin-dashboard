def iso_to_date_only(*iso_strs: str):
    """
    For each ISO date string in the input, returns only the date part in the format 'YYYY-MM-DD'
    e.g. '2021-01-01T00:00:00.000Z' -> '2021-01-01'
    """
    return [iso_str[:10] if iso_str else None for iso_str in iso_strs]
    