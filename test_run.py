import os
import sys
import time
from core_engine import process_video

def main():
    print("=" * 60)
    print("Multilingual Video Subtitle Generator - Local Test Runner")
    print("=" * 60)

    # 1. Parse CLI arguments
    video_path = None
    target_language = "es"  # default to Spanish
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    if len(sys.argv) > 2:
        target_language = sys.argv[2]
        
    # 2. If no video path provided, auto-detect .mp4 files in workspace
    if not video_path:
        print("No video path provided. Auto-detecting mp4 files in the workspace...")
        mp4_files = []
        for file in os.listdir("."):
            if file.endswith(".mp4") and "_subtitled_" not in file:
                mp4_files.append(file)
                
        if mp4_files:
            video_path = mp4_files[0]
            print(f"Detected sample video: {video_path}")
        else:
            # Check temp_outputs just in case, but usually it should be in the root
            print("\nError: No sample video detected in the workspace root.")
            print("Please do one of the following:")
            print("  1. Place an MP4 video with speech in the workspace root (e.g., 'sample.mp4').")
            print("  2. Run the script passing the path to a video file, e.g.:")
            print("     python test_run.py \"C:\\path\\to\\your\\video.mp4\" fr")
            print("-" * 60)
            sys.exit(1)

    # 3. Validate video path
    if not os.path.exists(video_path):
        print(f"Error: The video file '{video_path}' does not exist.")
        sys.exit(1)
        
    print(f"Processing Video: {video_path}")
    print(f"Target Language : {target_language}")
    print("Starting process...")
    
    start_time = time.time()
    output_path = process_video(video_path, target_language)
    elapsed_time = time.time() - start_time
    
    print("=" * 60)
    if output_path and os.path.exists(output_path):
        print("SUCCESS!")
        print(f"Subtitled video saved to: {output_path}")
        print(f"Total time elapsed: {elapsed_time:.2f} seconds")
    else:
        print("FAILED!")
        print("Video processing failed. Please check the logs above for details.")
    print("=" * 60)

if __name__ == "__main__":
    main()
