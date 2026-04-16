import os

# Avatar paths
USER_AVATAR = safe_avatar('assets/user_avatar.png', '😀')
BOT_AVATAR = safe_avatar('assets/mukti_avatar.png', '🤖')

# Helper function to safely validate avatar paths
def safe_avatar(path, fallback_emoji):
    if os.path.exists(path) and os.path.isfile(path):
        return path
    return fallback_emoji

# Existing functionality remains unchanged

# Your existing code...