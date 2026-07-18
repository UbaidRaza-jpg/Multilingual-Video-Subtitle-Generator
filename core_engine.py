import os
import sys
import subprocess
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Delay importing heavier packages until they are actually needed
# to ensure faster imports and check dependency presence safely.

def format_time(seconds: float) -> str:
    """
    Format time in seconds to SRT time format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    if milliseconds == 1000:
        secs += 1
        milliseconds = 0
    if secs == 60:
        minutes += 1
        secs = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def get_ffmpeg_subtitles_filter_path(srt_path: str) -> str:
    """
    Format the subtitle file path to be safe for FFmpeg's subtitles filter.
    Handles Windows path separators and drive letters.
    """
    abs_path = os.path.abspath(srt_path)
    # Replace backslashes with forward slashes
    path_with_slashes = abs_path.replace("\\", "/")
    # Escape colon for Windows drive letters (e.g. C:/... -> C\:/...)
    if len(path_with_slashes) > 1 and path_with_slashes[1] == ':':
        path_with_slashes = path_with_slashes[0] + "\\:" + path_with_slashes[2:]
    # Escape single quotes for the FFmpeg filter
    escaped_path = path_with_slashes.replace("'", "'\\\\''")
    return f"subtitles='{escaped_path}'"


def transcribe_video(video_path: str, output_srt_path: str, model_size: str = "small", segmentation_mode: str = "line_by_line") -> bool:
    """
    Transcribe audio from video_path and save to output_srt_path using faster-whisper.
    """
    print(f"Loading faster-whisper model ({model_size})...")
    from faster_whisper import WhisperModel
    
    # cpu is the default device, int8 compute type is optimized for CPU inference
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print(f"Transcribing {video_path} (segmentation: {segmentation_mode})...")
    segments, info = model.transcribe(video_path, beam_size=5, word_timestamps=True)
    
    # We must consume the generator to transcribe
    segments = list(segments)
    
    print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
    print(f"Writing raw transcript to {output_srt_path}...")
    
    with open(output_srt_path, "w", encoding="utf-8") as f:
        idx = 1
        for segment in segments:
            if segmentation_mode == "word_by_word":
                if segment.words:
                    for w in segment.words:
                        start = format_time(w.start)
                        end = format_time(w.end)
                        text = w.word.strip()
                        if text:
                            f.write(f"{idx}\n")
                            f.write(f"{start} --> {end}\n")
                            f.write(f"{text}\n\n")
                            idx += 1
                else:
                    # Fallback
                    start = format_time(segment.start)
                    end = format_time(segment.end)
                    text = segment.text.strip().replace("\n", " ").replace("\r", "")
                    if text:
                        f.write(f"{idx}\n")
                        f.write(f"{start} --> {end}\n")
                        f.write(f"{text}\n\n")
                        idx += 1
            else:
                # line_by_line
                start = format_time(segment.start)
                end = format_time(segment.end)
                text = segment.text.strip().replace("\n", " ").replace("\r", "")
                if text:
                    f.write(f"{idx}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{text}\n\n")
                    idx += 1
            
    return True


def parse_srt(srt_path: str) -> List[Dict[str, str]]:
    """
    Parse an SRT file into a list of subtitle blocks.
    """
    if not os.path.exists(srt_path):
        return []
        
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    content = content.replace("\r\n", "\n")
    raw_blocks = content.strip().split("\n\n")
    blocks = []
    
    for block in raw_blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text = "\n".join(lines[2:])
            blocks.append({
                "index": index,
                "timestamp": timestamp,
                "text": text
            })
    return blocks


def write_srt(blocks: List[Dict[str, str]], srt_path: str):
    """
    Write a list of subtitle blocks back to an SRT file.
    """
    with open(srt_path, "w", encoding="utf-8") as f:
        for block in blocks:
            f.write(f"{block['index']}\n")
            f.write(f"{block['timestamp']}\n")
            f.write(f"{block['text']}\n\n")


def translate_texts_deepl(texts: List[str], target_lang: str, api_key: str) -> List[str]:
    """
    Translate list of texts using the official DeepL API.
    """
    lang = target_lang.upper()
    if lang == "EN":
        lang = "EN-US"
    elif lang == "PT":
        lang = "PT-PT"
    
    url = "https://api-free.deepl.com/v2/translate" if api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": texts,
        "target_lang": lang
    }
    import requests
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    result = response.json()
    return [t["text"] for t in result["translations"]]


def translate_texts_google_official(texts: List[str], target_lang: str, api_key: str) -> List[str]:
    """
    Translate list of texts using the official Google Cloud Translation API.
    """
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {"key": api_key}
    payload = {
        "q": texts,
        "target": target_lang,
        "format": "text"
    }
    import requests
    response = requests.post(url, params=params, json=payload, timeout=10)
    response.raise_for_status()
    result = response.json()
    return [t["translatedText"] for t in result["data"]["translations"]]


def translate_srt(input_srt_path: str, output_srt_path: str, target_lang: str) -> bool:
    """
    Translate an SRT file's text to target_lang using official DeepL / Google APIs
    if configured, otherwise fall back to the free web googletrans scraper.
    """
    print(f"Translating {input_srt_path} to '{target_lang}'...")
    blocks = parse_srt(input_srt_path)
    if not blocks:
        print("No subtitles found to translate.")
        write_srt([], output_srt_path)
        return True
        
    texts_to_translate = [b["text"] for b in blocks]
    translated_texts = []
    
    deepl_key = os.environ.get("DEEPL_API_KEY")
    google_key = os.environ.get("GOOGLE_TRANSLATION_API_KEY")
    
    # Attempt 1: DeepL API
    if deepl_key:
        print("Detected DEEPL_API_KEY. Translating via DeepL API...")
        try:
            chunk_size = 50
            for i in range(0, len(texts_to_translate), chunk_size):
                chunk = texts_to_translate[i : i + chunk_size]
                translated_texts.extend(translate_texts_deepl(chunk, target_lang, deepl_key))
        except Exception as e:
            print(f"DeepL API translation failed: {e}. Falling back...")
            translated_texts = []  # reset and fallback
            
    # Attempt 2: Google Official Translation API
    if not translated_texts and google_key:
        print("Detected GOOGLE_TRANSLATION_API_KEY. Translating via Google Cloud Official API...")
        try:
            chunk_size = 50
            for i in range(0, len(texts_to_translate), chunk_size):
                chunk = texts_to_translate[i : i + chunk_size]
                translated_texts.extend(translate_texts_google_official(chunk, target_lang, google_key))
        except Exception as e:
            print(f"Google Cloud Official API translation failed: {e}. Falling back...")
            translated_texts = []  # reset and fallback

    # Attempt 3: Free googletrans fallback
    if not translated_texts:
        print("Using free googletrans scraper (default)...")
        from googletrans import Translator
        translator = Translator()
        chunk_size = 40
        for i in range(0, len(texts_to_translate), chunk_size):
            chunk = texts_to_translate[i : i + chunk_size]
            try:
                translations = translator.translate(chunk, dest=target_lang)
                if not isinstance(translations, list):
                    translations = [translations]
                translated_texts.extend([t.text for t in translations])
            except Exception as e:
                print(f"Translation chunk failed: {e}. Retrying line by line...")
                for text in chunk:
                    try:
                        if text.strip() == "":
                            translated_texts.append("")
                        else:
                            t = translator.translate(text, dest=target_lang)
                            translated_texts.append(t.text)
                    except Exception as e_line:
                        print(f"Line translation failed for '{text}': {e_line}")
                        translated_texts.append(text)  # fallback to original text
                        
    # Reassemble blocks
    translated_blocks = []
    for idx, block in enumerate(blocks):
        translated_text = translated_texts[idx] if idx < len(translated_texts) else block["text"]
        translated_blocks.append({
            "index": block["index"],
            "timestamp": block["timestamp"],
            "text": translated_text
        })
        
    write_srt(translated_blocks, output_srt_path)
    print(f"Saved translated subtitles to {output_srt_path}")
    return True


def get_ffmpeg_executable() -> str:
    """
    Detect the FFmpeg executable. Try system-level 'ffmpeg' first, and
    fallback to imageio_ffmpeg's static binary if available and system-level is missing.
    """
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "ffmpeg"
    except Exception:
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.exists(ffmpeg_path):
                print(f"System-level ffmpeg not found. Using static binary from imageio-ffmpeg: {ffmpeg_path}")
                return ffmpeg_path
        except Exception:
            pass
    return "ffmpeg"


def generate_subtitle_preview(video_path: str, alignment: int, font_size: int, font_color: str, output_image_path: str) -> bool:
    """
    Extracts a single frame from video_path at the 1-second mark and burns a 
    sample subtitle onto it at the specified alignment, size, and color.
    """
    print(f"Generating preview for {video_path} with alignment={alignment}, size={font_size}, color={font_color}...")
    
    # Ensure temp directories exist
    os.makedirs("temp_outputs", exist_ok=True)
    
    dummy_srt = os.path.join("temp_outputs", "dummy_preview.srt")
    with open(dummy_srt, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:05,000\n[Sample Subtitle Location Preview]\n\n")
        
    subtitles_filter = get_ffmpeg_subtitles_filter_path(dummy_srt)
    # Append alignment, font size, and color force_style
    subtitles_filter += f":force_style='Alignment={alignment},FontSize={font_size},PrimaryColour={font_color}'"
    
    ffmpeg_exe = get_ffmpeg_executable()
    
    command = [
        ffmpeg_exe,
        "-y",
        "-ss", "00:00:01.000",
        "-i", video_path,
        "-vf", subtitles_filter,
        "-vframes", "1",
        output_image_path
    ]
    
    print(f"Executing preview command: {' '.join(command)}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Clean up dummy srt
    try:
        if os.path.exists(dummy_srt):
            os.remove(dummy_srt)
    except Exception as e:
        print(f"Warning: Could not remove preview dummy srt: {e}")
        
    if result.returncode != 0:
        print(f"Preview extraction failed: {result.stderr}")
        return False
        
    return True


def burn_subtitles(video_path: str, srt_path: str, output_path: str, alignment: int = 2, font_size: int = 20, font_color: str = "&H00FFFFFF", resolution_cap: str = "original") -> bool:
    """
    Hardcode (burn) subtitles into video_path using ffmpeg with selected alignment, size, color, and resolution cap.
    """
    print(f"Burning subtitles from {srt_path} into {video_path} at alignment={alignment}, size={font_size}, color={font_color}, resolution_cap={resolution_cap}...")
    
    # Build filter graph (scaling first, then drawing subtitles)
    filters = []
    if resolution_cap == "720p":
        filters.append("scale=-2:'min(ih,720)'")
    elif resolution_cap == "480p":
        filters.append("scale=-2:'min(ih,480)'")
        
    subtitles_filter = get_ffmpeg_subtitles_filter_path(srt_path)
    subtitles_filter += f":force_style='Alignment={alignment},FontSize={font_size},PrimaryColour={font_color}'"
    filters.append(subtitles_filter)
    
    filter_graph = ",".join(filters)
    ffmpeg_exe = get_ffmpeg_executable()
    
    # Try with audio copy first for speed/quality retention
    command = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vf", filter_graph,
        "-c:a", "copy",
        output_path
    ]
    
    print(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print("FFmpeg with audio copy failed. Trying with audio re-encoding (AAC)...")
        command_fallback = [
            ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-vf", filter_graph,
            "-c:a", "aac",
            output_path
        ]
        print(f"Executing fallback: {' '.join(command_fallback)}")
        result_fallback = subprocess.run(command_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result_fallback.returncode != 0:
            print(f"FFmpeg fallback failed. stderr:\n{result_fallback.stderr}")
            return False
            
    print(f"Successfully burned subtitles. Output saved to {output_path}")
    return True


def process_video(input_path: str, target_language: str, alignment: int = 2, font_size: int = 20, font_color: str = "&H00FFFFFF", model_size: str = "small", resolution_cap: str = "original", segmentation_mode: str = "line_by_line") -> str:
    """
    Process the input video by transcribing it, translating the transcript,
    and hardcoding the translated subtitles.

    Args:
        input_path (str): The local path to the input video file.
        target_language (str): The target language code to translate subtitles to.
        alignment (int): The subtitle position alignment code.
        font_size (int): The subtitle font size.
        font_color (str): The subtitle font color (ASS hex format).
        model_size (str): The Whisper model size.
        resolution_cap (str): The video export resolution cap.

    Returns:
        str: The path to the final output video file, or empty string on failure.
    """
    print(f"Starting process_video for {input_path} (target language: {target_language}, alignment: {alignment}, size: {font_size}, color: {font_color}, resolution_cap: {resolution_cap})")
    
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} does not exist.")
        return ""
        
    # Ensure temp directories exist
    os.makedirs("temp_outputs", exist_ok=True)
    
    filename = os.path.splitext(os.path.basename(input_path))[0]
    
    raw_srt_path = os.path.join("temp_outputs", f"{filename}_raw.srt")
    translated_srt_path = os.path.join("temp_outputs", f"{filename}_{target_language}.srt")
    output_video_path = os.path.join("temp_outputs", f"{filename}_subtitled_{target_language}.mp4")
    
    try:
        # Step 1: Transcribe
        transcribe_success = transcribe_video(input_path, raw_srt_path, model_size=model_size, segmentation_mode=segmentation_mode)
        if not transcribe_success:
            raise Exception("Transcription failed.")
            
        # Step 2: Translate
        translate_success = translate_srt(raw_srt_path, translated_srt_path, target_language)
        if not translate_success:
            raise Exception("Translation failed.")
            
        # Step-3: Burn subtitles with selected styles and resolution cap
        burn_success = burn_subtitles(input_path, translated_srt_path, output_video_path, alignment, font_size, font_color, resolution_cap=resolution_cap)
        if not burn_success:
            raise Exception("Subtitle burning failed.")
            
        # Clean up temporary SRT files
        try:
            if os.path.exists(raw_srt_path):
                os.remove(raw_srt_path)
            if os.path.exists(translated_srt_path):
                os.remove(translated_srt_path)
        except Exception as e:
            print(f"Warning: Could not remove temporary SRT files: {e}")
            
        print(f"Successfully processed video. Output file at: {output_video_path}")
        return output_video_path
        
    except Exception as e:
        print(f"An unexpected error occurred during video processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up all temporary and output files on failure
        for temp_file in [raw_srt_path, translated_srt_path, output_video_path]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"Cleaned up partial file: {temp_file}")
                except Exception as clean_err:
                    print(f"Warning: Could not clean up {temp_file}: {clean_err}")
        return ""



if __name__ == "__main__":
    # Standard boilerplate entrypoint
    if len(sys.argv) > 5:
        process_video(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif len(sys.argv) > 4:
        process_video(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif len(sys.argv) > 3:
        process_video(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    elif len(sys.argv) > 2:
        process_video(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python core_engine.py <input_video_path> <target_language> [alignment] [font_size] [font_color]")
