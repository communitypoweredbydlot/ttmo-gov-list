from scripts.turism_gov_ro.original_file_properties import parse_filename_date
from datetime import date

def test_parse_filename():
    assert parse_filename_date('TraseeTuristicemontaneOmologate-04.03.2022.xls') \
           == date.fromisoformat('2022-03-04')
    assert parse_filename_date('TraseeTuristicemontaneOmologate-04.03-2022.xlsx') is None
    assert parse_filename_date('04.03.2022TraseeTuristicemontaneOmologate.xlsx') \
           == date.fromisoformat('2022-03-04')
    assert parse_filename_date('TraseeTuristicemontaneOmologate.xlsx') is None