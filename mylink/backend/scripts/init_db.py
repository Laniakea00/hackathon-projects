"""
Script to initialize database with initial migration
Run this after setting up the database
"""
import subprocess
import sys


def run_command(command):
    """Run a shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True


def main():
    print("🚀 Initializing SmartBot Database...")
    
    # Create initial migration
    print("\n📝 Creating initial migration...")
    if not run_command('alembic revision --autogenerate -m "Initial migration"'):
        print("❌ Failed to create migration")
        sys.exit(1)
    
    # Apply migrations
    print("\n⬆️  Applying migrations...")
    if not run_command('alembic upgrade head'):
        print("❌ Failed to apply migrations")
        sys.exit(1)
    
    print("\n✅ Database initialized successfully!")
    print("\n📚 Next steps:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Visit API docs: http://localhost:8000/docs")
    print("3. Register an employer: POST /employers/register")


if __name__ == "__main__":
    main()

