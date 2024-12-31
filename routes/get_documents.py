# from fastapi import APIRouter, HTTPException
# from fastapi.responses import JSONResponse
# from db_config import get_db_connection

# router = APIRouter()

# @router.get("/get_documents/")
# async def get_documents():
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM row_document")
#         rows = cursor.fetchall()
#         cursor.close()
#         conn.close()
#         return JSONResponse(
#             content={"name": rows},
#             status_code=200,
#         )
#     except Exception as error:
#         print(f"Error: {error}")
#         raise HTTPException(status_code=500, detail="Internal server error.")



from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from db_config import get_db_connection
from datetime import date

router = APIRouter()

@router.get("/get_documents/")
async def get_documents():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM row_document")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            row_data = list(row)
            for i, value in enumerate(row_data):
                if isinstance(value, date):
                    row_data[i] = value.strftime('%Y-%m-%d')
            result.append(tuple(row_data))
        cursor.close()
        conn.close()
        return JSONResponse(
            content={"name": result},
            status_code=200,
        )

    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail="Internal server error.")
