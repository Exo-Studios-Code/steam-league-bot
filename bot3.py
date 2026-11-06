# bot.py

import discord
from discord.ext import commands
from discord.commands import Option
import sqlite3
import requests
import json
from config import DISCORD_TOKEN, STEAM_API_KEY, STEAM_APP_ID, ADMIN_ROLE_ID

# --- ZÁKLADNÍ NASTAVENÍ BOTA ---
# Nastavujeme "intents" - v podstatě oprávnění, co bot může sledovat.
# Potřebujeme "guilds" (servery) a "members" (abychom viděli info o členech).
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- DATABÁZE ---
def setup_database():
    """Vytvoří databázi a tabulku, pokud neexistují."""
    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            discord_id INTEGER PRIMARY KEY,
            steam_id TEXT NOT NULL,
            team TEXT,
            bio TEXT,
            goals INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("Databáze je připravena.")

# --- KONTROLA OPRÁVNĚNÍ ---
def is_admin(ctx: discord.ApplicationContext) -> bool:
    """Zkontroluje, zda má autor příkazu admin roli nebo je admin serveru."""
    if ADMIN_ROLE_ID != 0:
        # Hledáme specifickou roli
        admin_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        return admin_role in ctx.author.roles
    else:
        # Kontrolujeme administrátorská oprávnění na serveru
        return ctx.author.guild_permissions.administrator

# --- PŘÍKAZY BOTA ---

@bot.event
async def on_ready():
    """Funkce, která se spustí, když se bot úspěšně připojí k Discordu."""
    print(f'Bot je online jako {bot.user}')
    # Synchronizace slash příkazů se servery. Může chvíli trvat.
    await bot.sync_commands()

@bot.slash_command(name="registrace", description="Zaregistruj svůj Steam účet k Discord účtu.")
async def registrace(ctx, steam_id: Option(str, "Tvoje SteamID64 (číslo, najdeš např. na steamid.io)", required=True)):
    """Zaregistruje nebo aktualizuje SteamID uživatele v databázi."""
    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    
    # INSERT OR REPLACE buď vloží nový záznam, nebo přepíše existující pro dané discord_id
    cursor.execute("INSERT OR REPLACE INTO players (discord_id, steam_id) VALUES (?, ?)", (ctx.author.id, steam_id))
    
    conn.commit()
    conn.close()
    
    await ctx.respond(f"Tvůj Steam účet (`{steam_id}`) byl úspěšně zaregistrován!", ephemeral=True)

# Nahraďte celou původní funkci player touto novou verzí

@bot.slash_command(name="player", description="Zobrazí profil a statistiky hráče.")
async def player(ctx, hrac: Option(discord.Member, "Zobraz profil tohoto hráče (nech prázdné pro sebe)", required=False) = None):
    target_user = hrac or ctx.author
    
    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    cursor.execute("SELECT steam_id, team, bio, goals FROM players WHERE discord_id = ?", (target_user.id,))
    player_data = cursor.fetchone()
    conn.close()

    if not player_data:
        await ctx.respond(f"Hráč {target_user.mention} ještě není zaregistrován. Musí použít příkaz `/registrace`.", ephemeral=True)
        return

    steam_id, team, bio, goals = player_data
    
    embed = discord.Embed(
        title=f"Profil hráče: {target_user.display_name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    steam_name = "Neznámé"
    playtime_hours = "Neznámé"

    if STEAM_API_KEY:
        try:
            # Získání jména
            summary_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steam_id}"
            summary_response = requests.get(summary_url)
            if summary_response.status_code == 200 and summary_response.json()["response"]["players"]:
                steam_name = summary_response.json()["response"]["players"][0]["personaname"]

            # Získání herního času
            playtime_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={steam_id}&format=json"
            
            # --- DIAGNOSTICKÉ PŘÍKAZY ---
            print("=======================================")
            print(f"DEBUG: Dotazuji se na URL: {playtime_url}") # Vypíše přesnou URL, na kterou se ptáme
            
            playtime_response = requests.get(playtime_url)
            
            print(f"DEBUG: Odpověď od Steamu (surová data): {playtime_response.text}") # Vypíše přesně to, co Steam odpověděl
            print("=======================================")
            # --- KONEC DIAGNOSTIKY ---

            if playtime_response.status_code == 200:
                playtime_data = playtime_response.json().get("response", {})
                if "games" in playtime_data:
                    game_info = next((g for g in playtime_data["games"] if g["appid"] == STEAM_APP_ID), None)
                    playtime_hours = f"{round(game_info['playtime_forever'] / 60, 1)}h" if game_info else "Hru nevlastní"
                else:
                    playtime_hours = "Soukromý profil?"
        except Exception as e:
            print(f"CHYBA PŘI ZPRACOVÁNÍ STEAM DAT: {e}")
            steam_name = "Chyba API"
    else:
        steam_name = "Klíč API nenastaven"
        playtime_hours = "Klíč API nenastaven"
    
    embed.add_field(name="Steam Jméno", value=steam_name, inline=True)
    embed.add_field(name="Nahrané hodiny", value=f"{playtime_hours}", inline=True)
    embed.add_field(name="Tým", value=team or "Bez týmu", inline=False)
    embed.add_field(name="Góly", value=goals or 0, inline=True)
    embed.add_field(name="Bio", value=bio or "Žádné bio.", inline=False)
    
    await ctx.respond(embed=embed)

@bot.slash_command(name="zebricek", description="Zobrazí žebříček hráčů podle gólů.")
async def zebricek(ctx):
    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, goals FROM players ORDER BY goals DESC LIMIT 10")
    leaderboard_data = cursor.fetchall()
    conn.close()

    if not leaderboard_data:
        await ctx.respond("Zatím nejsou žádná data pro žebříček.", ephemeral=True)
        return

    embed = discord.Embed(title="🏆 Žebříček střelců 🏆", color=discord.Color.gold())
    
    description = ""
    for i, (discord_id, goals) in enumerate(leaderboard_data, 1):
        user = bot.get_user(discord_id) or await bot.fetch_user(discord_id)
        user_name = user.display_name if user else f"Uživatel {discord_id}"
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        description += f"{medals.get(i, f'**{i}.**')} {user_name} - **{goals}** gólů\n"
        
    embed.description = description
    await ctx.respond(embed=embed)


# --- ADMIN PŘÍKAZY ---
admin_group = bot.create_group("admin", "Příkazy pro správu ligy")

@admin_group.command(name="set-team", description="[ADMIN] Nastaví tým hráči.")
async def set_team(ctx, hrac: Option(discord.Member, "Hráč, kterému měníš tým", required=True), tym: Option(str, "Název týmu", required=True)):
    if not is_admin(ctx):
        await ctx.respond("K tomuto příkazu nemáš oprávnění!", ephemeral=True)
        return
        
    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET team = ? WHERE discord_id = ?", (tym, hrac.id))
    conn.commit()
    conn.close()
    await ctx.respond(f"Tým hráče {hrac.mention} byl nastaven na **{tym}**.", ephemeral=True)

@admin_group.command(name="set-bio", description="[ADMIN] Nastaví bio hráči.")
async def set_bio(ctx, hrac: Option(discord.Member, "Hráč, kterému měníš bio", required=True), text: Option(str, "Text popisu", required=True)):
    if not is_admin(ctx):
        await ctx.respond("K tomuto příkazu nemáš oprávnění!", ephemeral=True)
        return

    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET bio = ? WHERE discord_id = ?", (text, hrac.id))
    conn.commit()
    conn.close()
    await ctx.respond(f"Bio hráče {hrac.mention} bylo nastaveno.", ephemeral=True)

@admin_group.command(name="add-goly", description="[ADMIN] Přidá góly hráči.")
async def add_goly(ctx, hrac: Option(discord.Member, "Hráč, kterému přidáváš góly", required=True), pocet: Option(int, "Počet gólů k přičtení (může být i záporný)", required=True)):
    if not is_admin(ctx):
        await ctx.respond("K tomuto příkazu nemáš oprávnění!", ephemeral=True)
        return
        
    conn = sqlite3.connect('liga.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET goals = goals + ? WHERE discord_id = ?", (pocet, hrac.id))
    conn.commit()
    # Získání nového počtu gólů pro zobrazení
    cursor.execute("SELECT goals FROM players WHERE discord_id = ?", (hrac.id,))
    new_total = cursor.fetchone()[0]
    conn.close()
    await ctx.respond(f"Hráči {hrac.mention} bylo přičteno **{pocet}** gólů. Nový celkový počet: **{new_total}**.", ephemeral=True)


# --- SPUŠTĚNÍ BOTA ---
if __name__ == "__main__":
    setup_database()  # Před spuštěním bota připravíme databázi
    
    # Kontrola, zda jsou vyplněny klíče
    if DISCORD_TOKEN == "TVUJ_DISCORD_TOKEN" or STEAM_API_KEY == "TVUJ_STEAM_API_KLIC" or STEAM_APP_ID == 0:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! CHYBA: Nevyplnil jsi potřebné hodnoty v souboru config.py !!!")
        print("!!! Otevři config.py a vlož svůj Discord token, Steam API klíč a Steam App ID. !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        bot.run(DISCORD_TOKEN)