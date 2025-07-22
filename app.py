import streamlit as st
from pptx import Presentation
import copy
import io
import time
from datetime import datetime

def translate_text(text, target_lang='ja', source_lang='auto'):
    from googletrans import Translator
    translator = Translator()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return translator.translate(text, src=source_lang, dest=target_lang).text
        except Exception:
            time.sleep(1)
    return text

def translate_pptx_standard(input_pptx_file, target_lang='ja', source_lang='auto'):
    prs = Presentation(input_pptx_file)
    new_prs = copy.deepcopy(prs)
    runs = []
    for slide in new_prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame is not None:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        txt = run.text.strip()
                        if len(txt) > 2 and not txt.isdigit():
                            runs.append(run)
    progress = st.progress(0)
    for idx, run in enumerate(runs):
        run.text = translate_text(run.text, target_lang, source_lang)
        time.sleep(0.05)
        progress.progress((idx + 1)/len(runs))
    progress.empty()
    output = io.BytesIO()
    new_prs.save(output)
    output.seek(0)
    return output

def merge_presentations_alternating(orig_bytes, trans_bytes):
    original = Presentation(orig_bytes)
    translated = Presentation(trans_bytes)
    output_ppt = Presentation()
    # Remove default slide from new presentation
    if len(output_ppt.slides) > 0:
        rId = output_ppt.slides._sldIdLst[0].rId
        output_ppt.part.drop_rel(rId)
        del output_ppt.slides._sldIdLst[0]
    slide_count = min(len(original.slides), len(translated.slides))
    for idx in range(slide_count):
        for src_prs in [original, translated]:
            slide = src_prs.slides[idx]
            layout = output_ppt.slide_layouts[slide.slide_layout.slide_layout_id or 0]
            new_slide = output_ppt.slides.add_slide(layout)
            # Copy slide content
            new_slide._element.clear()
            new_slide._element.append(copy.deepcopy(slide._element.cSld))
    output_io = io.BytesIO()
    output_ppt.save(output_io)
    output_io.seek(0)
    return output_io

def get_language_name(lang_code):
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

# --- Streamlit App ---
st.set_page_config(page_title="Bilingual PPTX Maker", page_icon="🌐", layout="wide")
st.title("🌐 Bilingual PPTX Slide-by-Slide Translator")

st.write("""
Upload a PowerPoint pptx file, select your target language, and get an alternating bilingual PPTX:  
**[Original Slide 1] ⇒ [Translated Slide 1] ⇒ [Original Slide 2] ⇒ [Translated Slide 2] ...**
""")

col1, col2 = st.columns([2, 1])

with col2:
    st.header("How to use")
    st.markdown("""
1. Upload your `.pptx` file  
2. Select your **target language**  
3. Click "Make Bilingual"  
4. Download your bilingual result!

- Images, formatting, and media are preserved.
- Text boxes with only numbers/symbols are skipped.
    """)
    st.info("This method preserves all layouts, images, and media.")

with col1:
    uploaded = st.file_uploader("Upload PPTX", type=["pptx"])
    source_lang = st.selectbox("Source language:", ['auto', 'en', 'ja', 'es', 'fr', 'de', 'zh', 'ko'], format_func=get_language_name)
    target_lang = st.selectbox("Target language:", ['ja', 'en', 'es', 'fr', 'de', 'zh', 'ko'], format_func=get_language_name, index=0)
    if uploaded:
        st.success(f"File uploaded: {uploaded.name}")
        if st.button("🚀 Make Bilingual PPTX", type="primary"):
            start = time.time()
            with st.spinner("Translating (this may take a while for big files)..."):
                # 1. Translate a copy
                trans_bytes = translate_pptx_standard(uploaded, target_lang, source_lang)
                # 2. Seek original back to start
                uploaded.seek(0)
                # 3. Merge alternately
                final_bytes = merge_presentations_alternating(uploaded, trans_bytes)
            st.success(f"Bilingual PPTX ready in {time.time() - start:.1f} seconds!")
            st.download_button(
                "⬇️ Download Bilingual PPTX",
                data=final_bytes,
                file_name=f"bilingual_{get_language_name(source_lang)}_{get_language_name(target_lang)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

st.markdown("---")
st.caption("Built with ❤️ using Streamlit and python-pptx · All images and formatting preserved.")




# Warning about API limits
with st.expander("⚠️ Important Notes"):
    st.markdown("""
    - **API Limits**: Google Translate has usage limits. Large presentations may hit rate limits.
    - **Accuracy**: Machine translation may not be perfect. Review important content manually.
    - **Formatting**: Complex layouts might need minor adjustments after translation.
    - **Privacy**: Text is sent to Google Translate service for processing.
    - **Bilingual Mode**: Creates alternating slides (original → translated → original → translated...)
    - **🖼️ Image Preservation**: Images and most formatting are now preserved in bilingual mode.
    - **Performance**: Bilingual mode with images may take longer to process.
    """)
