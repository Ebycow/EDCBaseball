# Baseball-relevant channels in EDCB
# onid/tsid/sid match EnumService output

BASEBALL_CHANNELS = [
    # J SPORTS 1-4 (MLB live, NPB games)
    {"name": "J SPORTS 1",   "onid": 4, "tsid": 18225, "sid": 242},
    {"name": "J SPORTS 2",   "onid": 4, "tsid": 18226, "sid": 243},
    {"name": "J SPORTS 3",   "onid": 4, "tsid": 18227, "sid": 244},
    {"name": "J SPORTS 4",   "onid": 4, "tsid": 18224, "sid": 245},
    # NHK BS (MLB with full-width ＭＬＢ in title; NPB; event relay to sub-ch)
    {"name": "NHK BS",       "onid": 4, "tsid": 16625, "sid": 101, "nhk": True},
    {"name": "NHK BS 2",     "onid": 4, "tsid": 16625, "sid": 102, "nhk": True},
    # BS-TBS (NPB)
    {"name": "BS-TBS",       "onid": 4, "tsid": 16401, "sid": 161},
    # BS Asahi (occasional NPB)
    {"name": "BS Asahi",     "onid": 4, "tsid": 16400, "sid": 151},
    # GAORA (mainly Hanshin + others)
    {"name": "GAORA",        "onid": 7, "tsid": 28864, "sid": 254},
    # Sky-A (mainly Hanshin + others)
    {"name": "Sky-A",        "onid": 7, "tsid": 28736, "sid": 250},
    # WOWOW (occasional NPB/MLB)
    {"name": "WOWOW Prime",  "onid": 4, "tsid": 16432, "sid": 191},
    {"name": "WOWOW Live",   "onid": 4, "tsid": 17488, "sid": 192},
    # TBS CS channels (NPB)
    {"name": "TBS Channel 1","onid": 6, "tsid": 24608, "sid": 296},
    {"name": "TBS Channel 2","onid": 7, "tsid": 29024, "sid": 297},
    # Fuji TV CS (NPB)
    {"name": "Fuji TV ONE",  "onid": 7, "tsid": 28992, "sid": 307},
    {"name": "Fuji TV TWO",  "onid": 7, "tsid": 28992, "sid": 308},
    # NTV channels (NPB)
    {"name": "NTV+",              "onid": 7, "tsid": 29056, "sid": 300},
    {"name": "日テレジータス",     "onid": 7, "tsid": 29056, "sid": 257},  # 巨人専用ch
    {"name": "日テレNEWS24",      "onid": 6, "tsid": 24704, "sid": 349},  # ロッテ主催公式戦
    {"name": "BS Nittele",        "onid": 4, "tsid": 16592, "sid": 141},
    # Sports Live+ (various NPB)
    {"name": "Sports Live+",      "onid": 6, "tsid": 24736, "sid": 800},
    # BS Fuji (occasional NPB)
    {"name": "BS Fuji",           "onid": 4, "tsid": 16593, "sid": 181},
    # BS12 トゥエルビ (occasional NPB)
    {"name": "BS12",              "onid": 4, "tsid": 16530, "sid": 222},
]
