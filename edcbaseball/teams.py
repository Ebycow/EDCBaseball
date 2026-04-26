# NPB 12 teams with keyword lists for title matching
NPB_TEAMS = [
    {"name": "読売ジャイアンツ",           "short": "巨人",       "keywords": ["巨人", "ジャイアンツ", "読売", "GIANTS"]},
    {"name": "阪神タイガース",             "short": "阪神",       "keywords": ["阪神", "タイガース", "TIGERS"]},
    {"name": "横浜DeNAベイスターズ",       "short": "DeNA",       "keywords": ["DeNA", "ベイスターズ", "横浜", "BAYSTARS"]},
    {"name": "広島東洋カープ",             "short": "広島",       "keywords": ["広島", "カープ", "CARP"]},
    {"name": "中日ドラゴンズ",             "short": "中日",       "keywords": ["中日", "ドラゴンズ", "DRAGONS"]},
    {"name": "東京ヤクルトスワローズ",     "short": "ヤクルト",   "keywords": ["ヤクルト", "スワローズ", "SWALLOWS"]},
    {"name": "福岡ソフトバンクホークス",   "short": "ソフトバンク","keywords": ["ソフトバンク", "ホークス", "HAWKS"]},
    {"name": "千葉ロッテマリーンズ",       "short": "ロッテ",     "keywords": ["ロッテ", "マリーンズ", "MARINES"]},
    {"name": "埼玉西武ライオンズ",         "short": "西武",       "keywords": ["西武", "ライオンズ", "埼玉西武", "LIONS"]},
    {"name": "東北楽天ゴールデンイーグルス","short": "楽天",      "keywords": ["楽天", "イーグルス", "EAGLES"]},
    {"name": "オリックス・バファローズ",   "short": "オリックス", "keywords": ["オリックス", "バファローズ", "BUFFALOES"]},
    {"name": "北海道日本ハムファイターズ", "short": "日本ハム",   "keywords": ["日本ハム", "ファイターズ", "FIGHTERS"]},
]

# MLB keywords: J SPORTS uses メジャーリーグ, NHK BS uses full-width ＭＬＢ
MLB_KEYWORDS = ["メジャーリーグ", "ＭＬＢ"]


def extract_matchup(title: str) -> str:
    """Extract NPB team matchup from a broadcast title.

    Returns 'ShortA×ShortB' if two teams found, 'ShortA' if one, '' if none.
    Teams are ordered by their position of first keyword match in the title.
    """
    found: list[tuple[int, str]] = []
    for team in NPB_TEAMS:
        for kw in team["keywords"]:
            idx = title.find(kw)
            if idx >= 0:
                found.append((idx, team["short"]))
                break

    found.sort(key=lambda x: x[0])
    shorts = [s for _, s in found]

    if len(shorts) >= 2:
        return f"{shorts[0]}×{shorts[1]}"
    elif len(shorts) == 1:
        return shorts[0]
    return ""
