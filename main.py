import requests
import json
import time
import logging
import os
import sys
import random
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nft_tracker.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("NFTTracker")


class NFTTracker:
    def __init__(self, start_id=2223, max_id=11110, webhook=None):
        self.current_token_id = start_id
        self.max_token_id = max_id
        self.base_url = "INSERT_SABONG_SAGA_BASE_URL"
        self.webhook_url = webhook
        self.check_interval = 30
        self.minted_tokens = set()
        self.regular_descriptions = [
            "Arise! A new Legacy Cock stands strong!",
            "From the feathers, a new legacy cock has been born",
            "Wow, look at this fabulous, juicy, wonderful chicken",
            "I hope this legacy chicken gets raised in a stress-free environment"
        ]
        self.legendary_description = "✨ A new legendary cock has been erected! ✨"
        self.load_tracked_tokens()

    @staticmethod
    def check_image_exists(token_id):
        image_url = f"INSERT_SABONG_SAGA_IMAGE_URL{token_id}"
        try:
            response = requests.head(image_url, timeout=10)
            return response.status_code == 200
        except Exception as img_error:
            logger.error(f"Error checking image for #{token_id}: {img_error}")
            return False

    def load_tracked_tokens(self):
        try:
            if os.path.exists("minted_tokens.json") and os.path.getsize("minted_tokens.json") > 0:
                with open("minted_tokens.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.minted_tokens = set(data["minted_tokens"])
                    if data.get("last_checked_id"):
                        self.current_token_id = max(self.current_token_id, data["last_checked_id"])
                logger.info(f"Loaded {len(self.minted_tokens)} previously tracked tokens")
            else:
                logger.info("No previous tracking data found or file is empty. Starting fresh.")
        except json.JSONDecodeError as json_error:
            logger.error(f"Invalid JSON in minted_tokens.json: {json_error}. Creating a new file.")
            self.save_tracked_tokens()
        except Exception as load_error:
            logger.error(f"Error loading tracked tokens: {load_error}")

    def save_tracked_tokens(self):
        try:
            with open("minted_tokens.json", "w", encoding="utf-8") as f:
                json.dump({
                    "minted_tokens": list(self.minted_tokens),
                    "last_checked_id": self.current_token_id
                }, f)
            logger.info(f"Saved {len(self.minted_tokens)} tracked tokens")
        except Exception as save_error:
            logger.error(f"Error saving tracked tokens: {save_error}")

    def check_metadata(self, token_id):
        url = f"{self.base_url}/{token_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    logger.debug(f"Token #{token_id} not minted yet: {data['error']}")
                    return None
                logger.info(f"Token #{token_id} has metadata")
                return data
            else:
                logger.warning(f"Failed to fetch metadata for #{token_id}: HTTP {response.status_code}")
                return None
        except Exception as request_error:
            logger.error(f"Error checking metadata for #{token_id}: {request_error}")
            return None

    def send_discord_notification(self, metadata):
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return

        try:
            token_id = metadata.get("edition")

            is_legendary = False
            if "attributes" in metadata:
                for attr in metadata["attributes"]:
                    if attr.get("trait_type") == "Legendary Count" and attr.get("value", 0) > 0:
                        is_legendary = True
                        break

            if is_legendary:
                description = self.legendary_description
                logger.info(f"Chicken #{token_id} is legendary!")
            else:
                description = random.choice(self.regular_descriptions)
                logger.info(f"Chicken #{token_id} is a regular chicken")

            embed = {
                "author": {
                    "name": "Sabong Saga - Legacy Collection",
                    "icon_url": "attachment://LOGO.png"
                },
                "color": 5763719,
                "title": f"Chicken #{token_id} minted!",
                "thumbnail": {"url": metadata.get("image")},
                "description": description,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            payload = {
                "embeds": [embed]
            }

            logo_file = open('LOGO.png', 'rb')
            files = {
                'payload_json': (None, json.dumps(payload), 'application/json'),
                'LOGO.png': ('LOGO.png', logo_file, 'image/png')
            }

            response = requests.post(self.webhook_url, files=files)
            logo_file.close()

            if response.status_code >= 400:
                logger.error(f"Discord webhook error: HTTP {response.status_code} - {response.text}")
            else:
                logger.info(f"Discord notification sent for #{token_id}")

        except Exception as notify_error:
            logger.error(f"Error sending Discord notification: {notify_error}")

    def start_tracking(self):
        logger.info(f"Starting NFT tracking from ID #{self.current_token_id} to #{self.max_token_id}")

        while self.current_token_id <= self.max_token_id:
            if self.current_token_id in self.minted_tokens:
                self.current_token_id += 1
                continue

            metadata = self.check_metadata(self.current_token_id)

            if metadata:
                image_exists = self.check_image_exists(self.current_token_id)

                if image_exists:
                    self.minted_tokens.add(self.current_token_id)
                    self.send_discord_notification(metadata)
                    self.save_tracked_tokens()

                    self.current_token_id += 1
                else:
                    logger.info(f"Metadata exists for #{self.current_token_id} but image doesn't exist yet. Waiting...")
                    self.save_tracked_tokens()
                    logger.info(f"Waiting {self.check_interval}s before checking again")
                    time.sleep(self.check_interval)
            else:
                self.save_tracked_tokens()

                logger.info(f"Waiting {self.check_interval}s before checking token #{self.current_token_id} again")
                time.sleep(self.check_interval)


if __name__ == "__main__":
    discord_webhook = "INSERT_CHANNEL_WEBHOOK"
    token_start = 2223
    token_max = 11110

    tracker = NFTTracker(
        start_id=token_start,
        max_id=token_max,
        webhook=discord_webhook
    )

    try:
        tracker.start_tracking()
    except KeyboardInterrupt:
        print("Tracking stopped by user")
        tracker.save_tracked_tokens()
    except Exception as main_error:
        print(f"Unexpected error: {main_error}")
        tracker.save_tracked_tokens()
