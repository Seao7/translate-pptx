import streamlit as st
from pptx import Presentation
from pptx.util import Pt
from googletrans import Translator
import copy
import io
import time
from datetime import datetime

def detect_language(text):
    """Detect the language of the input text."""
    translator = Translator()
    try:
        detection = translator.detect(text)
        return detection.lang
    except Exception as e:
        print(f"Language detection failed for: {text} - {e}")
        return 'unknown'

def translate_text(text, target_lang='ja', source_lang='auto'):
    """Translate text using googletrans with retry logic."""
    translator = Translator()
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            translated = translator.translate(text, src=source_lang, dest=target_lang)
            return translated.text
        except Exception as e:
            print(f"Translation attempt {attempt + 1} failed for: {text} - {e}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
            else:
                return text  # fallback to original if all attempts fail

def translate_pptx(input_pptx_file, target_lang='ja', source_lang='auto'):
    """Read PPTX, translate all text, return as BytesIO, with progress tracking."""
    prs = Presentation(input_pptx_file)
    new_prs = copy.deepcopy(prs)  # deep copy to preserve original
    
    # Count total number of text runs for progress bar
    total_runs = 0
    text_runs = []
    
    for slide in new_prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame is not None:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.text.strip():  # Only count non-empty text
                            total_runs += 1
                            text_runs.append(run)
    
    if total_runs == 0:
        st.warning("No text content found in the presentation.")
        return None
    
    progress = st.progress(0)
    status_text = st.empty()
    
    translated_count = 0
    skipped_count = 0
    
    for i, run in enumerate(text_runs):
        original_text = run.text.strip()
        
        # Skip very short text or numbers/symbols only
        if len(original_text) <= 2 or original_text.isdigit():
            skipped_count += 1
        else:
            status_text.text(f"Translating: {original_text[:50]}...")
            translated_text = translate_text(original_text, target_lang, source_lang)
            run.text = translated_text
            translated_count += 1
            
            # Small delay to avoid hitting API rate limits
            time.sleep(0.1)
        
        progress.progress((i + 1) / total_runs)
    
    status_text.text(f"Translation complete! Translated: {translated_count}, Skipped: {skipped_count}")
    
    output = io.BytesIO()
    new_prs.save(output)
    output.seek(0)
    return output

def get_language_name(lang_code):
    """Get language name from code."""
    languages = {
        'en': 'English',
        'ja': 'Japanese',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'zh': 'Chinese',
        'ko': 'Korean',
        'auto': 'Auto-detect'
    }
    return languages.get(lang_code, lang_code)

# ---- Streamlit App ----
st.set_page_config(
    page_title="PPTX Translator",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 PPTX Language Translator")
st.markdown("Translate PowerPoint presentations between different languages with ease!")

# Sidebar for settings
st.sidebar.header("Translation Settings")

# Language selection
source_lang = st.sidebar.selectbox(
    "Source Language:",
    options=['auto', 'en', 'ja', 'es', 'fr', 'de', 'zh', 'ko'],
    format_func=get_language_name,
    index=0
)

target_lang = st.sidebar.selectbox(
    "Target Language:",
    options=['ja', 'en', 'es', 'fr', 'de', 'zh', 'ko'],
    format_func=get_language_name,
    index=0 if source_lang != 'ja' else 1
)

# Quick translation buttons
st.sidebar.markdown("### Quick Options")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🇺🇸→🇯🇵", help="English to Japanese"):
        source_lang = 'en'
        target_lang = 'ja'
        st.rerun()

with col2:
    if st.button("🇯🇵→🇺🇸", help="Japanese to English"):
        source_lang = 'ja'
        target_lang = 'en'
        st.rerun()

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"### Translation: {get_language_name(source_lang)} → {get_language_name(target_lang)}")
    
    uploaded_file = st.file_uploader(
        "Upload a PPTX file",
        type=["pptx"],
        help="Select a PowerPoint presentation file to translate"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        # File info
        file_size = len(uploaded_file.getvalue()) / 1024 / 1024  # MB
        st.info(f"File size: {file_size:.2f} MB")
        
        # Validation
        if source_lang == target_lang:
            st.error("⚠️ Source and target languages cannot be the same!")
        else:
            if st.button("🚀 Start Translation", type="primary"):
                start_time = time.time()
                
                with st.spinner("Translating presentation... This may take a few minutes."):
                    translated_pptx = translate_pptx(uploaded_file, target_lang, source_lang)
                
                if translated_pptx:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    st.success(f"🎉 Translation completed in {duration:.1f} seconds!")
                    
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"translated_{get_language_name(source_lang).lower()}_to_{get_language_name(target_lang).lower()}_{timestamp}.pptx"
                    
                    st.download_button(
                        label="⬇️ Download Translated PPTX",
                        data=translated_pptx,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        type="primary"
                    )
                else:
                    st.error("❌ Translation failed. Please try again.")

with col2:
    st.markdown("### ℹ️ How to Use")
    st.markdown("""
    1. **Select languages** in the sidebar
    2. **Upload** your PPTX file
    3. **Click translate** and wait
    4. **Download** the translated file
    
    ### 🔧 Features
    - **Bidirectional translation** (EN↔JP and more)
    - **Auto language detection**
    - **Progress tracking**
    - **Retry mechanism** for failed translations
    - **Smart text filtering** (skips numbers, short text)
    
    ### 📝 Notes
    - Large files may take several minutes
    - Formatting is preserved
    - Original file remains unchanged
    - Rate limiting prevents API errors
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and Google Translate API")

# Warning about API limits
with st.expander("⚠️ Important Notes"):
    st.markdown("""
    - **API Limits**: Google Translate has usage limits. Large presentations may hit rate limits.
    - **Accuracy**: Machine translation may not be perfect. Review important content manually.
    - **Formatting**: Complex layouts might need minor adjustments after translation.
    - **Privacy**: Text is sent to Google Translate service for processing.
    """)
