#!/usr/bin/env python3
"""
JSONからH5Pパッケージを生成するスクリプト
既存のH5Pテンプレートをベースに、最小限の変更のみを適用
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
import uuid
import subprocess
import cairosvg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONTENT_TYPE_MAPPING = {
    "dialog_cards": "H5P.Dialogcards",
    "course_presentation": "H5P.CoursePresentation",
    "multiple_choice": "H5P.MultiChoice",
    "fill_blanks": "H5P.Blanks",
    "drag_drop": "H5P.DragQuestion",
    "memory_game": "H5P.MemoryGame"
}

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--templates_dir', default='src/templates')
    return parser.parse_args()

def find_json_files(input_dir):
    result = []
    for f in os.listdir(input_dir):
        if f.endswith('.json') and not f.startswith('.'):  # ← ドットファイルをスキップ
            result.append(os.path.join(input_dir, f))
    return result
def determine_content_type(json_file):
    base = os.path.basename(json_file)
    for key in CONTENT_TYPE_MAPPING:
        if key in base:
            return key
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if 'cards' in data or 'dialogs' in data:
            return 'dialog_cards'
        elif 'slides' in data:
            return 'course_presentation'
        elif 'questions' in data:
            if any('answers' in q for q in data['questions']):
                return 'multiple_choice'
            if any('*' in q.get('text', '') for q in data['questions']):
                return 'fill_blanks'
    return 'dialog_cards'

def find_template_h5p(content_type, templates_dir):
    pattern = os.path.join(templates_dir, content_type, '*.h5p')
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    all_templates = glob.glob(os.path.join(templates_dir, '**', '*.h5p'), recursive=True)
    return all_templates[0] if all_templates else None

def get_random_uuid():
    return str(uuid.uuid4())

def convert_svg_to_png_in_dir(images_dir):
    for filename in os.listdir(images_dir):
        if filename.endswith(".svg"):
            svg_path = os.path.join(images_dir, filename)
            png_path = os.path.join(images_dir, filename.replace(".svg", ".png"))
            try:
                cairosvg.svg2png(url=svg_path, write_to=png_path)
                os.remove(svg_path)
                logger.info(f"SVGをPNGに変換しました: {svg_path} -> {png_path}")
            except Exception as e:
                logger.error(f"SVGからPNGへの変換失敗: {svg_path} - {e}")

def update_content_json(path, data, content_type):
    with open(path, 'r', encoding='utf-8') as f:
        content = json.load(f)
    if content_type == 'dialog_cards' and 'cards' in data:
        content['dialogs'] = []
        for card in data['cards']:
            dialog = {
                'text': card.get('text', ''),
                'answer': card.get('answer', '')
            }
            if 'tip' in card:
                dialog['tips'] = card['tip']
            if 'image' in card:
                image_path = card['image'].get('path', '')
                if image_path.lower().endswith('.svg'):
                    image_path = re.sub(r'\.svg$', '.png', image_path)
                dialog['image'] = {
                    'path': image_path,
                    'width': card['image'].get('width', 300),
                    'height': card['image'].get('height', 300),
                    'alt': card['image'].get('alt', '')
                }
            # audio フィールドを追加
            if 'audio' in card:
                dialog['audio'] = [{
                    'path': card['audio'].get('path', ''),
                    'mime': card['audio'].get('mime', '')
                }]
            content['dialogs'].append(dialog)
        if 'title' in data:
            content['title'] = data['title']
        if 'description' in data:
            content['description'] = data['description']
        if 'behaviour' in data:
            content['behaviour'] = data['behaviour']
    unwanted_keys = [
        "answer", "next", "prev", "retry", "correctAnswer", "incorrectAnswer",
        "round", "cardsLeft", "nextRound", "startOver", "showSummary", "summary",
        "summaryCardsRight", "summaryCardsWrong", "summaryCardsNotShown",
        "summaryOverallScore", "summaryCardsCompleted", "summaryCompletedRounds",
        "summaryAllDone", "progressText", "cardFrontLabel", "cardBackLabel",
        "tipButtonLabel", "audioNotSupported", "confirmStartingOver"
    ]
    for key in unwanted_keys:
        content.pop(key, None)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    return True

def update_h5p_metadata(path, title):
    with open(path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    metadata['title'] = title
    metadata['language'] = 'ja'
    metadata.pop('defaultLanguage', None)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    return True

def create_h5p_package(json_file, content_type, templates_dir, output_dir):
    template = find_template_h5p(content_type, templates_dir)
    if not template:
        logger.error("テンプレートが見つかりません")
        return None
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    title = data.get('title', Path(json_file).stem)
    output_file = os.path.join(output_dir, Path(json_file).stem + '.h5p')
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(template, 'r') as zip_ref:
            zip_ref.extractall(tmp)
        update_content_json(os.path.join(tmp, 'content', 'content.json'), data, content_type)
        update_h5p_metadata(os.path.join(tmp, 'h5p.json'), title)
        img_src = os.path.join(os.path.dirname(json_file), 'images')
        img_dst = os.path.join(tmp, 'content', 'images')
        if os.path.exists(img_src):
            convert_svg_to_png_in_dir(img_src)
            os.makedirs(img_dst, exist_ok=True)
            for img in os.listdir(img_src):
                shutil.copy2(os.path.join(img_src, img), os.path.join(img_dst, img))

        audio_src = os.path.join(os.path.dirname(json_file), 'audios')
        audio_dst = os.path.join(tmp, 'content', 'audios')
        if os.path.exists(audio_src):
            os.makedirs(audio_dst, exist_ok=True)
            for aud in os.listdir(audio_src):
                shutil.copy2(os.path.join(audio_src, aud), os.path.join(audio_dst, aud))

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(tmp):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), tmp))
    return output_file

def main():
    args = parse_arguments()
    os.makedirs(args.output_dir, exist_ok=True)
    json_files = find_json_files(args.input_dir)
    for json_file in json_files:
        try:
            content_type = determine_content_type(json_file)
            create_h5p_package(json_file, content_type, args.templates_dir, args.output_dir)
        except Exception as e:
            logger.error(f"{json_file} の処理中にエラー: {e}", exc_info=True)

if __name__ == '__main__':
    main()