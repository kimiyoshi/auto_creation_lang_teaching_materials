#!/usr/bin/env python3
"""
GPT-4oを使用したH5Pコンテンツ生成スクリプト
(Devin AIからの実行を想定)
小学生の教科書スタイルのPNG画像生成機能を含む

使用方法:
1. 通常モード（本番用）:
   python scripts/generate_content.py --lesson_id hiragana --content_type dialog_cards --task_file tasks/hiragana-lesson.md --output_dir src/content/hiragana

2. テストモード（数文字のみ処理）:
   python scripts/generate_content.py --lesson_id test --content_type dialog_cards --output_dir src/content/test --test

3. テストモード（カスタム文字を指定）:
   python scripts/generate_content.py --lesson_id test --content_type dialog_cards --output_dir src/content/test --test --test_chars "なにぬねのナニヌ"

パラメータ説明:
  --lesson_id     : レッスンの識別子（例: hiragana, katakana, lesson01）
  --content_type  : コンテンツの種類（例: dialog_cards, course_presentation）
  --task_file     : タスク指示ファイル（テストモードでは不要）
  --output_dir    : 出力ディレクトリのパス
  --test          : テストモードで実行する（数文字のみ処理）
  --test_chars    : テストモードで処理する文字（デフォルト: あいうかきアイウ）
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
import platform
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment
from stability_sdk import client as stability_client
from stability_sdk.interfaces.gooseai.generation.generation_pb2 import (
    ARTIFACT_IMAGE,
    ARTIFACT_TEXT,
    FinishReason,
    SAMPLER_K_DPM_2_ANCESTRAL,
)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数のロード
load_dotenv()

# 環境変数に STABILITY_API_KEY を設定しておく (例: .env などで)
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

# OpenAI APIクライアント設定
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def save_json_content(content: Dict, output_dir: str, lesson_id: str, content_type: str):
    """生成されたJSONコンテンツを保存する"""
    # 出力ディレクトリがなければ作成
    os.makedirs(output_dir, exist_ok=True)

    # Dialog Cardsの場合、各カードにメディアと情報を追加
    if content_type == "dialog_cards" and "cards" in content:
        # 処理対象の文字を抽出
        characters = []
        for card in content["cards"]:
            if "text" in card and len(card["text"]) == 1:  # 1文字の場合のみ画像・音声生成
                characters.append(card["text"])

        # バッチでメディアを生成
        if characters:
            logger.info(f"全{len(characters)}文字のメディア（画像・音声）を生成します")
            media_results = generate_media_batch(characters, output_dir)

            # 生成したメディアと情報を各カードに追加
            for card in content["cards"]:
                if "text" in card and len(card["text"]) == 1:
                    character = card["text"]

                    # 例単語情報を直接取得（media_resultsを経由せず）
                    example_info = get_example_word_and_translation(character)
                    example_word = example_info.get('word', '')
                    example_reading = example_info.get('reading', '')
                    example_meaning = example_info.get('meaning', '')
                    kanji = example_info.get('kanji', '')
                    visual_cues = example_info.get('visual_cues', '')

                    logger.info(f"文字「{character}」の例単語情報: {example_info}")

                    # media_resultsからメディアファイルパスを取得
                    if character in media_results:
                        result = media_results[character]

                        # 文字画像
                        if result.get('char_image'):
                            card["image"] = {
                                "path": result['char_image'],
                                "width": 300,
                                "height": 300,
                                "alt": f"{character}"
                            }

                        # 音声
                        if result.get('audio'):
                            card["audio"] = {
                                "path": result['audio'],
                                "mime": "audio/mpeg"
                            }

                        # 例単語イラストがあれば
                        if result.get('example_image'):
                            example_image = result['example_image']
                        else:
                            example_image = None
                    else:
                        logger.warning(f"文字「{character}」のメディア生成結果が見つかりません")
                        example_image = None

                    # 表面のテキストを更新（文字と例単語）
                    if example_word:
                        card_text = f"<div style='font-size: 1.5em;'><strong>{character}</strong> - {example_word}</div>"
                        if example_image:
                            card_text += f"<div><img src='{example_image}' width='100' alt='{example_word}' /></div>"
                        card["text"] = card_text
                    else:
                        # 例単語がない場合は文字だけ表示
                        card["text"] = f"<div style='font-size: 1.5em;'><strong>{character}</strong></div>"

                    # 裏面の内容をより豊かに
                    pronunciation = get_indonesian_pronunciation_guide(character)

                    answer_html = f"<div><strong>{character}</strong></div>"
                    if pronunciation:
                        answer_html += f"<div>{pronunciation}</div>"
                    if example_word and example_reading and example_meaning:
                        answer_html += f"<div>{example_word} ({example_reading}) - {example_meaning}</div>"

                    card["answer"] = answer_html

                    # ヒントも追加
                    is_katakana = ord(character) >= ord('ア') and ord(character) <= ord('ン')
                    char_type_jp = 'カタカナ' if is_katakana else 'ひらがな'
                    card["tip"] = f"{char_type_jp}の「{character}」の発音を聞いて練習しましょう"

    # ファイル名を生成
    file_name = f"N5_{lesson_id}_{content_type}.json"
    file_path = os.path.join(output_dir, file_name)

    # カードの順序をランダムに
    if content_type == "dialog_cards":
        if "behaviour" not in content:
            content["behaviour"] = {}
        content["behaviour"]["randomCards"] = True


    # JSONを保存
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    logger.info(f"コンテンツを保存しました: {file_path}")
    return file_path


def generate_dalle_prompt_by_gpt4o(word, kanji, meaning, visual_cues=None):
    """
    GPT-4o を使って、その単語に合った DALL·E 3 向けプロンプトを動的に生成する関数。
    DALL·E に対して、教育用で意味が直感的に伝わる、清潔かつリアルな画像を生成させるためのプロンプトを作る。
    """
    import openai  # 必要に応じて pip install openai

    openai.api_key = "YOUR_API_KEY"  # ← ここにご自身の OpenAI API キーを設定してください
    client = openai.OpenAI()

    prompt = f"""
あなたは語学学習教材用の画像プロンプトデザイナーです。
以下の日本語の単語について、DALL·E 3 に与えるためのプロンプト（英語）を考えてください。

【語情報】
- 単語（ひらがな）: {word}
- 漢字: {kanji}
- 意味（英語）: {meaning}
- 視覚的なヒント（任意）: {visual_cues or "特になし"}

【プロンプト生成の目的】
- DALL·E 3 に英語で与えるプロンプトとして、photo-realistic な構図で、意味が直感的に伝わる画像を生成させたい
- 教材用途であり、学習者にとって「これがこの単語を表している」と一目で分かるビジュアルが必要

【制約と禁止事項】
- 主題（単語を表すもの）は画像の中心に、ひとつだけ配置すること
- 背景は白または非常にソフトにぼかされたもの。余計な物は置かない
- 主題の表面に、文字（日本語・英語・ローマ字）、記号、ロゴ、模様、装飾、アイコンを一切含めない
- ただし、主題が新聞や書籍は例外だが、文字はぼかすか潰すこと
- 特に漢字や意味不明な文字を鞄や服などに描かないこと（emboss, engrave, print を含めない）
- バッグ、動物、人物などには一切装飾を加えない
- 背景に書籍、家具、室内装飾、アート作品などを含めない
- ファンタジー風、未来風、抽象風の構図は避け、日常的で現実的なシーンにすること

【スタイル】
- 明るく、ミニマルで、教育用途にふさわしい雰囲気
- 親しみやすく、使いやすい写真風の構図（photo-realistic）

【出力形式】
- 出力は英語の DALL·E 用プロンプトのみとし、説明文やコメントを一切含めないこと

STYLE_HINTS = (
    "studio lighting, soft shadows, shallow depth of field, centered composition, "
    "realistic texture, minimalist, clean, aesthetic, photo-realistic, no text or symbols"
)
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a prompt generator for educational visual content."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,
        max_tokens=800
    )

    return response.choices[0].message.content.strip()


def generate_example_image(
    word: str,
    character: str,
    character_type: str,
    kanji: str,
    visual_cues: str,
    kanji_meaning_in_English: str,
    output_path: str,
    provider: str = "openai"  # 'openai' or 'stability'
) -> bool:
    """
    例単語または文字のイラストを生成するための関数。
    character 用か example 用かで挙動を分けたい場合は呼び出し側で引数を変えて使う。

    prompt内では「1枚絵のかるた札」「右上に文字の円」などを指示し、なるべく一貫したデザインを出す。
    """
    try:
        # ここでは引数を柔軟に使い分けて、文字用と例単語用を共通化。
        # character_image 生成時は word=character, visual_cues等を最小限、などで呼び出し。

        # 例：キャラクター用イメージなら "word" は単に文字そのもの or "Character"
        #     例単語なら kanji や meaning, visual_cues を活かす

        # シンプルにまとめたプロンプト例
        prompt = generate_dalle_prompt_by_gpt4o(
            word=word,
            kanji=kanji,
            meaning=kanji_meaning_in_English,
            visual_cues=visual_cues
        )

        # Generate a single illustration that visually represents the "{kanji}" (meaning: "{kanji_meaning_in_English}").
        # The image should be in the style of a Japanese karuta "e-fuda" intended for basic learning Japanese,
        # featuring a simple, clear, and child-friendly design reminiscent of a Ghibli-style watercolor or pastel scene.
        # If visual cues are provided, incorporate the following visual elements: {visual_cues}.
        # If no visual cues are given, generate the image based solely on the essence of the Kanji "{kanji}" and its meaning.
        # Focus solely on creating an image that expresses the concept of "{kanji}".
        logger.info(f"prompt: {prompt}")
        logger.info(f"model: {provider}")

        if provider == "stability":
            stability_key = os.getenv("STABILITY_API_KEY")
            if not stability_key:
                logger.error("STABILITY_API_KEY が設定されていません。")
                return False

            endpoint = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
            data = {
                "prompt": prompt,
                "output_format": "png",
            }

            try:
                response = requests.post(
                    endpoint,
                    headers={
                        "authorization": f"Bearer {stability_key}",
                        "accept": "image/*"
                    },
                    files={"none": ""},
                    data=data
                )
            except Exception as e:
                logger.error(f"Stability AI へのリクエスト中にエラー: {e}")
                return False

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Stability AIから生成したイラストを保存しました: {output_path}")

                # 画像を300x300にリサイズする処理を追加
                try:
                    from PIL import Image
                    with Image.open(output_path) as img:
                        img_resized = img.resize((300, 300), Image.ANTIALIAS)
                        img_resized.save(output_path)
                    logger.info(f"画像を300x300にリサイズしました: {output_path}")
                except Exception as e:
                    logger.error(f"画像のリサイズ処理中にエラーが発生しました: {e}")
                    return False

                return True
            else:
                try:
                    err_msg = response.json()
                except:
                    err_msg = response.text
                logger.error(f"Stability AI APIエラー: {err_msg}")
                return False


        else:
            # DALL·E 3 (OpenAI) を使う場合
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            image_url = response.data[0].url
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(image_response.content)
                logger.info(f"DALL·E 3から生成したイラストを保存しました: {output_path}")

                # 画像を300x300にリサイズする処理を追加
                try:
                    from PIL import Image
                    with Image.open(output_path) as img:
                        img_resized = img.resize((300, 300), Image.ANTIALIAS)
                        img_resized.save(output_path)
                    logger.info(f"画像を300x300にリサイズしました: {output_path}")
                except Exception as e:
                    logger.error(f"画像のリサイズ処理中にエラーが発生しました: {e}")
                    return False

                return True
            else:
                logger.error(f"イラストのダウンロードに失敗しました: ステータスコード {image_response.status_code}")
                return False


    except Exception as e:
        logger.error(f"イラスト生成中にエラーが発生しました: {e}")
        return False

def generate_audio(character: str, output_path: str, include_example: bool = True) -> bool:
    """文字と例単語の発音音声ファイルを生成する（同期生成）"""
    try:
        # 例単語情報の取得
        example_info = get_example_word_and_translation(character)
        example_word = example_info.get('word', '')

        # 文字単独用ファイルパス
        char_path = f"{os.path.splitext(output_path)[0]}_char.mp3"

        # 文字の音声を生成
        char_text = character
        char_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=char_text,
            response_format="mp3"
        )
        with open(char_path, 'wb') as f:
            f.write(char_response.content)

        logger.info(f"文字の音声ファイルを作成しました: {char_path}")

        if include_example and example_word:
            # 例単語用ファイルパス
            word_path = f"{os.path.splitext(output_path)[0]}_word.mp3"
            word_response = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=example_word,
                response_format="mp3"
            )
            with open(word_path, 'wb') as f:
                f.write(word_response.content)

            logger.info(f"例単語の音声ファイルを作成しました: {word_path}")

            # 結合
            char_audio = AudioSegment.from_file(char_path)
            word_audio = AudioSegment.from_file(word_path)
            silence = AudioSegment.silent(duration=250)  # 0.25秒くらい
            combined = char_audio + silence + word_audio
            combined.export(output_path, format="mp3")

            os.remove(char_path)
            os.remove(word_path)
            logger.info(f"文字音声＋例単語音声を結合し、{output_path} を作成しました。")
        else:
            # 例単語なしの場合は文字だけを正式パスに
            os.rename(char_path, output_path)

        return True

    except Exception as e:
        logger.error(f"音声生成中にエラーが発生: {e}")
        # 後始末
        char_path = f"{os.path.splitext(output_path)[0]}_char.mp3"
        word_path = f"{os.path.splitext(output_path)[0]}_word.mp3"
        for path in [char_path, word_path]:
            if os.path.exists(path):
                os.remove(path)
        return False

def get_indonesian_pronunciation_guide(character: str) -> str:
    """各文字のインドネシア語対応発音を返す (一部抜粋)"""
    pronunciation_guides = {
        # あ行
        "あ": "a seperti dalam kata 'api'",
        "い": "i seperti dalam kata 'ikan'",
        "う": "u seperti dalam kata 'untuk'",
        "え": "e seperti dalam kata 'enak'",
        "お": "o seperti dalam kata 'obat'",

        # か行
        "か": "ka seperti dalam kata 'kamar'",
        "き": "ki seperti dalam kata 'kita'",
        "く": "ku seperti dalam kata 'kuda'",
        "け": "ke seperti dalam kata 'kereta'",
        "こ": "ko seperti dalam kata 'kopi'",

        # さ行
        "さ": "sa seperti dalam kata 'satu'",
        "し": "shi seperti dalam kata 'siang' tapi dengan bunyi 'sh'",
        "す": "su seperti dalam kata 'susah'",
        "せ": "se seperti dalam kata 'sepatu'",
        "そ": "so seperti dalam kata 'sore'",

        # た行
        "た": "ta seperti dalam kata 'tangan'",
        "ち": "chi seperti dalam kata 'cinta' dengan sedikit sentuhan 't'",
        "つ": "tsu seperti dalam kata 'tsunami'",
        "て": "te seperti dalam kata 'teman'",
        "と": "to seperti dalam kata 'tolong'",

        # な行
        "な": "na seperti dalam kata 'nama'",
        "に": "ni seperti dalam kata 'nilai'",
        "ぬ": "nu seperti dalam kata 'nuansa'",
        "ね": "ne seperti dalam kata 'nenek'",
        "の": "no seperti dalam kata 'nomor'",

        # は行
        "は": "ha seperti dalam kata 'hari'",
        "ひ": "hi seperti dalam kata 'hijau'",
        "ふ": "fu seperti dalam kata 'full' dalam bahasa Inggris",
        "へ": "he seperti dalam kata 'hebat'",
        "ほ": "ho seperti dalam kata 'hokage'",

        # ま行
        "ま": "ma seperti dalam kata 'makan'",
        "み": "mi seperti dalam kata 'minum'",
        "む": "mu seperti dalam kata 'muncul'",
        "め": "me seperti dalam kata 'merah'",
        "も": "mo seperti dalam kata 'motor'",

        # や行
        "や": "ya seperti dalam kata 'yang'",
        "ゆ": "yu seperti dalam kata 'yudisium'",
        "よ": "yo seperti dalam kata 'yogurt'",

        # ら行
        "ら": "ra seperti dalam kata 'ramai'",
        "り": "ri seperti dalam kata 'ringan'",
        "る": "ru seperti dalam kata 'rumah'",
        "れ": "re seperti dalam kata 'resep'",
        "ろ": "ro seperti dalam kata 'robot'",

        # わ行
        "わ": "wa seperti dalam kata 'wanita'",
        "を": "wo seperti 'o' dalam kata 'obat'",
        "ん": "n seperti dalam kata 'antar'",

        # カタカナ（ア行）
        "ア": "a seperti dalam kata 'api'",
        "イ": "i seperti dalam kata 'ikan'",
        "ウ": "u seperti dalam kata 'untuk'",
        "エ": "e seperti dalam kata 'enak'",
        "オ": "o seperti dalam kata 'obat'",

        # カタカナ（カ行）
        "カ": "ka seperti dalam kata 'kamar'",
        "キ": "ki seperti dalam kata 'kita'",
        "ク": "ku seperti dalam kata 'kuda'",
        "ケ": "ke seperti dalam kata 'kereta'",
        "コ": "ko seperti dalam kata 'kopi'",

        # カタカナ（サ行）
        "サ": "sa seperti dalam kata 'satu'",
        "シ": "shi seperti dalam kata 'siang' tapi dengan bunyi 'sh'",
        "ス": "su seperti dalam kata 'susah'",
        "セ": "se seperti dalam kata 'sepatu'",
        "ソ": "so seperti dalam kata 'sore'",

        # カタカナ（タ行）
        "タ": "ta seperti dalam kata 'tangan'",
        "チ": "chi seperti dalam kata 'cinta' dengan sedikit sentuhan 't'",
        "ツ": "tsu seperti dalam kata 'tsunami'",
        "テ": "te seperti dalam kata 'teman'",
        "ト": "to seperti dalam kata 'tolong'",

        # カタカナ（ナ行）
        "ナ": "na seperti dalam kata 'nama'",
        "ニ": "ni seperti dalam kata 'nilai'",
        "ヌ": "nu seperti dalam kata 'nuansa'",
        "ネ": "ne seperti dalam kata 'nenek'",
        "ノ": "no seperti dalam kata 'nomor'",

        # カタカナ（ハ行）
        "ハ": "ha seperti dalam kata 'hari'",
        "ヒ": "hi seperti dalam kata 'hijau'",
        "フ": "fu seperti dalam kata 'full' dalam bahasa Inggris",
        "ヘ": "he seperti dalam kata 'hebat'",
        "ホ": "ho seperti dalam kata 'hokage'",

        # カタカナ（マ行）
        "マ": "ma seperti dalam kata 'makan'",
        "ミ": "mi seperti dalam kata 'minum'",
        "ム": "mu seperti dalam kata 'muncul'",
        "メ": "me seperti dalam kata 'merah'",
        "モ": "mo seperti dalam kata 'motor'",

        # カタカナ（ヤ行）
        "ヤ": "ya seperti dalam kata 'yang'",
        "ユ": "yu seperti dalam kata 'yudisium'",
        "ヨ": "yo seperti dalam kata 'yogurt'",

        # カタカナ（ラ行）
        "ラ": "ra seperti dalam kata 'ramai'",
        "リ": "ri seperti dalam kata 'ringan'",
        "ル": "ru seperti dalam kata 'rumah'",
        "レ": "re seperti dalam kata 'resep'",
        "ロ": "ro seperti dalam kata 'robot'",

        # カタカナ（ワ行）
        "ワ": "wa seperti dalam kata 'wanita'",
        "ヲ": "wo seperti 'o' dalam kata 'obat'",
        "ン": "n seperti dalam kata 'antar'"
    }
    return pronunciation_guides.get(character, "")

def get_example_word_and_translation(character: str) -> dict:
    """各文字の例単語、読み方、訳を返す (一部抜粋)"""
    character_examples = {
        # あ行
        "あ": {"word": "あめ", "reading": "ame", "meaning": "hujan (雨)", "kanji": "雨"},
        "い": {"word": "いぬ", "reading": "inu", "meaning": "anjing (犬)", "kanji": "犬"},
        "う": {"word": "うみ", "reading": "umi", "meaning": "laut (海)", "kanji": "海"},
        "え": {"word": "えき", "reading": "eki", "meaning": "stasiun (駅)", "kanji": "駅"},
        "お": {"word": "おかし", "reading": "okashi", "meaning": "permen/kue (お菓子)", "kanji": "お菓子"},

        # か行
        "か": {"word": "かばん", "reading": "kaban", "meaning": "tas (鞄)", "kanji": "鞄"},
        "き": {"word": "きっぷ", "reading": "kippu", "meaning": "tiket (切符)", "kanji": "切符"},
        "く": {"word": "くつ", "reading": "kutsu", "meaning": "sepatu (靴)", "kanji": "靴"},
        "け": {"word": "けいたい", "reading": "keitai", "meaning": "telepon genggam (携帯)", "kanji": "携帯"},
        "こ": {"word": "こども", "reading": "kodomo", "meaning": "anak (子供)", "kanji": "子供"},

        # さ行
        "さ": {"word": "さくら", "reading": "sakura", "meaning": "bunga sakura (桜)", "kanji": "桜"},
        "し": {"word": "しんぶん", "reading": "shinbun", "meaning": "koran (新聞)", "kanji": "新聞"},
        "す": {"word": "すし", "reading": "sushi", "meaning": "sushi (寿司)", "kanji": "寿司"},
        "せ": {"word": "せんせい", "reading": "sensei", "meaning": "guru (先生)", "kanji": "先生"},
        "そ": {"word": "そら", "reading": "sora", "meaning": "langit (空)", "kanji": "空"},

        # た行
        "た": {"word": "たべもの", "reading": "tabemono", "meaning": "makanan (食べ物)", "kanji": "食べ物"},
        "ち": {"word": "ちず", "reading": "chizu", "meaning": "peta (地図)", "kanji": "地図"},
        "つ": {"word": "つくえ", "reading": "tsukue", "meaning": "meja (机)", "kanji": "机"},
        "て": {"word": "てがみ", "reading": "tegami", "meaning": "surat (手紙)", "kanji": "手紙"},
        "と": {"word": "とり", "reading": "tori", "meaning": "burung (鳥)", "kanji": "鳥"},

        # な行
        "な": {"word": "なつ", "reading": "natsu", "meaning": "musim panas (夏)", "kanji": "夏", "visual_cues":"sunflowers, cicadas, fans, blue sky, watermelon", "kanji_meaning_in_English":"summer"},
        "に": {"word": "にわ", "reading": "niwa", "meaning": "taman (庭)", "kanji": "庭"},
        "ぬ": {"word": "ぬいぐるみ", "reading": "nuigurumi", "meaning": "boneka (縫いぐるみ)", "kanji": "縫いぐるみ"},
        "ね": {"word": "ねこ", "reading": "neko", "meaning": "kucing (猫)", "kanji": "猫"},
        "の": {"word": "のみもの", "reading": "nomimono", "meaning": "minuman (飲み物)", "kanji": "飲み物"},

        # は行
        "は": {"word": "はな", "reading": "hana", "meaning": "bunga (花)", "kanji": "花"},
        "ひ": {"word": "ひと", "reading": "hito", "meaning": "orang (人)", "kanji": "人"},
        "ふ": {"word": "ふね", "reading": "fune", "meaning": "kapal (船)", "kanji": "船"},
        "へ": {"word": "へや", "reading": "heya", "meaning": "kamar (部屋)", "kanji": "部屋"},
        "ほ": {"word": "ほん", "reading": "hon", "meaning": "buku (本)", "kanji": "本"},

        # ま行
        "ま": {"word": "まど", "reading": "mado", "meaning": "jendela (窓)", "kanji": "窓"},
        "み": {"word": "みず", "reading": "mizu", "meaning": "air (水)", "kanji": "水"},
        "む": {"word": "むし", "reading": "mushi", "meaning": "serangga (虫)", "kanji": "虫"},
        "め": {"word": "めがね", "reading": "megane", "meaning": "kacamata (眼鏡)", "kanji": "眼鏡"},
        "も": {"word": "もり", "reading": "mori", "meaning": "hutan (森)", "kanji": "森"},

        # や行
        "や": {"word": "やま", "reading": "yama", "meaning": "gunung (山)", "kanji": "山"},
        "ゆ": {"word": "ゆき", "reading": "yuki", "meaning": "salju (雪)", "kanji": "雪"},
        "よ": {"word": "よる", "reading": "yoru", "meaning": "malam (夜)", "kanji": "夜"},

        # ら行
        "ら": {"word": "らいねん", "reading": "rainen", "meaning": "tahun depan (来年)", "kanji": "来年"},
        "り": {"word": "りんご", "reading": "ringo", "meaning": "apel (林檎)", "kanji": "林檎"},
        "る": {"word": "るす", "reading": "rusu", "meaning": "tidak ada di rumah (留守)", "kanji": "留守"},
        "れ": {"word": "れいぞうこ", "reading": "reizouko", "meaning": "kulkas (冷蔵庫)", "kanji": "冷蔵庫"},
        "ろ": {"word": "ろうそく", "reading": "rousoku", "meaning": "lilin (蝋燭)", "kanji": "蝋燭"},

        # わ行
        "わ": {"word": "わたし", "reading": "watashi", "meaning": "saya (私)", "kanji": "私"},
        "を": {"word": "をたく", "reading": "wotaku", "meaning": "otaku (ヲタク)", "kanji": "ヲタク"},
        "ん": {"word": "んーと", "reading": "n-to", "meaning": "hmm (んーと)", "kanji": ""},

        # 濁音（がぎぐげご）
        "が": {"word": "がっこう", "reading": "gakkou", "meaning": "sekolah (学校)", "kanji": "学校"},
        "ぎ": {"word": "ぎんこう", "reading": "ginkou", "meaning": "bank (銀行)", "kanji": "銀行"},
        "ぐ": {"word": "ぐんて", "reading": "gunte", "meaning": "sarung tangan (軍手)", "kanji": "軍手"},
        "げ": {"word": "げんき", "reading": "genki", "meaning": "sehat/baik (元気)", "kanji": "元気"},
        "ご": {"word": "ごはん", "reading": "gohan", "meaning": "nasi (ご飯)", "kanji": "ご飯"},

        # 濁音（ざじずぜぞ）
        "ざ": {"word": "ざっし", "reading": "zasshi", "meaning": "majalah (雑誌)", "kanji": "雑誌"},
        "じ": {"word": "じかん", "reading": "jikan", "meaning": "waktu (時間)", "kanji": "時間"},
        "ず": {"word": "ずかん", "reading": "zukan", "meaning": "buku ensiklopedia (図鑑)", "kanji": "図鑑"},
        "ぜ": {"word": "ぜんぶ", "reading": "zenbu", "meaning": "semua (全部)", "kanji": "全部"},
        "ぞ": {"word": "ぞう", "reading": "zou", "meaning": "gajah (象)", "kanji": "象"},

        # 濁音（だぢづでど）
        "だ": {"word": "だいがく", "reading": "daigaku", "meaning": "universitas (大学)", "kanji": "大学"},
        "ぢ": {"word": "ぢしん", "reading": "jishin", "meaning": "gempa bumi (地震)", "kanji": "地震"},
        "づ": {"word": "づくえ", "reading": "zukue", "meaning": "meja (机)", "kanji": "机"},
        "で": {"word": "でんわ", "reading": "denwa", "meaning": "telepon (電話)", "kanji": "電話"},
        "ど": {"word": "どあ", "reading": "doa", "meaning": "pintu (ドア)", "kanji": "ドア"},

        # 濁音（ばびぶべぼ）
        "ば": {"word": "ばす", "reading": "basu", "meaning": "bus (バス)", "kanji": "バス"},
        "び": {"word": "びょういん", "reading": "byouin", "meaning": "rumah sakit (病院)", "kanji": "病院"},
        "ぶ": {"word": "ぶたにく", "reading": "butaniku", "meaning": "daging babi (豚肉)", "kanji": "豚肉"},
        "べ": {"word": "べんとう", "reading": "bentou", "meaning": "bekal (弁当)", "kanji": "弁当"},
        "ぼ": {"word": "ぼうし", "reading": "boushi", "meaning": "topi (帽子)", "kanji": "帽子"},

        # 半濁音（ぱぴぷぺぽ）
        "ぱ": {"word": "ぱん", "reading": "pan", "meaning": "roti (パン)", "kanji": "パン"},
        "ぴ": {"word": "ぴあの", "reading": "piano", "meaning": "piano (ピアノ)", "kanji": "ピアノ"},
        "ぷ": {"word": "ぷれぜんと", "reading": "purezento", "meaning": "hadiah (プレゼント)", "kanji": "プレゼント"},
        "ぺ": {"word": "ぺん", "reading": "pen", "meaning": "pulpen (ペン)", "kanji": "ペン"},
        "ぽ": {"word": "ぽけっと", "reading": "poketto", "meaning": "saku (ポケット)", "kanji": "ポケット"},

        # カタカナ（ア行）
        "ア": {"word": "アイス", "reading": "aisu", "meaning": "es krim", "kanji": ""},
        "イ": {"word": "インドネシア", "reading": "indonesia", "meaning": "Indonesia", "kanji": ""},
        "ウ": {"word": "ウール", "reading": "ūru", "meaning": "wol", "kanji": ""},
        "エ": {"word": "エレベーター", "reading": "erebētā", "meaning": "elevator", "kanji": ""},
        "オ": {"word": "オレンジ", "reading": "orenji", "meaning": "jeruk", "kanji": ""},

        # カタカナ（カ行）
        "カ": {"word": "カメラ", "reading": "kamera", "meaning": "kamera", "kanji": ""},
        "キ": {"word": "キッチン", "reading": "kitchin", "meaning": "dapur", "kanji": ""},
        "ク": {"word": "クラス", "reading": "kurasu", "meaning": "kelas", "kanji": ""},
        "ケ": {"word": "ケーキ", "reading": "kēki", "meaning": "kue", "kanji": ""},
        "コ": {"word": "コーヒー", "reading": "kōhī", "meaning": "kopi", "kanji": ""},

        # カタカナ（サ行）
        "サ": {"word": "サッカー", "reading": "sakkā", "meaning": "sepak bola", "kanji": ""},
        "シ": {"word": "シャツ", "reading": "shatsu", "meaning": "kemeja", "kanji": ""},
        "ス": {"word": "スマホ", "reading": "sumaho", "meaning": "smartphone", "kanji": ""},
        "セ": {"word": "セーター", "reading": "sētā", "meaning": "sweater", "kanji": ""},
        "ソ": {"word": "ソファ", "reading": "sofa", "meaning": "sofa", "kanji": ""},

        # カタカナ（タ行）
        "タ": {"word": "タクシー", "reading": "takushī", "meaning": "taksi", "kanji": ""},
        "チ": {"word": "チケット", "reading": "chiketto", "meaning": "tiket", "kanji": ""},
        "ツ": {"word": "ツアー", "reading": "tsuā", "meaning": "tur", "kanji": ""},
        "テ": {"word": "テレビ", "reading": "terebi", "meaning": "televisi", "kanji": ""},
        "ト": {"word": "トマト", "reading": "tomato", "meaning": "tomat", "kanji": ""},

        # カタカナ（ナ行）
        "ナ": {"word": "ナイフ", "reading": "naifu", "meaning": "pisau", "kanji": ""},
        "ニ": {"word": "ニュース", "reading": "nyūsu", "meaning": "berita", "kanji": ""},
        "ヌ": {"word": "ヌードル", "reading": "nūdoru", "meaning": "mi", "kanji": ""},
        "ネ": {"word": "ネクタイ", "reading": "nekutai", "meaning": "dasi", "kanji": ""},
        "ノ": {"word": "ノート", "reading": "nōto", "meaning": "buku catatan", "kanji": ""},

        # カタカナ（ハ行）
        "ハ": {"word": "ハンバーガー", "reading": "hanbāgā", "meaning": "hamburger", "kanji": ""},
        "ヒ": {"word": "ヒーター", "reading": "hītā", "meaning": "pemanas", "kanji": ""},
        "フ": {"word": "フルーツ", "reading": "furūtsu", "meaning": "buah", "kanji": ""},
        "ヘ": {"word": "ヘアスタイル", "reading": "heasutairu", "meaning": "gaya rambut", "kanji": ""},
        "ホ": {"word": "ホテル", "reading": "hoteru", "meaning": "hotel", "kanji": ""},

        # カタカナ（マ行）
        "マ": {"word": "マンゴー", "reading": "mangō", "meaning": "mangga", "kanji": ""},
        "ミ": {"word": "ミルク", "reading": "miruku", "meaning": "susu", "kanji": ""},
        "ム": {"word": "ムード", "reading": "mūdo", "meaning": "suasana", "kanji": ""},
        "メ": {"word": "メール", "reading": "mēru", "meaning": "email", "kanji": ""},
        "モ": {"word": "モデル", "reading": "moderu", "meaning": "model", "kanji": ""},

        # カタカナ（ヤ行）
        "ヤ": {"word": "ヤクルト", "reading": "yakuruto", "meaning": "yakult", "kanji": ""},
        "ユ": {"word": "ユニフォーム", "reading": "yunifōmu", "meaning": "seragam", "kanji": ""},
        "ヨ": {"word": "ヨーグルト", "reading": "yōguruto", "meaning": "yogurt", "kanji": ""},

        # カタカナ（ラ行）
        "ラ": {"word": "ラジオ", "reading": "rajio", "meaning": "radio", "kanji": ""},
        "リ": {"word": "リモコン", "reading": "rimokon", "meaning": "remote control", "kanji": ""},
        "ル": {"word": "ルーム", "reading": "rūmu", "meaning": "kamar", "kanji": ""},
        "レ": {"word": "レストラン", "reading": "resutoran", "meaning": "restoran", "kanji": ""},
        "ロ": {"word": "ロボット", "reading": "robotto", "meaning": "robot", "kanji": ""},

        # カタカナ（ワ行）
        "ワ": {"word": "ワイン", "reading": "wain", "meaning": "anggur", "kanji": ""},
        "ヲ": {"word": "ヲタク", "reading": "wotaku", "meaning": "otaku", "kanji": ""},
        "ン": {"word": "パン", "reading": "pan", "meaning": "roti", "kanji": ""},

        # カタカナ濁音（ガ行）
        "ガ": {"word": "ガム", "reading": "gamu", "meaning": "permen karet", "kanji": ""},
        "ギ": {"word": "ギター", "reading": "gitā", "meaning": "gitar", "kanji": ""},
        "グ": {"word": "グラス", "reading": "gurasu", "meaning": "gelas", "kanji": ""},
        "ゲ": {"word": "ゲーム", "reading": "gēmu", "meaning": "permainan", "kanji": ""},
        "ゴ": {"word": "ゴルフ", "reading": "gorufu", "meaning": "golf", "kanji": ""},

        # カタカナ濁音（ザ行）
        "ザ": {"word": "ザクロ", "reading": "zakuro", "meaning": "delima", "kanji": ""},
        "ジ": {"word": "ジュース", "reading": "jūsu", "meaning": "jus", "kanji": ""},
        "ズ": {"word": "ズボン", "reading": "zubon", "meaning": "celana panjang", "kanji": ""},
        "ゼ": {"word": "ゼリー", "reading": "zerī", "meaning": "jeli", "kanji": ""},
        "ゾ": {"word": "ゾウ", "reading": "zou", "meaning": "gajah", "kanji": ""},

        # カタカナ濁音（ダ行）
        "ダ": {"word": "ダンス", "reading": "dansu", "meaning": "tarian", "kanji": ""},
        "ヂ": {"word": "ヂーゼル", "reading": "dīzeru", "meaning": "diesel", "kanji": ""},
        "ヅ": {"word": "カヅオ", "reading": "kazuo", "meaning": "ikan cakalang", "kanji": ""},
        "デ": {"word": "デザイン", "reading": "dezain", "meaning": "desain", "kanji": ""},
        "ド": {"word": "ドア", "reading": "doa", "meaning": "pintu", "kanji": ""},

        # カタカナ濁音（バ行）
        "バ": {"word": "バス", "reading": "basu", "meaning": "bus", "kanji": ""},
        "ビ": {"word": "ビール", "reading": "bīru", "meaning": "bir", "kanji": ""},
        "ブ": {"word": "ブドウ", "reading": "budou", "meaning": "anggur", "kanji": ""},
        "ベ": {"word": "ベッド", "reading": "beddo", "meaning": "tempat tidur", "kanji": ""},
        "ボ": {"word": "ボール", "reading": "bōru", "meaning": "bola", "kanji": ""},

        # カタカナ半濁音（パ行）
        "パ": {"word": "パソコン", "reading": "pasokon", "meaning": "komputer", "kanji": ""},
        "ピ": {"word": "ピザ", "reading": "piza", "meaning": "pizza", "kanji": ""},
        "プ": {"word": "プール", "reading": "pūru", "meaning": "kolam renang", "kanji": ""},
        "ペ": {"word": "ペン", "reading": "pen", "meaning": "pulpen", "kanji": ""},
        "ポ": {"word": "ポケット", "reading": "poketto", "meaning": "saku", "kanji": ""}
    }
    default_example = {"word": "", "reading": "", "meaning": "", "kanji": ""}
    return character_examples.get(character, default_example)

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
    parser.add_argument('--test', action='store_true',
                        help='テストモード（数文字のみ処理）')
    parser.add_argument('--test_chars', type=str, default="あいうかきアイウ",
                        help='テストモードで処理する文字（デフォルト: あいうかきアイウ）')
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
    """タスク指示からJSONの構造を抽出する (未使用)"""
    pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, task_content)
    for match in matches:
        try:
            json_obj = json.loads(match)
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
                model="gpt-4o-mini",
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
                retry_delay *= 2
            else:
                logger.error("GPT-4oリクエストの最大試行回数を超えました")
                raise

def extract_json_from_response(response: str) -> Dict:
    """GPT-4oのレスポンスからJSONを抽出する"""
    json_pattern = r"```json\s*([\s\S]*?)\s*```"
    json_match = re.search(json_pattern, response)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSONのパースエラー: {e}")
        logger.debug(f"解析しようとしたJSON文字列: {json_str}")
        raise

def generate_title_and_description_from_task(task):
    # taskにtitleやdescriptionがある場合は優先して使う
    title = task.get("title")
    description = task.get("description")

    if not title:
        word = task.get("kanji", "") or task.get("word", "")
        title = f"{word} の学習カード"

    if not description:
        meaning = task.get("meaning", "")
        description = f"<p>この教材では「{word}」の語彙を視覚的に学習します。意味: {meaning}</p>"

    return title, description

def generate_media_batch(characters: List[str], output_dir: str) -> Dict[str, Dict[str, Optional[str]]]:
    """
    複数の文字の画像と音声ファイルをバッチ生成する。
    - generate_example_image のみを使って文字画像を生成する。
    - example_imagesフォルダは作らず、すべてimagesフォルダに保存する。
    - 例単語用の画像 (ex_...) は生成しない。
    """
    images_dir = os.path.join(output_dir, 'images')
    audio_dir = os.path.join(output_dir, 'audios')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    results = {}
    batch_size = 5

    # 進捗管理ファイル
    progress_file = os.path.join(output_dir, '.media_progress.json')
    processed_chars = {}
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                processed_chars = json.load(f)
            logger.info(f"進捗状態読み込み: {len(processed_chars)}文字が既に処理済み")
        except Exception as e:
            logger.warning(f"進捗ファイル読み込み失敗: {e}")

    # 処理対象絞り込み
    characters_to_process = [c for c in characters if c not in processed_chars]
    logger.info(f"処理対象: {len(characters_to_process)}文字 / 全{len(characters)}文字")

    for i in range(0, len(characters_to_process), batch_size):
        batch = characters_to_process[i:i + batch_size]
        logger.info(
            f"バッチ {i // batch_size + 1} / {(len(characters_to_process) + batch_size - 1) // batch_size} : {batch}"
        )

        for char in batch:
            char_result = {}
            try:
                # 文字タイプ
                is_katakana = (ord(char) >= ord('ア') and ord(char) <= ord('ン'))
                char_type = 'katakana' if is_katakana else 'hiragana'

                # ファイルパス定義（例単語用のex_... は作らない）
                char_img_name = f"char_{char_type}_{char}.png"
                char_img_path = os.path.join(images_dir, char_img_name)

                audio_name = f"{char_type}_{char}.mp3"
                audio_path = os.path.join(audio_dir, audio_name)
                example_info = get_example_word_and_translation(char)
                word = example_info.get('word', '')
                example_reading = example_info.get('reading', '')
                example_meaning = example_info.get('meaning', '')
                kanji = example_info.get('kanji', '')
                kanji_meaning_in_English = example_info.get('kanji_meaning_in_English', '')
                visual_cues = example_info.get('visual_cues', '')

                # --- 文字画像の生成 ---
                if not os.path.exists(char_img_path):
                    logger.info(f"{char} の文字画像(generate_example_image)生成...")
                    success = generate_example_image(
                        word=char,                # word はあえて文字を使う
                        character=char,
                        character_type=char_type,
                        kanji=kanji,
                        visual_cues=visual_cues,
                        kanji_meaning_in_English=kanji_meaning_in_English,
                        output_path=char_img_path,
                        provider="openai"      # 必要に応じて "openai" に変更
                    )
                    if success:
                        char_result['char_image'] = f"images/{char_img_name}"
                    else:
                        char_result['char_image'] = None
                else:
                    logger.info(f"文字画像が既に存在: {char_img_path}")
                    char_result['char_image'] = f"images/{char_img_name}"

                # --- 音声の生成 ---
                if not os.path.exists(audio_path):
                    logger.info(f"{char} の音声ファイルを生成...")
                    success = generate_audio(char, audio_path, include_example=True)
                    if success:
                        char_result['audio'] = f"audios/{audio_name}"
                    else:
                        char_result['audio'] = None
                else:
                    logger.info(f"音声ファイル既存: {audio_path}")
                    char_result['audio'] = f"audio/{audio_name}"

                # 例単語用の画像は作らないので、'example_image' は作らない
                # char_result['example_image'] = None  # 必要なら明示的にNoneを入れてもよい

                # 結果保存
                results[char] = char_result
                processed_chars[char] = char_result

                # 進捗ファイル更新
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(processed_chars, f, ensure_ascii=False, indent=2)

            except Exception as e:
                logger.error(f"{char} メディア生成エラー: {e}")
                results[char] = {
                    'char_image': None,
                    'audio': None
                }

        if i + batch_size < len(characters_to_process):
            logger.info("バッチ完了。少し待機して次のバッチへ...")
            time.sleep(2)

    return results

def main():
    """メイン実行関数"""
    args = parse_arguments()

    # テストモード
    if args.test:
        test_characters = list(args.test_chars)
        logger.info(f"テストモード。文字リスト: {test_characters}")

        content = {
            "title": f"ひらがな・カタカナテスト - {args.lesson_id}",
            "cards": []
        }
        for char in test_characters:
            card = {
                "text": char,
                "answer": f"{char}の読み方・意味など",
                "tip": f"{char}の発音をチェック"
            }
            content["cards"].append(card)

        output_path = save_json_content(
            content,
            args.output_dir,
            args.lesson_id,
            args.content_type
        )
        logger.info(f"テスト用コンテンツ生成完了: {output_path}")
        return

    # 通常モード
    task_content = read_task_file(args.task_file)
    prompt = generate_prompt(task_content, args.content_type, args.lesson_id)

    logger.info(f"GPT-4oにリクエスト送信中...")
    response = call_gpt4o(prompt)

    content_json = extract_json_from_response(response)

    # title/description を task から補完
    if args.content_type == "dialog_cards":
        title, description = generate_title_and_description_from_task(content_json)
        content_json["title"] = title
        content_json["description"] = description

    output_path = save_json_content(
        content_json,
        args.output_dir,
        args.lesson_id,
        args.content_type
    )

    logger.info(f"H5Pコンテンツ生成完了: {output_path}")

if __name__ == "__main__":
    main()
