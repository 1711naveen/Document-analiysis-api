from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import os
import io
from mammoth import extract_raw_text
from db_config import get_db_connection  # Importing get_db_connection from your db_config module
import logging

router = APIRouter()


@router.get("/openfile/", response_class=HTMLResponse)
async def get_document(final_doc_id: str, file: str):
    """
    API endpoint to fetch and process a document (text or .docx) by final_doc_id and file name.
    """
    try:
        # Fetch file data from the database
        file_data = get_file_data_from_database(final_doc_id)

        if not file_data or not file_data.get("final_doc_url"):
            raise HTTPException(status_code=404, detail="File not found in the database")

        # Construct the full file path
        folder_path = os.path.join(os.getcwd(), "output", final_doc_id)
        file_path = os.path.join(folder_path, file)

        # Check if the file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # Read the file content
        with open(file_path, "rb") as f:
            file_buffer = f.read()

        # Process the file based on its type
        if file.endswith(".docx"):
            # Handle .docx files using Mammoth
            file_stream = io.BytesIO(file_buffer)  # Create a file-like object from the binary content
            result = extract_raw_text(file_stream)  # Extract text using Mammoth
            text = result.value  # Get the extracted plain text
        elif file.endswith(".txt"):
            
            try:
                # Attempt to decode as UTF-8 first
                text = file_buffer.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    # Fallback to decoding as ISO-8859-1 (Latin-1)
                    text = file_buffer.decode("iso-8859-1")
                except UnicodeDecodeError as e:
                    logging.error(f"Error decoding text file: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="Text file encoding not supported. Please ensure the file uses UTF-8 or a common encoding."
                    )
                    
        else:
            # Unsupported file type
            raise HTTPException(status_code=400, detail="Unsupported file type. Only .docx and .txt are allowed.")

        # Format the extracted or read text into HTML
        html_content = generate_html(format_text(text))

        # Return the HTML response
        return HTMLResponse(content=html_content, status_code=200)

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail="Server error")


def get_file_data_from_database(final_doc_id: str):
    """
    Fetch file data from the database using the provided final_doc_id.
    """
    try:
        conn = get_db_connection()  # Use the database connection from db_config
        cursor = conn.cursor(dictionary=True)
        query = "SELECT final_doc_url FROM final_document WHERE row_doc_id = %s"
        cursor.execute(query, (final_doc_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        logging.error(f"Database error: {e}")
        return None


def format_text(text):
    """
    Format plain text into paragraphs wrapped in <p> tags for HTML display.
    """
    return "\n".join(
        f"<p>{line.strip()}</p>"
        for line in text.strip().split("\n") if line.strip()
    )


def generate_html(content):
    """
    Generate an HTML page to display the document content.
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Document Viewer</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          line-height: 1.6;
          margin: 2rem auto;
          max-width: 800px;
          padding: 1rem;
          background-color: #f9f9f9;
          color: #333;
        }}
        p {{
          margin-bottom: 1.5rem;
        }}
      </style>
    </head>
    <body>
      <h1>Document Content</h1>
      {content}
    </body>
    </html>
    """



582. Kill Process
Medium
Topics
Companies
You have n processes forming a rooted tree structure. You are given two integer arrays pid and ppid, where pid[i] is the ID of the ith process and ppid[i] is the ID of the ith process's parent process.

Each process has only one parent process but may have multiple children processes. Only one process has ppid[i] = 0, which means this process has no parent process (the root of the tree).

When a process is killed, all of its children processes will also be killed.

Given an integer kill representing the ID of a process you want to kill, return a list of the IDs of the processes that will be killed. You may return the answer in any order.

 

Example 1:

Input: pid = [1,3,10,5], ppid = [3,0,5,3], kill = 5 

process-0 : id-1 parent-3
process-1 : id-3 parent-0
process-2 : id-10 parent-5
process-3 : id-5 parent-3

Output: [5,10]
Explanation: The processes colored in red are the processes that should be killed.



Example 2:

Input: pid = [1], ppid = [0], kill = 1
Output: [1]
 

class Graph{
    int n;
    List<List<Integer>> adjList;
    
    public Graph(int size){
        n=size;
        adjList=new ArrayList<>();
        for(int i=0;i<n;i++){
            adjList.add(new ArrayList<>());
        }
    }
    
    
}
 
class Solution {
    public List<Integer> killProcess(List<Integer> pid, List<Integer> ppid, int kill) {
        
    }
}