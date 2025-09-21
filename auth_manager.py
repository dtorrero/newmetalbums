import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional
import sqlite3
from pathlib import Path

class AuthManager:
    def __init__(self, db_path: str = "data/albums.db"):
        self.db_path = db_path
        self.secret_key = self._get_or_create_secret_key()
        self._init_auth_table()
    
    def _get_or_create_secret_key(self) -> str:
        """Get or create a secret key for JWT signing"""
        secret_file = Path("data/.secret_key")
        secret_file.parent.mkdir(exist_ok=True)
        
        if secret_file.exists():
            return secret_file.read_text().strip()
        else:
            # Generate a secure random secret key
            secret_key = secrets.token_urlsafe(32)
            secret_file.write_text(secret_key)
            # Make file readable only by owner
            secret_file.chmod(0o600)
            return secret_key
    
    def _init_auth_table(self):
        """Initialize the authentication table in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_auth (
                    id INTEGER PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP
                )
            """)
            conn.commit()
    
    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """Hash a password with salt using PBKDF2"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256, 100,000 iterations
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return password_hash.hex(), salt
    
    def is_first_time_setup(self) -> bool:
        """Check if this is the first time setup (no admin password set)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM admin_auth")
            count = cursor.fetchone()[0]
            return count == 0
    
    def set_admin_password(self, password: str) -> bool:
        """Set the admin password (first-time setup or password change)"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        password_hash, salt = self._hash_password(password)
        
        with sqlite3.connect(self.db_path) as conn:
            # Clear any existing admin records (should only be one)
            conn.execute("DELETE FROM admin_auth")
            
            # Insert new admin credentials
            conn.execute("""
                INSERT INTO admin_auth (password_hash, salt, created_at)
                VALUES (?, ?, ?)
            """, (password_hash, salt, datetime.utcnow()))
            conn.commit()
        
        return True
    
    def verify_password(self, password: str) -> bool:
        """Verify the admin password"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT password_hash, salt, login_attempts, locked_until
                FROM admin_auth
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if not result:
                return False
            
            stored_hash, salt, login_attempts, locked_until = result
            
            # Check if account is locked
            if locked_until:
                locked_until_dt = datetime.fromisoformat(locked_until)
                if datetime.utcnow() < locked_until_dt:
                    raise ValueError("Account is temporarily locked due to too many failed attempts")
            
            # Verify password
            password_hash, _ = self._hash_password(password, salt)
            
            if password_hash == stored_hash:
                # Reset login attempts on successful login
                conn.execute("""
                    UPDATE admin_auth 
                    SET login_attempts = 0, last_login = ?, locked_until = NULL
                    WHERE password_hash = ?
                """, (datetime.utcnow(), stored_hash))
                conn.commit()
                return True
            else:
                # Increment login attempts
                new_attempts = login_attempts + 1
                locked_until = None
                
                # Lock account after 5 failed attempts for 15 minutes
                if new_attempts >= 5:
                    locked_until = datetime.utcnow() + timedelta(minutes=15)
                
                conn.execute("""
                    UPDATE admin_auth 
                    SET login_attempts = ?, locked_until = ?
                    WHERE password_hash = ?
                """, (new_attempts, locked_until, stored_hash))
                conn.commit()
                
                if locked_until:
                    raise ValueError("Too many failed attempts. Account locked for 15 minutes.")
                
                return False
    
    def generate_token(self, expires_hours: int = 24) -> str:
        """Generate a JWT token for admin authentication"""
        payload = {
            'admin': True,
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> bool:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload.get('admin', False)
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
    
    def get_auth_status(self) -> dict:
        """Get authentication status information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT created_at, last_login, login_attempts, locked_until
                FROM admin_auth
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if not result:
                return {
                    "setup_required": True,
                    "locked": False,
                    "last_login": None
                }
            
            created_at, last_login, login_attempts, locked_until = result
            
            is_locked = False
            if locked_until:
                locked_until_dt = datetime.fromisoformat(locked_until)
                is_locked = datetime.utcnow() < locked_until_dt
            
            return {
                "setup_required": False,
                "locked": is_locked,
                "last_login": last_login,
                "created_at": created_at,
                "login_attempts": login_attempts
            }
