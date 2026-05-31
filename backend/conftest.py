import os

os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("DISCORD_CLIENT_ID", "test-client-id")
os.environ.setdefault("DISCORD_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("DISCORD_REDIRECT_URI", "http://localhost:5001/auth/discord/callback")
os.environ.setdefault("DISCORD_ADMIN_ROLE_ID", "123456789")
os.environ.setdefault("DISCORD_GUILD_ID", "987654321")
os.environ.setdefault("ADMIN_SECRET", "test-secret")
