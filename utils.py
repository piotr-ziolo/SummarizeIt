import os
import time
import re
from pytube import YouTube
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv(), override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_youtube_video_details(link):
    """
    Get details of a YouTube video.

    Args:
        link (str): The YouTube video URL.

    Returns:
        tuple: A tuple with a success flag and either the video details or an error message.
    """
    try:
        if 'youtube.com' not in link:
            return False, 'Please provide a valid YouTube URL'

        yt = YouTube(link)
        details = {
            'title': yt.title,
            'author': yt.author,
            'views': yt.views,
            'length': convert_seconds_to_time(yt.length),
            'publish_date': yt.publish_date.date(),
            'thumbnail_url': yt.thumbnail_url
        }
        return True, details
    except Exception as e:
        return False, f'An error occurred while fetching video details: {e}'

def convert_seconds_to_time(seconds):
    """
    Convert seconds to HH:MM:SS format.

    Args:
        seconds (int): The number of seconds.

    Returns:
        str: The time in HH:MM:SS format.
    """
    return time.strftime("%H:%M:%S", time.gmtime(seconds))

def youtube_audio_downloader(link):
    """
    Download audio from a YouTube video.

    Args:
        link (str): The YouTube video URL.

    Returns:
        tuple: A tuple with a success flag and either the audio file path or an error message.
    """
    try:
        yt = YouTube(link)
        audio = yt.streams.filter(only_audio=True).first()
        output_file = audio.download()

        if not os.path.exists(output_file):
            return False, 'Download failed!'

        audio_file = rename_audio_file(output_file)
        return True, audio_file
    except Exception as e:
        return False, f'An error occurred while downloading the audio: {e}'

def rename_audio_file(output_file):
    """
    Rename the downloaded audio file to a standard format.

    Args:
        output_file (str): The path to the downloaded file.

    Returns:
        str: The renamed audio file path.
    """
    basename = os.path.basename(output_file)
    name, _ = os.path.splitext(basename)
    audio_file = f'downloaded_{name}.mp3'
    audio_file = re.sub(r'\s+', '_', audio_file)
    os.rename(output_file, audio_file)
    return audio_file

def transcribe(audio_file):
    """
    Transcribe the audio file.

    Args:
        audio_file (str): The path to the audio file.

    Returns:
        tuple: A tuple with a success flag and either the transcript file path or an error message.
    """
    try:
        if not os.path.exists(audio_file):
            return False, 'File does not exist!'

        with open(audio_file, 'rb') as f:
            transcript = client.audio.transcriptions.create(model='whisper-1', file=f)

        transcript_filename = save_transcript(audio_file, transcript.text)
        return True, transcript_filename
    except Exception as e:
        return False, f'An error occurred while transcribing the audio: {e}'

def translate(transcript_file):
    """
    Translate the transcript file.

    Args:
        transcript_file (str): The path to the transcript file.

    Returns:
        tuple: A tuple with a success flag and either the translated file path or an error message.
    """
    try:
        if not os.path.exists(transcript_file):
            return False, 'File does not exist!'

        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': 'You are an AI assistant that translates text to different languages.'},
                {'role': 'user', 'content': f'Translate the following text to English:\n{transcript_text}'}
            ]
        )

        translated_filename = save_transcript(transcript_file, response.choices[0].message.content)
        return True, translated_filename
    except Exception as e:
        return False, f'An error occurred while translating the transcript: {e}'

def save_transcript(audio_file, transcript_text):
    """
    Save the transcript to a file.

    Args:
        audio_file (str): The path to the audio file.
        transcript_text (str): The transcript text.

    Returns:
        str: The path to the saved transcript file.
    """
    name, _ = os.path.splitext(audio_file)
    transcript_filename = f'transcript_{name.replace("downloaded_", "")}.txt'
    with open(transcript_filename, 'w', encoding='utf-8') as f:
        f.write(transcript_text)
    return transcript_filename

def summarize(transcript_filename, summary_length):
    """
    Generate a summary of the transcript.

    Args:
        transcript_filename (str): The path to the transcript file.
        summary_length (int): The desired length of the summary.

    Returns:
        tuple: A tuple with a success flag and either the summary text or an error message.
    """
    try:
        if not os.path.exists(transcript_filename):
            return False, 'File does not exist!'

        with open(transcript_filename, 'r', encoding='utf-8') as f:
            transcript = f.read()

        response = generate_summary(transcript, summary_length)
        return True, response
    except Exception as e:
        return False, f'An error occurred while summarizing the transcript: {e}'

def generate_summary(transcript, summary_length):
    """
    Generate a summary using OpenAI API.

    Args:
        transcript (str): The transcript text.
        summary_length (int): The desired length of the summary.

    Returns:
        str: The generated summary.
    """
    system_prompt = 'You are an AI assistant that creates engaging and informative summaries of various types of input, such as videos, audio files, and text.'
    prompt = f"""Create a summary of approximately {summary_length} words.
    Create a short title for the summary.
    Include the most important points and key details.
    Be factual and concise. Do NOT include content that is not in the original text.
    When possible, use bullet points.
    Create the summary in the same language as the text you're asked to summarize (which is NOT necessarily English).

    Text to summarize:
    {transcript}    
    """

    response = client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        max_tokens=2048,
        temperature=1
    )
    return response.choices[0].message.content

def cleanup_files():
    """
    Clean up temporary files.
    """
    try:
        for file in os.listdir():
            if file.startswith('downloaded_') or file.startswith('transcript_') or file.startswith('uploaded_') or file.startswith('temp_'):
                os.remove(file)
    except Exception as e:
        print(f"Error cleaning up files: {e}")
