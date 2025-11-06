import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

# Get Postgres connection string from environment
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")

# Note: This checkpointer is optional - LangGraph API manages checkpointing automatically
# Only use this for standalone deployments or when explicitly enabled
if not POSTGRES_CONNECTION_STRING:
    # Don't raise error - let LangGraph API handle it if connection string is missing
    print("[WARNING] POSTGRES_CONNECTION_STRING not set - checkpointer will not be available")
    print("[INFO] LangGraph API will manage checkpointing automatically if running in managed environment")

# Create a singleton instance for use in the agent
# PostgresSaver.from_conn_string() returns a context manager, so we need to
# enter it and keep the instance alive for the lifetime of the application
_checkpointer_instance = None
_checkpointer_context = None

def get_checkpointer_instance():
    """
    Get or create a singleton checkpointer instance.
    This ensures we reuse the same connection pool.
    
    According to LangGraph docs, PostgresSaver.from_conn_string() returns
    a context manager. We enter it once and keep it alive.
    
    Returns:
        PostgresSaver instance (already entered context)
        
    Raises:
        ValueError: If POSTGRES_CONNECTION_STRING is not set
    """
    global _checkpointer_instance, _checkpointer_context
    
    if not POSTGRES_CONNECTION_STRING:
        raise ValueError("POSTGRES_CONNECTION_STRING must be set to use custom checkpointer")
    
    if _checkpointer_instance is None:
        # Get the context manager
        context_manager = PostgresSaver.from_conn_string(POSTGRES_CONNECTION_STRING)
        # Enter the context to get the actual checkpointer instance
        _checkpointer_instance = context_manager.__enter__()
        # Keep reference to context manager for cleanup (if needed)
        _checkpointer_context = context_manager
        
        # Setup tables on first run (idempotent)
        # According to docs, setup() should be called after entering context
        try:
            _checkpointer_instance.setup()
            print("[INFO] Postgres checkpointer tables initialized successfully")
        except Exception as e:
            # If setup fails, it might already be set up, so we can continue
            # In production, you may want to handle this more gracefully
            print(f"[INFO] Checkpointer setup: {e}")
            # Don't raise - setup() is idempotent and tables may already exist
    
    return _checkpointer_instance

