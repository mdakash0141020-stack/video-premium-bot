# Video Premium Telegram Bot

## Files
- `main.py`: bot code
- `requirements.txt`: Python dependency

## Required environment variables (set in your hosting provider's Secrets/Variables)
- `BOT_TOKEN`: fresh token from @BotFather (never put it in GitHub)
- `ADMIN_ID`: your numeric Telegram user ID
- `BKASH_NUMBER`: defaults to `01609230133`

Monthly price is 300 BDT for 30 days. Payment is manual: the admin checks the bKash transaction and presses Approve or Reject.

## Commands
- `/start` — 18+ age confirmation and payment instructions
- `/submit` — submit bKash Transaction ID
- `/videos` — view videos while premium is active
- `/status` — check premium status
- `/addvideo` — admin-only; then send a video

Use only lawful content featuring consenting adults, and only content you own or are authorized to distribute. Do not upload or share anyone's intimate content without their explicit consent. This project does not verify age or payments automatically; the admin must verify both appropriately.
