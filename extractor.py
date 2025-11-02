from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import re
import pandas as pd
from bs4 import BeautifulSoup
from cleaner import extract_text_content


class TableRow(BaseModel):
    data: Dict[str, Any] = Field(description="Dictionary of column names and their values")


class ExtractedTable(BaseModel):
    columns: List[str] = Field(description="List of column names for the table")
    rows: List[TableRow] = Field(description="List of rows, each containing data dictionary")
    description: Optional[str] = Field(default=None, description="Description of what was extracted")


def get_token_limit_for_model(model_name: str) -> int:
    free_tier_limits = {
        "llama-3.1-8b-instant": 4000,
        "llama-3.3-70b-versatile": 8000,
        "llama-3-groq-8b-tool-use": 4000,
        "llama-3-groq-70b-tool-use": 8000,
        "mixtral-8x7b-32768": 8000,
        "gemma2-9b-it": 4000,
        "llama-3.2-3b-instruct": 4000,
        "llama-3.2-11b-versatile": 5000,
    }
    return free_tier_limits.get(model_name, 5000)


def get_tpm_limit_for_model(model_name: str) -> int:
    tpm_limits = {
        "llama-3.1-8b-instant": 6000,
        "llama-3.3-70b-versatile": 30000,
        "llama-3-groq-8b-tool-use": 6000,
        "llama-3-groq-70b-tool-use": 30000,
        "mixtral-8x7b-32768": 30000,
        "gemma2-9b-it": 6000,
        "llama-3.2-3b-instruct": 6000,
        "llama-3.2-11b-versatile": 14000,
    }
    return tpm_limits.get(model_name, 14000)


def smart_content_reduction(html_content: str, max_chars: int, user_query: str) -> str:
    if len(html_content) <= max_chars:
        return html_content
    soup = BeautifulSoup(html_content, 'lxml')
    query_lower = user_query.lower()
    if any(word in query_lower for word in ['table', 'data', 'row', 'column', 'list', 'product']):
        tables = soup.find_all('table')
        if tables:
            table_html = '\n'.join([str(table) for table in tables])
            if len(table_html) <= max_chars:
                return table_html
    main_content = None
    selectors = ['main', 'article', '[role="main"]', '#content', '.content', 'body']
    for selector in selectors:
        if selector.startswith('[') or selector.startswith('.') or selector.startswith('#'):
            main_content = soup.select_one(selector)
        else:
            main_content = soup.find(selector)
        if main_content:
            main_html = str(main_content)
            if len(main_html) <= max_chars:
                return main_html
            break
    text_content = extract_text_content(html_content)
    if len(text_content) > max_chars:
        truncated = text_content[:max_chars]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        cut_point = max(last_period, last_newline)
        if cut_point > max_chars * 0.8:
            text_content = truncated[:cut_point + 1]
        else:
            text_content = truncated + "... [Content truncated]"
    return text_content


def create_extraction_chain(groq_api_key: str, model_name: str = "llama-3.1-8b-instant"):
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=model_name,
        temperature=0.1
    )
    parser = PydanticOutputParser(pydantic_object=ExtractedTable)
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a data extraction assistant. Extract information from the content and return it in the EXACT JSON format specified below.

CRITICAL: Follow this format EXACTLY:
- "columns" must be a list of strings (e.g., ["Name", "Price", "Description"])
- "rows" must be a list of objects, each with a "data" key containing a dictionary
- Each row's "data" dictionary should have keys matching the column names
- "description" is optional and should be a string

Example format:
{{
  "columns": ["Product", "Price", "Stock"],
  "rows": [
    {{"data": {{"Product": "Widget A", "Price": "$10", "Stock": "50"}}}},
    {{"data": {{"Product": "Widget B", "Price": "$20", "Stock": "30"}}}}
  ],
  "description": "Extracted product information"
}}

{format_instructions}"""),
        ("human", """Content:
{html_content}

Query: {user_query}

Extract the information matching the query and return it in the EXACT JSON format specified above.""")
    ])
    return llm, parser, prompt_template


def extract_tabular_data(
    html_content: str,
    user_query: str,
    groq_api_key: str,
    model_name: str = "llama-3.1-8b-instant"
) -> Dict[str, Any]:
    try:
        llm, parser, prompt_template = create_extraction_chain(groq_api_key, model_name)
        format_instructions = parser.get_format_instructions()
        token_limit = get_token_limit_for_model(model_name)
        max_content_chars = int(token_limit * 4 * 0.6)
        reduced_content = smart_content_reduction(html_content, max_content_chars, user_query)
        content_reduced = len(html_content) > len(reduced_content)
        if content_reduced and not ('<' in reduced_content and '>' in reduced_content):
            reduced_content = f"[Text content extracted from HTML for efficiency]\n\n{reduced_content}"
        prompt = prompt_template.format_messages(
            html_content=reduced_content,
            user_query=user_query,
            format_instructions=format_instructions
        )
        response = llm.invoke(prompt)
        usage_info = {}
        try:
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                if metadata and isinstance(metadata, dict):
                    if 'usage' in metadata and isinstance(metadata['usage'], dict):
                        usage_info = {
                            'prompt_tokens': metadata['usage'].get('prompt_tokens', 0),
                            'completion_tokens': metadata['usage'].get('completion_tokens', 0),
                            'total_tokens': metadata['usage'].get('total_tokens', 0),
                        }
                    elif 'prompt_tokens' in metadata or 'total_tokens' in metadata:
                        usage_info = {
                            'prompt_tokens': metadata.get('prompt_tokens', 0),
                            'completion_tokens': metadata.get('completion_tokens', 0),
                            'total_tokens': metadata.get('total_tokens', 0),
                        }
            if not usage_info and hasattr(response, 'usage_metadata'):
                usage_metadata = response.usage_metadata
                if usage_metadata:
                    if isinstance(usage_metadata, dict):
                        usage_info = {
                            'prompt_tokens': usage_metadata.get('prompt_tokens', 0),
                            'completion_tokens': usage_metadata.get('completion_tokens', 0),
                            'total_tokens': usage_metadata.get('total_tokens', 0),
                        }
                    else:
                        usage_info = {
                            'prompt_tokens': getattr(usage_metadata, 'prompt_tokens', 0),
                            'completion_tokens': getattr(usage_metadata, 'completion_tokens', 0),
                            'total_tokens': getattr(usage_metadata, 'total_tokens', 0),
                        }
            if not usage_info and hasattr(response, 'llm_output'):
                llm_output = response.llm_output
                if llm_output and isinstance(llm_output, dict):
                    if 'token_usage' in llm_output:
                        token_usage = llm_output['token_usage']
                        usage_info = {
                            'prompt_tokens': token_usage.get('prompt_tokens', 0),
                            'completion_tokens': token_usage.get('completion_tokens', 0),
                            'total_tokens': token_usage.get('total_tokens', 0),
                        }
                    elif 'usage' in llm_output:
                        usage = llm_output['usage']
                        if isinstance(usage, dict):
                            usage_info = {
                                'prompt_tokens': usage.get('prompt_tokens', 0),
                                'completion_tokens': usage.get('completion_tokens', 0),
                                'total_tokens': usage.get('total_tokens', 0),
                            }
            if not usage_info and hasattr(response, 'additional_kwargs'):
                additional_kwargs = response.additional_kwargs
                if isinstance(additional_kwargs, dict):
                    if 'usage' in additional_kwargs:
                        usage = additional_kwargs['usage']
                        if isinstance(usage, dict):
                            usage_info = {
                                'prompt_tokens': usage.get('prompt_tokens', 0),
                                'completion_tokens': usage.get('completion_tokens', 0),
                                'total_tokens': usage.get('total_tokens', 0),
                            }
        except Exception as e:
            usage_info = {'error': str(e)}
        try:
            parsed_output = parser.parse(response.content)
        except Exception as parse_error:
            try:
                response_text = response.content
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
                response_json = json.loads(response_text)
                if isinstance(response_json.get('columns'), dict):
                    if 'data' in response_json['columns']:
                        response_json['columns'] = response_json['columns']['data']
                    else:
                        response_json['columns'] = list(response_json['columns'].keys()) if response_json['columns'] else []
                if not isinstance(response_json.get('columns'), list):
                    if 'rows' in response_json and response_json['rows']:
                        first_row = response_json['rows'][0]
                        if isinstance(first_row, dict):
                            row_data = first_row.get('data', first_row)
                            if isinstance(row_data, dict):
                                response_json['columns'] = list(row_data.keys())
                            else:
                                response_json['columns'] = []
                    else:
                        response_json['columns'] = []
                if 'rows' in response_json and isinstance(response_json['rows'], list):
                    fixed_rows = []
                    for row in response_json['rows']:
                        if isinstance(row, dict):
                            if 'data' in row:
                                fixed_rows.append(row)
                            else:
                                fixed_rows.append({'data': row})
                    response_json['rows'] = fixed_rows
                parsed_output = ExtractedTable(**response_json)
            except Exception as fix_error:
                error_msg = f"Failed to parse LLM response. Original error: {str(parse_error)}. "
                error_msg += f"Attempted fix also failed: {str(fix_error)}. "
                error_msg += f"LLM response: {response.content[:500]}"
                raise ValueError(error_msg)
        if parsed_output.rows:
            data_list = [row.data for row in parsed_output.rows]
            df = pd.DataFrame(data_list)
            if parsed_output.columns:
                existing_columns = [col for col in parsed_output.columns if col in df.columns]
                if existing_columns:
                    df = df[existing_columns]
            if not usage_info or 'error' not in usage_info:
                if not usage_info:
                    usage_info = {}
                usage_info['tpm_limit'] = get_tpm_limit_for_model(model_name)
            return {
                'success': True,
                'data': parsed_output.dict(),
                'dataframe': df,
                'description': parsed_output.description,
                'usage': usage_info,
                'error': None
            }
        else:
            empty_df = pd.DataFrame(columns=parsed_output.columns if parsed_output.columns else [])
            if not usage_info or 'error' not in usage_info:
                if not usage_info:
                    usage_info = {}
                usage_info['tpm_limit'] = get_tpm_limit_for_model(model_name)
            return {
                'success': True,
                'data': parsed_output.dict(),
                'dataframe': empty_df,
                'description': parsed_output.description or "No data found matching the query",
                'usage': usage_info,
                'error': None
            }
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'dataframe': None,
            'description': None,
            'usage': {},
            'error': str(e)
        }


def dataframe_to_json(df: pd.DataFrame, orient: str = 'records') -> str:
    return df.to_json(orient=orient, indent=2)
