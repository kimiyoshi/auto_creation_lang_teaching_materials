# カタカナ学習コンテンツ開発タスク

## タスク概要

インドネシア人学習者向けのN5レベル「カタカナ学習」H5Pコンテンツを自動生成する。

## 出力要件

1. コンテンツタイプ: Dialog Cards & Course Presentation
2. 対象: インドネシア語を母語とする初心者（ひらがな学習後）
3. N5レベル: 基礎的な文字学習

## データ構造

### Dialog Cards JSON構造

```json
{
  "title": "カタカナ学習 - 基本セット",
  "cards": [
    {
      "text": "ア",
      "answer": "a - ひらがなの「あ」と同じ発音",
      "tip": "「あ」との形の違いに注目",
      "image": {
        "path": "images/katakana_a.jpg",
        "width": 300,
        "height": 300,
        "alt": "カタカナの「ア」"
      }
    },
    // 他のカードも同様の形式で...
  ],
  "behaviour": {
    "enableRetry": true,
    "disableBackwards": false,
    "scaleTextNotCard": false,
    "textAlignment": "center",
    "defaultAnswerText": "裏面を見る",
    "defaultExplanationText": "詳細"
  }
}
```

### Course Presentation JSON構造

```json
{
  "title": "カタカナ - 筆順と外来語",
  "slides": [
    {
      "elements": [
        {
          "x": 0,
          "y": 0,
          "width": 100,
          "height": 100,
          "type": "text",
          "content": "<h2>カタカナ学習</h2><p>外来語と外国の名前に使われる文字</p>"
        }
      ],
      "keywords": ["導入", "はじめに"]
    },
    // 他のスライドも同様の形式で...
  ],
  "display": {
    "showTitleScreen": true,
    "showProgressBar": true,
    "showTableOfContents": true
  }
}
```

## コンテンツ要件

### カタカナDialog Cards (46文字)

1. ア行 (ア、イ、ウ、エ、オ)
2. カ行 (カ、キ、ク、ケ、コ)
3. サ行 (サ、シ、ス、セ、ソ)
4. タ行 (タ、チ、ツ、テ、ト)
5. ナ行 (ナ、ニ、ヌ、ネ、ノ)
6. ハ行 (ハ、ヒ、フ、ヘ、ホ)
7. マ行 (マ、ミ、ム、メ、モ)
8. ヤ行 (ヤ、ユ、ヨ)
9. ラ行 (ラ、リ、ル、レ、ロ)
10. ワヲン (ワ、ヲ、ン)
11. 濁音 (ガ、ギ、グ、ゲ、ゴ など)
12. 半濁音 (パ、ピ、プ、ペ、ポ)
13. 特殊音 (ファ、フィ、フェ、フォ、ヴァなど)

### 各カードの内容

* 表面: カタカナ1文字
* 裏面: ローマ字表記と対応するひらがな
* ヒント: ひらがなとの形の違い
* 画像: 筆順を示す図（オプション）

### Course Presentation内容

1. 導入: カタカナの概要と用途
2. ひらがなとカタカナの使い分け
3. 五十音図（カタカナ版）
4. 各行の詳細解説と筆順
5. ひらがなとカタカナの形の比較
6. 外来語の表記規則
7. インドネシア語からの外来語例
8. 外国の地名・人名の表記
9. 特殊音（ファ、ヴァなど）の説明
10. 練習問題と確認クイズ
11. まとめと応用

## インドネシア人学習者向け特別配慮

1. インドネシア語の外来語とカタカナ表記の対比
2. インドネシアの地名・人名のカタカナ表記例
3. インドネシアで一般的なブランド名や商品名のカタカナ表記
4. 長音記号(ー)の使い方の丁寧な説明

## 生成指示

* Dialog Cardsは五十音順に整理
* ひらがな学習との連続性を意識
* インドネシア関連の外来語を多く含める
* 形が似ているカタカナとひらがなの違いを強調

## 実用的な例単語

1. インドネシア関連: ジャカルタ、バリ、ナシゴレン、テンペ
2. 国際的ブランド: コカコーラ、トヨタ、サムスン
3. 日常的外来語: コンピューター、スマートフォン、カメラ
4. 食べ物・飲み物: コーヒー、ジュース、パン
5. インドネシア人名例: スカルノ、ジョコ・ウィドド

## 参考情報

* カタカナ一覧: https://www.nhk.or.jp/lesson/en/letters/katakana.html
* 筆順: https://kakijun.jp/
* 外来語表記の規則: https://www.bunka.go.jp/kokugo\_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/
* インドネシア語と日本語の外来語比較: https://www.wasabi-jpn.com/japanese-lessons/loan-words-in-japanese-and-indonesian/
