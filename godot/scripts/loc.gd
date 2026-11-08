extends Node
# Tajik / Russian / English. Add a Cyrillic-capable font (e.g. Noto Sans, OFL) to assets/ for ғ ӣ қ ӯ ҳ ҷ.
var lang := "tg"
const T := {
	"tg": {"home": "Асосӣ", "play": "Бозӣ", "friends": "Дӯстон", "shop": "Мағоза", "profile": "Профил",
		"settings": "Танзимот", "coins": "Тангаҳо", "win": "Ғалаба", "lose": "Бохт", "take": "Гирифтан",
		"pass": "Бито", "m1v1": "1 бар 1", "mffa": "4 нафар", "mteam": "2 бар 2", "variant": "Навъ",
		"podkidnoy": "Подкидной", "perevodnoy": "Переводной", "trump": "Козир", "lang": "Забон"},
	"ru": {"home": "Главная", "play": "Игра", "friends": "Друзья", "shop": "Магазин", "profile": "Профиль",
		"settings": "Настройки", "coins": "Монеты", "win": "Победа", "lose": "Поражение", "take": "Взять",
		"pass": "Бито", "m1v1": "1 на 1", "mffa": "4 игрока", "mteam": "2 на 2", "variant": "Вид",
		"podkidnoy": "Подкидной", "perevodnoy": "Переводной", "trump": "Козырь", "lang": "Язык"},
	"en": {"home": "Home", "play": "Play", "friends": "Friends", "shop": "Shop", "profile": "Profile",
		"settings": "Settings", "coins": "Coins", "win": "Victory", "lose": "Defeat", "take": "Take",
		"pass": "Done", "m1v1": "1 vs 1", "mffa": "4 players", "mteam": "2 vs 2", "variant": "Variant",
		"podkidnoy": "Podkidnoy", "perevodnoy": "Perevodnoy", "trump": "Trump", "lang": "Language"},
}
func t(key: String) -> String:
	return T[lang].get(key, key)
