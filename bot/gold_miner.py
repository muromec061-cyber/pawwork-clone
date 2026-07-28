#!/usr/bin/env python3
"""GitHub Gold Miner — ищет золото на GitHub"""
import requests, json, os, sys
from datetime import datetime, timedelta

API = 'https://api.github.com'
TOKEN = os.environ.get('GITHUB_TOKEN', '')

def trending(language='', days=7, min_stars=100):
    """Топ проектов по звёздам"""
    since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    q = f'created:>{since}+stars:>{min_stars}'
    if language: q += f'+language:{language}'
    
    headers = {'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'PawWork'}
    if TOKEN: headers['Authorization'] = f'token {TOKEN}'
    
    try:
        r = requests.get(f'{API}/search/repositories?q={q}&sort=stars&order=desc&per_page=10', headers=headers, timeout=10)
        if r.status_code != 200:
            return [{'error': f'GitHub API {r.status_code}'}]
        return [{
            'name': item['full_name'],
            'stars': item['stargazers_count'],
            'forks': item['forks_count'],
            'desc': (item.get('description') or '')[:120],
            'url': item['html_url'],
            'lang': item.get('language') or '-',
            'topics': item.get('topics', [])[:5],
            'today': item.get('stargazers_count', 0),
        } for item in r.json().get('items', [])[:10]]
    except Exception as e:
        return [{'error': str(e)}]

def format_text(items):
    if not items or 'error' in items[0]:
        return f'❌ Ошибка: {items[0].get("error", "нет данных")}' if items else '❌ Ничего не найдено'
    
    lines = ['🔥 <b>GitHub Gold Miner</b>', '— Топ проектов —\n']
    for i, item in enumerate(items, 1):
        lines.append(
            f'{i}. <b>{item["name"]}</b>\n'
            f'   ⭐ {item["stars"]:,} | 🍴 {item["forks"]:,} | 🛠 {item["lang"]}\n'
            f'   {item["desc"]}\n'
            f'   <a href="{item["url"]}">Открыть</a>'
            + (f' | 🏷 {", ".join(item["topics"])}' if item["topics"] else '')
        )
    return '\n'.join(lines)

def format_json(items):
    return json.dumps(items, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    lang = sys.argv[1] if len(sys.argv) > 1 else ''
    fmt = 'text'
    if '--json' in sys.argv: fmt = 'json'
    
    items = trending(lang)
    if fmt == 'json':
        print(format_json(items))
    else:
        print(format_text(items))
