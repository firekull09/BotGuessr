import discord
from discord.ext import commands
import requests
import os
from concurrent.futures import ThreadPoolExecutor

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

all_players = []

#Ingesta de jugadores del TOP (Primeros 5000)


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
            await ctx.send("No se encontraron jugadores.")
            return

        # Si se pasa un país, filtramos
        if pais:
            pais = pais.lower()
            players = [p for p in players if p.get("countryCode", "").lower() == pais]

        if not players:
            await ctx.send(f"No se encontraron jugadores para `{pais.upper()}`.")
            return

        #msg = f"🌍 **Top 20 GeoGuessr 🏆 {'Global' if not pais else pais.upper()}**:\n"

        if pais:
            flag_code = pais.lower() if pais.lower() != "zz" else "white"
            flag_emoji = f":flag_{flag_code}:"
            pais_display = f"{flag_emoji} {pais.upper()}"
        else:
            pais_display = "🌐 GLOBAL"

        msg = f"**Ranking Overall 🏆 {pais_display}**:\n"

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
        await ctx.send("❌ Error al procesar la solicitud.")

bot.run(os.getenv("TOKEN"))
