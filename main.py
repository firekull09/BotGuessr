import discord
from discord.ext import commands
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from translations import translations


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

def t(server_id, key):
    lang = get_language(server_id) or "es"  # función que trae el idioma desde la DB
    return translations.get(lang, {}).get(key, f"[{key}]")


def set_language(server_id, lang):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO server_config (server_id, language)
        VALUES (%s, %s)
        ON CONFLICT (server_id) DO UPDATE SET language = EXCLUDED.language;
    """, (str(server_id), lang))
    conn.commit()
    cur.close()
    conn.close()

def get_language(server_id):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT language FROM server_config WHERE server_id = %s;", (str(server_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else "es"

@bot.command()
@commands.has_permissions(administrator=True)
async def setlanguage(ctx, lang: str):
    if lang not in ["es", "en"]:
        await ctx.send(t(ctx.guild.id, "AVAILABLE_LANGUAGES"))
        return

    set_language(ctx.guild.id, lang)
    await ctx.send(t(ctx.guild.id, "LANGUAGE_SET").format(lang=lang))


all_players = []

#Ingesta de jugadores del TOP (Primeros 6000)

def fetch_chunk(offset):
    url = f"https://www.geoguessr.com/api/v4/ranked-system/ratings?offset={offset}&limit=100"
    headers = {"cookie": f"_ncfa={os.getenv('NCFA_COOKIE')}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []
    return r.json()

def cargar_jugadores():
    global all_players
    all_players = []
    offsets = range(0, 6000, 100)

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_chunk, offsets)
        for chunk in results:
            if not chunk:
                break
            all_players.extend(chunk)


#Display ranking global o por pais
@bot.command()
async def rank(ctx, pais: str = None):

    global all_players
    cargar_jugadores()

    try:
        players = all_players

        if not players:
            await ctx.send(t(ctx.guild.id, "RANK_NOT_FOUND"))
            return

        # Si se pasa un país, filtramos
        if pais:
            pais = pais.lower()
            players = [p for p in players if p.get("countryCode", "").lower() == pais]

        if not players:
            await ctx.send(t(ctx.guild.id, "RANK_NO_PLAYERS").format(pais.upper()))
            return

        if pais:
            flag_code = pais.lower() if pais.lower() != "zz" else "white"
            flag_emoji = f":flag_{flag_code}:"
            pais_display = f"{flag_emoji} {pais.upper()}"
        else:
            pais_display = "🌐 GLOBAL"

        msg = f"**Ranking Overall 🏆{pais_display}**:\n"

        for i, p in enumerate(players[:20], 1):  # solo los primeros 20
            username = p.get("nick", "¿Sin nombre?")
            rating = p.get("rating", "?")
            userCountryCode = p.get("countryCode", "")
            userFlagCode = userCountryCode.lower() if userCountryCode.lower() != "zz" else "white"
            userFlag = f":flag_{userFlagCode}:" if userFlagCode else "🏳️"

            # Determinar ícono de posición
            if i == 1:
                posicion = ":first_place:"
            elif i == 2:
                posicion = ":second_place:"
            elif i == 3:
                posicion = ":third_place:"
            else:
                posicion = f"{i}."
            
            msg += f"{posicion} **{username}** {userFlag}: {rating}\n"

        await ctx.send(msg)

    except Exception as e:
        print("Error:", e)
        await ctx.send("❌ Error.")

bot.run(os.environ["TOKEN"])