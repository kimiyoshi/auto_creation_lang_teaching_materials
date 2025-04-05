# ひらがな学習コンテンツ開発タスク

## タスク概要

インドネシア人学習者向けのN5レベル「ひらがな学習」H5Pコンテンツを自動生成する。

## 出力要件

1. コンテンツタイプ: Dialog Cards & Course Presentation
2. 対象: インドネシア語を母語とする初心者
3. N5レベル: 基礎的な文字学習
4. 漢字には必ずカッコ書きでルビをふる。難しい漢字は使わない。

## データ構造

### Dialog Cards JSON構造

```json
{
  "title": "ひらがな学習 - 基本（きほん）セット",
　"description":"ひらがなを覚（おぼ）えましょう",
  "cards": [
    {
      "text": "あ",
      "answer": "a - アルファベットの「a」に似（に）た発音（はつおん）",
      "tip": "「a」のように発音（はつおん）します",
      "image": {
        "path": "images/hiragana_a.jpg",
        "width": 300,
        "height": 300,
        "alt": "ひらがなの「あ」"
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

{
"title": "ひらがな - 練習",
"slides": [
{
"elements": [
{
"x": 0,
"y": 0,
"width": 100,
"height": 100,
"type": "text",
"content": "<h2>ひらがな学習</h2><p>日本語の基本文字</p>"
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

## コンテンツ要件

### ひらがなDialog Cards (46文字)

1. あ行 (あ、い、う、え、お)
2. か行 (か、き、く、け、こ)
3. さ行 (さ、し、す、せ、そ)
4. た行 (た、ち、つ、て、と)
5. な行 (な、に、ぬ、ね、の)
6. は行 (は、ひ、ふ、へ、ほ)
7. ま行 (ま、み、む、め、も)
8. や行 (や、ゆ、よ)
9. ら行 (ら、り、る、れ、ろ)
10. わをん (わ、を、ん)
11. 濁音 (が、ぎ、ぐ、げ、ご など)
12. 半濁音 (ぱ、ぴ、ぷ、ぺ、ぽ)

### 各カードの内容

* 表面: ひらがな1文字
* 裏面: ローマ字表記と簡単な発音説明
* ヒント: インドネシア語の類似音との比較
* 画像: 筆順を示す図（オプション）

### Course Presentation内容

1. 導入: ひらがなの概要と歴史
2. 五十音図の説明
3. 母音(あ行)の詳細解説と筆順
4. 子音+母音の仕組み
5. グループごとの筆順練習
6. 発音のコツとインドネシア語との比較
7. 簡単な単語作成練習
8. 確認クイズ
9. まとめと次のステップ

## インドネシア人学習者向け特別配慮

1. インドネシア語の発音体系と比較した説明
2. 日本語固有の音（長音、促音など）の丁寧な解説
3. インドネシア語話者が混同しやすい音の区別（例: らとだ）
4. 文化的な要素を取り入れた例単語

## 生成指示

* Dialog Cardsは五十音順に整理
* Course Presentationは論理的な学習順序で構成
* インドネシア語と日本語の対比を入れる
* 例単語はN5レベルで、インドネシア文化に関連するものも含める

## 参考情報

* ひらがな一覧: https://www.nhk.or.jp/lesson/en/letters/hiragana.html
* 筆順: https://kakijun.jp/
* インドネシア語と日本語の発音比較: https://www.wasabi-jpn.com/japanese-lessons/similarities-and-differences-between-japanese-and-indonesian/
