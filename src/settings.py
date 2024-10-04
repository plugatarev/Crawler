DATABASE_FILENAME = "lab1.db"
STATISTICS_FILENAME = "statistics.csv"
IGNORED_WORDS = set(
    [
        "с помощью",
        "из-под",
        "поверх",
        "ниже",
        "вглубь",
        "о",
        "исходя из",
        "выключая",
        "по направлению к",
        "опричь",
        "в/на",
        "поперёд",
        "прежде",
        "при помощи",
        "вплоть до",
        "по поводу",
        "смотря по",
        "близко от",
        "во имя",
        "по сравнению с",
        "обо",
        "вслед за",
        "несмотря",
        "над",
        "в зависимости от",
        "позади",
        "по отношению к",
        "по",
        "замест",
        "окромя",
        "сродни",
        "кончая",
        "супротив",
        "среди",
        "в силу",
        "позадь",
        "поблизости от",
        "после",
        "посредством",
        "в продолжение",
        "вкруг",
        "наверху",
        "выше",
        "через",
        "вразрез",
        "впереди",
        "сверху",
        "окрест",
        "скрозь",
        "от",
        "на глазах у",
        "вопреки",
        "согласно",
        "по-за",
        "в честь",
        "насчёт",
        "сквозь",
        "подле",
        "вроде",
        "под видом",
        "по линии",
        "посередине",
        "спустя",
        "вблизи",
        "в интересах",
        "лицом к лицу с",
        "исключая",
        "наперерез",
        "навстречу",
        "включая",
        "рядом с",
        "насупротив",
        "по причине",
        "предо",
        "взамен",
        "внутри",
        "до",
        "вовнутрь",
        "заместо",
        "подобно",
        "опосля",
        "внутрь",
        "с ведома",
        "окроме",
        "в целях",
        "посереди",
        "внизу",
        "применительно к",
        "невзирая на",
        "обок",
        "вдоль по",
        "промежду",
        "наподобье",
        "путём",
        "независимо от",
        "за-ради",
        "середь",
        "в",
        "наподобие",
        "без ведома",
        "в роли",
        "напротив",
        "во славу",
        "противно",
        "от лица",
        "начиная с",
        "близь",
        "в качестве",
        "посверху",
        "в связи с",
        "не без",
        "безъ",
        "повдоль",
        "кругом",
        "по-под",
        "позднее",
        "вслед",
        "из-подо",
        "по мере",
        "за исключением",
        "во",
        "кроме",
        "при",
        "сверх",
        "обочь",
        "на",
        "надо",
        "ото",
        "а-ля",
        "сбоку",
        "об",
        "посреди",
        "про",
        "назади",
        "вместо",
        "наперехват",
        "посерёдке",
        "на виду у",
        "преж",
        "следом за",
        "средь",
        "вокруг",
        "помимо",
        "к",
        "в случае",
        "у",
        "снизу",
        "изнутри",
        "наряду с",
        "вдогон",
        "на предмет",
        "наперекор",
        "ко",
        "изо",
        "сопротив",
        "вне",
        "встречу",
        "из-за",
        "несмотря на",
        "в лице",
        "с",
        "округ",
        "пред",
        "вследствие",
        "против",
        "за вычетом",
        "посредине",
        "в течение",
        "по случаю",
        "в результате",
        "возле",
        "в виде",
        "дли",
        "чрез",
        "назло",
        "из",
        "судя по",
        "наместо",
        "порядка",
        "соответственно",
        "относительно",
        "назад",
        "накануне",
        "касаемо",
        "близ",
        "вослед",
        "свыше",
        "касательно",
        "с целью",
        "безо",
        "передо",
        "не считая",
        "за счёт",
        "с точки зрения",
        "черезо",
        "навроде",
        "в пользу",
        "в пандан",
        "под",
        "противу",
        "по-над",
        "за",
        "от имени",
        "под эгидой",
        "около",
        "ввиду",
        "с прицелом на",
        "для-ради",
        "недалеко от",
        "впредь до",
        "в отношении",
        "в преддверии",
        "перед",
        "для",
        "ради",
        "подо",
        "середи",
        "со",
        "поперёк",
        "без",
        "промеж",
        "благодаря",
        "на благо",
        "посередь",
        "в соответствии с",
        "сзади",
        "вдоль",
    ]
)
