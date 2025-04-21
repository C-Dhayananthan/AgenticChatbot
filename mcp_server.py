# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from mcp.server.fastmcp import Context, FastMCP
from db_utilities.mongo_implementation import MongoImplement
from logging import Logger, StreamHandler, Formatter, INFO
from datetime import datetime
from typing import Optional, List
mcp = FastMCP("MongoDB", dependencies=["pymongo"])
logger = Logger(__name__, level=INFO)
# Create a handler to output logs to the console
console_handler = StreamHandler()

# Set a formatter for the logs
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)
@dataclass
class AppContext:
    db: MongoImplement


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    logger.info("Starting MongoDB connection...")
    db = MongoImplement(
        connection_string="mongodb://localhost:27017/",
        db_name="fundaura",
        max_pool=5,
        server_selection_timeout=60000
    )
    try:
        yield AppContext(db=db)
    finally:
        # Cleanup resources if needed
        db.client.close()
        print("Closed MongoDB connection")

mcp = FastMCP("MongoDB", lifespan=app_lifespan)

# # Access type-safe lifespan context in tools
# @mcp.tool(name="mongdb_query")
# def query_db(ctx: Context, collection_name: str, query: dict, start ) -> list:
#     """Query the transactions collection in MongoDB. Each document represents a financial transaction and includes the following fields:

#         user_id (int): ID of the user who made the transaction

#         transaction_id (int): Unique identifier for the transaction

#         acc_details (string): Masked account number (e.g., "ac x007")

#         bank_name (string): Name of the bank involved

#         merchant_name (string): Name of the merchant

#         expense_type (string): Optional subtype of the transaction

#         amount (float): Amount spent in the transaction

#         date (ISODate): Transaction date

#         message (string): Optional message or description

#         category (string): Category of the transaction (e.g., Food, Travel)

#         created_at (ISODate): Document creation timestamp

#         Note: date refers to the actual transaction date use ISO date for queries, while created_at refers to the time the document was stored in the database. Do not confuse the two.

#         Use this tool to:
#         Filter transactions by user, date, amount, category, etc.
#         Analyze spending patterns across banks, merchants, or timeframes"""
#     db :MongoImplement = ctx.request_context.lifespan_context.db
#     result = list(db.read(collection_name, query))
#     if result:
#         print(f"Querying Collection  {collection_name} with query {query} and result {result}")
#         return result
#     else: 
#         return "No transction found for given query "

# @mcp.tool(name="mongodb_find_query")
# def query_db_find(ctx: Context, collection_name: str, query: dict, start: Optional[str] = None, end: Optional[str] = None) -> list:
#     """
#     Perform a simple MongoDB `.find()` query on the 'transactions' collection.

#     This collection contains documents representing financial transactions. Each document includes:

#         user_id (int): ID of the user who made the transaction
#         transaction_id (int): Unique identifier for the transaction
#         acc_details (string): Masked account number (e.g., "ac x007")
#         bank_name (string): Name of the bank where the transaction occurred
#         merchant_name (string): Name of the merchant or vendor
#         expense_type (string): Optional expense subtype (can be empty)
#         amount (float): Amount spent in the transaction
#         date (ISODate): Date of the actual transaction
#         message (string): Optional description or message (can be empty)
#         category (string): Category of the transaction (e.g., Food, Travel)
#         created_at (ISODate): Timestamp when the transaction was recorded in the database

#     ⚠️ Note:
#         - Use `date` for filtering based on the real transaction time.
#         - `created_at` is when the document was saved in the DB (not the transaction time).

#     Parameters:
#         - query (dict): Standard MongoDB query
#         - start (str, optional): Start of date range (ISO format)
#         - end (str, optional): End of date range (ISO format)

#     Automatically adds date filtering if `start` and `end` are given.

#     Returns:
#         - A list of matching transaction documents
#     """
#     db: MongoImplement = ctx.request_context.lifespan_context.db

#     if start and end:
#         try:
#             start_dt = datetime.fromisoformat(start)
#             end_dt = datetime.fromisoformat(end)
#             query["date"] = {"$gte": start_dt, "$lt": end_dt}
#         except Exception as e:
#             return f"Invalid date format. Use ISO format (e.g., '2025-04-19T00:00:00'). Error: {str(e)}"

#     result = list(db.read(collection_name, query))
#     return result if result else "No transaction found for the given query."

@mcp.tool(name="mongodb_aggregate_query")
def query_db_aggregate(ctx: Context,  pipeline: List[dict], start: Optional[str] = None, end: Optional[str] = None) -> list:
    """
    Perform an aggregation pipeline query on the 'transactions' collection.

    Documents in this collection contain:

        user_id (int): ID of the user who made the transaction
        transaction_id (int): Unique identifier for the transaction
        acc_details (string): Masked account number (e.g., "ac x007")
        bank_name (string): Name of the bank involved
        merchant_name (string): Name of the merchant
        expense_type (string): Optional subtype of the transaction(Credit/Debit)
        amount (float): Amount spent in the transaction
        date (ISODate): Date the transaction happened
        message (string): Optional message/description
        category (string): Transaction category (e.g., Food, Travel)
        created_at (ISODate): Timestamp when the document was added to the DB

    Use this tool for:
        - Aggregating total spending
        - Grouping transactions by category, bank, merchant, etc.
        - Time-based analysis
        - Filtering by transaction date using optional start and end dates

    Parameters:
        - pipeline (List[dict]): MongoDB aggregation pipeline stages
        - start (str, optional): Start of date filter (ISO format)
        - end (str, optional): End of date filter (ISO format)

    If `start` and `end` are provided, a `$match` stage on the `date` field is automatically added at the beginning of the pipeline.
    So you no longer need to include a `$match` stage for date filtering in your pipeline.
    Example pipeline:
        [
            { "$match": { "user_id": 111 } },
            { "$group": { "_id": "$category", "totalAmount": { "$sum": "$amount" } } }
        ]

    Returns:
        - Aggregation result list
    """
    db: MongoImplement = ctx.request_context.lifespan_context.db
    final_pipeline = []

    if start and end:
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            final_pipeline.append({
                "$match": {
                    "date": {
                        "$gte": start_dt,
                        "$lt": end_dt
                    }
                }
            })
        except Exception as e:
            return f"Invalid date format. Use ISO format (e.g., '2025-04-19T00:00:00'). Error: {str(e)}"

    final_pipeline.extend(pipeline)
    transactions = db.client["fundaura"]["transactions"]
    result = list(transactions.aggregate(final_pipeline))
    return result if result else "No results found for the aggregation."


if __name__ == "__main__":
    mcp.run(transport="stdio")