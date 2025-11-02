import streamlit as st
import os
from dotenv import load_dotenv
from scraper import fetch_html_with_info
from cleaner import clean_html, get_html_stats, extract_text_content
from extractor import extract_tabular_data, dataframe_to_json
import pandas as pd

load_dotenv()

st.set_page_config(
    page_title="Web Scraper & Data Extractor",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'html_content' not in st.session_state:
    st.session_state.html_content = None
if 'cleaned_html' not in st.session_state:
    st.session_state.cleaned_html = None
if 'page_info' not in st.session_state:
    st.session_state.page_info = None
if 'extraction_result' not in st.session_state:
    st.session_state.extraction_result = None


def main():
    with st.sidebar:
        st.title("⚙️ Configuration")
        groq_api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=os.getenv("GROQ_API_KEY", ""),
            help="Enter your Groq API key. You can get one from https://console.groq.com/"
        )
        if groq_api_key:
            st.success("✓ API Key configured")
        else:
            st.warning("⚠️ API Key required for data extraction")
        model_name = st.selectbox(
            "Groq Model",
            options=[
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "llama-3-groq-8b-tool-use",
                "llama-3.2-11b-versatile",
                "llama-3.2-3b-instruct",
                "gemma2-9b-it",
                "mixtral-8x7b-32768",
            ],
            index=0,
            help="Select the Groq model to use for extraction. Smaller models use fewer tokens and are better for free tier."
        )
        st.divider()
        st.markdown("""
        ### 📖 How to Use
        1. Go to **Scrape Website** tab
        2. Enter a website URL
        3. Click **Fetch & Clean**
        4. Review the cleaned HTML
        5. Go to **Extract Data** tab
        6. Enter what data you want to extract
        7. Click **Extract Information**
        8. View and download results
        """)
    tab1, tab2 = st.tabs(["🔍 Scrape Website", "📊 Extract Data"])
    with tab1:
        st.title("Website Scraper")
        st.markdown("Enter a website URL to fetch and clean its HTML content.")
        col1, col2 = st.columns([4, 1])
        with col1:
            url_input = st.text_input(
                "Website URL",
                placeholder="https://example.com",
                label_visibility="collapsed"
            )
        with col2:
            fetch_button = st.button("Fetch & Clean", type="primary", use_container_width=True)
        if fetch_button:
            if not url_input:
                st.error("Please enter a URL")
            else:
                with st.spinner("Fetching website content..."):
                    try:
                        page_info = fetch_html_with_info(url_input, headless=True)
                        st.session_state.page_info = page_info
                        cleaned_html = clean_html(page_info['html'], preserve_structure=True)
                        st.session_state.cleaned_html = cleaned_html
                        st.session_state.html_content = page_info['html']
                        st.success(f"✓ Successfully fetched: {page_info['title']}")
                    except Exception as e:
                        st.error(f"Error fetching website: {str(e)}")
                        st.session_state.page_info = None
                        st.session_state.cleaned_html = None
                        st.session_state.html_content = None
        if st.session_state.page_info and st.session_state.cleaned_html:
            st.divider()
            st.subheader("📄 Page Information")
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("Page Title", st.session_state.page_info['title'])
            with info_col2:
                st.metric("Final URL", st.session_state.page_info['url'][:50] + "..." if len(st.session_state.page_info['url']) > 50 else st.session_state.page_info['url'])
            with info_col3:
                stats = get_html_stats(st.session_state.cleaned_html)
                st.metric("Elements", stats['element_count'])
            with st.expander("📈 HTML Statistics", expanded=False):
                stats = get_html_stats(st.session_state.cleaned_html)
                stats_col1, stats_col2 = st.columns(2)
                with stats_col1:
                    st.metric("Total Elements", stats['element_count'])
                    st.metric("Text Length", f"{stats['text_length']:,} characters")
                    st.metric("Cleaned HTML Length", f"{stats['cleaned_html_length']:,} characters")
                with stats_col2:
                    st.metric("Links", stats['link_count'])
                    st.metric("Images", stats['image_count'])
                    st.metric("Tables", stats['table_count'])
            with st.expander("🧹 Cleaned HTML Content", expanded=False):
                st.code(st.session_state.cleaned_html, language="html")
                st.download_button(
                    label="Download Cleaned HTML",
                    data=st.session_state.cleaned_html,
                    file_name="cleaned_html.html",
                    mime="text/html"
                )
            with st.expander("📝 Text Content Only", expanded=False):
                text_content = extract_text_content(st.session_state.cleaned_html)
                st.text_area("Extracted Text", text_content, height=300, disabled=True)
                st.download_button(
                    label="Download Text Content",
                    data=text_content,
                    file_name="extracted_text.txt",
                    mime="text/plain"
                )
    with tab2:
        st.title("Data Extractor")
        st.markdown("Extract specific information from the scraped HTML in tabular format using AI.")
        if not st.session_state.cleaned_html:
            st.warning("⚠️ Please scrape a website first in the 'Scrape Website' tab.")
            st.info("💡 Example queries:\n- Extract all product names and prices\n- Get all table data\n- Extract contact information\n- List all links with their text")
        else:
            st.subheader("What would you like to extract?")
            user_query = st.text_area(
                "Extraction Query",
                placeholder="e.g., Extract all product names, prices, and descriptions from the page",
                height=100,
                help="Describe what information you want to extract from the HTML. Be specific about the data you need."
            )
            with st.expander("💡 Example Queries"):
                example_queries = [
                    "Extract all product names and prices",
                    "Get all table data from HTML tables",
                    "Extract all contact information (email, phone, address)",
                    "List all links with their anchor text and URLs",
                    "Extract all headings (h1, h2, h3) with their text",
                    "Get all image URLs and alt text",
                    "Extract all prices and currency information"
                ]
                for query in example_queries:
                    if st.button(query, key=f"example_{query}", use_container_width=True):
                        st.session_state.example_query = query
                        st.rerun()
            if 'example_query' in st.session_state:
                user_query = st.session_state.example_query
                del st.session_state.example_query
                st.rerun()
            extract_button = st.button("Extract Information", type="primary", use_container_width=True)
            if extract_button:
                if not user_query:
                    st.error("Please enter an extraction query")
                elif not groq_api_key:
                    st.error("Please configure your Groq API key in the sidebar")
                else:
                    with st.spinner("🤖 AI is analyzing the HTML and extracting data..."):
                        result = extract_tabular_data(
                            html_content=st.session_state.cleaned_html,
                            user_query=user_query,
                            groq_api_key=groq_api_key,
                            model_name=model_name
                        )
                        st.session_state.extraction_result = result
            if st.session_state.extraction_result:
                result = st.session_state.extraction_result
                if result['success']:
                    st.divider()
                    st.subheader("📊 Extracted Data")
                    st.markdown("### 🔢 API Usage (This Response)")
                    usage = result.get('usage', {})
                    if usage and usage.get('total_tokens', 0) > 0:
                        usage_col1, usage_col2, usage_col3, usage_col4 = st.columns(4)
                        with usage_col1:
                            st.metric("Total Tokens", f"{usage.get('total_tokens', 0):,}")
                        with usage_col2:
                            st.metric("Prompt Tokens", f"{usage.get('prompt_tokens', 0):,}")
                        with usage_col3:
                            st.metric("Completion Tokens", f"{usage.get('completion_tokens', 0):,}")
                        with usage_col4:
                            tpm_limit = usage.get('tpm_limit', 0)
                            st.metric("TPM Limit", f"{tpm_limit:,}")
                        st.caption("💡 TPM = Tokens Per Minute limit for this model (resets every minute on Groq's side)")
                        if tpm_limit > 0:
                            pct_used = (usage.get('total_tokens', 0) / tpm_limit) * 100
                            if pct_used > 80:
                                st.warning(f"⚠️ This request used {pct_used:.1f}% of your TPM limit. Multiple requests may hit the rate limit.")
                            elif pct_used > 50:
                                st.info(f"ℹ️ This request used {pct_used:.1f}% of your TPM limit.")
                    elif usage and usage.get('error'):
                        st.warning(f"⚠️ Could not retrieve usage information: {usage.get('error')}")
                        if st.checkbox("Show debug info", key="show_usage_debug"):
                            st.json(usage)
                    else:
                        st.info("📊 Usage information not available for this response.")
                        st.caption("💡 This may be normal depending on the API response format. The extraction completed successfully.")
                        if usage and st.checkbox("Show raw usage data", key="show_raw_usage"):
                            st.json(usage)
                    if result['description']:
                        st.info(f"ℹ️ {result['description']}")
                    df = result['dataframe']
                    if not df.empty:
                        st.markdown("### Interactive Dataframe")
                        st.dataframe(df, use_container_width=True)
                        st.divider()
                        st.subheader("💾 Download Options")
                        download_col1, download_col2 = st.columns(2)
                        with download_col1:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name="extracted_data.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with download_col2:
                            json_str = dataframe_to_json(df, orient='records')
                            st.download_button(
                                label="📥 Download JSON",
                                data=json_str,
                                file_name="extracted_data.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        with st.expander("📈 Data Statistics"):
                            st.metric("Rows", len(df))
                            st.metric("Columns", len(df.columns))
                            st.write("**Columns:**", ", ".join(df.columns.tolist()))
                    else:
                        st.warning("No data was extracted. Try refining your query.")
                else:
                    st.error(f"❌ Extraction failed: {result['error']}")
                    st.info("💡 Tips:\n- Make sure your Groq API key is valid\n- Try rephrasing your query\n- The HTML might not contain the requested information")


if __name__ == "__main__":
    main()
