from datetime import date

from app.services.nse_bhavcopy import bhavcopy_url, infer_trade_date_from_filename, parse_current_csv, parse_legacy_csv

LEGACY_CSV = (
    "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,\n"
    "TCS,EQ,3811.1,3811.1,3767.25,3783.2,3781.15,3811.1,1344068,5090055959.15,02-JAN-2024,133902,INE467B01029,\n"
    "182D020524,TB,97.59,97.75,97.59,97.75,97.75,97.59,2300,224473,02-JAN-2024,2,IN002023Y326,\n"
)

CURRENT_CSV = (
    "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,"
    "StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,"
    "SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,"
    "Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n"
    "2025-12-22,2025-12-22,CM,NSE,STK,11536,INE467B01029,TCS,EQ,,,,,TATA CONSULTANCY SERV LT,3310.00,"
    "3328.60,3291.00,3324.90,3324.90,3282.00,,3324.90,,,2632816,8725523457.10,101733,F1,1,,,,,\n"
    "2025-12-22,2025-12-22,CM,NSE,STK,19078,IN0020200104,SGBJUN28,GB,,,,,2.5%GOLDBONDS2028SR-III,"
    "13797.99,13944.00,13769.00,13928.51,13944.00,13683.09,,13929.66,,,357,4938697.95,114,F1,1,,,,,\n"
)


def test_bhavcopy_url_picks_legacy_format_before_cutover():
    url = bhavcopy_url(date(2024, 1, 2))
    assert url == "https://archives.nseindia.com/content/historical/EQUITIES/2024/JAN/cm02JAN2024bhav.csv.zip"


def test_bhavcopy_url_picks_current_format_after_cutover():
    url = bhavcopy_url(date(2025, 12, 22))
    assert url == "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip"


def test_parse_legacy_csv_filters_to_equity_series():
    rows = parse_legacy_csv(LEGACY_CSV)
    assert len(rows) == 1
    row = rows[0]
    assert row.symbol == "TCS"
    assert row.open == 3811.1
    assert row.close == 3783.2
    assert row.volume == 1344068


def test_parse_current_csv_filters_to_equity_series():
    rows = parse_current_csv(CURRENT_CSV)
    assert len(rows) == 1
    row = rows[0]
    assert row.symbol == "TCS"
    assert row.open == 3310.00
    assert row.close == 3324.90
    assert row.volume == 2632816
    assert row.name == "TATA CONSULTANCY SERV LT"


def test_infer_trade_date_from_udiff_filename():
    assert infer_trade_date_from_filename("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip") == date(2025, 12, 22)


def test_infer_trade_date_from_legacy_filename():
    assert infer_trade_date_from_filename("cm02JAN2024bhav.csv.zip") == date(2024, 1, 2)


def test_infer_trade_date_from_unknown_filename_returns_none():
    assert infer_trade_date_from_filename("my_download.zip") is None
