from urllib.parse import urlsplit

from app.navigation import _module_path, _snowflake_fragment_route, _url_query


def test_snowflake_module_links_preserve_streamlit_app_prefix():
    assert _module_path(
        "/streamlit-apps/EFNS_DEV.APP.EFNS_INTERNAL_APP/!/Flocks",
        "Quota_Registrations",
    ) == "/streamlit-apps/EFNS_DEV.APP.EFNS_INTERNAL_APP/!/Quota_Registrations"
    assert _url_query("/app/!/Flocks", {"view": "detail", "id": "q1"}) == (
        "streamlit-view=detail&streamlit-id=q1"
    )


def test_local_module_links_keep_normal_page_path():
    assert _module_path("/Flocks", "Quota Registrations") == "/Quota%20Registrations"
    parsed = urlsplit(
        "https://app.snowflake.com/org/account/#/streamlit-apps/EFNS_DEV.APP.APP/!/Flocks"
    )
    assert _snowflake_fragment_route(parsed).endswith("/!/Flocks")
