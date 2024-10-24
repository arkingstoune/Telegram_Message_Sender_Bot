import asyncio
import sqlite3
from telethon import TelegramClient, events

api_id = 'your api_id'
api_hash = 'your api_hash'

# Initialize the client for personal account login
client = TelegramClient('me_client_bot', api_id, api_hash)

# Variables
user_message = ''
timer = 0
start_sending = False

# Database setup
def create_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Create a table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,  
                        group_id TEXT
                    )''')
    conn.commit()
    conn.close()

# Fetch group IDs from the database
def retrieve_group_ids():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM groups")
    all_groups = cursor.fetchall()
    conn.close()
    return all_groups

# Store a new group in the database
def store_group_id(group_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
    conn.commit()
    conn.close()

# Retrieve the ID for "Saved Messages"
async def get_saved_messages_chat_id():
    me = await client.get_me()
    return me.id

# Command handler decorator
def in_saved_messages_chat(func):
    async def wrapper(event):
        # Check if the command comes from the "Saved Messages" chat
        saved_messages_chat_id = await get_saved_messages_chat_id()
        if event.chat_id == saved_messages_chat_id:
            await func(event)
        else:
            await event.respond("This command can only be used in 'Saved Messages' chat.")
    return wrapper

# Start sending messages to groups at intervals
async def start_sending_messages():
    global start_sending, user_message, timer
    while start_sending:
        groups = retrieve_group_ids()
        for group in groups:
            group_id = group[0]  # Extract group ID or username
            try:
                # Check if the group_id is numeric or a username
                if group_id.isdigit():
                    chat = await client.get_entity(int(group_id))
                else:
                    chat = await client.get_entity(group_id)

                await client.send_message(chat, user_message)
            except ValueError as ve:
                print(f"ValueError: {ve}. Failed to send message to {group_id}")
            except Exception as e:
                print(f"Failed to send message to {group_id}: {e}")
        await asyncio.sleep(timer * 60)
@client.on(events.NewMessage(pattern='/get_groups'))
@in_saved_messages_chat
async def get_groups_handler(event):
    # Retrieve groups from the database
    all_groups = retrieve_group_ids()  # Ensure this function is defined and returns the expected data

    if all_groups:
        try:
            # Change this line to use group[0] since each tuple has only one item
            groups_list = "\n".join([f"Group ID: {group[0]}" for group in all_groups])
            await event.respond(f"Groups:\n{groups_list}")
        except IndexError as e:
            print(f"IndexError: {e}")  # Debug: print the exception
            await event.respond('Error: Failed to format group list.')
    else:
        await event.respond('No groups found.')

@client.on(events.NewMessage(pattern='/clear_list'))
@in_saved_messages_chat
async def clear_db(event):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()

        # Clear all rows from the 'groups' table
        cursor.execute('''DELETE FROM groups''')

        # Commit the deletion transaction
        conn.commit()

        # Optimize the database after deletion
        cursor.execute('''VACUUM''')

        print('Database was cleared and vacuumed')

        # Send a message to the chat confirming the action
        await event.respond("Database has been cleared and optimized.")

    except sqlite3.Error as error:
        print(f"Error while clearing database: {error}")
        await event.respond(f"Error occurred while clearing the database: {error}")


# Start sending command
@client.on(events.NewMessage(pattern='/start_sending'))
@in_saved_messages_chat
async def start_sending_handler(event):
    global start_sending
    if(timer != 0):
        start_sending = True
        await event.respond("Started sending messages.")
    else :
        await event.respond("please set the timer")
    # Start the sending task
    await start_sending_messages()

# Stop sending command
@client.on(events.NewMessage(pattern='/stop_sending'))
@in_saved_messages_chat
async def stop_sending_handler(event):
    global start_sending
    start_sending = False
    await event.respond("Stopped sending messages.")

# Store group command
@client.on(events.NewMessage(pattern='/store_group'))
@in_saved_messages_chat
async def store_group_handler(event):
    try:
        group_id = event.message.text.split(" ", 1)[1]  # Extract group ID from the message text
        store_group_id(group_id)
        await event.respond(f"Group {group_id} stored.")
    except IndexError:
        await event.respond("Please provide a group ID after the command.")
# Set timer command
@client.on(events.NewMessage(pattern='/set_timer'))
@in_saved_messages_chat
async def set_timer_handler(event):
    global timer
    timer = int(event.message.text.split(" ", 1)[1])
    await event.respond(f"Timer set to {timer} minutes.")

# Set message command
@client.on(events.NewMessage(pattern='/set_message'))
@in_saved_messages_chat
async def set_message_handler(event):
    global user_message
    user_message = event.message.text.split(" ", 1)[1]
    await event.respond(f"Message set: {user_message}")

@client.on(events.NewMessage(pattern='/view_message'))
@in_saved_messages_chat
async def view_message_handler(event):
    global user_message, timer
    if user_message and timer:
        await event.respond(f'Your message: "{user_message}"\nTimer: {timer} minutes')
    else:
        await event.respond('No message or timer set.')
# Run the bot
create_db()
client.start()
client.run_until_disconnected()
