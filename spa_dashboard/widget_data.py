WIDGET_FETCHERS = {
    "placeholder": lambda user, slot: {},
}


def fetch_widget_data(user, slot):
    fetcher = WIDGET_FETCHERS.get(slot["type"])
    if fetcher is None:
        return {}
    return fetcher(user, slot)
