# test_tools.py

import os
import traceback

from tools import (
    web_search_tool,
    weather_info_tool,
    hub_stats_tool,
    guest_info_tool,
    latest_news_tool,
    youtube_transcript_tool,
    image_info_tool,
    audio_transcriber_tool,
    python_executor_tool,
    excel_reader_tool,
    pdf_reader_tool,
)

# =====================================================
# Helper
# =====================================================

def run_test(test_name, tool_func, params):
    print("\n" + "=" * 80)
    print(f"🧪 TEST: {test_name}")
    print("=" * 80)

    try:
        result = tool_func.invoke(params)

        print("✅ PASS")
        print("\nResult:")
        print("-" * 80)
        print(str(result)[:2000])
        print("-" * 80)

    except Exception as e:
        print("❌ FAIL")
        print(f"Error: {e}")
        traceback.print_exc()


# =====================================================
# File Existence Helper
# =====================================================

def file_exists(filepath):
    if not os.path.exists(filepath):
        print(f"⚠️ Skipping test. File not found: {filepath}")
        return False
    return True


# =====================================================
# Main
# =====================================================

if __name__ == "__main__":

    print("\n🚀 Starting Tool Tests")
    print("=" * 80)

    # =================================================
    # Web Search
    # =================================================

    run_test(
        "Web Search",
        web_search_tool,
        {
            "query": "Who is Ada Lovelace"
        }
    )

    # =================================================
    # Weather
    # =================================================

    run_test(
        "Weather",
        weather_info_tool,
        {
            "location": "Pune"
        }
    )

    # =================================================
    # Hugging Face Hub
    # =================================================

    run_test(
        "HF Hub Stats",
        hub_stats_tool,
        {
            "author": "Qwen"
        }
    )

    # =================================================
    # Guest Retriever
    # =================================================

    run_test(
        "Guest Retriever",
        guest_info_tool,
        {
            "query": "Ada Lovelace"
        }
    )

    # =================================================
    # Latest News
    # =================================================

    run_test(
        "Latest News",
        latest_news_tool,
        {
            "topic": "Artificial Intelligence"
        }
    )

    # =================================================
    # YouTube Transcript
    # =================================================

    run_test(
        "YouTube Transcript",
        youtube_transcript_tool,
        {
            "video_id": "dQw4w9WgXcQ"
        }
    )

    # =================================================
    # PDF Reader
    # =================================================

    pdf_file = "test_data/sample.pdf"

    if file_exists(pdf_file):
        run_test(
            "PDF Reader",
            pdf_reader_tool,
            {
                "filepath": pdf_file
            }
        )

    # =================================================
    # Excel Reader
    # =================================================

    excel_file = "test_data/sample.xlsx"

    if file_exists(excel_file):
        run_test(
            "Excel Reader",
            excel_reader_tool,
            {
                "filepath": excel_file
            }
        )

    # =================================================
    # Image Tool
    # =================================================

    image_file = "test_data/sample.png"

    if file_exists(image_file):
        run_test(
            "Image Tool",
            image_info_tool,
            {
                "filepath": image_file
            }
        )

    # =================================================
    # Audio Tool
    # =================================================

    audio_file = "test_data/sample.mp3"

    if file_exists(audio_file):
        run_test(
            "Audio Transcriber",
            audio_transcriber_tool,
            {
                "filepath": audio_file
            }
        )

    # =================================================
    # Python Executor
    # =================================================

    python_file = "test_data/hello.py"

    if file_exists(python_file):
        run_test(
            "Python Executor",
            python_executor_tool,
            {
                "filepath": python_file
            }
        )

    print("\n" + "=" * 80)
    print("🎉 ALL TOOL TESTS COMPLETED")
    print("=" * 80)