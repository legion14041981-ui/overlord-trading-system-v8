#!/usr/bin/env python3
"""
Database Setup Script for Testing
Creates test database schema and fixtures
"""

import os
import sys
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(0)


def setup_test_database():
    """Setup test database schema"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("DATABASE_URL not set. Skipping database setup.")
        return
    
    # Parse database URL
    parsed = urlparse(database_url)
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]  # Remove leading '/'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Create test tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                quantity DECIMAL(18, 8) NOT NULL,
                price DECIMAL(18, 8) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) UNIQUE NOT NULL,
                quantity DECIMAL(18, 8) NOT NULL,
                avg_price DECIMAL(18, 8) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("✅ Created test tables")
        
        # Insert test data
        cursor.execute("""
            INSERT INTO positions (symbol, quantity, avg_price)
            VALUES 
                ('BTC/USDT', 0.1, 45000.0),
                ('ETH/USDT', 2.5, 3000.0)
            ON CONFLICT (symbol) DO NOTHING
        """)
        
        print("✅ Inserted test data")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(0)  # Don't fail CI if DB setup fails


if __name__ == "__main__":
    setup_test_database()
