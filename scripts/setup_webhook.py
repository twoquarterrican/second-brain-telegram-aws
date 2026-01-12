#!/usr/bin/env python3
"""
Interactive script to set up Telegram webhook for Second Brain processor Lambda.
"""

import os
import sys
import subprocess
import json
from typing import Optional

try:
    from InquirerPy import inquirer
    from InquirerPy.base import Choice
except ImportError:
    print("❌ InquirerPy is required. Install with: pip install InquirerPy")
    print("   Or run: uv sync")
    sys.exit(1)


def get_function_url(function_name: str, region: str = "us-east-1") -> Optional[str]:
    """Get the Function URL for a Lambda function using AWS CLI"""
    try:
        result = subprocess.run(
            [
                "aws",
                "lambda",
                "get-function-url-config",
                "--function-name",
                function_name,
                "--region",
                region,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        config = json.loads(result.stdout)
        return config["FunctionUrl"]
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting function URL: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing function URL response: {e}")
        return None


def set_webhook(bot_token: str, webhook_url: str, secret_token: str = None) -> bool:
    """Set the Telegram webhook"""
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    payload = {"url": webhook_url}
    if secret_token:
        payload["secret_token"] = secret_token

    try:
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()

        if result.get("ok"):
            return True, "Webhook set successfully!"
        else:
            return False, result.get("description", "Unknown error")

    except Exception as e:
        return False, str(e)


def get_webhook_info(bot_token: str) -> bool:
    """Get current webhook information"""
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    try:
        response = requests.get(url, timeout=30)
        result = response.json()

        if result.get("ok"):
            return True, result["result"]
        else:
            return False, result.get("description", "Unknown error")

    except Exception as e:
        return False, str(e)


def delete_webhook(bot_token: str) -> bool:
    """Delete the Telegram webhook"""
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"

    try:
        response = requests.post(url, timeout=30)
        result = response.json()

        if result.get("ok"):
            return True, "Webhook deleted successfully!"
        else:
            return False, result.get("description", "Unknown error")

    except Exception as e:
        return False, str(e)


def interactive_setup():
    """Interactive setup using InquirerPy"""

    print("🤖 Telegram Webhook Setup for Second Brain")
    print("=" * 50)

    # Get bot token
    bot_token = inquirer.text(
        message="Enter your Telegram Bot Token:",
        validate=lambda x: len(x) > 10 and x.isdigit(),
        invalid_message="Please enter a valid Telegram bot token",
        transformer=lambda x: f"{x[:15]}..." if len(x) > 15 else x,
    ).execute()

    # Choose action
    action = inquirer.select(
        message="What would you like to do?",
        choices=[
            Choice("set", "Set up new webhook"),
            Choice("info", "Get current webhook info"),
            Choice("delete", "Delete webhook"),
            Choice("test", "Test bot connection"),
        ],
    ).execute()

    if action == "info":
        success, result = get_webhook_info(bot_token)
        if success:
            print("\n📋 Current webhook info:")
            print(f"   URL: {result.get('url', 'Not set')}")
            print(
                f"   Has custom certificate: {result.get('has_custom_certificate', False)}"
            )
            print(f"   Pending updates: {result.get('pending_update_count', 0)}")
            print(f"   Last error: {result.get('last_error_message', 'None')}")
            print(f"   Custom secret: {'Yes' if result.get('secret_token') else 'No'}")
        else:
            print(f"❌ Failed to get webhook info: {result}")
        return

    elif action == "delete":
        confirm = inquirer.confirm(
            message="Are you sure you want to delete the webhook?", default=False
        ).execute()

        if confirm:
            success, message = delete_webhook(bot_token)
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ Failed to delete webhook: {message}")
        else:
            print("❌ Cancelled.")
        return

    elif action == "test":
        print("🔍 Testing bot connection...")
        success, result = get_webhook_info(bot_token)
        if success:
            print(
                f"✅ Bot is accessible! Webhook URL: {result.get('url', 'Not configured')}"
            )
        else:
            print(f"❌ Failed to connect to bot: {result}")
        return

    # Set webhook
    print("🔧 Setting up webhook...")

    # Choose function source
    webhook_source = inquirer.select(
        message="How do you want to get the webhook URL?",
        choices=[
            Choice("auto", "Auto-detect from AWS"),
            Choice("manual", "Enter manually"),
        ],
    ).execute()

    if webhook_source == "auto":
        function_name = inquirer.text(
            message="Lambda function name:",
            default="SecondBrainProcessor",
        ).execute()

        region = inquirer.text(
            message="AWS region:",
            default="us-east-1",
        ).execute()

        print("🔍 Getting function URL from AWS...")
        webhook_url = get_function_url(function_name, region)
        if not webhook_url:
            print(
                "❌ Could not get function URL. Please check AWS CLI configuration and permissions."
            )
            return
    else:
        webhook_url = inquirer.text(
            message="Enter webhook URL:",
            validate=lambda x: x.startswith("https://"),
            invalid_message="Please enter a valid HTTPS URL",
        ).execute()

    # Secret token
    use_secret = inquirer.confirm(
        message="Use secret token for webhook security?", default=True
    ).execute()

    secret_token = None
    if use_secret:
        if inquirer.confirm("Generate random secret token?", default=True):
            import secrets

            secret_token = secrets.token_urlsafe(32)
            print(f"🔑 Generated secret token: {secret_token}")
        else:
            secret_token = inquirer.text(
                message="Enter secret token:",
                validate=lambda x: len(x) >= 8,
                invalid_message="Secret token must be at least 8 characters",
            ).execute()

    # Confirmation
    print(f"\n📋 Webhook Configuration Summary:")
    print(f"   Bot Token: {bot_token[:15]}...")
    print(f"   Webhook URL: {webhook_url}")
    print(f"   Secret Token: {'Yes' if secret_token else 'No'}")

    if not inquirer.confirm("Proceed with webhook setup?", default=True):
        print("❌ Cancelled.")
        return

    # Set webhook
    print("⏳ Setting webhook...")
    success, message = set_webhook(bot_token, webhook_url, secret_token)

    if success:
        print("✅ Webhook set successfully!")
        print(f"   URL: {webhook_url}")
        if secret_token:
            print(f"   Secret token configured")
        print("\n🎉 Your Second Brain bot is ready to receive messages!")
    else:
        print(f"❌ Failed to set webhook: {message}")


def main():
    """Main entry point"""
    try:
        interactive_setup()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
