"""Validation script to check setup before running audit"""
import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ required, found:", f"{version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Create one from env.example")
        return False
    
    with open(env_path) as f:
        content = f.read()
    
    required = ["DATABASE_URL", "OPENAI_API_KEY"]
    missing = []
    
    for var in required:
        if var not in content or f"{var}=" not in content:
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    if "sk-your-" in content:
        print("⚠️  Warning: OPENAI_API_KEY looks like placeholder")
        print("   Update with real API key")
        return False
    
    # Provider-aware key check (OpenAI vs OpenRouter)
    provider = None
    base_url = None
    for line in content.splitlines():
        if line.startswith("LLM_PROVIDER="):
            provider = line.split("=", 1)[1].strip()
        if line.startswith("OPENAI_BASE_URL="):
            base_url = line.split("=", 1)[1].strip()
    
    using_openrouter = (provider == "openrouter") or (base_url and "openrouter.ai" in base_url.lower())
    if using_openrouter:
        if "OPENAI_API_KEY=sk-or-" not in content:
            print("❌ OPENAI_API_KEY missing/invalid for OpenRouter (expected sk-or-...)")
            return False
    else:
        # If user pasted OpenRouter key while using OpenAI
        if "OPENAI_API_KEY=sk-or-" in content:
            print("❌ OPENAI_API_KEY looks like an OpenRouter key (sk-or-...), but provider/base_url is OpenAI")
            return False
    
    print("✓ .env file configured")
    return True

def check_imports():
    """Check if all required packages are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "asyncpg",
        "httpx",
        "bs4",
        "openai",
        "weasyprint",
        "jinja2",
        "alembic",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("✓ All packages installed")
    return True

def check_reports_dir():
    """Check if reports directory exists"""
    reports_dir = Path(__file__).parent / "reports"
    if not reports_dir.exists():
        print("⚠️  Reports directory doesn't exist, creating...")
        reports_dir.mkdir()
    print("✓ Reports directory ready")
    return True

def check_database_connection():
    """Try to connect to database"""
    try:
        from app.config import get_settings
        settings = get_settings()
        
        if "localhost" not in settings.database_url and "127.0.0.1" not in settings.database_url:
            print("⚠️  Database URL points to non-localhost")
            print(f"   URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'unknown'}")
        else:
            print("✓ Database URL configured for localhost")
        
        return True
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

def main():
    """Run all validation checks"""
    print("="*50)
    print("LLM Audit Engine - Setup Validation")
    print("="*50)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Python Packages", check_imports),
        ("Reports Directory", check_reports_dir),
        ("Database Config", check_database_connection),
    ]
    
    results = []
    for name, check in checks:
        print(f"\nChecking {name}...")
        result = check()
        results.append(result)
    
    print()
    print("="*50)
    
    if all(results):
        print("✓ All checks passed!")
        print()
        print("Next steps:")
        print("1. Make sure PostgreSQL is running")
        print("2. Run: alembic upgrade head")
        print("3. Start API: uvicorn app.main:app --reload --port 8000")
        print("4. Start worker: python -m app.worker")
        print("="*50)
        return 0
    else:
        print("❌ Some checks failed. Fix the issues above and try again.")
        print("="*50)
        return 1

if __name__ == "__main__":
    sys.exit(main())


