import pandas as pd
import requests
from urllib.parse import urlparse, parse_qs

token = 'ваш_токен'
version = 5.131
id_rk = ваш_айди_кабинета

r = requests.get('https://api.vk.com/method/ads.getAds', params={
    'access_token': token,
    'v': version,
    'account_id': id_rk
})

data = r.json()['response']

ad_campaign_dict = {}
for i in range(len(data)):
    ad_campaign_dict[data[i]['id']] = data[i]['campaign_id']

unique_ad_ids = set(ad_id for ad_id in ad_campaign_dict.keys())
ad_ids_string = ', '.join(str(ad_id) for ad_id in unique_ad_ids)

chunk_size = 1000
ad_ids_list = [int(ad_id) for ad_id in unique_ad_ids]

ad_ids_chunks = [ad_ids_list[i:i + chunk_size] for i in range(0, len(ad_ids_list), chunk_size)]

result_df_list = []

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

df = pd.concat(result_df_list, ignore_index=True)

parsed_stats_list = []

for _, row in df.iterrows():
    stats = row['stats']
    if stats:
        parsed_stats_list.extend(stats)

parsed_stats_df = pd.DataFrame(parsed_stats_list)

df = pd.concat([df.drop(columns=['stats']), parsed_stats_df], axis=1)

df['campaign_id'] = df['id'].map(ad_campaign_dict)

df = df.dropna(subset=['day'])

df = df[['campaign_id', 'id', 'spent', 'impressions', 'clicks', 'reach', 'ctr', 'uniq_views_count', 'effective_cost_per_click', 'effective_cost_per_mille', 'join_rate', 'effective_cpf', 'link_external_clicks', 'conversions_external', 'conversion_count', 'conversion_cr', 'message_sends_by_any_user', 'effective_cost_per_message']]

r2 = requests.get('https://api.vk.com/method/ads.getAdsLayout', params={
    'access_token': token,
    'v': version,
    'account_id': id_rk,
    'include_deleted': 0
})

data_ads_layout = r2.json()['response']
data_ads_layout = pd.DataFrame(data_ads_layout)
data_ads_layout = data_ads_layout[['id', 'campaign_id', 'link_url']]

def extract_utm_params(link_url):
    parsed_url = urlparse(link_url)
    utm_params = parse_qs(parsed_url.query)
    return utm_params

data_ads_layout['utm_params'] = data_ads_layout['link_url'].apply(extract_utm_params)

data_ads_layout['utm_source'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_source', [None])[0])
data_ads_layout['utm_medium'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_medium', [None])[0])
data_ads_layout['utm_campaign'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_campaign', [None])[0])
data_ads_layout['utm_id'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_id', [None])[0])
data_ads_layout['utm_content'] = data_ads_layout['utm_params'].apply(lambda x: x.get('utm_content', [None])[0])

data_ads_layout.drop('utm_params', axis=1, inplace=True)

df = df.merge(data_ads_layout, left_on=['campaign_id', 'id'], right_on=['campaign_id', 'id'], how='left')

r3 = requests.get('https://api.vk.com/method/ads.getCampaigns', params={
    'access_token': token,
    'v': version,
    'account_id': id_rk,
    'include_deleted': 0
})
data_campaigns = r3.json()['response']

campaign_df = pd.DataFrame(data_campaigns)

campaign_df = campaign_df[['id', 'name']]

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

df['campaign_id'] = df['campaign_id'].astype('object')

df['spent'] = df['spent'].astype('float64')
df['ctr'] = df['ctr'].astype('float64')
df['effective_cost_per_click'] = df['effective_cost_per_click'].astype('float64')
df['effective_cost_per_mille'] = df['effective_cost_per_mille'].astype('float64')
df['effective_cpf'] = df['effective_cpf'].astype('float64')
df['conversion_cr'] = df['conversion_cr'].astype('float64')
df['effective_cost_per_message'] = df['effective_cost_per_message'].astype('float64')

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