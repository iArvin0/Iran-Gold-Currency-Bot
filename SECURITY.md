# Security

Never commit:

- `.env`
- Telegram bot tokens
- Oanor API keys
- private logs that contain user information

The application redacts the configured Telegram bot token and Oanor API key from its own log
formatter, but you should still review logs before publishing them.

If a secret is exposed in a commit, screenshot, issue, or chat message, revoke/rotate it immediately.
