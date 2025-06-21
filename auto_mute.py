# auto_mute.py
from moviepy.editor import VideoFileClip
import tempfile
import os

def mute_video_file(file_storage, filename):
    ext = os.path.splitext(filename)[1]
    temp_input = os.path.join(tempfile.gettempdir(), f"input_{filename}")
    temp_output = os.path.join(tempfile.gettempdir(), f"muted_{filename}")

    # Save the uploaded file to a temporary location
    file_storage.stream.seek(0)
    file_storage.save(temp_input)

    try:
        clip = VideoFileClip(temp_input)
        muted = clip.without_audio()
        muted.write_videofile(temp_output, codec='libx264', audio_codec='aac', verbose=False, logger=None)
        clip.close()
        muted.close()
        return open(temp_output, 'rb')
    except Exception as e:
        print(f"[Mute Error] {filename}: {e}")
        return open(temp_input, 'rb')
