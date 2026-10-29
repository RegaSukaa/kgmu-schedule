# Расписание КГМУ Казань — статичная копия

Копия сервиса расписания Казанского ГМУ (`calendar.kazangmu.org`), сделанная на
случай отключения оригинала (разработчик предупредил, что система перестанет
работать 1 ноября 2026). Данные берутся из официальных источников КГМУ:

* `https://kazangmu.ru/obuchenie/studentam/raspisanie-zanyatij` — таблица со ссылками
  на все направления и курсы;
* `https://calendar.kazangmu.org/api/schedule/front` — JSON расписаний для части
  направлений;
* `https://cloud.kazangmu.ru` (Nextcloud-шары КГМУ) — Excel/PDF с расписаниями для
  остальных направлений.

## Что уже есть

* 11 направлений, 44 курса, ~4 500 занятий (осенний семестр 2026/2027);
* выбор направления → курса → группы;
* два вида: «Сетка» (как официальный документ: дни, пары, колонки групп, цвета дней)
  и «Дни» (карточки, удобно на телефоне);
* поиск по дисциплине, преподавателю, аудитории;
* тёмная/светлая тема, шаринг ссылкой на конкретную группу.

## Структура

```
tools/scrape.py        # скачивание каталога + JSON + Excel с сайтов КГМУ
tools/parse_xlsx.py    # разбор недельных Excel-сеток в JSON
tools/build_data.py    # сборка site/data/schedule.json
tools/selftest.js      # проверка вёрстки в headless-браузере
data/manifest.json     # что и откуда скачано
data/raw/, data/parsed/# исходники и промежуточные JSON (в git не входят)
site/                  # сам статичный сайт (публикуется на GitHub Pages)
```

## Обновление данных

```bash
py tools/scrape.py      # обновить исходники с сайтов КГМУ
py tools/parse_xlsx.py  # пересобрать JSON из Excel
py tools/build_data.py  # собрать site/data/schedule.json
```

## Локальный просмотр

```bash
cd site && py -m http.server 8765
# http://127.0.0.1:8765/
```

## Ссылки

Адрес копии: https://regasukaa.github.io/kgmu-schedule/
Оригинал: https://calendar.kazangmu.org/
