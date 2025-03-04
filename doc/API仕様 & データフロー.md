以下は、**Google Slides APIやHeyGen APIなど動画・スライド生成に関わる部分を省いた**バージョンです。  
前回と同様の構成で必要な要素のみを抜粋・変更しています。

---

## **[暫定]API仕様 & データフロー（動画・スライド生成なし）**
以下に、**APIの設計方針、エンドポイント、データフロー** のドラフトを作成しました。  
最後に **「決定すべき事項」** をまとめているので、そちらを確認しながらご指示ください。

---

## **1. APIの概要**
本システムでは、以下のAPIを使用して、**教材の自動生成・管理・学習進捗の記録を実装** します。

| **APIの種類**          | **主な用途**                   |
|-----------------------|--------------------------------|
| **OCR API**           | PDF画像からテキストを抽出       |
| **GPT-4 API**         | 文法解説・クイズの自動生成       |
| **H5P API (Moodle経由)** | クイズコンテンツの登録・管理    |
| **Moodle API**        | 学習者の成績管理・教材の登録     |

---

## **2. APIエンドポイント一覧**
### **(1) OCR API**
| **メソッド** | **エンドポイント**       | **説明**                         |
|--------------|-------------------------|----------------------------------|
| `POST`       | `/api/ocr/upload`      | PDFをアップロードし、OCR処理を実行 |
| `GET`        | `/api/ocr/result/{document_id}` | OCRの結果を取得                  |

#### **リクエスト例**
```json
{
  "file": "base64_encoded_pdf"
}
```

#### **レスポンス例**
```json
{
  "document_id": "12345",
  "extracted_text": "これはペンです。"
}
```

---

### **(2) GPT-4 API**
| **メソッド** | **エンドポイント**              | **説明**                |
|--------------|--------------------------------|-------------------------|
| `POST`       | `/api/gpt/generate_script`     | 文法解説スクリプトを生成   |
| `POST`       | `/api/gpt/generate_quiz`       | クイズを自動生成         |

#### **リクエスト例**
```json
{
  "input_text": "これはペンです。",
  "grammar_point": "これは～です。",
  "level": "N5"
}
```

#### **レスポンス例**
```json
{
  "grammar_script": "「これは～です」は、物の名前を言う時に使う文法です。",
  "quiz": [
    {
      "type": "multiple_choice",
      "question": "「これはペンです。」の意味は？",
      "options": ["This is a pen.", "That is a book."],
      "answer": "This is a pen."
    }
  ]
}
```

---

### **(3) H5P API (Moodle経由)**
| **メソッド** | **エンドポイント**         | **説明**                       |
|--------------|---------------------------|--------------------------------|
| `POST`       | `/api/h5p/upload`        | H5Pコンテンツをアップロード    |
| `GET`        | `/api/h5p/get/{h5p_id}`  | H5Pコンテンツを取得            |

---

### **(4) Moodle API**
| **メソッド** | **エンドポイント**              | **説明**                 |
|--------------|--------------------------------|--------------------------|
| `POST`       | `/api/moodle/enroll`           | 学習者を登録             |
| `POST`       | `/api/moodle/record_progress`  | 学習進捗を記録           |
| `GET`        | `/api/moodle/get_progress/{user_id}` | 学習進捗を取得         |

---

## **3. データフロー**
### **(1) 教材生成のフロー**
1. **OCR API** にPDFを送信 → **テキストを取得**  
2. **GPT-4 API** に文法ポイントを送信 → **解説スクリプトとクイズを生成**  
3. **H5P API (Moodle経由)** にクイズを送信 → **学習コンテンツとして登録**  
4. **Moodle API** に登録情報を反映し、学習者が利用可能にする  

---

## **4. エラーハンドリング**
- **OCR失敗時** → 画像処理を再試行 or 管理者へ通知  
- **GPT-4のAPI制限エラー** → 自動リトライ or 後で再実行  
- **Moodle API通信失敗** → 直前の処理を再送信  

---

## **5. セキュリティ**
- **認証・認可**:
  - APIアクセスには **APIキーを使用**  
  - **学習者はクイズ結果の取得のみ可能**  
  - **管理者のみ教材の登録・削除が可能**
- **データ保護**:
  - API通信は **HTTPSで暗号化**  
  - **Moodleの成績データは暗号化して保存**

---

## **6. 未決定の要件（確認が必要な項目）**
以下の点について決定が必要です。**確認のうえ、確定したら設計に反映します。**

1. **APIの認証方式**  
   - **APIキー方式 or OAuth2方式** どちらを採用するか？  
   - APIキー方式なら、発行・管理の方法は？

2. **APIのレートリミット**  
   - **1分間に何回までリクエストを許可するか？**  
   - GPT-4 APIなどの制限を考慮する必要がある。

3. **Moodleのデータ保存期間**  
   - 学習者の **クイズ履歴は何年間保持するか？**  
   - **自動削除するか？ それとも管理者が削除するか？**

---

### **🚀 次のステップ**
1. **上記確認事項の決定**（1〜3）  
2. **決定後、API仕様を確定**  
3. **設計書に反映して、開発へ進む**  
