# 05/11/24 - Discord Python bot by Jordan
# Used for making various MariaDB database manipulations from Discord
# Allows admins to check various statistics about the game server,
# track donations and credit users with in-game currency.

import discord
import mariadb
import asyncio
from datetime import timedelta

# Discord bot token
TOKEN = "#########"

# Database credentials for `pw` database
PW_DB_USER = "infernal"
PW_DB_PASS = "#########"
PW_DB_NAME = "pw"
PW_DB_HOST = "localhost"
PW_DB_PORT = 3306

# Database credentials for `user_panel` database
PANEL_DB_USER = "panel"
PANEL_DB_PASS = "#########"
PANEL_DB_NAME = "user_panel"
PANEL_DB_HOST = "localhost"
PANEL_DB_PORT = 3306

# Channel to send donation information
CHANNEL_NAME = "test"

# Enable necessary intents
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Function to connect to `pw` database and update gold
def update_gold(name, amount, action):
    try:
        conn = mariadb.connect(
            user=PW_DB_USER,
            password=PW_DB_PASS,
            host=PW_DB_HOST,
            port=PW_DB_PORT,
            database=PW_DB_NAME
        )
        cur = conn.cursor()

        # Determine SQL command based on action
        if action == "add":
            sql = "UPDATE users SET lkgold = lkgold + %s WHERE name = %s"
            log_message = f"Added {amount} coins to {name}'s lkgold."
        elif action == "remove":
            sql = "UPDATE users SET lkgold = GREATEST(lkgold - %s, 0) WHERE name = %s"
            log_message = f"Removed {amount} coins from {name}'s lkgold."
        else:
            return f"Invalid action '{action}'. Use 'add' or 'remove'."

        # Execute the SQL command
        cur.execute(sql, (amount, name))
        conn.commit()

        # Fetch the user's new balance
        cur.execute("SELECT lkgold FROM users WHERE name = %s", (name,))
        new_balance = cur.fetchone()[0]

        cur.close()
        conn.close()

        return f"{log_message} New balance: {new_balance} coins."

    except mariadb.Error as e:
        return f"Error connecting to the database: {e}"

# Function to set a player's balance directly
def set_gold(name, amount):
    try:
        conn = mariadb.connect(
            user=PW_DB_USER,
            password=PW_DB_PASS,
            host=PW_DB_HOST,
            port=PW_DB_PORT,
            database=PW_DB_NAME
        )
        cur = conn.cursor()

        # Update the user's balance directly
        sql = "UPDATE users SET lkgold = %s WHERE name = %s"
        cur.execute(sql, (amount, name))
        conn.commit()

        cur.close()
        conn.close()

        return f"Set {name}'s gold balance to {amount} coins."

    except mariadb.Error as e:
        return f"Error connecting to the database: {e}"

# Function to fetch player's balance
async def fetch_balance(name):
    try:
        conn = mariadb.connect(
            user=PW_DB_USER,
            password=PW_DB_PASS,
            host=PW_DB_HOST,
            port=PW_DB_PORT,
            database=PW_DB_NAME
        )
        cur = conn.cursor()

        # Query to get the lkgold balance of the specified player
        query = "SELECT lkgold FROM users WHERE name = %s"
        cur.execute(query, (name,))
        result = cur.fetchone()

        cur.close()
        conn.close()

        return result[0] if result else None

    except mariadb.Error as e:
        print(f"Error connecting to the database: {e}")
        return None

# Function to connect to `user_panel` database and fetch new donations
async def fetch_new_donations():
    try:
        conn = mariadb.connect(
            user=PANEL_DB_USER,
            password=PANEL_DB_PASS,
            host=PANEL_DB_HOST,
            port=PANEL_DB_PORT,
            database=PANEL_DB_NAME
        )
        cur = conn.cursor()

        # Query to select new rows where discord_logged is "0" (unprocessed)
        query = "SELECT id, data, out_summ, don_kurs, money, act_bonus, bonus_money, login, userid, ip, intid, status, pay_system FROM donate_client WHERE discord_logged = 0"
        cur.execute(query)

        new_donations = cur.fetchall()
        update_query = "UPDATE donate_client SET discord_logged = 1 WHERE discord_logged = 0"
        cur.execute(update_query)
        conn.commit()

        cur.close()
        conn.close()

        return new_donations

    except mariadb.Error as e:
        print(f"Error connecting to the database: {e}")
        return []

# Function to format donation data into a readable message
def format_donation_message(donation):
    adjusted_date = donation[1] - timedelta(hours=3)  # Adjust from Moscow to UTC

    return (
        f"**__New Donation Attempt Made__**\n"
        f"**Date**: {adjusted_date}\n"
        f"**Account Name**: {donation[7]}\n"
        f"**Account ID**: {donation[8]}\n"
        f"**IP Address**: {donation[9]}\n"
        f"**Payment System**: {donation[12]}\n"
        f"**Amount**: ${donation[2]}\n"
        f"**Gold Coins**: {donation[4]}\n"
        f"**Donation Bonus**: {donation[5]}%\n"
        f"**Total Gold Coins**: {donation[4] + donation[6]}\n"
    )

# Function to fetch the latest online statistics
async def fetch_latest_online_stats():
    try:
        conn = mariadb.connect(
            user=PANEL_DB_USER,
            password=PANEL_DB_PASS,
            host=PANEL_DB_HOST,
            port=PANEL_DB_PORT,
            database=PANEL_DB_NAME
        )
        cur = conn.cursor()

        # Query to get the latest online statistics based on the date (data) column
        query = """
            SELECT online_acc, online_pers, online_world, online_instance, data
            FROM online_stat
            ORDER BY data DESC
            LIMIT 1
        """
        cur.execute(query)
        latest_stats = cur.fetchone()

        cur.close()
        conn.close()

        return latest_stats

    except mariadb.Error as e:
        print(f"Error connecting to the database: {e}")
        return None

# Check for new donations periodically
async def check_for_new_donations():
    await client.wait_until_ready()
    channel = discord.utils.get(client.get_all_channels(), name=CHANNEL_NAME)

    if not channel:
        print(f"Channel '{CHANNEL_NAME}' not found.")
        return

    while not client.is_closed():
        new_donations = await fetch_new_donations()
        for donation in new_donations:
            message = format_donation_message(donation)
            await channel.send(message)
        await asyncio.sleep(60)

# Define the command prefix and listen for messages
@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    client.loop.create_task(check_for_new_donations())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    parts = message.content.split()
    if parts[0] == "!help":
        help_message = (
            "Here are the available commands:\n"
            "`!balance <name>` - Show the balance of a player's lkgold.\n"
            "`!addgold <name> <amount>` - Add gold to a user's lkgold.\n"
            "`!removegold <name> <amount>` - Remove gold from a user's lkgold.\n"
            "`!setgold <name> <amount>` - Set a user's lkgold to a specific amount.\n"
            "`!donohistory [number]` - Show the last [number] donations (default is 5).\n"
            "`!online` - Show the latest online statistics.\n"
            "`!help` - Show this help message."
        )
        await message.channel.send(help_message)

    elif len(parts) == 3 and (parts[0] == "!addgold" or parts[0] == "!removegold"):
        command = parts[0]
        name = parts[1]
        amount = parts[2]

        if not amount.isdigit():
            await message.channel.send("Amount must be a positive integer.")
            return
        amount = int(amount)

        action = "add" if command == "!addgold" else "remove"
        result = update_gold(name, amount, action)
        await message.channel.send(result)

    elif parts[0] == "!setgold" and len(parts) == 3:
        name = parts[1]
        amount = parts[2]

        if not amount.isdigit():
            await message.channel.send("Amount must be a positive integer.")
            return
        amount = int(amount)

        result = set_gold(name, amount)
        await message.channel.send(result)

    elif parts[0] == "!balance" and len(parts) == 2:
        name = parts[1]
        balance = await fetch_balance(name)
        if balance is not None:
            await message.channel.send(f"**{name}'s Balance**: {balance} coins")
        else:
            await message.channel.send(f"Player '{name}' not found.")

client.run(TOKEN)
