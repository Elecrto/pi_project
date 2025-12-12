# Шрифты для проекта

Для корректной работы системы необходимо разместить в этой папке следующие файлы шрифта Montserrat в формате WOFF2:

## Необходимые файлы:

- `Montserrat-Regular.woff2` (font-weight: 400)
- `Montserrat-Medium.woff2` (font-weight: 500)
- `Montserrat-SemiBold.woff2` (font-weight: 600)
- `Montserrat-Bold.woff2` (font-weight: 700)

## Где скачать:

### Вариант 1: Google Fonts
1. Перейдите на https://fonts.google.com/specimen/Montserrat
2. Нажмите "Download family"
3. Конвертируйте TTF файлы в WOFF2 используя онлайн-конвертер (например, https://cloudconvert.com/ttf-to-woff2)

### Вариант 2: Прямая загрузка через терминал
```bash
cd static/fonts

# Regular
curl -o Montserrat-Regular.woff2 "https://fonts.gstatic.com/s/montserrat/v26/JTUSjIg1_i6t8kCHKm459WlhyyTh89Y.woff2"

# Medium
curl -o Montserrat-Medium.woff2 "https://fonts.gstatic.com/s/montserrat/v26/JTUSjIg1_i6t8kCHKm459WRhyyTh89Y.woff2"

# SemiBold
curl -o Montserrat-SemiBold.woff2 "https://fonts.gstatic.com/s/montserrat/v26/JTUSjIg1_i6t8kCHKm459W1hyyTh89Y.woff2"

# Bold
curl -o Montserrat-Bold.woff2 "https://fonts.gstatic.com/s/montserrat/v26/JTUSjIg1_i6t8kCHKm459Wlhyw3h89Y.woff2"
```

## Fallback
Если файлы шрифтов отсутствуют, система автоматически будет использовать системный шрифт Montserrat (если установлен) или стандартные системные шрифты.
