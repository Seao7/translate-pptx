import streamlit as st
from pptx import Presentation
from pptx.util import Pt
from googletrans import Translator
import copy
import io

def translate_text(text, target_lang='ja'):
    """Translate text using googletrans."""
    translator = Translator()
    try:
        translated = translator.translate(text, dest=target_lang)
        return translated.text
    except Exception as e:
        print(f"Translation failed for: {text} - {e}")
        return text  # fallback to original if translation fails

def translate_pptx(input_pptx_file):
    """Read PPTX, translate all text to Japanese, return as BytesIO, with progress tracking."""
    prs = Presentation(input_pptx_file)
    new_prs = copy.deepcopy(prs)  # deep copy to preserve original

    # Count total number of runs for progress bar
    total_runs = sum(
        1 for slide in new_prs.slides
          for shape in slide.shapes
            if hasattr(shape, "text_frame") and shape.text_frame is not None
              for paragraph in shape.text_frame.paragraphs
                for run in paragraph.runs
    )
    progress = st.progress(0)
    run_count = 0

    for slide in new_prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame is not None:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        original_text = run.text.strip()
                        if original_text:
                            jp_text = translate_text(original_text)
                            run.text = jp_text
                        run_count += 1
                        progress.progress(run_count / total_runs)

    output = io.BytesIO()
    new_prs.save(output)
    output.seek(0)
    return output

# ---- Streamlit App ----
st.title("PPTX English to Japanese Translator with Progress Bar")

uploaded_file = st.file_uploader("Upload a PPTX file", type=["pptx"])

if uploaded_file is not None:
    st.success("File uploaded successfully.")
    
    if st.button("Translate to Japanese"):
        with st.spinner("Translating... please wait..."):
            translated_pptx = translate_pptx(uploaded_file)
        
        st.success("Translation complete!")
        
        st.download_button(
            label="Download Translated PPTX",
            data=translated_pptx,
            file_name="translated_presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )