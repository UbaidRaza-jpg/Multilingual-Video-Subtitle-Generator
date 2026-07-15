import os
import sys
import subprocess
from typing import List, Dict, Any

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


def transcribe_video(video_path: str, output_srt_path: str, model_size: str = "base") -> bool:
    """
    Transcribe audio from video_path and save to output_srt_path using faster-whisper.
    """
    print(f"Loading faster-whisper model ({model_size})...")
    from faster_whisper import WhisperModel
    
    # cpu is the default device, int8 compute type is optimized for CPU inference
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print(f"Transcribing {video_path}...")
    segments, info = model.transcribe(video_path, beam_size=5)
    
    # We must consume the generator to transcribe
    segments = list(segments)
    
    print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
    print(f"Writing raw transcript to {output_srt_path}...")
    
    with open(output_srt_path, "w", encoding="utf-8") as f:
        for idx, segment in enumerate(segments, start=1):
            start = format_time(segment.start)
            end = format_time(segment.end)
            text = segment.text.strip()
            f.write(f"{idx}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
            
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


def translate_srt(input_srt_path: str, output_srt_path: str, target_lang: str) -> bool:
    """
    Translate an SRT file's text to target_lang using googletrans.
    """
    print(f"Translating {input_srt_path} to '{target_lang}'...")
    blocks = parse_srt(input_srt_path)
    if not blocks:
        print("No subtitles found to translate.")
        # If input was empty, write empty output
        write_srt([], output_srt_path)
        return True
        
    from googletrans import Translator
    translator = Translator()
    
    # Translate in chunks to optimize requests and avoid rate limits
    chunk_size = 40
    translated_blocks = []
    
    texts_to_translate = [b["text"] for b in blocks]
    translated_texts = []
    
    for i in range(0, len(texts_to_translate), chunk_size):
        chunk = texts_to_translate[i : i + chunk_size]
        print(f"Translating chunk {i // chunk_size + 1} of {(len(texts_to_translate) - 1) // chunk_size + 1}...")
        try:
            translations = translator.translate(chunk, dest=target_lang)
            if not isinstance(translations, list):
                translations = [translations]
            translated_texts.extend([t.text for t in translations])
        except Exception as e:
            print(f"Translation chunk failed: {e}. Retrying line by line...")
            # Fallback line-by-line translation
            for text in chunk:
                try:
                    if text.strip() == "":
                        translated_texts.append("")
                    else:
                        t = translator.translate(text, dest=target_lang)
                        translated_texts.append(t.text)
                except Exception as e_line:
                    print(f"Line translation failed for '{text}': {e_line}")
                    translated_texts.append(text) # Fallback to original text
                    
    # Reassemble blocks
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


def burn_subtitles(video_path: str, srt_path: str, output_path: str) -> bool:
    """
    Hardcode (burn) subtitles into video_path using ffmpeg.
    """
    print(f"Burning subtitles from {srt_path} into {video_path}...")
    subtitles_filter = get_ffmpeg_subtitles_filter_path(srt_path)
    ffmpeg_exe = get_ffmpeg_executable()
    
    # Try with audio copy first for speed/quality retention
    command = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vf", subtitles_filter,
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
            "-vf", subtitles_filter,
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


def process_video(input_path: str, target_language: str) -> str:
    """
    Process the input video by transcribing it, translating the transcript,
    and hardcoding the translated subtitles.

    Args:
        input_path (str): The local path to the input video file.
        target_language (str): The target language code to translate subtitles to.

    Returns:
        str: The path to the final output video file, or empty string on failure.
    """
    print(f"Starting process_video for {input_path} (target language: {target_language})")
    
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
        transcribe_success = transcribe_video(input_path, raw_srt_path)
        if not transcribe_success:
            raise Exception("Transcription failed.")
            
        # Step 2: Translate
        translate_success = translate_srt(raw_srt_path, translated_srt_path, target_language)
        if not translate_success:
            raise Exception("Translation failed.")
            
        # Step 3: Burn subtitles
        burn_success = burn_subtitles(input_path, translated_srt_path, output_video_path)
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
    if len(sys.argv) > 2:
        process_video(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python core_engine.py <input_video_path> <target_language>")
