*

# N5日本語教材プロジェクトのフォルダ構造

```
n5-japanese-course/
│
├── README.md                      # プロジェクト概要
│
├── .github/                       # GitHub設定
│   └── workflows/                 # GitHubワークフロー
│       └── content-generation.yml # コンテンツ自動生成ワークフロー
│
├── tasks/                         # 自動化タスク指示書
│   ├── hiragana-lesson.md         # ひらがな学習タスク
│   ├── katakana-lesson.md         # カタカナ学習タスク
│   └── lesson01-task.md           # 課1タスク
│
├── scripts/                       # 自動化スクリプト
│   ├── generate_content.py        # GPT-4oによるコンテンツ生成
│   ├── json_to_h5p.py             # JSONからH5Pへの変換
│   └── upload_to_moodle.py        # Moodleアップロード
│
├── docs/                          # プロジェクトドキュメント
│   ├── design-doc.md              # 設計概要書
│   ├── issues-roadmap.md        　# 
│   ├── folder-structure.md
│   └── guides/                    # 各種ガイド
│       ├── h5p-template-guide.md  # H5P作成ガイド
│       └── content-checklist.md   # コンテンツチェックリスト
│
├── .github/                       # GitHub設定
│   └── ISSUE_TEMPLATE/            # Issueテンプレート
│       ├── content-development.md # コンテンツ開発テンプレート
│       └── bug-report.md          # バグ報告テンプレート
│
├── src/                           # ソースファイル
│   ├── templates/                 # テンプレートファイル
│   │   ├── dialog-cards/         # Dialog Cards用テンプレート
│   │   ├── course-presentation/  # Course Presentation用テンプレート
│   │   └── quiz/                 # Quiz用テンプレート
│   │
│   ├── content/                   # 各課コンテンツ
│   │   ├── hiragana/             # ひらがな学習コンテンツ
│   │   ├── katakana/             # カタカナ学習コンテンツ
│   │   ├── lesson01/             # 課1コンテンツ
│   │   └── ...                   # 課2〜25
│   │
│   └── common/                    # 共通リソース
│       ├── images/                # 画像素材
│       ├── css/                   # スタイルシート
│       └── js/                    # JavaScriptファイル
│
├── h5p/                           # 完成したH5Pパッケージ
│   ├── hiragana/                  # ひらがな関連H5P
│   ├── katakana/                  # カタカナ関連H5P
│   ├── lesson01/                  # 課1関連H5P
│   └── ...                        # 課2〜25
│
└── moodle/                        # Moodle関連ファイル
    ├── backups/                   # コースバックアップ
    └── import/                    # インポート用ファイル
```

## ファイル命名規則

### H5Pファイル

* 形式: `N5_[セクション]_[コンテンツタイプ]_[詳細].h5p`
* 例: `N5_Hiragana_DialogCards_AIUEO.h5p`

### 画像ファイル

* 形式: `[タイプ]_[セクション]_[詳細].拡張子`
* 例: `char_hiragana_a.png`

### テキストコンテンツ

* 形式: `[タイプ]_[セクション]_[詳細].md`
* 例: `grammar_L01_introduction.md`
