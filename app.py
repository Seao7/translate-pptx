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

def copy_slide_with_layout(source_slide, target_prs):
    """Copy a slide while preserving layout, colors, and all visual elements."""
    # Try to find a matching layout or use a blank one
    try:
        slide_layout = target_prs.slide_layouts[source_slide.slide_layout.name] if hasattr(source_slide, 'slide_layout') else target_prs.slide_layouts[0]
    except:
        slide_layout = target_prs.slide_layouts[0]  # Fallback to blank layout
    
    new_slide = target_prs.slides.add_slide(slide_layout)
    
    # Copy slide background if it exists
    try:
        if hasattr(source_slide, 'background') and hasattr(new_slide, 'background'):
            new_slide.background = source_slide.background
    except:
        pass
    
    return new_slide

def copy_shape_completely(source_shape, target_slide):
    """Copy a shape completely including all formatting, colors, and properties."""
    try:
        if hasattr(source_shape, "text_frame") and source_shape.text_frame is not None:
            # Text box or shape with text
            new_shape = target_slide.shapes.add_textbox(
                source_shape.left, 
                source_shape.top, 
                source_shape.width, 
                source_shape.height
            )
            
            # Copy text frame properties
            new_shape.text_frame.clear()
            new_shape.text_frame.margin_left = source_shape.text_frame.margin_left
            new_shape.text_frame.margin_right = source_shape.text_frame.margin_right
            new_shape.text_frame.margin_top = source_shape.text_frame.margin_top
            new_shape.text_frame.margin_bottom = source_shape.text_frame.margin_bottom
            new_shape.text_frame.word_wrap = source_shape.text_frame.word_wrap
            new_shape.text_frame.auto_size = source_shape.text_frame.auto_size
            
            # Copy all paragraphs
            for i, paragraph in enumerate(source_shape.text_frame.paragraphs):
                if i == 0:
                    new_paragraph = new_shape.text_frame.paragraphs[0]
                else:
                    new_paragraph = new_shape.text_frame.add_paragraph()
                
                # Copy paragraph properties
                new_paragraph.alignment = paragraph.alignment
                new_paragraph.space_before = paragraph.space_before
                new_paragraph.space_after = paragraph.space_after
                new_paragraph.line_spacing = paragraph.line_spacing
                
                # Copy all runs in the paragraph
                for j, run in enumerate(paragraph.runs):
                    if j == 0 and len(new_paragraph.runs) > 0:
                        new_run = new_paragraph.runs[0]
                    else:
                        new_run = new_paragraph.add_run()
                    
                    new_run.text = run.text
                    
                    # Copy font properties
                    try:
                        new_run.font.name = run.font.name
                        new_run.font.size = run.font.size
                        new_run.font.bold = run.font.bold
                        new_run.font.italic = run.font.italic
                        new_run.font.underline = run.font.underline
                        if hasattr(run.font, 'color') and run.font.color:
                            new_run.font.color.rgb = run.font.color.rgb
                    except:
                        pass
            
            # Copy shape fill and line properties
            try:
                if hasattr(source_shape, 'fill'):
                    new_shape.fill.solid()
                    if hasattr(source_shape.fill, 'fore_color'):
                        new_shape.fill.fore_color.rgb = source_shape.fill.fore_color.rgb
                
                if hasattr(source_shape, 'line'):
                    new_shape.line.color.rgb = source_shape.line.color.rgb
                    new_shape.line.width = source_shape.line.width
            except:
                pass
                
            return new_shape
            
        elif source_shape.shape_type == 13:  # Picture/Image
            # For images, we need to extract and re-insert
            try:
                image_stream = source_shape.image.blob
                new_shape = target_slide.shapes.add_picture(
                    io.BytesIO(image_stream),
                    source_shape.left,
                    source_shape.top,
                    source_shape.width,
                    source_shape.height
                )
                return new_shape
            except Exception as e:
                print(f"Failed to copy image: {e}")
                return None
                
        else:
            # For other shapes (rectangles, circles, diagrams, etc.)
            try:
                # This is a more complex case - we'll try to duplicate the shape
                # For basic shapes, we can try to recreate them
                if source_shape.shape_type in [1, 2, 3, 4, 5]:  # Basic shapes
                    # Add a rectangle as placeholder and try to copy properties
                    new_shape = target_slide.shapes.add_shape(
                        source_shape.auto_shape_type,
                        source_shape.left,
                        source_shape.top,
                        source_shape.width,
                        source_shape.height
                    )
                    
                    # Copy fill properties
                    try:
                        if hasattr(source_shape.fill, 'solid') and source_shape.fill.type == 1:  # Solid fill
                            new_shape.fill.solid()
                            new_shape.fill.fore_color.rgb = source_shape.fill.fore_color.rgb
                        
                        # Copy line properties
                        if hasattr(source_shape, 'line'):
                            new_shape.line.color.rgb = source_shape.line.color.rgb
                            new_shape.line.width = source_shape.line.width
                    except:
                        pass
                        
                    return new_shape
                else:
                    print(f"Unsupported shape type: {source_shape.shape_type}")
                    return None
                    
            except Exception as e:
                print(f"Failed to copy shape: {e}")
                return None
                
    except Exception as e:
        print(f"Error in copy_shape_completely: {e}")
        return None

def translate_slide_text(slide, target_lang='ja', source_lang='auto'):
    """Translate text in a slide while preserving all formatting."""
    translated_count = 0
    skipped_count = 0
    
    for shape in slide.shapes:
        if hasattr(shape, "text_frame") and shape.text_frame is not None:
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    original_text = run.text.strip()
                    
                    # Skip very short text or numbers/symbols only
                    if original_text and len(original_text) > 2 and not original_text.isdigit():
                        translated_text = translate_text(original_text, target_lang, source_lang)
                        run.text = translated_text
                        translated_count += 1
                        time.sleep(0.1)  # Rate limiting
                    else:
                        skipped_count += 1
    
    return translated_count, skipped_count

def translate_pptx_bilingual(input_pptx_file, target_lang='ja', source_lang='auto'):
    """Bilingual translation - creates alternating original and translated slides with full formatting."""
    prs = Presentation(input_pptx_file)
    new_prs = copy.deepcopy(prs)  # Start with a deep copy to preserve themes and layouts
    
    # Clear all slides from the new presentation
    slide_ids_to_remove = [slide.slide_id for slide in new_prs.slides]
    for slide_id in slide_ids_to_remove:
        for i, slide in enumerate(new_prs.slides):
            if slide.slide_id == slide_id:
                rId = new_prs.slides._sldIdLst[i].rId
                new_prs.part.drop_rel(rId)
                del new_prs.slides._sldIdLst[i]
                break
    
    total_slides = len(prs.slides)
    if total_slides == 0:
        st.warning("No slides found in the presentation.")
        return None
    
    progress = st.progress(0)
    status_text = st.empty()
    
    total_translated = 0
    total_skipped = 0
    
    for slide_idx, slide in enumerate(prs.slides):
        status_text.text(f"Processing slide {slide_idx + 1} of {total_slides}...")
        
        # Add original slide (complete copy)
        original_slide = copy_slide_with_layout(slide, new_prs)
        
        # Copy all shapes to original slide
        for shape in slide.shapes:
            copy_shape_completely(shape, original_slide)
        
        # Add translated slide (complete copy)
        translated_slide = copy_slide_with_layout(slide, new_prs)
        
        # Copy all shapes to translated slide
        for shape in slide.shapes:
            copy_shape_completely(shape, translated_slide)
        
        # Now translate the text in the translated slide
        translated_count, skipped_count = translate_slide_text(translated_slide, target_lang, source_lang)
        total_translated += translated_count
        total_skipped += skipped_count
        
        progress.progress((slide_idx + 1) / total_slides)
    
    status_text.text(f"Bilingual presentation created! Translated: {total_translated}, Skipped: {total_skipped}")
    
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
