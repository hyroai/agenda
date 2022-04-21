import datetime

from config_to_bot import extract


def test_extract_future_date():
    assert extract.future_date(
        datetime.datetime(2022, 4, 11), "Sunday at 5 pm"
    ) == datetime.date(2022, 4, 17)


def test_extract_time():
    assert extract.time(
        datetime.datetime(2022, 4, 11, 15), "Sunday at 5 pm"
    ) == datetime.time(17, 0)


def test_extract_datetime_options():
    assert (
        extract.datetime_choice(
            [datetime.datetime(2022, 4, 17, 17), datetime.datetime(2022, 4, 18, 18)],
            datetime.datetime(2022, 4, 11),
        )("sunday")
        == datetime.datetime(2022, 4, 17, 17).isoformat()
    )

    assert (
        extract.datetime_choice(
            [datetime.datetime(2022, 4, 17, 17), datetime.datetime(2022, 4, 17, 18)],
            datetime.datetime(2022, 4, 11),
        )("5 pm")
        == datetime.datetime(2022, 4, 17, 17).isoformat()
    )
