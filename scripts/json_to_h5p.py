#!/usr/bin/env python3
"""
JSONからH5Pパッケージを生成するスクリプト
既存のH5Pテンプレートファイルをベースに内容を置き換える
"""

import os
import json
import argparse
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
import re
import glob

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# H5Pコンテンツタイプのマッピング
CONTENT_TYPE_MAPPING = {
    "dialog_cards": "H5P.DialogCards",
    "course_presentation": "H5P.CoursePresentation",
    "multiple_choice": "H5P.MultiChoice",
    "fill_blanks": "H5P.Blanks",
    "drag_drop": "H5P.DragQuestion",
    "memory_game": "H5P.MemoryGame"
}


def parse_arguments():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(description='JSONからH5Pパッケージを生成する')
    parser.add_argument('--input_dir', type=str, required=True,
                        help='入力JSONディレクトリ')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='出力H5Pディレクトリ')
    parser.add_argument('--templates_dir', type=str, default='src/templates',
                        help='H5Pテンプレートディレクトリ')
    return parser.parse_args()


def find_json_files(input_dir):
    """指定ディレクトリからJSONファイルを検索する"""
    json_files = []
    for file in os.listdir(input_dir):
        if file.endswith('.json'):
            json_files.append(os.path.join(input_dir, file))
    return json_files


def determine_content_type(json_file):
    """ファイル名からコンテンツタイプを決定する"""
    file_name = os.path.basename(json_file)
    for content_type in CONTENT_TYPE_MAPPING.keys():
        if content_type in file_name:
            return content_type

    # ファイル名での判断ができない場合はJSON内容から判断
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'cards' in data:
                return 'dialog_cards'
            elif 'slides' in data:
                return 'course_presentation'
            elif 'questions' in data and any('answers' in q for q in data.get('questions', [])):
                return 'multiple_choice'
            elif 'questions' in data and any(
                    'text' in q and '*' in q.get('text', '') for q in data.get('questions', [])):
                return 'fill_blanks'
    except Exception as e:
        logger.error(f"JSONファイルの解析エラー: {e}")

    # デフォルト値
    return 'dialog_cards'


def find_template_h5p(content_type, templates_dir):
    """指定されたコンテンツタイプのテンプレートH5Pファイルを検索"""
    # 直接指定されたディレクトリを探す
    template_dir = os.path.join(templates_dir, content_type)
    template_pattern = os.path.join(template_dir, "*.h5p")
    templates = glob.glob(template_pattern)

    if templates:
        # 最初に見つかったテンプレートを使用
        return templates[0]

    # ディレクトリに直接ない場合は再帰的に検索
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.h5p') and content_type in file.lower():
                return os.path.join(root, file)

    # 見つからない場合はデフォルトテンプレートを検索
    default_pattern = os.path.join(templates_dir, "**", "*.h5p")
    templates = glob.glob(default_pattern, recursive=True)
    if templates:
        logger.warning(f"{content_type}用のテンプレートが見つからないため、デフォルトテンプレートを使用します: {templates[0]}")
        return templates[0]

    logger.error(f"テンプレートH5Pファイルが見つかりませんでした: {content_type}")
    return None


def extract_h5p_template(template_file, extract_dir):
    """H5Pテンプレートファイルを指定ディレクトリに解凍"""
    try:
        with zipfile.ZipFile(template_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return True
    except Exception as e:
        logger.error(f"テンプレートの解凍に失敗しました: {e}")
        return False


def update_content_json(content_json_path, new_content_data, content_type):
    """content.jsonファイルを新しいコンテンツデータで更新"""
    try:
        # 既存のcontent.jsonを読み込む
        with open(content_json_path, 'r', encoding='utf-8') as f:
            existing_content = json.load(f)

        # コンテンツタイプに応じて更新
        if content_type == 'dialog_cards':
            update_dialog_cards(existing_content, new_content_data)
        elif content_type == 'course_presentation':
            update_course_presentation(existing_content, new_content_data)
        elif content_type == 'multiple_choice':
            update_multiple_choice(existing_content, new_content_data)
        elif content_type == 'fill_blanks':
            update_fill_blanks(existing_content, new_content_data)
        elif content_type == 'drag_drop':
            update_drag_drop(existing_content, new_content_data)
        elif content_type == 'memory_game':
            update_memory_game(existing_content, new_content_data)
        else:
            # 不明なコンテンツタイプの場合は、主要フィールドのみ更新
            for key in new_content_data:
                if key in existing_content:
                    existing_content[key] = new_content_data[key]

        # 更新したcontent.jsonを書き込む
        with open(content_json_path, 'w', encoding='utf-8') as f:
            json.dump(existing_content, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"content.jsonの更新に失敗しました: {e}")
        return False


def update_dialog_cards(existing_content, new_content_data):
    """DialogCardsコンテンツを更新"""
    # タイトルと説明の更新
    if 'title' in new_content_data:
        existing_content['title'] = new_content_data['title']
    if 'description' in new_content_data:
        existing_content['description'] = new_content_data.get('description', '')

    # カードデータの更新
    if 'cards' in new_content_data:
        # dialogsフィールドにカードデータを設定
        existing_content['dialogs'] = []
        for card in new_content_data['cards']:
            dialog = {
                'text': card.get('text', ''),
                'answer': card.get('answer', ''),
                'tips': card.get('tip', '')
            }
            existing_content['dialogs'].append(dialog)

    # behaviourの更新
    if 'behaviour' in new_content_data:
        if 'behaviour' not in existing_content:
            existing_content['behaviour'] = {}
        for key, value in new_content_data['behaviour'].items():
            existing_content['behaviour'][key] = value


def update_course_presentation(existing_content, new_content_data):
    """CoursePresentationコンテンツを更新"""
    # プレゼンテーションフィールドを確認
    if 'presentation' not in existing_content:
        existing_content['presentation'] = {}

    # タイトルの更新
    if 'title' in new_content_data:
        existing_content['presentation']['title'] = new_content_data['title']

    # スライドの更新
    if 'slides' in new_content_data:
        existing_content['presentation']['slides'] = []
        for slide in new_content_data['slides']:
            slide_data = {'elements': []}

            if 'elements' in slide:
                for element in slide['elements']:
                    element_data = {
                        'x': element.get('x', 0),
                        'y': element.get('y', 0),
                        'width': element.get('width', 50),
                        'height': element.get('height', 50)
                    }

                    # テキスト要素
                    if element.get('type') == 'text':
                        element_data['action'] = {
                            'library': 'H5P.Text 1.1',
                            'params': {
                                'text': element.get('content', '')
                            }
                        }
                    # 他の要素タイプも同様に処理

                    slide_data['elements'].append(element_data)

            existing_content['presentation']['slides'].append(slide_data)

    # 表示設定の更新
    if 'display' in new_content_data:
        for key, value in new_content_data['display'].items():
            existing_content['presentation'][key] = value


def update_multiple_choice(existing_content, new_content_data):
    """MultipleChoiceコンテンツを更新"""
    # タイトルの更新
    if 'title' in new_content_data:
        existing_content['title'] = new_content_data['title']

    # 質問と回答の更新
    if 'questions' in new_content_data and new_content_data['questions']:
        first_question = new_content_data['questions'][0]
        existing_content['question'] = first_question.get('text', '')

        if 'answers' in first_question:
            existing_content['answers'] = []
            for answer in first_question['answers']:
                answer_data = {
                    'text': answer.get('text', ''),
                    'correct': answer.get('correct', False)
                }
                if 'feedback' in answer:
                    answer_data['tipsAndFeedback'] = {
                        'chosenFeedback': answer.get('feedback', '')
                    }
                existing_content['answers'].append(answer_data)

    # behaviourの更新
    if 'behaviour' in new_content_data:
        if 'behaviour' not in existing_content:
            existing_content['behaviour'] = {}
        for key, value in new_content_data['behaviour'].items():
            existing_content['behaviour'][key] = value


def update_fill_blanks(existing_content, new_content_data):
    """Fill in the Blanksコンテンツを更新"""
    # タイトルの更新
    if 'title' in new_content_data:
        existing_content['title'] = new_content_data['title']

    # 問題テキストの更新
    if 'questions' in new_content_data:
        questions_text = []
        for question in new_content_data['questions']:
            questions_text.append(question.get('text', ''))
        existing_content['text'] = '\n\n'.join(questions_text)

    # behaviourの更新
    if 'behaviour' in new_content_data:
        if 'behaviour' not in existing_content:
            existing_content['behaviour'] = {}
        for key, value in new_content_data['behaviour'].items():
            existing_content['behaviour'][key] = value


def update_drag_drop(existing_content, new_content_data):
    """Drag and Dropコンテンツを更新"""
    # 基本フィールドの更新
    if 'title' in new_content_data:
        existing_content['title'] = new_content_data['title']

    # ドラッグ要素とドロップゾーンの更新は構造が複雑なため、
    # 実際のテンプレートを確認して実装する必要がある


def update_memory_game(existing_content, new_content_data):
    """Memory Gameコンテンツを更新"""
    # 基本フィールドの更新
    if 'title' in new_content_data:
        existing_content['title'] = new_content_data['title']

    # カードペアの更新も、実際のテンプレートを確認して実装する必要がある


def update_h5p_metadata(h5p_json_path, content_data, content_type):
    """h5p.jsonファイルのメタデータを更新"""
    try:
        # 既存のh5p.jsonを読み込む
        with open(h5p_json_path, 'r', encoding='utf-8') as f:
            h5p_metadata = json.load(f)

        # タイトルの更新
        if 'title' in content_data:
            h5p_metadata['title'] = content_data['title']

        # 他のメタデータフィールドは変更せず、既存のものを維持

        # 更新したh5p.jsonを書き込む
        with open(h5p_json_path, 'w', encoding='utf-8') as f:
            json.dump(h5p_metadata, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"h5p.jsonの更新に失敗しました: {e}")
        return False


def create_h5p_package(json_file, content_type, templates_dir, output_dir):
    """H5Pパッケージを作成する"""
    # テンプレートH5Pファイルを検索
    template_file = find_template_h5p(content_type, templates_dir)
    if not template_file:
        logger.error(f"テンプレートファイルが見つかりませんでした: {content_type}")
        return None

    # JSONデータを読み込む
    with open(json_file, 'r', encoding='utf-8') as f:
        content_data = json.load(f)

    # 出力ファイル名を生成
    file_name = os.path.basename(json_file).replace('.json', '.h5p')
    output_path = os.path.join(output_dir, file_name)

    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # テンプレートファイルを一時ディレクトリに解凍
        if not extract_h5p_template(template_file, temp_dir):
            return None

        # content.jsonを更新
        content_json_path = os.path.join(temp_dir, 'content', 'content.json')
        if not update_content_json(content_json_path, content_data, content_type):
            return None

        # h5p.jsonを更新
        h5p_json_path = os.path.join(temp_dir, 'h5p.json')
        if not update_h5p_metadata(h5p_json_path, content_data, content_type):
            return None

        # ZIPファイルとしてパッケージング
        os.makedirs(output_dir, exist_ok=True)

        with zipfile.ZipFile(output_path, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arc_name)

        logger.info(f"H5Pパッケージを作成しました: {output_path}")
        return output_path


def main():
    """メイン実行関数"""
    args = parse_arguments()

    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(args.output_dir, exist_ok=True)

    # 入力ディレクトリからJSONファイルを検索
    json_files = find_json_files(args.input_dir)
    if not json_files:
        logger.warning(f"入力ディレクトリにJSONファイルが見つかりませんでした: {args.input_dir}")
        return

    # 各JSONファイルを処理
    for json_file in json_files:
        try:
            # コンテンツタイプを決定
            content_type = determine_content_type(json_file)
            logger.info(f"コンテンツタイプを決定しました: {content_type} - {json_file}")

            # H5Pパッケージを作成
            output_path = create_h5p_package(json_file, content_type, args.templates_dir, args.output_dir)

            if not output_path:
                logger.error(f"H5Pパッケージの作成に失敗しました: {json_file}")
        except Exception as e:
            logger.error(f"H5Pパッケージの作成中にエラーが発生しました: {e}", exc_info=True)

    logger.info(f"全てのH5Pパッケージの生成が完了しました。出力ディレクトリ: {args.output_dir}")


if __name__ == "__main__":
    main()