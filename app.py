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
    """Bilingual translation - creates alternating original and translated slides."""
    prs = Presentation(input_pptx_file)
    new_prs = Presentation()  # Create a new presentation
    
    # Copy slide master and layouts from original
    # Note: This is a simplified approach. Complex themes might need more sophisticated handling.
    
    total_slides = len(prs.slides)
    if total_slides == 0:
        st.warning("No slides found in the presentation.")
        return None
    
    progress = st.progress(0)
    status_text = st.empty()
    
    translated_count = 0
    skipped_count = 0
    
    for slide_idx, slide in enumerate(prs.slides):
        status_text.text(f"Processing slide {slide_idx + 1} of {total_slides}...")
        
        # Add original slide
        original_slide_layout = new_prs.slide_layouts[0]  # Use blank layout
        new_original_slide = new_prs.slides.add_slide(original_slide_layout)
        
        # Add translated slide
        translated_slide_layout = new_prs.slide_layouts[0]  # Use blank layout
        new_translated_slide = new_prs.slides.add_slide(translated_slide_layout)
        
        # Process each shape in the original slide
        for shape in slide.shapes:
            # Copy shape to original slide
            try:
                # This is a simplified copy - for complex shapes, you might need more sophisticated copying
                if hasattr(shape, "text_frame") and shape.text_frame is not None:
                    # Create text box with same position and size
                    orig_textbox = new_original_slide.shapes.add_textbox(
                        shape.left, shape.top, shape.width, shape.height
                    )
                    trans_textbox = new_translated_slide.shapes.add_textbox(
                        shape.left, shape.top, shape.width, shape.height
                    )
                    
                    # Copy text formatting and content
                    orig_textbox.text_frame.clear()
                    trans_textbox.text_frame.clear()
                    
                    for paragraph in shape.text_frame.paragraphs:
                        # Add paragraph to original slide
                        orig_p = orig_textbox.text_frame.paragraphs[0] if len(orig_textbox.text_frame.paragraphs) == 1 else orig_textbox.text_frame.add_paragraph()
                        trans_p = trans_textbox.text_frame.paragraphs[0] if len(trans_textbox.text_frame.paragraphs) == 1 else trans_textbox.text_frame.add_paragraph()
                        
                        # Process each run in the paragraph
                        paragraph_text = ""
                        for run in paragraph.runs:
                            paragraph_text += run.text
                        
                        # Set original text
                        orig_p.text = paragraph_text
                        
                        # Translate and set translated text
                        if paragraph_text.strip() and len(paragraph_text.strip()) > 2 and not paragraph_text.strip().isdigit():
                            translated_text = translate_text(paragraph_text.strip(), target_lang, source_lang)
                            trans_p.text = translated_text
                            translated_count += 1
                            time.sleep(0.1)  # Rate limiting
                        else:
                            trans_p.text = paragraph_text  # Keep original for short/numeric text
                            skipped_count += 1
                        
                        # Copy paragraph formatting
                        try:
                            orig_p.font.size = paragraph.font.size
                            trans_p.font.size = paragraph.font.size
                            if paragraph.font.name:
                                orig_p.font.name = paragraph.font.name
                                trans_p.font.name = paragraph.font.name
                        except:
                            pass  # Skip if formatting copy fails
                            
                elif hasattr(shape, 'image'):
                    # For images, we'll skip copying for now as it's complex
                    # You could extend this to copy images if needed
                    pass
                else:
                    # For other shape types (like basic shapes), you might want to copy them
                    # This is complex and depends on the shape type
                    pass
                    
            except Exception as e:
                print(f"Error copying shape: {e}")
                continue
        
        progress.progress((slide_idx + 1) / total_slides)
    
    status_text.text(f"Bilingual presentation created! Translated: {translated_count}, Skipped: {skipped_count}")
    
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
