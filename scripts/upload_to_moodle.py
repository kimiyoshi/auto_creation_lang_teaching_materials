#!/usr/bin/env python3
"""
H5PファイルをMoodleにアップロードするスクリプト
Moodle Web Services APIを使用
"""

import os
import json
import argparse
import logging
import requests
import time
import glob
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urljoin

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数のロード
load_dotenv()


def parse_arguments():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(description='H5PファイルをMoodleにアップロードする')
    parser.add_argument('--h5p_dir', type=str, required=True,
                        help='H5Pファイルが保存されているディレクトリ')
    parser.add_argument('--course_id', type=str,
                        help='アップロード先のMoodleコースID（指定がない場合は環境変数から取得）')
    parser.add_argument('--section_id', type=str,
                        help='アップロード先のセクションID（指定がない場合は環境変数から取得）')
    parser.add_argument('--moodle_url', type=str,
                        help='MoodleサーバーのURL（指定がない場合は環境変数から取得）')
    parser.add_argument('--token', type=str,
                        help='Moodle APIトークン（指定がない場合は環境変数から取得）')
    return parser.parse_args()


def find_h5p_files(h5p_dir):
    """指定ディレクトリからH5Pファイルを検索する"""
    h5p_files = []
    for file in os.listdir(h5p_dir):
        if file.endswith('.h5p'):
            h5p_files.append(os.path.join(h5p_dir, file))
    return h5p_files


def get_config():
    """環境変数から設定を取得"""
    config = {
        'moodle_url': os.getenv('MOODLE_URL'),
        'token': os.getenv('MOODLE_TOKEN'),
        'course_id': os.getenv('MOODLE_COURSE_ID'),
        'section_id': os.getenv('MOODLE_SECTION_ID', '0'),  # デフォルトはセクション0
    }

    if not config['moodle_url'] or not config['token'] or not config['course_id']:
        logger.error("必要な環境変数が設定されていません (MOODLE_URL, MOODLE_TOKEN, MOODLE_COURSE_ID)")
        return None

    return config


def upload_file_to_moodle(file_path, moodle_url, token):
    """ファイルをMoodleにアップロードする（ドラフトエリア）"""
    # エンドポイントを構築
    endpoint = urljoin(moodle_url, '/webservice/upload.php')

    # ファイル名を取得
    file_name = os.path.basename(file_path)

    # リクエストデータの準備
    data = {
        'token': token
    }

    # ファイルを開いてmultipart/form-dataでアップロード
    files = {
        'file': (file_name, open(file_path, 'rb'))
    }

    try:
        # POSTリクエストを送信
        response = requests.post(endpoint, data=data, files=files)

        # レスポンスのチェック
        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    logger.info(f"ファイルがアップロードされました: {file_name}")
                    return result[0]  # item idを返す
                else:
                    logger.error(f"ファイルアップロードエラー: 不正なレスポンス - {response.text}")
            except ValueError:
                logger.error(f"ファイルアップロードエラー: JSONデコードに失敗 - {response.text}")
        else:
            logger.error(f"ファイルアップロードエラー: ステータスコード {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"ファイルアップロード中に例外が発生しました: {e}")

    return None


def create_h5p_activity(item_id, file_name, course_id, section_id, moodle_url, token):
    """アップロードされたH5PファイルからH5Pアクティビティを作成する"""
    # エンドポイントを構築
    endpoint = urljoin(moodle_url, '/webservice/rest/server.php')

    # タイトルをファイル名から取得（.h5pを削除）
    title = os.path.splitext(file_name)[0]

    # リクエストデータの準備
    data = {
        'wstoken': token,
        'wsfunction': 'mod_h5pactivity_add_instance',
        'moodlewsrestformat': 'json',
        'h5pactivity': {
            'course': course_id,
            'name': title,
            'intro': f"自動生成されたH5Pアクティビティ: {title}",
            'introformat': 1,  # 1 = HTML形式
            'section': section_id,
            'visible': 1,  # 1 = 表示
            'displayoptions': 0,  # デフォルト表示オプション
        },
        'h5pfile': item_id
    }

    try:
        # POSTリクエストを送信
        response = requests.post(endpoint, data=data)

        # レスポンスのチェック
        if response.status_code == 200:
            try:
                result = response.json()
                if 'exception' in result:
                    logger.error(f"H5Pアクティビティ作成エラー: {result.get('message', 'Unknown error')}")
                    return None
                else:
                    h5p_id = result.get('h5pactivityid')
                    logger.info(f"H5Pアクティビティが作成されました: ID={h5p_id}, タイトル={title}")
                    return h5p_id
            except ValueError:
                logger.error(f"H5Pアクティビティ作成エラー: JSONデコードに失敗 - {response.text}")
        else:
            logger.error(f"H5Pアクティビティ作成エラー: ステータスコード {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"H5Pアクティビティ作成中に例外が発生しました: {e}")

    return None


def check_api_access(moodle_url, token):
    """Moodle APIへのアクセスをチェック"""
    endpoint = urljoin(moodle_url, '/webservice/rest/server.php')

    data = {
        'wstoken': token,
        'wsfunction': 'core_webservice_get_site_info',
        'moodlewsrestformat': 'json'
    }

    try:
        response = requests.post(endpoint, data=data)
        if response.status_code == 200:
            result = response.json()
            if 'exception' in result:
                logger.error(f"APIアクセスエラー: {result.get('message', 'Unknown error')}")
                return False
            else:
                logger.info(f"Moodle APIアクセス成功: サイト名 {result.get('sitename', 'Unknown site')}")
                return True
        else:
            logger.error(f"APIアクセスエラー: ステータスコード {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"APIアクセスチェック中に例外が発生しました: {e}")
        return False


def main():
    """メイン実行関数"""
    args = parse_arguments()

    # 設定の取得
    config = get_config()
    if not config:
        return

    # コマンドライン引数で設定を上書き
    if args.moodle_url:
        config['moodle_url'] = args.moodle_url
    if args.token:
        config['token'] = args.token
    if args.course_id:
        config['course_id'] = args.course_id
    if args.section_id:
        config['section_id'] = args.section_id

    # APIアクセスをチェック
    if not check_api_access(config['moodle_url'], config['token']):
        logger.error("Moodle APIへのアクセスに失敗しました。トークンとURLを確認してください。")
        return

    # H5Pファイルを検索
    h5p_files = find_h5p_files(args.h5p_dir)
    if not h5p_files:
        logger.warning(f"ディレクトリにH5Pファイルが見つかりませんでした: {args.h5p_dir}")
        return

    # 各H5Pファイルを処理
    successful_uploads = 0
    failed_uploads = 0

    for h5p_file in h5p_files:
        file_name = os.path.basename(h5p_file)
        logger.info(f"処理中: {file_name}")

        # ファイルをアップロード
        item_id = upload_file_to_moodle(h5p_file, config['moodle_url'], config['token'])
        if not item_id:
            logger.error(f"ファイルのアップロードに失敗しました: {file_name}")
            failed_uploads += 1
            continue

        # H5Pアクティビティを作成
        h5p_id = create_h5p_activity(
            item_id,
            file_name,
            config['course_id'],
            config['section_id'],
            config['moodle_url'],
            config['token']
        )

        if h5p_id:
            successful_uploads += 1
        else:
            failed_uploads += 1

        # APIレート制限を避けるため少し待機
        time.sleep(1)

    # 結果の表示
    logger.info(f"アップロード完了: 成功={successful_uploads}, 失敗={failed_uploads}")


if __name__ == "__main__":
    main()