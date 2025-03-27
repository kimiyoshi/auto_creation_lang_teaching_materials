#!/usr/bin/env python3
"""
GPT-4oを使用したH5Pコンテンツ生成スクリプト
(Devin AIからの実行を想定)
"""

import os
import json
import argparse
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数のロード
load_dotenv()

# OpenAI APIクライアント設定
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def parse_arguments():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(description='H5Pコンテンツを生成する')
    parser.add_argument('--lesson_id', type=str, required=True,
                        help='レッスンID (例: hiragana, katakana)')
    parser.add_argument('--content_type', type=str, required=True,
                        help='コンテンツタイプ (例: dialog_cards, course_presentation)')
    parser.add_argument('--task_file', type=str, required=True,
                        help='タスク指示ファイルのパス')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='出力ディレクトリ')
    return parser.parse_args()


def read_task_file(file_path: str) -> str:
    """タスク指示ファイルを読み込む"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"タスクファイルの読み込みエラー: {e}")
        raise


def extract_json_structure(task_content: str, content_type: str) -> Optional[Dict]:
    """タスク指示からJSONの構造を抽出する"""
    # JSONブロックを抽出する正規表現パターン
    pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, task_content)

    for match in matches:
        try:
            json_obj = json.loads(match)
            # content_typeに関連するJSONを見つける
            if (content_type == "dialog_cards" and "cards" in json_obj) or \
                    (content_type == "course_presentation" and "slides" in json_obj) or \
                    (content_type == "multiple_choice" and "questions" in json_obj) or \
                    (content_type == "fill_blanks" and "questions" in json_obj):
                return json_obj
        except json.JSONDecodeError:
            continue

    return None


def generate_prompt(task_content: str, content_type: str, lesson_id: str) -> str:
    """GPT-4oへのプロンプトを生成する"""
    prompt = f"""
あなたはH5Pコンテンツ作成の専門家です。以下のタスク指示に基づいて、{content_type}形式のJSONコンテンツを生成してください。
レッスンID: {lesson_id}

{task_content}

このコンテンツは日本語学習のためのものです。インドネシア人学習者向けに調整してください。
JSONだけを返してください。説明やコメントは不要です。
"""
    return prompt


def call_gpt4o(prompt: str) -> str:
    """GPT-4oにリクエストを送信して結果を取得する"""
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-turbo",  # 最新のGPT-4oモデル名に置き換える
                messages=[
                    {"role": "system", "content": "You are a H5P content creation expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"GPT-4oリクエスト失敗 (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数バックオフ
            else:
                logger.error("GPT-4oリクエストの最大試行回数を超えました")
                raise


def extract_json_from_response(response: str) -> Dict:
    """GPT-4oのレスポンスからJSONを抽出する"""
    # JSONブロックを探す
    json_pattern = r"```json\s*([\s\S]*?)\s*```"
    json_match = re.search(json_pattern, response)

    if json_match:
        json_str = json_match.group(1)
    else:
        # マークダウンのコードブロックがない場合は、レスポンス全体をJSONとして扱う
        json_str = response.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSONのパースエラー: {e}")
        logger.debug(f"解析しようとしたJSON文字列: {json_str}")
        raise


def save_json_content(content: Dict, output_dir: str, lesson_id: str, content_type: str):
    """生成されたJSONコンテンツを保存する"""
    # 出力ディレクトリがなければ作成
    os.makedirs(output_dir, exist_ok=True)

    # ファイル名を生成
    file_name = f"N5_{lesson_id}_{content_type}.json"
    file_path = os.path.join(output_dir, file_name)

    # JSONを保存
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    logger.info(f"コンテンツを保存しました: {file_path}")
    return file_path


def main():
    """メイン実行関数"""
    args = parse_arguments()

    # タスク指示ファイルを読み込む
    task_content = read_task_file(args.task_file)

    # プロンプトを生成
    prompt = generate_prompt(task_content, args.content_type, args.lesson_id)

    # GPT-4oに問い合わせ
    logger.info(f"GPT-4oにリクエスト送信中: {args.lesson_id} - {args.content_type}")
    response = call_gpt4o(prompt)

    # レスポンスからJSONを抽出
    content_json = extract_json_from_response(response)

    # コンテンツを保存
    output_path = save_json_content(
        content_json,
        args.output_dir,
        args.lesson_id,
        args.content_type
    )

    logger.info(f"H5Pコンテンツ生成完了: {output_path}")


if __name__ == "__main__":
    main()