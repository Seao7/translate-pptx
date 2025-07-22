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

def translate_pptx_standard(input_pptx_file, target_lang='ja', source_lang='auto'):
    """Standard translation - replaces original text with translated text."""
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

def translate_pptx_bilingual(input_pptx_file, target_lang='ja', source_lang='auto'):
    """Bilingual translation - creates alternating original and translated slides by combining two presentations."""
    
    # Step 1: Create standard translated version
    st.info("Step 1/2: Creating translated version...")
    translated_pptx_bytes = translate_pptx_standard(input_pptx_file, target_lang, source_lang)
    
    if translated_pptx_bytes is None:
        return None
    
    # Step 2: Load original and translated presentations
    st.info("Step 2/2: Creating bilingual version...")
    
    # Reset file pointer for original
    input_pptx_file.seek(0)
    original_prs = Presentation(input_pptx_file)
    
    # Load translated presentation
    translated_prs = Presentation(translated_pptx_bytes)
    
    # Create new bilingual presentation starting with original structure
    bilingual_prs = copy.deepcopy(original_prs)
    
    # Clear all slides from bilingual presentation
    slide_ids_to_remove = [slide.slide_id for slide in bilingual_prs.slides]
    for slide_id in slide_ids_to_remove:
        for i, slide in enumerate(bilingual_prs.slides):
            if slide.slide_id == slide_id:
                try:
                    rId = bilingual_prs.slides._sldIdLst[i].rId
                    bilingual_prs.part.drop_rel(rId)
                    del bilingual_prs.slides._sldIdLst[i]
                except:
                    pass
                break
    
    # Step 3: Add slides alternating between original and translated
    total_slides = len(original_prs.slides)
    progress = st.progress(0)
    status_text = st.empty()
    
    for i in range(total_slides):
        status_text.text(f"Adding slide pair {i + 1} of {total_slides}...")
        
        # Add original slide
        original_slide = original_prs.slides[i]
        original_slide_layout = bilingual_prs.slide_layouts[original_slide.slide_layout.slide_layout.name] if hasattr(original_slide.slide_layout, 'slide_layout') else bilingual_prs.slide_layouts[0]
        
        try:
            # Use the duplicate_slide method if available (more reliable)
            new_original = bilingual_prs.slides.add_slide(original_slide_layout)
            
            # Copy slide content using XML manipulation (more reliable than shape-by-shape)
            new_original._element.clear()
            new_original._element.append(copy.deepcopy(original_slide._element.cSld))
            
        except Exception as e:
            # Fallback method
            new_original = bilingual_prs.slides.add_slide(original_slide_layout)
            # This will have the layout but might miss some content
            print(f"Fallback copying for original slide {i+1}: {e}")
        
        # Add translated slide
        translated_slide = translated_prs.slides[i]
        translated_slide_layout = bilingual_prs.slide_layouts[translated_slide.slide_layout.slide_layout.name] if hasattr(translated_slide.slide_layout, 'slide_layout') else bilingual_prs.slide_layouts[0]
        
        try:
            # Use the same XML method for consistency
            new_translated = bilingual_prs.slides.add_slide(translated_slide_layout)
            new_translated._element.clear()
            new_translated._element.append(copy.deepcopy(translated_slide._element.cSld))
            
        except Exception as e:
            # Fallback method
            new_translated = bilingual_prs.slides.add_slide(translated_slide_layout)
            print(f"Fallback copying for translated slide {i+1}: {e}")
        
        progress.progress((i + 1) / total_slides)
    
    status_text.text(f"Bilingual presentation created with {total_slides * 2} slides!")
    
    output = io.BytesIO()
    bilingual_prs.save(output)
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

# Translation mode selection
translation_mode = st.sidebar.radio(
    "Translation Mode:",
    options=["standard", "bilingual"],
    format_func=lambda x: "Standard (Replace original)" if x == "standard" else "Bilingual (Original + Translation)",
    index=0
)

st.sidebar.markdown("---")

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
    mode_description = "Standard Mode: Replaces original text with translations" if translation_mode == "standard" else "Bilingual Mode: Creates alternating original and translated slides"
    st.markdown(f"### {mode_description}")
    st.markdown(f"**Translation: {get_language_name(source_lang)} → {get_language_name(target_lang)}**")
    
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
        
        if translation_mode == "bilingual":
            st.info("📄 Bilingual mode will create a presentation with double the slides (original → translated → original → translated...)")
        
        # Validation
        if source_lang == target_lang:
            st.error("⚠️ Source and target languages cannot be the same!")
        else:
            if st.button("🚀 Start Translation", type="primary"):
                start_time = time.time()
                
                with st.spinner(f"{'Creating bilingual' if translation_mode == 'bilingual' else 'Translating'} presentation... This may take a few minutes."):
                    if translation_mode == "standard":
                        translated_pptx = translate_pptx_standard(uploaded_file, target_lang, source_lang)
                    else:
                        translated_pptx = translate_pptx_bilingual(uploaded_file, target_lang, source_lang)
                
                if translated_pptx:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    st.success(f"🎉 {'Bilingual presentation' if translation_mode == 'bilingual' else 'Translation'} completed in {duration:.1f} seconds!")
                    
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    mode_suffix = "bilingual" if translation_mode == "bilingual" else "translated"
                    filename = f"{mode_suffix}_{get_language_name(source_lang).lower()}_to_{get_language_name(target_lang).lower()}_{timestamp}.pptx"
                    
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
    1. **Choose translation mode**:
       - Standard: Replaces text
       - Bilingual: Alternating slides
    2. **Select languages** in the sidebar
    3. **Upload** your PPTX file
    4. **Click translate** and wait
    5. **Download** the result
    
    ### 🔧 Features
    - **Two translation modes**
    - **Bidirectional translation** (EN↔JP and more)
    - **Auto language detection**
    - **Progress tracking**
    - **Retry mechanism** for failed translations
    - **Smart text filtering** (skips numbers, short text)
    
    ### 📝 Notes
    - **Bilingual mode** doubles slide count
    - Large files may take several minutes
    - Basic formatting is preserved
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
    - **Bilingual Mode**: Creates alternating slides (original → translated → original → translated...)
    - **Shape Copying**: Complex shapes and images may not be perfectly copied in bilingual mode.
    """)
