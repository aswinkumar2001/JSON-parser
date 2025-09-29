import streamlit as st
import json
import pandas as pd
from io import BytesIO
import datetime

st.set_page_config(page_title="JSON Data Extractor", page_icon="📊", layout="wide")

st.title("📊 JSON Data Extractor")

# Sidebar for additional options
with st.sidebar:
    st.header("Settings")
    show_raw_json = st.checkbox("Show raw JSON structure", value=False)
    auto_select_all = st.checkbox("Auto-select all keys", value=False)

# Allow user to upload the JSON file# Allow user to upload the JSON file (replace the existing uploader line)
uploaded_file = st.file_uploader("Upload your JSON file", type=["json", "txt"], help="Upload a JSON file or a text file containing JSON data.")

if uploaded_file is not None:
    try:
        # Load the JSON data
        json_data = json.load(uploaded_file)
        
        if show_raw_json:
            with st.expander("Raw JSON Structure"):
                st.json(json_data)
        
        # Extract the 'data' list
        data_list = json_data.get("data", [])
        
        if not data_list:
            st.error("No 'data' key found or it is empty in the JSON.")
            # Alternative: check if the root is already a list
            if isinstance(json_data, list):
                data_list = json_data
                st.info("Using root array as data source.")
            else:
                # Show available keys to help user
                available_keys = list(json_data.keys())
                st.info(f"Available keys in JSON: {', '.join(available_keys)}")
        else:
            # Collect all unique keys from the data items with data types
            keys_info = {}
            for item in data_list:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key not in keys_info:
                            keys_info[key] = set()
                        keys_info[key].add(type(value).__name__)
            
            if not keys_info:
                st.error("No dictionary items found in the 'data' array.")
            else:
                # Display keys with their data types
                st.subheader("Available Keys")
                
                keys_list = sorted(list(keys_info.keys()))
                default_keys = keys_list if auto_select_all else []
                
                # Multi-select for keys with type information
                selected_keys = st.multiselect(
                    "Select keys to retrieve",
                    options=keys_list,
                    default=default_keys,
                    format_func=lambda x: f"{x} ({', '.join(keys_info[x])})"
                )
                
                if selected_keys:
                    # Prepare data for DataFrame
                    df_data = []
                    for item in data_list:
                        if isinstance(item, dict):
                            row = {}
                            for key in selected_keys:
                                value = item.get(key, None)
                                # Handle nested dictionaries or lists
                                if isinstance(value, (dict, list)):
                                    value = json.dumps(value)
                                row[key] = value
                            df_data.append(row)
                    
                    if df_data:
                        df = pd.DataFrame(df_data, columns=selected_keys)
                        
                        # Display statistics
                        st.subheader("Data Overview")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Records", len(df))
                        with col2:
                            st.metric("Selected Columns", len(selected_keys))
                        with col3:
                            st.metric("Total Cells", len(df) * len(selected_keys))
                        
                        # Data preview with expander
                        with st.expander("Preview Data", expanded=True):
                            st.dataframe(df, use_container_width=True)
                        
                        # Data summary
                        with st.expander("Data Summary"):
                            st.write("Column Overview:")
                            summary_data = []
                            for col in df.columns:
                                non_null = df[col].count()
                                null_count = len(df) - non_null
                                dtype = str(df[col].dtype)
                                unique_count = df[col].nunique()
                                summary_data.append({
                                    'Column': col,
                                    'Non-Null': non_null,
                                    'Null': null_count,
                                    'Data Type': dtype,
                                    'Unique Values': unique_count
                                })
                            st.dataframe(pd.DataFrame(summary_data))
                        
                        # Download section
                        st.subheader("Download Options")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Excel download
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            excel_filename = f"extracted_data_{timestamp}.xlsx"
                            
                            output_excel = BytesIO()
                            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, sheet_name='Data')
                                # Add summary sheet
                                summary_df = pd.DataFrame(summary_data)
                                summary_df.to_excel(writer, index=False, sheet_name='Summary')
                            output_excel.seek(0)
                            
                            st.download_button(
                                label="📥 Download as Excel",
                                data=output_excel,
                                file_name=excel_filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="Download data as Excel file with data and summary sheets"
                            )
                        
                        with col2:
                            # CSV download
                            csv_filename = f"extracted_data_{timestamp}.csv"
                            output_csv = BytesIO()
                            df.to_csv(output_csv, index=False)
                            output_csv.seek(0)
                            
                            st.download_button(
                                label="📥 Download as CSV",
                                data=output_csv,
                                file_name=csv_filename,
                                mime="text/csv",
                                help="Download data as CSV file"
                            )
                    else:
                        st.error("No data items found to extract.")

                    # Duplicate Detection Section
                    st.markdown("---")
                    st.subheader("🔍 Duplicate Detection")
                    
                    # Let user choose which keys to check for duplicates
                    duplicate_check_keys = st.multiselect(
                        "Select keys to check for duplicates",
                        options=selected_keys,
                        default=[selected_keys[0]] if selected_keys else [],
                        help="Select one or more keys to identify duplicate records. Duplicates will be found based on combinations of selected keys."
                    )
                    
                    if duplicate_check_keys:
                        # Create a combined key for duplicate checking
                        if len(duplicate_check_keys) == 1:
                            df['_combined_key'] = df[duplicate_check_keys[0]].astype(str)
                        else:
                            df['_combined_key'] = df[duplicate_check_keys].astype(str).agg(' - '.join, axis=1)
                        
                        # Find duplicates
                        duplicate_mask = df.duplicated(subset=duplicate_check_keys, keep=False)
                        duplicate_records = df[duplicate_mask]
                        unique_duplicate_keys = duplicate_records['_combined_key'].unique()
                        
                        if len(duplicate_records) > 0:
                            st.warning(f"Found {len(duplicate_records)} duplicate records based on {len(unique_duplicate_keys)} unique duplicate combinations")
                            
                            # Create tabs for different views
                            tab1, tab2, tab3 = st.tabs([
                                "📊 Duplicate Summary", 
                                "👀 All Duplicate Entries", 
                                "📥 Download Duplicates"
                            ])
                            
                            with tab1:
                                st.write("**Duplicate Combinations Summary:**")
                                summary_df = duplicate_records.groupby('_combined_key').size().reset_index()
                                summary_df.columns = ['Combined Key', 'Count']
                                summary_df = summary_df.sort_values('Count', ascending=False)
                                st.dataframe(summary_df, use_container_width=True)
                                
                                # Show one example per duplicate group
                                st.write("**Sample from each duplicate group:**")
                                sample_duplicates = duplicate_records.drop_duplicates(subset=duplicate_check_keys)
                                st.dataframe(sample_duplicates[selected_keys], use_container_width=True)
                            
                            with tab2:
                                st.write("**All duplicate entries:**")
                                # Sort by the combined key for better organization
                                duplicate_records_sorted = duplicate_records.sort_values('_combined_key')
                                st.dataframe(duplicate_records_sorted[selected_keys], use_container_width=True)
                                
                                st.write(f"**Total duplicate records:** {len(duplicate_records)}")
                                st.write(f"**Unique duplicate combinations:** {len(unique_duplicate_keys)}")
                            
                            with tab3:
                                # Download duplicate records
                                st.write("Download the duplicate records:")
                                
                                duplicate_excel = BytesIO()
                                with pd.ExcelWriter(duplicate_excel, engine='xlsxwriter') as writer:
                                    duplicate_records[selected_keys].to_excel(writer, index=False, sheet_name='Duplicate_Records')
                                    
                                    # Add summary sheet
                                    summary_df = duplicate_records.groupby('_combined_key').size().reset_index()
                                    summary_df.columns = ['Combined_Key', 'Duplicate_Count']
                                    summary_df = summary_df.sort_values('Duplicate_Count', ascending=False)
                                    summary_df.to_excel(writer, index=False, sheet_name='Duplicate_Summary')
                                
                                duplicate_excel.seek(0)
                                
                                st.download_button(
                                    label="📥 Download Duplicate Report",
                                    data=duplicate_excel,
                                    file_name=f"duplicate_report_{timestamp}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    help="Download Excel file with duplicate records and summary"
                                )
                                
                                # Also offer CSV download for duplicates
                                duplicate_csv = BytesIO()
                                duplicate_records[selected_keys].to_csv(duplicate_csv, index=False)
                                duplicate_csv.seek(0)
                                
                                st.download_button(
                                    label="📥 Download Duplicates as CSV",
                                    data=duplicate_csv,
                                    file_name=f"duplicates_{timestamp}.csv",
                                    mime="text/csv"
                                )
                        else:
                            st.success("✅ No duplicates found based on the selected keys!")
                        
                        # Clean up temporary column
                        df.drop('_combined_key', axis=1, inplace=True, errors='ignore')
    except json.JSONDecodeError:
        # Enhanced error message for TXT files
        if uploaded_file.name.endswith('.txt'):
            st.error("""
            Invalid JSON in text file. Please check:
            - The text file must contain valid JSON format
            - Common issues: missing quotes, trailing commas, or incorrect brackets
            - Try validating your JSON with an online validator
            """)
        else:
            st.error("Invalid JSON file. Please upload a valid JSON.")
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
else:
    # Show instructions when no file is uploaded
    st.info("👆 Please upload a JSON file to get started.")
    
    # Example JSON structure
    with st.expander("💡 Expected JSON Structure"):
        st.write("""
        Your JSON file should have a structure similar to:
        ```json
        {
            "data": [
                {"id": 1, "name": "John", "age": 30},
                {"id": 2, "name": "Jane", "age": 25},
                ...
            ]
        }
        ```
        Alternatively, the file can be a direct array:
        ```json
        [
            {"id": 1, "name": "John", "age": 30},
            {"id": 2, "name": "Jane", "age": 25}
        ]
        ```
        """)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit • JSON Data Extractor")
