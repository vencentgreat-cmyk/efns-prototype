"""Optional coordinate validation and Account form state regression coverage."""

from pathlib import Path

import pytest
import pandas as pd

from data.validation import parse_optional_coordinate
from tests.auth_support import authenticated_app
from tests.test_connection import FakeSession, FakeStatement, FakeRow
from tests.test_snowflake_repository import FakeConnection, repository_with_connection, repository_without_connection
from data.connection import SnowparkExecutor
from data.repositories.base import RepositoryError
from data.repositories.mock import MockRepository


@pytest.mark.parametrize("field, value, expected", [
    ("LATITUDE", None, None), ("LONGITUDE", "  ", None),
    ("LATITUDE", "0", 0.0), ("LONGITUDE", "-63.5752", -63.5752),
    ("LATITUDE", "90", 90.0), ("LONGITUDE", "-180", -180.0),
])
def test_optional_coordinate(field, value, expected):
    assert parse_optional_coordinate(value, field) == expected


@pytest.mark.parametrize("field, value, message", [
    ("LATITUDE", "abc", "must be a number"),
    ("LONGITUDE", "None", "must be a number"),
    ("LATITUDE", "91", "between -90 and 90"),
    ("LONGITUDE", "-181", "between -180 and 180"),
    ("LATITUDE", "nan", "finite number"),
    ("LONGITUDE", "inf", "finite number"),
])
def test_invalid_coordinate(field, value, message):
    with pytest.raises(ValueError, match=message):
        parse_optional_coordinate(value, field)


@pytest.mark.parametrize("runtime", ["connector", "snowpark"])
@pytest.mark.parametrize("coordinates", [(None, None), (0.0, -63.5752)])
def test_account_coordinates_reach_persistence_with_correct_types(runtime, coordinates):
    if runtime == "connector":
        connection = FakeConnection()
        repo = repository_with_connection(connection)
        calls = connection.cursor_instance.calls
    else:
        def respond(sql, params):
            if sql.startswith('SHOW PARAMETERS'):
                return FakeStatement([FakeRow(key='LOCK_TIMEOUT',value='43200',level='ACCOUNT')],['key','value','level'])
            if "RAW.INTAKE_LOCK" in sql:
                return FakeStatement([FakeRow(**{"number of rows updated": 1})], ["number of rows updated"])
            if sql.startswith("INSERT"):
                assert None not in params
                return FakeStatement(
                    [FakeRow(**{"number of rows inserted": 1})],
                    ["number of rows inserted"],
                )
            return FakeStatement([], [])

        session = FakeSession(respond)
        repo = repository_without_connection()
        repo.executor = SnowparkExecutor(session)
        calls = session.calls
    repo.upsert_account({
        "ORGANIZATION_NAME": "Synthetic Account",
        "LATITUDE": coordinates[0], "LONGITUDE": coordinates[1],
    })
    sql, params = next((sql, params) for sql, params in calls if sql.startswith("INSERT"))
    assert "None" not in params
    if coordinates[0] is None:
        if runtime == "connector":
            assert tuple(params[-2:]) == (None, None)
        else:
            assert sql.count("NULL") == 2
            assert len(params) == 2
    else:
        assert tuple(params[-2:]) == coordinates


def new_account_app(tmp_path, monkeypatch):
    app = authenticated_app(Path(__file__).parents[1] / "app" / "Home.py", tmp_path, monkeypatch)
    app.switch_page("pages/3_Accounts_Facilities_Flocks.py").run()
    next(button for button in app.button if button.label == "New").click().run()
    return app


def save(app):
    next(button for button in app.button if button.label == "Save").click().run()


@pytest.mark.parametrize("latitude, longitude", [("", ""), ("0", "-63.5752")])
def test_account_form_saves_blank_and_valid_coordinates(tmp_path, monkeypatch, latitude, longitude):
    app = new_account_app(tmp_path, monkeypatch)
    app.text_input(key="account_form_name").set_value("Synthetic Coordinate Account")
    app.text_input(key="account_form_latitude").set_value(latitude)
    app.text_input(key="account_form_longitude").set_value(longitude)
    save(app)
    assert not app.exception
    assert not app.error
    records = app.session_state.repo.get_accounts()
    row = records[records.ORGANIZATION_NAME == "Synthetic Coordinate Account"].iloc[0]
    assert pd.isna(row.LATITUDE) if latitude == "" else row.LATITUDE == float(latitude)
    assert pd.isna(row.LONGITUDE) if longitude == "" else row.LONGITUDE == float(longitude)


def test_account_form_invalid_coordinates_preserve_all_inputs(tmp_path, monkeypatch):
    app = new_account_app(tmp_path, monkeypatch)
    app.text_input(key="account_form_name").set_value("Synthetic Invalid Account")
    app.text_input(key="account_form_email").set_value("synthetic@example.invalid")
    app.text_input(key="account_form_latitude").set_value("not a number")
    app.text_input(key="account_form_longitude").set_value("181")
    save(app)
    assert not app.exception
    assert any("Latitude must be a number" in error.value for error in app.error)
    assert any("Longitude must be between" in error.value for error in app.error)
    assert app.text_input(key="account_form_name").value == "Synthetic Invalid Account"
    assert app.text_input(key="account_form_email").value == "synthetic@example.invalid"
    assert app.text_input(key="account_form_latitude").value == "not a number"
    assert app.text_input(key="account_form_longitude").value == "181"
    assert app.session_state.repo.get_accounts().query("ORGANIZATION_NAME == 'Synthetic Invalid Account'").empty


def test_account_write_error_preserves_form_inputs(tmp_path, monkeypatch):
    app = new_account_app(tmp_path, monkeypatch)
    app.text_input(key="account_form_name").set_value("Synthetic Unsaved Account")
    app.text_input(key="account_form_latitude").set_value("45.25")
    app.text_input(key="account_form_longitude").set_value("-63.5")

    def fail(self, record):
        raise RepositoryError("Synthetic write failure")

    monkeypatch.setattr(MockRepository, "upsert_account", fail)
    save(app)
    assert not app.exception
    assert any("Synthetic write failure" in error.value for error in app.error)
    assert app.text_input(key="account_form_name").value == "Synthetic Unsaved Account"
    assert app.text_input(key="account_form_latitude").value == "45.25"
    assert app.text_input(key="account_form_longitude").value == "-63.5"
