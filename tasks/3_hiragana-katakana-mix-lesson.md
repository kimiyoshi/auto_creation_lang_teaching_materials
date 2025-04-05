# ひらがな・カタカナ混合練習コンテンツ開発タスク

## タスク概要

インドネシア人学習者向けのN5レベル「ひらがな・カタカナ混合練習」H5Pコンテンツを自動生成する。ひらがな学習とカタカナ学習の後に行う統合練習。

## 出力要件

1. コンテンツタイプ: Multiple Choice, Fill in the Blanks, Course Presentation
2. 対象: インドネシア語を母語とする初心者（ひらがな・カタカナ基本学習後）
3. N5レベル: 基礎的な文字の識別と簡単な文の読み

## データ構造

### Multiple Choice JSON構造

```json
{
  "title": "ひらがな・カタカナ識別クイズ",
  "questions": [
    {
      "text": "次の文字はどちらですか？「あ」",
      "answers": [
        {"text": "ひらがな", "correct": true},
        {"text": "カタカナ", "correct": false}
      ],
      "singleAnswer": true,
      "feedback": {
        "correct": "正解です！「あ」はひらがなです。カタカナでは「ア」と書きます。",
        "incorrect": "不正解です。「あ」はひらがなです。カタカナでは「ア」と書きます。"
      }
    },
    // 他の問題も同様の形式で...
  ],
  "behaviour": {
    "enableRetry": true,
    "randomizeQuestions": true,
    "showSolutionsRequiresInput": true
  }
}
```

### Fill in the Blanks JSON構造

```json
{
  "title": "ひらがな・カタカナ変換練習",
  "questions": [
    {
      "text": "ひらがな「あいうえお」をカタカナで書くと *アイウエオ* です。",
      "hint": "ひらがなとカタカナは発音が同じです"
    },
    // 他の問題も同様の形式で...
  ],
  "behaviour": {
    "caseSensitive": false,
    "showSolutions": true
  }
}
```

### Course Presentation JSON構造

```json
{
  "title": "ひらがな・カタカナ混合音読練習",
　"description":"ひらがなを覚（おぼ）えましょう",
  "slides": [
    {
      "elements": [
        {
          "x": 0,
          "y": 0,
          "width": 100,
          "height": 100,
          "type": "text",
          "content": "<h2>ひらがな・カタカナ混合練習</h2><p>日本語の実際の表記に慣れよう</p>"
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

### ひらがな・カタカナ識別クイズ

1. 単一文字の識別（ひらがなかカタカナか）
2. 似た形の文字ペア識別（あ/ア、き/キ、さ/サなど）
3. 単語中の文字種識別（りんご、コーヒーなど）
4. 混合文の中での識別

### ひらがな⇔カタカナ変換練習

1. ひらがな→カタカナ変換
2. カタカナ→ひらがな変換
3. 単語レベルの変換
4. 短文レベルの変換

### 音読練習（Course Presentation）

1. ひらがな・カタカナが混在する実際の日本語テキスト
2. 外来語を含む簡単な文
3. 日常生活で見かける表示や標識
4. インドネシア関連の内容を含む短い文章

### 読解練習の文章例

1. 「わたしは マイク です。インドネシア から きました。」
2. 「これは カメラ です。デジタルカメラ です。」
3. 「ジャカルタ は インドネシア の とうきょう です。」
4. 「コーヒー と ケーキ を ください。」
5. 「バス は ステーション に とまります。」

## インドネシア人学習者向け特別配慮

1. インドネシア語由来のカタカナ語を積極的に使用
2. インドネシアの地名や食べ物を文例に入れる
3. 観光や買い物など、訪日インドネシア人に有用な表現
4. ローマ字読みとの比較（つ/ツ → tsu など）

## 生成指示

* 簡単な内容から徐々に難しくする構成
* 識別クイズは視覚的に判別しやすい提示方法
* 変換練習は実用的な単語や表現を使用
* 音読練習はN5レベルの語彙・文法に限定

## インドネシア人向け特化単語例

1. ナシゴレン、サテ、テンペ（インドネシア料理）
2. バリ、ジャカルタ、スラバヤ（地名）
3. ラーメン、すし、てんぷら（日本食）
4. コンビニ、レストラン、ホテル（観光関連）
5. アニメ、マンガ、カラオケ（文化関連）

## 学習目標

1. ひらがなとカタカナを瞬時に区別できる
2. 両方の文字が混在する文を正確に読める
3. 適切な場面でひらがな・カタカナを使い分けられる
4. 日本の日常生活で見かける表記に慣れる

## 参考情報

* 日本語の実際の表記例: https://www.japan-guide.com/e/e2047.html
* 日本の公共表示: https://www.jnto.go.jp/eng/basic-info/emergency-info/sign.html
* 外来語リスト: https://www.tofugu.com/japanese/japanese-loan-words/
* インドネシア語と日本語のバイリンガル例: https://www.wasabi-jpn.com/japanese-lessons/japanese-vocabulary-with-indonesian-translations/
