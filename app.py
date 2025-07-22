import streamlit as st
from pptx import Presentation
import copy
import io
import time
from datetime import datetime

def translate_text(text, target_lang='ja', source_lang='auto'):
    from googletrans import Translator
    translator = Translator()
    for _ in range(3):
        try:
            return translator.translate(text, src=source_lang, dest=target_lang).text
        except Exception:
            time.sleep(1)
    return text

def translate_pptx_standard(input_pptx_file, target_lang='ja', source_lang='auto'):
    prs = Presentation(input_pptx_file)
    new_prs = copy.deepcopy(prs)
    # Gather all runs to translate (for progress bar and API quota)
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
    # Remove default slide if present
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
st.set_page_config(page_title="PPTX Translator", page_icon="🌐", layout="wide")
st.title("🌐 PPTX Language Translator")
st.markdown("""
Translate your PowerPoint presentation – or create bilingual [Original ➔ Translated] slide format!
""")

# Sidebar for settings
st.sidebar.header("Translation Settings")
mode = st.sidebar.radio(
    "Mode:",
    options=["standard", "bilingual"],
    format_func=lambda x: "Standard (Replace text)" if x=="standard" else "Bilingual (Alternate original & translation)"
)
st.sidebar.markdown("---")
source_lang = st.sidebar.selectbox("Source language:",
    ['auto', 'en', 'ja', 'es', 'fr', 'de', 'zh', 'ko'], format_func=get_language_name
)
target_lang = st.sidebar.selectbox("Target language:",
    ['ja', 'en', 'es', 'fr', 'de', 'zh', 'ko'], format_func=get_language_name, index=0)
st.sidebar.markdown("Quick:")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🇺🇸→🇯🇵"):
        source_lang = 'en'
        target_lang = 'ja'
        st.rerun()
with col2:
    if st.button("🇯🇵→🇺🇸"):
        source_lang = 'ja'
        target_lang = 'en'
        st.rerun()

col1, col2 = st.columns([2,1])
with col2:
    st.header("How it works")
    st.markdown("""
- **Standard**: Replaces all text
- **Bilingual**: Alternates slides (original → translated)
- Formatting and images are preserved
- Simple & reliable
""")

with col1:
    uploaded = st.file_uploader("Upload your PPTX", type=["pptx"])
    if uploaded:
        st.success(f"File uploaded: {uploaded.name}")
        if source_lang == target_lang:
            st.error("Source and target languages cannot be the same!")
        else:
            btn_label = "Translate" if mode=="standard" else "Create bilingual"
            if st.button(f"🚀 {btn_label}"):
                start = time.time()
                with st.spinner("Working..."):
                    # 1. Translate in memory
                    translated_bytes = translate_pptx_standard(uploaded, target_lang, source_lang)
                    if mode == "standard":
                        output_bytes = translated_bytes
                    else:
                        uploaded.seek(0)
                        output_bytes = merge_presentations_alternating(uploaded, translated_bytes)
                st.success(f"Done in {time.time()-start:.1f} seconds!")
                suffix = "bilingual" if mode=="bilingual" else "translated"
                filename = f"{suffix}_{get_language_name(source_lang)}_{get_language_name(target_lang)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
                st.download_button(
                    "⬇️ Download PPTX",
                    data=output_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

st.markdown("---")
st.caption("Built with ❤️ using Streamlit and python-pptx.")
