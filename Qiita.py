import requests
import hashlib
from bs4 import BeautifulSoup
import sqlite3
import webbrowser
from dotenv import load_dotenv
import os
import difflib

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


def getArticleInfoFromDB():
# DBのURLを使用してQiitaよりページ情報を取得する
    
    updated_pages = []
    session = requests.Session()
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    conn = sqlite3.connect('my_database.db')
    cursor = conn.cursor()

    # DBが存在しないなら追加
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qiita_db (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            article TEXT,
            hash TEXT
        )
    ''')

    # すべてのURLを取得しておく
    cursor.execute("SELECT url, title FROM qiita_db ", ())
    existing_data = cursor.fetchall()

    ret = []
    for item in existing_data:
        title = item[1]
        targetURL = item[0]
        print(title)
        print(f"targetURL: {targetURL}") # 追加

        try:
            response = session.get(targetURL)
            response.raise_for_status()
            target_soup = BeautifulSoup(response.content, 'html.parser')
            article = target_soup.select('article section')
            # ページ内のすべてのテキストを取得
            page_text = article[0].get_text(separator='\n', strip=True)
            hash = generate_md5(page_text)
            pageData = PageData(targetURL, title,page_text,  hash)
            ret.append(pageData)
        except requests.exceptions.RequestException as e:
            print(f"記事ページの取得に失敗しました ({targetURL}): {e}")
    return ret
def getArticleInfo(url, login_url, username, password):
# Qiitaよりページ情報を取得する
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
    ret =list() 
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
                article = target_soup.select('article section')
                # ページ内のすべてのテキストを取得
                page_text = article[0].get_text(separator='\n', strip=True)
                hash = generate_md5(page_text)
                pageData = PageData(targetURL, title,page_text,  hash)
                ret.append(pageData)
            except requests.exceptions.RequestException as e:
                print(f"記事ページの取得に失敗しました ({targetURL}): {e}")
        else:
            print("タイトルが見つかりませんでした。")
    else:
        print("article要素が見つかりませんでした。")
    return ret



def checkUpdate(currentPageDatas):
    # ページ情報より、DBを更新する
    try:
        updated_pages = []
        updated = False
        conn = None

        conn = sqlite3.connect('my_database.db')
        cursor = conn.cursor()

        # DBが存在しないなら追加
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qiita_db (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                article TEXT,
                hash TEXT
            )
        ''')

        for insertData in currentPageDatas:
            cursor.execute("SELECT hash, article FROM qiita_db WHERE url=?", (insertData.url,))
            existing_data = cursor.fetchone()

            # 存在しないなら追加
            if existing_data is None:
                cursor.execute('''
                    INSERT INTO qiita_db (url, title, article, hash) VALUES (?, ?,?, ?)
                ''', (insertData.url, insertData.title,insertData.article ,insertData.hash))
                # 追加したものは、更新情報に追加する
                updated_pages.append(insertData)
                print(f"new record {insertData.title} - {insertData.url}")

            elif insertData.article != existing_data[1]:
                cursor.execute("UPDATE qiita_db SET title=?, article=?, hash=? WHERE url=?", (insertData.title, insertData.article, insertData.hash, insertData.url))
                updated = True
                updated_pages.append(insertData)
                print(f"record updated {insertData.title}")
                # 差分を作り出す
                diff = difflib.unified_diff(insertData.article, existing_data[1], fromfile="before" , tofile="after")
                # 差分を出力
                for line in diff:
                    print(line, end="")

        conn.commit()
        print("データが正常に保存されました。")

    except sqlite3.Error as e:
        print(f"データベースエラーが発生しました: {e}")

    finally:
        if conn:
            conn.close()

    return updated_pages



# .env ファイルをロード
load_dotenv()
username = os.getenv("QIITA_USER")
password = os.getenv("QIITA_PASS")

url = 'https://qiita.com/'
login_url = 'https://qiita.com/login'

# 表示されている記事の情報を取得
currentPageDatas = getArticleInfo(url, login_url, username, password)
currentPageDatas += getArticleInfoFromDB()
# DBの情報と比較
updatePages = checkUpdate(currentPageDatas)

if len(updatePages)> 0:
    print("-------更新されたページは以下の通りです---------")
    for item in updatePages:
        print(f"{item.title} {item.url}")
        webbrowser.open(item.url)
else:
    print("-----------更新情報はありません------------------")

    