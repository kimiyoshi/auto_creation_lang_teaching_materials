import subprocess
import argparse
import os
from pathlib import Path
from datetime import datetime

def run_generate_content(content_type, task_file, lesson_id, output_dir, test=False, test_chars=None):
    cmd = [
        "python", "generate_content.py",
        "--lesson_id", lesson_id,
        "--content_type", content_type,
        "--task_file", task_file,
        "--output_dir", output_dir,
    ]
    if test:
        cmd.append("--test")
        if test_chars:
            cmd.extend(["--test_chars", test_chars])
    subprocess.run(cmd, check=True)

def run_json_to_h5p(input_dir, h5p_output_dir, templates_dir="../src/templates"):
    cmd = [
        "python", "json_to_h5p.py",
        "--input_dir", input_dir,
        "--output_dir", h5p_output_dir,
        "--templates_dir", templates_dir
    ]
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="Run generate_content.py and json_to_h5p.py in sequence.")
    parser.add_argument("--content_type", required=True, help="例: dialog_cards")
    parser.add_argument("--task_file", required=True, help="例: tasks/test.md")
    parser.add_argument("--templates_dir", default="../src/templates")
    parser.add_argument("--h5p_output_dir", default="h5p_output", help="H5P出力フォルダ（共通保存先）")
    parser.add_argument("--test", action="store_true", help="テストモード")
    parser.add_argument("--test_chars", type=str, help="テスト用文字")

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lesson_id = f"lesson_{timestamp}"
    working_dir = Path("src/content") / f"content_{timestamp}"
    working_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Step 1: Generating JSON content (lesson_id: {lesson_id}) ===")
    run_generate_content(
        content_type=args.content_type,
        task_file=args.task_file,
        lesson_id=lesson_id,
        output_dir=str(working_dir),
        test=args.test,
        test_chars=args.test_chars
    )

    print(f"=== Step 2: Converting JSON to H5P ===")
    h5p_output_dir = Path(args.h5p_output_dir).resolve()
    h5p_output_dir.mkdir(parents=True, exist_ok=True)

    run_json_to_h5p(
        input_dir=str(working_dir),
        h5p_output_dir=str(h5p_output_dir),
        templates_dir=args.templates_dir
    )

    print(f"✅ Done! H5P saved to: {h5p_output_dir}")
    print(f"📁 Intermediate files are in: {working_dir}")

if __name__ == "__main__":
    main()
