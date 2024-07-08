import streamlit as st
from utils import get_youtube_video_details, youtube_audio_downloader, transcribe, translate, summarize, cleanup_files

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="SummarizeIt", page_icon="images/ai_summarize.png")

    col1, col2 = st.columns([0.85, 0.15])

    with col1:
        st.title('SummarizeIt')
        st.write("Generate a summary of anything you need: text, files and YouTube videos!")

    with col2:
        st.image('images/ai_summarize.png', width=160)

    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'transcript' not in st.session_state:
        st.session_state.transcript = ""

    input_type = st.radio('Choose the input type:', ['Direct text input', 'Text file', 'YouTube link', 'Video file', 'Audio file'], key='input_type')

    if 'last_input_type' not in st.session_state or st.session_state.last_input_type != input_type:
        st.session_state.summary = ""
        st.session_state.transcript = ""
        st.session_state.last_input_type = input_type

    file_info = None
    if input_type == 'Direct text input':
        file_info = handle_direct_text_input()
    
    elif input_type == 'Text file':
        file_info = handle_text_input()
    
    elif input_type == 'YouTube link':
        file_info = handle_youtube_input()
    
    elif input_type == 'Video file':
        file_info = handle_video_input()
    
    elif input_type == 'Audio file':
        file_info = handle_audio_input()
    
    if file_info:
        st.divider()
        summary_length = st.slider('Choose the length of the summary:', 50, 300, 150, 10)
        translate_text = st.checkbox('Translate to English', help='Translate the input and the summary to English if the input is in another language.')

        file, is_text, is_youtube = file_info
        if st.button('Generate Summary', type='primary', use_container_width=True):
            process_file(file, is_youtube=is_youtube, is_text=is_text, summary_length=summary_length, translate_text=translate_text)

    display_results()

def handle_direct_text_input():
    user_input_text = st.text_area("Enter your text here:")
    if user_input_text.strip():
        temp_text_file = 'temp_user_input.txt'
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(user_input_text)
        return temp_text_file, True, False
    return None

def handle_text_input():
    if 'uploaded_file' in st.session_state:
        del st.session_state.uploaded_file
    
    uploaded_file = st.file_uploader('Upload a text file:', type=['txt'], key='text_file_uploader')
    if uploaded_file is not None:
        if 'uploaded_file' in st.session_state:
            st.session_state.uploaded_file.close()
        st.session_state.uploaded_file = uploaded_file
        text_file = save_uploaded_file(uploaded_file, 'uploaded_text.txt')
        return text_file, True, False
    return None

def handle_youtube_input():
    youtube_link = st.text_input('Enter the YouTube link:', value='')
    if youtube_link.strip():
        with st.expander('Video Information', expanded=False):
            with st.spinner('Loading...'):
                success, details = get_youtube_video_details(youtube_link)
                if success:
                    display_video_details(details)
                else:
                    st.error(details)
        return youtube_link, False, True
    return None

def handle_video_input():
    if 'uploaded_file' in st.session_state:
        del st.session_state.uploaded_file

    uploaded_file = st.file_uploader('Upload a video file:', type=['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm'], key='video_file_uploader')
    if uploaded_file is not None:
        if 'uploaded_file' in st.session_state:
            st.session_state.uploaded_file.close()
        st.session_state.uploaded_file = uploaded_file
        video_file = save_uploaded_file(uploaded_file, 'uploaded_video.mp4')
        return video_file, False, False
    return None

def handle_audio_input():
    if 'uploaded_file' in st.session_state:
        del st.session_state.uploaded_file

    uploaded_file = st.file_uploader('Upload an audio file:', type=['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'wma'], key='audio_file_uploader')
    if uploaded_file is not None:
        if 'uploaded_file' in st.session_state:
            st.session_state.uploaded_file.close()
        st.session_state.uploaded_file = uploaded_file
        audio_file = save_uploaded_file(uploaded_file, 'uploaded_audio.mp3')
        return audio_file, False, False
    return None

def save_uploaded_file(uploaded_file, filename):
    """Save uploaded file to the specified filename."""
    with open(filename, 'wb') as f:
        f.write(uploaded_file.read())
    st.write(f'File saved as {filename}')
    return filename

def process_file(file, is_youtube=False, is_text=False, summary_length=150, translate_text=False):
    """Process the file (download, transcribe, translate, summarize)"""
    try:
        if is_youtube:
            with st.spinner('Downloading video...'):
                success, result = youtube_audio_downloader(file)
                if not success:
                    st.error(result)
                    return
                file = result

        if not is_text:
            with st.spinner('Transcribing...'):
                success, result = transcribe(file)
                if not success:
                    st.error(result)
                    return
            transcript_file = result

            if translate_text:
                with st.spinner('Translating...'):
                    success, result = translate(transcript_file)
                    if not success:
                        st.error(result)
                        return
                transcript_file = result
        else:
            transcript_file = file

        with st.spinner('Summarizing...'):
            success, result = summarize(transcript_file, summary_length)
            if not success:
                st.error(result)
                return

        with open(transcript_file, 'r', encoding='utf-8') as f:
            st.session_state.transcript = f.read()
        
        st.session_state.summary = result
    finally:
        cleanup_files()

def display_results():
    """Display the results: summary and transcript."""
    if st.session_state.summary:
        st.subheader('Summary:')
        st.write(st.session_state.summary)
        st.download_button('Download Summary', data=st.session_state.summary, file_name='summary.txt')

    if st.session_state.transcript:
        with st.expander('Full Transcript'):
            st.write(st.session_state.transcript)
            st.download_button('Download Transcript', data=st.session_state.transcript, file_name='transcript.txt')

def display_video_details(details):
    """Display details of a YouTube video in the Streamlit app."""
    st.subheader(details['title'])
    col1, col2 = st.columns([0.6, 0.4])
    with col1:
        st.write(f'Channel: {details["author"]}')
        st.write(f'Views: {details["views"]:,}')
        st.write(f'Length: {details["length"]}')
        st.write(f'Publish Date: {details["publish_date"]}')
    with col2:
        st.image(details['thumbnail_url'])

if __name__ == '__main__':
    main()
