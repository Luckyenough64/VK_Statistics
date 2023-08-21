# VK_Statistics
Строим сквозную аналитику из того, чего можем - получаем данные по расходам и целевым действиям из старого кабинета VK по API в разрезе UTM-меток с помощью четырёх запросов и трёх библиотек.

## Для кого?

- Для тех, кому нужно связывать расходы по меткам в системах аналитик (Яндекс.Метрика, GA4, Piwik)
- Тем, кто хочет автоматизировать отчётность с помощью ETL (данный скрипт протестирован в KNIME и отлично себя показал, без выбивания ошибок интерпретатора)
- Web/product/data аналитикам - не писать что-то с нуля по неработающим гайдам из интернета, а доработать текущее решение

### Суть

Небольшое отступление:

Перед началов работы вам нужно зарегистрировать приложение а платформе VK для разработчиков, и получить токен авторизации. Можете поиграться с webbrowser, а можете просто скопипастить 
его из результата перехода на https://oauth.vk.com/authorize?client_id=АЙДИ-ВАШЕГО-ПРИЛОЖЕНИЯ&scope=ads&response_type=token, где вам нужно вставить айдишник.

Сам скрипт достаточно подробно описан в комментриях, но его суть можно изложить так - три разным метода API получают разные данные, преобразуются и соединяются воедино.

1) ads.getAds

Получаем статистику по креативам. Нужно для получения списка креативов

2) ads.getAdsLayout

Получаем данные о "внутренностях" наших объявлений, таких как ссылка, заголовки, текст и так далее. Нужно для получения данных о UTM-ках

3) ads.getStatistics

Получаем статистику по кампаниям - расходы и всё остальное.

4) ads.getStatistics

Получаем названия кампаний в виде текста, а не обезличенного id.

## Результат
```
import pandas as pd
import requests
from urllib.parse import urlparse, parse_qs

#  Данные для авторизации - токен, версия API и номер рекламного кабинета
token = 'место_для_токена'
version = 5.131
id_rk = место_для_айди_кабинета

# Делаем первый запрос для получения данных по рекламным объявлениям с помощью метода getAds
r = requests.get('https://api.vk.com/method/ads.getAds', params={
    'access_token': token,
    'v': version,
    'account_id': id_rk
})

data = r.json()['response']

# Создаим словарь с рекламными кампаниями и объявлениями
ad_campaign_dict = {}
for i in range(len(data)):
    ad_campaign_dict[data[i]['id']] = data[i]['campaign_id']

# Получим строку с айдишниками объявлений - нужно будет дальше
unique_ad_ids = set(ad_id for ad_id in ad_campaign_dict.keys())
ad_ids_string = ', '.join(str(ad_id) for ad_id in unique_ad_ids)

chunk_size = 1000  # Максимальное количество объявлений в одном запросе - VK не принимает больше 2000
ad_ids_list = [int(ad_id) for ad_id in unique_ad_ids]  # Преобразуем id объявлений в список целых чисел

# Разбиваем список на мелкие подсписки
ad_ids_chunks = [ad_ids_list[i:i + chunk_size] for i in range(0, len(ad_ids_list), chunk_size)]

# Создаем список для хранения результатов
result_df_list = []

# Для каждой подсписки id объявлений делаем запрос и добавляем результат в список
for ad_ids_chunk in ad_ids_chunks:
    ad_ids_string_chunk = ', '.join(str(ad_id) for ad_id in ad_ids_chunk)
    r33 = requests.get('https://api.vk.com/method/ads.getStatistics', params={
        'access_token': token,
        'v': version,
        'account_id': id_rk,
        'ids_type': 'ad',
        'ids': ad_ids_string_chunk,
        'period': 'day',
        'date_from': '2023-07-01',
        'date_to': '2023-07-31'
    })
    r33 = r33.json()['response']
    result_df_list.append(pd.DataFrame(r33))

# Объединяем результаты запросов в один датафрейм
df = pd.concat(result_df_list, ignore_index=True)

# Создаем пустой список для хранения разобранной статистики
parsed_stats_list = []

# Разбираем статистику для каждой записи в 'stats' и добавляем ее в список
for _, row in df.iterrows():
    stats = row['stats']
    if stats:
        parsed_stats_list.extend(stats)

# Создаем новый датафрейм из списка разобранной статистики
parsed_stats_df = pd.DataFrame(parsed_stats_list)

# Объединяем новый датафрейм с исходным для сохранения информации об объявлениях
df = pd.concat([df.drop(columns=['stats']), parsed_stats_df], axis=1)

# Добавляем новую колонку 'campaign_id' к final_df
df['campaign_id'] = df['id'].map(ad_campaign_dict)

df = df.dropna(subset=['day'])

df = df[['campaign_id', 'id', 'spent', 'impressions', 'clicks', 'reach', 'ctr', 'uniq_views_count', 'effective_cost_per_click', 'effective_cost_per_mille', 'join_rate', 'effective_cpf', 'link_external_clicks', 'conversions_external', 'conversion_count', 'conversion_cr', 'message_sends_by_any_user', 'effective_cost_per_message']]

# Делаем второй запрос - для получения UTM-меток из креативов

r2 = requests.get('https://api.vk.com/method/ads.getAdsLayout', params={
    'access_token': token,
    'v': version,
    'account_id': id_rk,
    'include_deleted': 0
})

data_ads_layout = r2.json()['response']
data_ads_layout = pd.DataFrame(data_ads_layout)
data_ads_layout = data_ads_layout[['id', 'campaign_id', 'link_url']]

# Небольшая функция, которая распарсит ссылки в объявлениях
def extract_utm_params(link_url):
    parsed_url = urlparse(link_url)
    utm_params = parse_qs(parsed_url.query)
    return utm_params

# Применить функцию к столбцу 'link_url'
data_ads_layout['utm_params'] = data_ads_layout['link_url'].apply(extract_utm_params)

# Извлечь значения UTM параметров в отдельные столбцы
data_ads_layout['utm_source'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_source', [None])[0])
data_ads_layout['utm_medium'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_medium', [None])[0])
data_ads_layout['utm_campaign'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_campaign', [None])[0])
data_ads_layout['utm_id'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_id', [None])[0])
data_ads_layout['utm_content'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_content', [None])[0])

# Удалить столбец 'utm_params', если он больше не нужен
data_ads_layout.drop('utm_params', axis=1, inplace=True)

df = df.merge(data_ads_layout, left_on=['campaign_id', 'id'], right_on=['campaign_id', 'id'], how='left')

# Делаем третий, вспомогательный запрос - с помощью метода getCampaigns получим человеческие названия кампаний

r3 = requests.get('https://api.vk.com/method/ads.getCampaigns', params={
    'access_token': token,
    'v': version,
    'account_id': id_rk,
    'include_deleted': 0
})
data_campaigns = r3.json()['response']

# Создать датафрейм из списка data2
campaign_df = pd.DataFrame(data_campaigns)

# Выбрать только столбцы 'id' и 'name'
campaign_df = campaign_df[['id', 'name']]

# Соединяем их с нашим основным датафреймом и убираем то, что нам не нужно
df = df.merge(campaign_df, how='left', left_on='campaign_id', right_on='id')

df = df[['name', 
         'campaign_id', 
         'utm_source', 
         'utm_medium', 
         'utm_campaign', 
         'utm_content', 
         'spent', 
         'impressions', 
         'clicks', 
         'reach', 
         'ctr', 
         'uniq_views_count', 
         'effective_cost_per_click', 
         'effective_cost_per_mille', 
         'join_rate', 
         'effective_cpf', 
         'link_external_clicks', 
         'conversions_external', 
         'conversion_count', 
         'conversion_cr', 
         'message_sends_by_any_user', 
         'effective_cost_per_message']]

# Конвертация campaign_id в тип данных object
df['campaign_id'] = df['campaign_id'].astype('object')

# Конвертация spent и других в тип данных float64
df['spent'] = df['spent'].astype('float64')
df['ctr'] = df['ctr'].astype('float64')
df['effective_cost_per_click'] = df['effective_cost_per_click'].astype('float64')
df['effective_cost_per_mille'] = df['effective_cost_per_mille'].astype('float64')
df['effective_cpf'] = df['effective_cpf'].astype('float64')
df['conversion_cr'] = df['conversion_cr'].astype('float64')
df['effective_cost_per_message'] = df['effective_cost_per_message'].astype('float64')

# Заканчиваем уборку

df[['spent', 
    'impressions', 
    'clicks', 
    'reach', 
    'ctr', 
    'uniq_views_count', 
    'effective_cost_per_click', 
    'effective_cost_per_mille', 
    'join_rate', 
    'effective_cpf', 
    'link_external_clicks', 
    'conversions_external', 
    'conversion_count', 
    'conversion_cr', 
    'message_sends_by_any_user', 
    'effective_cost_per_message']] = df[['spent', 
                                         'impressions', 
                                         'clicks', 
                                         'reach', 
                                         'ctr', 
                                         'uniq_views_count', 
                                         'effective_cost_per_click', 
                                         'effective_cost_per_mille', 
                                         'join_rate', 
                                         'effective_cpf', 
                                         'link_external_clicks', 
                                         'conversions_external', 
                                         'conversion_count', 
                                         'conversion_cr', 
                                         'message_sends_by_any_user', 
                                         'effective_cost_per_message']].fillna(0)

df.head()
```

### Что можно улучшить/поправить?

- Некоторые поля я убирал под свои нужды, поэтому you free to pick что ва захочется
- Можно вместо айдишников объявлений выводить названия - данное поле есть в методе ads.getAds, и при желании можете его использовать
- Местами мне кажется некоторые вещи можно оптимизировать и не делать некоторую работу дважды, как например отбор колонок в датафрейме

### Что по скорости

Скрипт от ребят из интернета, который работает черезщ циклы у меня занимал порядка 5-6 минут при выборке в месяц. Моё решение пересобирает 22к объявлений и формирует результирующий датафрейм (819,22) за ~13.6 секунд. 

P.S
Часть этого скрипта, про UTM-ки мне приснилась во сне, пруфов не будет но это правда)
