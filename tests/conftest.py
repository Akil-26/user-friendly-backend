import os
from unittest.mock import patch, MagicMock

# Set test environment variables BEFORE importing app
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
os.environ["SECRET_KEY"] = "test-secret-key-for-jenkins-only"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["AI_PROVIDER"] = "ollama"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.2"

# Mock DB so tests don't need a real PostgreSQL connection
patch('sqlalchemy.sql.schema.MetaData.create_all', MagicMock()).start()
patch('sqlalchemy.engine.Engine.connect', MagicMock()).start()