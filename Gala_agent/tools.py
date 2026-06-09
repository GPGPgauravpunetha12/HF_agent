# tools.py

import os
import subprocess
import requests
import pandas as pd
import base64
import sys

from PIL import Image
from pypdf import PdfReader
from huggingface_hub import HfApi
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import observe
from retriever import bm25_retriever

# ==========================================================
# Optional Imports
# ==========================================================

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from ddgs import DDGS

# ==========================================================
# Lazy Whisper Loader
# ==========================================================

_whisper_model = None


def get_whisper_model():
    global _whisper_model

    if WhisperModel is None:
        raise ImportError(
            "faster-whisper is not installed"
        )

    if _whisper_model is None:
        _whisper_model = WhisperModel(
            "base",
            device="cpu"
        )

    return _whisper_model


# ==========================================================
# Lazy Vision Loader
# ==========================================================

_vision_llm = None

def get_vision_llm():
    global _vision_llm
    if _vision_llm is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        _vision_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
        )
    return _vision_llm


# ==========================================================
# Web Search
# ==========================================================
# ==========================================================
# Webpage Scraper & Parser
# ==========================================================

from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.ignore = False

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style", "header", "footer", "nav", "aside", "iframe", "noscript"]:
            self.ignore = True

    def handle_endtag(self, tag):
        if tag in ["script", "style", "header", "footer", "nav", "aside", "iframe", "noscript"]:
            self.ignore = False

    def handle_data(self, data):
        if not self.ignore:
            text = data.strip()
            if text:
                text = " ".join(text.split())
                self.result.append(text)

    def get_text(self):
        return "\n".join(self.result)


def scrape_url(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        if response.encoding is None or response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding

        html = response.text
        parser = HTMLTextExtractor()
        parser.feed(html)
        text = parser.get_text()

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)[:8000]
    except Exception as e:
        return f"Scrape failed: {e}"


@tool
def webpage_reader_tool(url: str) -> str:
    """
    Scrape and extract main text content from a webpage URL.
    """
    return scrape_url(url)


# ==========================================================
# Wikipedia Search
# ==========================================================

def search_wikipedia(query: str) -> str:
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 2
        }
        res = requests.get(search_url, params=search_params, timeout=5)
        res.raise_for_status()
        search_results = res.json().get("query", {}).get("search", [])

        if not search_results:
            return ""

        outputs = []
        for item in search_results:
            title = item.get("title")
            extract_params = {
                "action": "query",
                "prop": "extracts",
                "explaintext": True,
                "titles": title,
                "format": "json",
                "exintro": True
            }
            ex_res = requests.get(search_url, params=extract_params, timeout=5)
            ex_res.raise_for_status()
            pages = ex_res.json().get("query", {}).get("pages", {})
            page_id = next(iter(pages))
            extract = pages[page_id].get("extract", "")
            if extract:
                outputs.append(f"Wikipedia Page: {title}\nSummary:\n{extract}")

        return "\n\n---\n\n".join(outputs)
    except Exception as e:
        return f"Wikipedia search failed: {e}"


# ==========================================================
# Web Search (Wikipedia + DDGS Snippets)
# ==========================================================

@observe(
    as_type="span",
    name="duckduckgo_search"
)
def _execute_web_search(query: str) -> str:
    wiki_result = search_wikipedia(query)

    ddgs_result = ""
    if DDGS is not None:
        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(
                        query,
                        max_results=5
                    )
                )

            if results:
                output = []
                for result in results:
                    title = result.get("title", "No Title")
                    url = result.get("href") or result.get("url") or "No URL"
                    snippet = result.get("body") or result.get("snippet") or ""
                    output.append(
                        f"Title: {title}\n"
                        f"URL: {url}\n"
                        f"Snippet: {snippet}"
                    )
                ddgs_result = "\n\n---\n\n".join(output)
            else:
                ddgs_result = "No search results found."
        except Exception as e:
            ddgs_result = f"Search failed: {e}"
    else:
        ddgs_result = "DuckDuckGo package not installed."

    combined_results = []
    if wiki_result:
        combined_results.append(f"=== WIKIPEDIA SEARCH RESULTS ===\n{wiki_result}")
    if ddgs_result:
        combined_results.append(f"=== WEB SEARCH RESULTS ===\n{ddgs_result}")

    return "\n\n=================================\n\n".join(combined_results) if combined_results else "No results found."


@tool
def web_search_tool(query: str) -> str:
    """
    Search the web for current information. Returns a combination of Wikipedia entries and search engine snippets.
    """
    return _execute_web_search(query)

@tool
def tavily_search_tool(query: str) -> str:
    """Search the web using Tavily API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "TAVILY_API_KEY not set in environment."
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": 5},
            headers={"x-api-key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return "No results found."
        output = []
        for r in results:
            title = r.get("title", "No Title")
            url = r.get("url", "")
            snippet = r.get("content", "")
            output.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")
        return "\n\n---\n\n".join(output)
    except Exception as e:
        return f"Tavily search failed: {e}"



# ==========================================================
# Guest Information Retriever
# ==========================================================

@tool
def guest_info_tool(query: str) -> str:
    """
    Retrieve guest information.
    """

    try:

        documents = bm25_retriever.invoke(query)

        if not documents:
            return (
                "No matching guest found."
            )

        return "\n\n".join(
            doc.page_content
            for doc in documents[:3]
        )

    except Exception as e:
        return (
            f"Retriever error: {e}"
        )


# ==========================================================
# Weather Tool
# ==========================================================

@tool
def weather_info_tool(location: str) -> str:
    """
    Get current weather.
    """

    try:

        headers = {
            "User-Agent":
            "LangGraph-Agent"
        }

        geo_url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={location}"
            "&format=json"
            "&limit=1"
        )

        geo_response = requests.get(
            geo_url,
            headers=headers,
            timeout=10
        )

        geo_response.raise_for_status()

        geo_data = geo_response.json()

        if not geo_data:
            return (
                f"Location not found: "
                f"{location}"
            )

        latitude = geo_data[0]["lat"]
        longitude = geo_data[0]["lon"]

        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current_weather=true"
        )

        weather_response = requests.get(
            weather_url,
            timeout=10
        )

        weather_response.raise_for_status()

        weather_data = (
            weather_response.json()
        )

        current = weather_data.get(
            "current_weather"
        )

        if not current:
            return (
                "Weather data unavailable."
            )

        return (
            f"Temperature: "
            f"{current['temperature']}°C\n"
            f"Wind Speed: "
            f"{current['windspeed']} km/h"
        )

    except Exception as e:
        return (
            f"Weather lookup failed: {e}"
        )


# ==========================================================
# Hugging Face Hub Stats
# ==========================================================

@tool
def hub_stats_tool(author: str) -> str:
    """
    Return top downloaded HF model.
    """

    try:
        api = HfApi()

        models = list(
            api.list_models(
                author=author,
                sort="downloads",
                limit=5,
            )
        )

        print(f"DEBUG author={author}")
        print(f"DEBUG models found={len(models)}")

        for m in models:
            m_id = getattr(m, 'id', None) or getattr(m, 'modelId', None)
            m_downloads = getattr(m, 'downloads', None)
            print(f"id={m_id} downloads={m_downloads}")

        if not models:
            return (
                f"No models found "
                f"for {author}"
            )

        model = max(models, key=lambda m: getattr(m, 'downloads', 0) or 0)

        model_id = (
            getattr(model, "id", None)
            or getattr(
                model,
                "modelId",
                "Unknown"
            )
        )

        return (
            f"Model: {model_id}\n"
            f"Downloads: "
            f"{getattr(model, 'downloads', 'N/A')}\n"
            f"Likes: "
            f"{getattr(model, 'likes', 'N/A')}"
        )

    except Exception as e:
        print("DEBUG HF HUB ERROR:", e)
        import traceback
        traceback.print_exc()
        return (
            f"HF Hub error: {e}"
        )


# ==========================================================
# News Tool
# ==========================================================

@tool
def latest_news_tool(topic: str) -> str:
    """
    Fetch latest news.
    """

    return _execute_web_search(
        f"latest news about {topic}"
    )

# ==========================================================
# YouTube Transcript Tool
# ==========================================================

@tool
def youtube_transcript_tool(
    video_input: str,
    max_chars: int = 15000,
) -> str:
    """Retrieve YouTube transcript."""

    def extract_id(inp: str) -> str:
        if inp.startswith("http"):
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(inp)

            if parsed.netloc.endswith("youtu.be"):
                return parsed.path.lstrip("/")

            qs = parse_qs(parsed.query)

            if "v" in qs:
                return qs["v"][0]

            parts = parsed.path.split("/")

            if parts:
                return parts[-1]

            return inp

        return inp

    if YouTubeTranscriptApi is None:
        return "youtube-transcript-api not installed."

    video_id = extract_id(video_input)

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        text = " ".join(
            item["text"]
            for item in transcript
        )

        return text[:max_chars]

    except Exception as e:
        return f"Transcript unavailable: {e}"


# ==========================================================
# Image Tool
# ==========================================================

@tool
def image_info_tool(filepath: str) -> str:
    """
    Return image metadata and describe the contents of the image file.
    """

    try:

        img = Image.open(filepath)

        metadata = (
            f"Width={img.width}\n"
            f"Height={img.height}\n"
            f"Mode={img.mode}"
        )

        with open(filepath, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")
        
        ext = filepath.split(".")[-1].lower()
        mime_type = "image/png"
        if ext in ["jpg", "jpeg"]:
            mime_type = "image/jpeg"
        elif ext == "webp":
            mime_type = "image/webp"

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return f"Metadata:\n{metadata}\n\n(Vision unavailable: GOOGLE_API_KEY not set)"
            
        vision_llm = get_vision_llm()
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Describe this image in detail. Be very specific about any text, numbers, graphs, or objects visible."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"},
                },
            ]
        )
        description = vision_llm.invoke([message]).content
        return f"Metadata:\n{metadata}\n\nDescription:\n{description}"

    except Exception as e:
        return (
            f"Image read failed: {e}"
        )


# ==========================================================
# Audio Transcription Tool
# ==========================================================

@tool
def audio_transcriber_tool(
    filepath: str
) -> str:
    """
    Transcribe audio.
    """

    try:

        model = get_whisper_model()

        segments, _ = model.transcribe(
            filepath
        )

        text = " ".join(
            segment.text
            for segment in segments
        )

        return text

    except Exception as e:
        return (
            f"Transcription failed: {e}"
        )


# ==========================================================
# Python Executor Tool
# ==========================================================

@tool
def python_executor_tool(
    filepath: str
) -> str:
    """
    Execute Python file.
    """

    try:

        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=15,
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]:\n{result.stderr}"
        return output.strip() or "(no output)"

    except subprocess.TimeoutExpired:
        return "Execution timed out after 15 seconds."
    except Exception as e:
        return (
            f"Execution failed: {e}"
        )
# ==========================================================
# Excel Reader Tool
# ==========================================================

@tool
def excel_reader_tool(
    filepath: str,
    max_rows: int = 50,
) -> str:
    """
    Read Excel file.
    """

    import tempfile
    from pathlib import Path

    try:

        if filepath.startswith("http://") or filepath.startswith("https://"):

            response = requests.get(
                filepath,
                timeout=15
            )

            response.raise_for_status()

            suffix = (
                Path(filepath).suffix
                or ".xlsx"
            )

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as tmp:

                tmp.write(response.content)

                local_path = tmp.name

        else:
            local_path = filepath

        sheets = pd.read_excel(
            local_path,
            sheet_name=None
        )

        output = []

        for name, df in sheets.items():

            row_count = len(df)

            preview = df.head(max_rows)

            warning = ""

            if row_count > max_rows:
                warning = (
                    f"\n[WARNING: Showing only first "
                    f"{max_rows} rows of {row_count}]"
                )

            output.append(
                f"Sheet: {name}\n"
                f"{preview.to_string(index=False)}"
                f"{warning}"
            )

        return "\n\n".join(output)

    except Exception as e:
        return f"Excel read failed: {e}"


# ==========================================================
# PDF Reader Tool
# ==========================================================

@tool
def pdf_reader_tool(
    filepath: str
) -> str:
    """
    Extract PDF text.
    """

    try:

        reader = PdfReader(filepath)

        text = []

        for page in reader.pages:

            text.append(
                page.extract_text() or ""
            )

        full_text = "\n".join(text)
        if len(full_text) > 15000:
            return full_text[:15000] + "\n\n[WARNING: Document truncated at 15000 characters]"
        return full_text

    except Exception as e:
        return (
            f"PDF read failed: {e}"
        )


# ==========================================================
# GAIA File Downloader
# ==========================================================

BASE_URL = (
    "https://agents-course-unit4-scoring.hf.space"
)


@tool
def download_file_tool(
    task_id: str
) -> str:
    """
    Download a GAIA task file.
    """

    try:
        from gaia_client import download_task_file

        filepath = download_task_file(task_id)
        if not filepath:
            return f"Download failed: no file available for task {task_id}"

        try:
            from supabase_gaia import upload_gaia_file

            upload_gaia_file(task_id, filepath, file_name=os.path.basename(filepath))
        except Exception:
            pass

        return filepath

    except Exception as e:
        return (
            f"Download failed: {e}"
        )


def _analyze_local_file(filepath: str) -> str:
    from pathlib import Path
    ext = Path(filepath).suffix.lower()

    try:
        if ext == ".pdf":
            content = pdf_reader_tool.invoke({"filepath": filepath})
            return f"File Type: PDF\nPath: {filepath}\nContent:\n{content}"

        elif ext in [".xlsx", ".xls"]:
            content = excel_reader_tool.invoke({"filepath": filepath})
            return f"File Type: Excel\nPath: {filepath}\nContent:\n{content}"

        elif ext in [".mp3", ".wav", ".m4a"]:
            content = audio_transcriber_tool.invoke({"filepath": filepath})
            return f"File Type: Audio\nPath: {filepath}\nContent:\n{content}"

        elif ext == ".py":
            content = python_executor_tool.invoke({"filepath": filepath})
            return f"File Type: Python Script\nPath: {filepath}\nExecution Output:\n{content}"

        elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
            content = image_info_tool.invoke({"filepath": filepath})
            return f"File Type: Image\nPath: {filepath}\nMetadata:\n{content}"

        elif ext in [".txt", ".csv"]:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(15000)
            truncated = "(truncated)" if len(content) == 15000 else ""
            return f"File Type: Text/CSV\nPath: {filepath}\nContent:\n{content}{truncated}"

        else:
            return f"Downloaded file at {filepath} with unsupported extension '{ext}'."

    except Exception as e:
        return f"Error analyzing file {filepath} (extension {ext}): {e}"


@tool
def analyze_file_tool(task_id: str) -> str:
    """
    Given a GAIA task_id, automatically download the associated file,
    detect its file type/extension, execute the correct reader or analysis tool,
    and return the contents.
    """
    # 1. Download the file
    filepath = download_file_tool.invoke({"task_id": task_id})

    # If download failed
    if "failed" in filepath.lower() or not os.path.exists(filepath):
        return f"Could not analyze file: {filepath}"

    # 2. Extract extension and route
    return _analyze_local_file(filepath)


@tool
def analyze_url_file_tool(url: str) -> str:
    """
    Download a file from a direct URL, detect its type, and return its contents.
    Useful when a task provides a link to a file rather than a task_id.
    """
    import tempfile

    try:
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0"
        })
        response.raise_for_status()

        # Detect extension from URL or Content-Disposition
        content_disp = response.headers.get("content-disposition", "")
        if "filename=" in content_disp:
            filename = content_disp.split("filename=")[1].strip('"')
        else:
            filename = url.split("?")[0].split("/")[-1] or "file.bin"

        os.makedirs("downloads", exist_ok=True)
        filepath = os.path.join("downloads", filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        return _analyze_local_file(filepath)
    except Exception as e:
        return f"URL file analysis failed: {e}"