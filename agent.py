"""LLM + SQL Agent logic."""
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent

from config import settings, _langsmith_config
from db import get_database

# Global agent instance (singleton)
_AGENT = None


def get_llm() -> ChatOpenAI:
    """Create and return ChatOpenAI LLM instance."""
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=settings.require_openai_api_key(),
    )


def build_sql_system_prompt(db_name: str, top_k: int = 5) -> str:
    """Build system prompt for SQL agent."""
    return f"""
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {db_name} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
"""


def get_agent():
    """Get or create SQL agent singleton."""
    global _AGENT
    if _AGENT is not None:
        return _AGENT

    llm = get_llm()
    db = get_database()
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    system_prompt = build_sql_system_prompt(db_name=settings.db_name)

    _AGENT = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type="tool-calling",
        system_prompt=system_prompt,
        verbose=False,
        # If you want more observability from the executor, you can set:
        # return_intermediate_steps=True,
    )
    return _AGENT


def answer_question(
    question: str,
    request_id: int | str | None = None,
    session_id: int | str | None = None,
) -> str:
    """Run SQL agent on a question and return the answer."""
    agent = get_agent()
    user_msg = f"{question}\n(Use LIMIT <= {settings.default_limit}.)"
    result = agent.invoke(
        {"input": user_msg},
        config=_langsmith_config(request_id, session_id),
    )
    return (result.get("output") or "").strip()
