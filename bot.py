
import telegram
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
import requests
import json
import os
import asyncio
from datetime import datetime, timedelta
import threading

# --- Configuration ---
BOT_TOKEN = "7291551332:AAHLMrmDvz0L0I_psVao-YCfY-qn73RV77E"  # Replace with your bot token
API_BASE_URL = "https://narayan-like-umber.vercel.app"
DATA_FILE = "bot_data.json"
OWNER_ID = 6282055190  # Owner user ID
ALLOWED_GROUPS = []  # Add your group IDs here, empty list means all groups allowed

# --- Helper Functions for Data Storage ---

def is_owner(user_id):
    """Checks if the user is the bot owner."""
    return user_id == OWNER_ID

def is_allowed_group(chat_id):
    """Checks if the group is allowed to use the bot."""
    data = load_data()
    allowed_groups = data.get("allowed_groups", [])
    if not allowed_groups:  # If no groups set, deny access
        return False
    return chat_id in allowed_groups

def is_private_chat(update):
    """Checks if the message is from a private chat."""
    return update.effective_chat.type == 'private'

def load_data():
    """Loads user data and the custom message from a JSON file."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return {"users": {}, "total_likes": {}, "custom_message": ""}

def save_data(data):
    """Saves user data and the custom message to a JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    await update.message.reply_text(
        "Welcome to the Auto-Like Bot!\n\n"
        "Use /help to see all available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays help information with all available commands."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    help_text = (
        "🤖 Auto-Like Bot Commands:\n\n"
        "📋 Available Commands:\n"
        "/help - Show this help message\n"
        "/start - Welcome message\n"
        "/autolike {uid} {region} {day} - Set automatic 24h likes\n"
        "/like {uid} {region} - Send single like request (Owner only)\n"
        "/mylike - Check your total likes\n"
        "/status - See who is using the bot (Owner only)\n"
        "/setmessage <text> - Set custom autolike response message (Owner only)\n"
        "/setgroup {group_id} - Add group to allowed groups (Owner only)\n\n"
        "📝 Usage Examples:\n"
        "/autolike 1234567890 US 30\n"
        "/like 1234567890 US\n"
        "/setgroup -1234567890"
    )
    
    await update.message.reply_text(help_text)

async def autolike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /autolike command - sets up automatic 24h likes."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /autolike {uid} {region} {day}")
        return

    uid = context.args[0]
    region = context.args[1]
    day = context.args[2]
    
    # Save auto-like configuration
    data = load_data()
    if "auto_like_users" not in data:
        data["auto_like_users"] = {}
    
    user_id = str(update.effective_user.id)
    data["auto_like_users"][user_id] = {
        "uid": uid,
        "region": region,
        "day": day,
        "chat_id": update.effective_chat.id,
        "last_run": datetime.now().isoformat()
    }
    
    # Update allowed groups if not already in list
    if "allowed_groups" not in data:
        data["allowed_groups"] = []
    
    if update.effective_chat.id not in data["allowed_groups"]:
        data["allowed_groups"].append(update.effective_chat.id)
    
    save_data(data)
    
    # Send initial like request
    await send_like_request(uid, region, day, update, context)
    
    await update.message.reply_text(
        f"✅ Auto-like activated!\n"
        f"UID: {uid}\n"
        f"Region: {region}\n"
        f"Day: {day}\n\n"
        f"🔄 Automatic likes will be sent every 24 hours.\n"
        f"Thank for use this bot"
    )

async def send_like_request(uid, region, day, update, context):
    """Sends a like request to the API."""
    api_url = f"{API_BASE_URL}/{uid}/{region}/narayan"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        api_data = response.json()

        # Format the response message
        formatted_response = (
            f"🎮 Auto-Like Results:\n\n"
            f"Player Nickname: {api_data.get('PlayerNickname', 'N/A')}\n"
            f"UID: {api_data.get('UID', 'N/A')}\n"
            f"Likes Before Command: {api_data.get('LikesbeforeCommand', 'N/A')}\n"
            f"Likes After Command: {api_data.get('LikesafterCommand', 'N/A')}\n"
            f"Likes Given by Bot: {api_data.get('LikesGivenByAPI', 'N/A')}\n"
            f"Day: {day}\n"
            f"Status: {api_data.get('status', 'N/A')}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        data = load_data()
        custom_message = data.get("custom_message", "")
        if custom_message:
            formatted_response += f"\n\n{custom_message}"

        await update.message.reply_text(formatted_response)

        # Update user stats
        user = update.effective_user
        user_id = str(user.id)
        if user_id not in data["users"]:
            data["users"][user_id] = {
                "telegram_name": user.full_name,
                "uid": uid
            }

        if "LikesGivenByAPI" in api_data:
            if user_id not in data["total_likes"]:
                data["total_likes"][user_id] = {"count": 0, "days": 0}
            data["total_likes"][user_id]["count"] += api_data["LikesGivenByAPI"]
            data["total_likes"][user_id]["days"] += 1
            save_data(data)

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"❌ Error calling the API: {e}")
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Error: Could not decode the API response.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /status command. Owner only."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    data = load_data()
    users = data.get("users", {})
    auto_like_users = data.get("auto_like_users", {})
    allowed_groups = data.get("allowed_groups", [])

    if not users and not auto_like_users:
        await update.message.reply_text("No users are currently using the bot.")
        return

    response_message = "📊 Bot Status:\n\n"
    
    # Show regular users
    if users:
        response_message += "👥 Users:\n"
        for user_id, user_info in users.items():
            response_message += (
                f"- {user_info['telegram_name']}\n"
                f"  ID: {user_id}\n"
                f"  UID: {user_info['uid']}\n\n"
            )
    
    # Show auto-like users
    if auto_like_users:
        response_message += "🔄 Auto-Like Users:\n"
        for user_id, auto_info in auto_like_users.items():
            user_name = users.get(user_id, {}).get('telegram_name', 'Unknown')
            last_run = datetime.fromisoformat(auto_info['last_run']).strftime('%Y-%m-%d %H:%M')
            response_message += (
                f"- {user_name}\n"
                f"  UID: {auto_info['uid']}\n"
                f"  Region: {auto_info['region']}\n"
                f"  Last Run: {last_run}\n\n"
            )
    
    # Show allowed groups
    if allowed_groups:
        response_message += f"🏢 Allowed Groups: {len(allowed_groups)}\n"
        for group_id in allowed_groups:
            response_message += f"- {group_id}\n"
    
    await update.message.reply_text(response_message)

async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /like command - sends a single like request. Owner only."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /like {uid} {region}")
        return

    uid = context.args[0]
    region = context.args[1]
    
    # Send like request
    await send_like_request(uid, region, "1", update, context)

async def mylike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /mylike command."""
    # This command is free for everyone - no access restrictions
    
    data = load_data()
    user_id = str(update.effective_user.id)
    user_likes = data.get("total_likes", {}).get(user_id)

    if user_likes:
        response_message = (
            f"Your Like Stats:\n\n"
            f"Total Likes Received: {user_likes['count']}\n"
            f"Total Days Used: {user_likes['days']}"
        )
    else:
        response_message = "You have not used the /autolike command yet."

    await update.message.reply_text(response_message)

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /setmessage command. Owner only."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setmessage <your_message_here>")
        return

    custom_message = ' '.join(context.args)
    data = load_data()
    data["custom_message"] = custom_message
    save_data(data)
    await update.message.reply_text(f"The autolike response message has been set to:\n\n{custom_message}")

async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /setgroup command. Owner only."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Access denied. This command is only available to the bot owner.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setgroup {group_id}\n\nExample: /setgroup -1001234567890")
        return

    try:
        group_id = int(context.args[0])
        data = load_data()
        
        if "allowed_groups" not in data:
            data["allowed_groups"] = []
        
        if group_id not in data["allowed_groups"]:
            data["allowed_groups"].append(group_id)
            save_data(data)
            await update.message.reply_text(f"✅ Group {group_id} has been added to allowed groups.")
        else:
            await update.message.reply_text(f"ℹ️ Group {group_id} is already in the allowed groups list.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID. Please provide a valid numeric group ID.")

async def auto_like_scheduler():
    """Background task to send automatic likes every 24 hours."""
    while True:
        try:
            data = load_data()
            auto_like_users = data.get("auto_like_users", {})
            
            for user_id, auto_info in auto_like_users.items():
                last_run = datetime.fromisoformat(auto_info['last_run'])
                if datetime.now() - last_run >= timedelta(hours=24):
                    # Create a mock update object for the API call
                    class MockMessage:
                        async def reply_text(self, text, **kwargs):
                            print(f"Auto message to {auto_info['chat_id']}: {text}")
                    
                    class MockUpdate:
                        def __init__(self, chat_id, user_id):
                            self.effective_chat = type('obj', (object,), {'id': chat_id})
                            self.effective_user = type('obj', (object,), {
                                'id': int(user_id), 
                                'full_name': data.get("users", {}).get(user_id, {}).get("telegram_name", "Auto User")
                            })
                            self.message = MockMessage()
                    
                    mock_update = MockUpdate(auto_info['chat_id'], user_id)
                    mock_context = None
                    
                    try:
                        await send_like_request(
                            auto_info['uid'], 
                            auto_info['region'], 
                            auto_info['day'], 
                            mock_update, 
                            mock_context
                        )
                        
                        # Update last run time
                        data['auto_like_users'][user_id]['last_run'] = datetime.now().isoformat()
                        save_data(data)
                        
                    except Exception as e:
                        print(f"Error in auto-like for user {user_id}: {e}")
            
        except Exception as e:
            print(f"Error in auto_like_scheduler: {e}")
        
        # Wait 1 hour before checking again
        await asyncio.sleep(3600)

def main():
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("autolike", autolike))
    application.add_handler(CommandHandler("like", like))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("mylike", mylike))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("setgroup", setgroup))

    # Start the auto-like scheduler in a separate thread
    def start_scheduler():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(auto_like_scheduler())
    
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
