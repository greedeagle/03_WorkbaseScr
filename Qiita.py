import requests
import hashlib
from bs4 import BeautifulSoup
import sqlite3
import webbrowser
from dotenv import load_dotenv
import os

class PageData:
    def __init__(self, url, title, article,hash):
        self.url = url
        self.title = title
        self.article = article
        self.hash = hash

    def __str__(self):
        return f"{self.title}"

def generate_md5(text):
    m = hashlib.md5()
    m.update(text.encode('utf-8'))
    return m.hexdigest()

def UpdateDB(pageDatas):
    try:
        updated_pages = []
        updated = False
        conn = None

        conn = sqlite3.connect('my_database.db')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qiita_db (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                article TEXT,
                hash TEXT
            )
        ''')

        for insertData in pageDatas:
            cursor.execute("SELECT hash FROM qiita_db WHERE url=?", (insertData.url,))
            existing_data = cursor.fetchone()

            if existing_data is None:
                cursor.execute('''
                    INSERT INTO qiita_db (url, title, article, hash) VALUES (?, ?,?, ?)
                ''', (insertData.url, insertData.title,insertData.article insertData.hash))
            elif insertData.hash != existing_data[0]:
                cursor.execute("UPDATE qiita_db SET title=?, article=?, hash=? WHERE url=?", (insertData.title, insertData.article, insertData.hash, insertData.url))
                updated = True
                updated_pages.append(insertData)

        conn.commit()
        print("データが正常に保存されました。")

    except sqlite3.Error as e:
        print(f"データベースエラーが発生しました: {e}")

    finally:
        if conn:
            conn.close()

    return updated_pages

def login_and_get_elements(url, login_url, username, password):
    session = requests.Session()

    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.content, 'html.parser')

    csrf_token = soup.find('input', {'name': 'csrf_token'})

    login_data = {
        'username': username,
        'password': password,
        'csrf_token': csrf_token,
        # 他に必要なログイン情報を追加
    }
    session.post(login_url, data=login_data)

    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    article = soup.find_all('article')
    ret = []
    for item in article:
        title_tag = item.select_one('h2 a')

        if title_tag:
            title = title_tag.text
            targetURL = title_tag.attrs["href"]
            print(title)
            print(f"targetURL: {targetURL}") # 追加

            try:
                response = session.get(targetURL)
                response.raise_for_status()
                target_soup = BeautifulSoup(response.content, 'html.parser')
                article = target_soup.find_all('article')
                # ページ内のすべてのテキストを取得
                page_text = article[0].get_text(separator='\n', strip=True)
                hash = generate_md5(page_text)
                pageData = PageData(targetURL, title, hash)
                ret.append(pageData)
            except requests.exceptions.RequestException as e:
                print(f"記事ページの取得に失敗しました ({targetURL}): {e}")
        else:
            print("タイトルが見つかりませんでした。")
    else:
        print("article要素が見つかりませんでした。")
    return ret


# .env ファイルをロード
load_dotenv()
username = os.getenv("QIITA_USER")
password = os.getenv("QIITA_PASS")

url = 'https://qiita.com/'
login_url = 'https://qiita.com/login'

pageDatas = login_and_get_elements(url, login_url, username, password)
updatePages = UpdateDB(pageDatas)

if updatePages is not []:
    print("-------更新されたページは以下の通りです---------")
    for item in updatePages:
        print(f"{item.title} {item.url}")
        webbrowser.open(item.url)

    